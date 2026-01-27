#!/usr/bin/env python3
"""
2025年から新規所属の選手たちについて、NPB公式サイトからよみがなをスクレイピングしてreportを作成
外国人選手は英字のままでよい
"""

import csv
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

import requests
from bs4 import BeautifulSoup

# プロジェクトルートを取得
script_dir = Path(__file__).parent
project_root = script_dir.parent

# WindowsでのUnicode出力対応
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def detect_encoding(file_path: Path) -> str:
    """ファイルの文字コードを検出"""
    encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1024)
            return encoding
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return 'utf-8'


def normalize_player_name(name: str) -> str:
    """選手名を正規化（全角スペースを半角に、連続スペースを1つに）"""
    if not name:
        return ''
    normalized = name.replace('\u3000', ' ').replace('　', ' ')
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()


def load_previous_years_players(data_dir: Path, years: range = range(1950, 2025)) -> Set[str]:
    """2024年以前のデータから選手名を収集（新規選手判定用）"""
    player_set = set()
    
    search_dirs = [
        data_dir / 'master_csv_calculated',
        data_dir / 'master_csv',
        data_dir / 'master_csv__import_1950_2024',
    ]
    
    pattern = re.compile(r'batting_(\d{4})_(PL|CL)_from_master\.csv$', re.IGNORECASE)
    
    csv_files = []
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for csv_file in search_dir.rglob('*.csv'):
            if 'node_modules' in str(csv_file) or '.next' in str(csv_file):
                continue
            match = pattern.search(csv_file.name)
            if match:
                year = int(match.group(1))
                if year in years:
                    csv_files.append(csv_file)
    
    print(f"📁 2024年以前のデータから選手名を収集中... ({len(csv_files)}ファイル)")
    
    for csv_file in csv_files:
        encoding = detect_encoding(csv_file)
        try:
            with open(csv_file, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # player_name_jaを取得
                    player_name_ja = ''
                    for key in row.keys():
                        key_lower = key.lower()
                        if key_lower in ['player_name_ja', 'playername_ja', 'name_ja', '選手名', 'name']:
                            player_name_ja = str(row[key]).strip()
                            if player_name_ja and player_name_ja not in ['', 'nan', 'None', '-']:
                                normalized = normalize_player_name(player_name_ja)
                                if normalized:
                                    player_set.add(normalized)
                            break
        except Exception:
            continue
    
    print(f"✅ {len(player_set)}件の選手名を収集しました")
    return player_set


def fetch_html(url: str, timeout: Tuple[int, int] = (5, 15)) -> Tuple[Optional[str], int, Optional[str]]:
    """HTMLを取得"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        
        raw = response.content
        encodings_to_try = ['utf-8', 'cp932', 'shift_jis', 'euc-jp']
        text = None
        
        for enc in encodings_to_try:
            try:
                test_text = raw.decode(enc, errors='strict')
                if re.search(r'[あ-んア-ン一-龠]', test_text):
                    text = test_text
                    break
            except (UnicodeDecodeError, LookupError):
                continue
        
        if not text:
            text = raw.decode('utf-8', errors='replace')
        
        return text, response.status_code, None
    except requests.exceptions.Timeout:
        return None, 0, 'TIMEOUT'
    except requests.exceptions.RequestException as e:
        status_code = getattr(e.response, 'status_code', 0) if hasattr(e, 'response') else 0
        return None, status_code, 'NETWORK_ERROR'


def find_kana_from_stats_page(html: str, player_name_ja: str) -> Optional[str]:
    """成績ページのHTMLから選手名のよみがなを探す"""
    if not html or not player_name_ja:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # 成績ページのテーブルから選手名を探す
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                for i, cell in enumerate(cells):
                    cell_text = cell.get_text(strip=True)
                    # 選手名が見つかった場合
                    if player_name_ja in cell_text or cell_text in player_name_ja:
                        # 同じ行の他のセルを確認（よみがなの可能性）
                        for j, other_cell in enumerate(cells):
                            if i != j:
                                other_text = other_cell.get_text(strip=True)
                                # ひらがなのみの場合は優先
                                if re.match(r'^[あ-ん・\s]+$', other_text) and not re.search(r'[ア-ン一-龠A-Za-z]', other_text):
                                    if 2 <= len(other_text) <= 30:
                                        return other_text
                        # 次の行を確認
                        next_row = row.find_next_sibling('tr')
                        if next_row:
                            next_cells = next_row.find_all(['td', 'th'])
                            if i < len(next_cells):
                                next_text = next_cells[i].get_text(strip=True)
                                if re.match(r'^[あ-ん・\s]+$', next_text) and not re.search(r'[ア-ン一-龠A-Za-z]', next_text):
                                    if 2 <= len(next_text) <= 30:
                                        return next_text
    except Exception:
        pass
    
    return None


def search_player_on_npb_site_by_name(player_name_ja: str, team: str) -> Tuple[Optional[str], Optional[str]]:
    """
    NPB公式サイトで選手名から検索してよみがなを取得
    選手個人ページにアクセスするため、player_idを推測または検索する
    """
    # NPB公式サイトの検索機能を使用するか、または選手名からplayer_idを推測する
    # 現時点では、成績ページから直接取得を試みる
    
    # リーグを判定
    league = 'CL' if any(t in team for t in ['巨人', '阪神', 'DeNA', '横浜', '広島', '中日', 'ヤクルト']) else 'PL'
    league_code = 'c' if league == 'CL' else 'p'
    
    # 2025年の成績ページのURL
    url = f"https://npb.jp/bis/2025/stats/bat_{league_code}.html"
    
    html, status_code, error_type = fetch_html(url, timeout=(5, 15))
    
    if not html or status_code != 200:
        return None, None
    
    # 成績ページから選手名のリンクを探す（player_idを取得）
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # 選手名のリンクを探す
        player_links = soup.find_all('a', href=re.compile(r'/bis/players/\d+\.html'))
        
        for link in player_links:
            link_text = link.get_text(strip=True)
            # 選手名が一致するか確認
            if player_name_ja in link_text or link_text in player_name_ja:
                # player_idを抽出
                href = link.get('href', '')
                player_id_match = re.search(r'/bis/players/(\d+)\.html', href)
                if player_id_match:
                    player_id = player_id_match.group(1)
                    # 選手個人ページからよみがなを取得
                    return fetch_kana_from_player_page(player_id)
    except Exception:
        pass
    
    return None, None


def fetch_kana_from_player_page(player_id: str) -> Tuple[Optional[str], Optional[str]]:
    """選手個人ページからよみがなを取得"""
    url = f"https://npb.jp/bis/players/{player_id}.html"
    
    html, status_code, error_type = fetch_html(url, timeout=(5, 15))
    
    if not html or status_code != 200:
        return None, None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # id="pc_v_kana"のli要素を探す
        pc_v_kana = soup.find('li', id='pc_v_kana')
        if pc_v_kana:
            kana_text = pc_v_kana.get_text().strip()
            
            # 括弧がある場合（カタカナ + 英字の形式、またはひらがな + 英字の形式）
            if '(' in kana_text or '（' in kana_text:
                # 括弧前の部分を抽出
                match = re.search(r'^([^\(（]+)', kana_text)
                if match:
                    kana_part = match.group(1).strip()
                    # ひらがなのみの場合は優先
                    if re.match(r'^[あ-ん・\s]+$', kana_part) and not re.search(r'[ア-ン一-龠A-Za-z]', kana_part):
                        if 2 <= len(kana_part) <= 30:
                            return kana_part, None
                    # カタカナ・ひらがなが含まれている場合
                    elif re.search(r'[あ-んア-ン]', kana_part) and not re.search(r'[一-龠A-Za-z]', kana_part):
                        if 2 <= len(kana_part) <= 30:
                            return kana_part, None
            else:
                # 括弧がない場合
                # ひらがなのみ（カタカナや漢字、英字が混ざっていない）を優先
                if re.match(r'^[あ-ん・\s]+$', kana_text) and not re.search(r'[ア-ン一-龠A-Za-z]', kana_text):
                    if 2 <= len(kana_text) <= 30:
                        return kana_text, None
                # カタカナが含まれている場合も許容
                elif re.search(r'[あ-んア-ン]', kana_text) and not re.search(r'[一-龠A-Za-z]', kana_text):
                    if 2 <= len(kana_text) <= 30:
                        return kana_text, None
    except Exception:
        pass
    
    return None, None


def is_foreign_player(player_name_ja: str) -> bool:
    """外国人選手かどうかを判定（カタカナのみ、または英字が含まれている）"""
    if not player_name_ja:
        return False
    
    # カタカナのみの場合は外国人選手の可能性が高い
    if re.match(r'^[ァ-ヶ・\s]+$', player_name_ja) and not re.search(r'[あ-ん一-龠]', player_name_ja):
        return True
    
    # 英字が含まれている場合
    if re.search(r'[A-Za-z]', player_name_ja):
        return True
    
    return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description='2025年新規選手のreportを作成（NPB公式からよみがなをスクレイピング）')
    parser.add_argument('--data-dir', type=str, default=None, help='データディレクトリ（デフォルト: _data）')
    parser.add_argument('--output', type=str, default=None, help='出力CSVファイル（デフォルト: _data/reports/2025_new_players_report.csv）')
    parser.add_argument('--rate', type=float, default=1.0, help='レート制限（秒、デフォルト: 1.0）')
    args = parser.parse_args()
    
    # データディレクトリを決定
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        data_dir = project_root / '_data'
    
    if not data_dir.exists():
        print(f"❌ データディレクトリが見つかりません: {data_dir}")
        return 1
    
    # 2024年以前の選手名を収集
    print("📖 2024年以前の選手名を収集中...")
    previous_players = load_previous_years_players(data_dir)
    
    # 2025年のCSVファイルを読み込む
    print("\n📝 2025年の選手データを読み込み中...")
    pattern = re.compile(r'batting_2025_(PL|CL)_from_master\.csv$', re.IGNORECASE)
    
    csv_files = []
    search_dirs = [
        data_dir / 'master_csv_calculated',
        data_dir / 'master_csv',
    ]
    
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for csv_file in search_dir.rglob('*.csv'):
            if pattern.search(csv_file.name):
                csv_files.append(csv_file)
    
    csv_files = sorted(set(csv_files))  # 重複を除去
    print(f"   見つかったCSVファイル: {len(csv_files)}件")
    
    if not csv_files:
        print("❌ 2025年のCSVファイルが見つかりませんでした")
        return 1
    
    # 2025年の選手を収集
    new_players = []
    seen_identifiers = set()
    
    for csv_file in csv_files:
        encoding = detect_encoding(csv_file)
        try:
            with open(csv_file, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # player_name_jaを取得
                    player_name_ja = ''
                    for key in row.keys():
                        key_lower = key.lower()
                        if key_lower in ['player_name_ja', 'playername_ja', 'name_ja', '選手名', 'name']:
                            player_name_ja = str(row[key]).strip()
                            if player_name_ja in ['', 'nan', 'None', '-']:
                                player_name_ja = ''
                            break
                    
                    # teamを取得
                    team = ''
                    for key in row.keys():
                        key_lower = key.lower()
                        if key_lower in ['team', 'チーム']:
                            team = str(row[key]).strip()
                            if team in ['', 'nan', 'None', '-']:
                                team = ''
                            break
                    
                    # player_name_enを取得
                    player_name_en = ''
                    for key in row.keys():
                        key_lower = key.lower()
                        if key_lower in ['player_name_en', 'playername_en', 'name_en', 'romanname', 'roman_name']:
                            player_name_en = str(row[key]).strip()
                            if player_name_en in ['', 'nan', 'None', '-']:
                                player_name_en = ''
                            break
                    
                    if not player_name_ja:
                        continue
                    
                    # 正規化して新規選手かどうかを判定
                    normalized_name = normalize_player_name(player_name_ja)
                    if normalized_name in previous_players:
                        continue  # 既存選手はスキップ
                    
                    # 重複チェック
                    identifier = f"{normalized_name}::{team}"
                    if identifier in seen_identifiers:
                        continue
                    seen_identifiers.add(identifier)
                    
                    # 外国人選手かどうかを判定
                    is_foreign = is_foreign_player(player_name_ja)
                    
                    new_players.append({
                        'player_name_ja': player_name_ja,
                        'team': team,
                        'player_name_en': player_name_en,
                        'is_foreign': is_foreign,
                        'identifier': identifier,
                    })
        except Exception as e:
            print(f"⚠️  エラー ({csv_file.name}): {e}")
            continue
    
    print(f"✅ 2025年新規選手: {len(new_players)}件を特定しました")
    
    # NPB公式サイトからよみがなをスクレイピング
    print(f"\n📡 NPB公式サイトからよみがなをスクレイピング中...")
    
    results = []
    for i, player in enumerate(new_players, 1):
        player_name_ja = player['player_name_ja']
        team = player['team']
        is_foreign = player['is_foreign']
        
        print(f"[{i}/{len(new_players)}] {player_name_ja} ({team})...", end=' ', flush=True)
        
        # 外国人選手の場合は、英字名前をそのまま使用（よみがなは空）
        if is_foreign:
            name_kana = ''
            roman_name = player.get('player_name_en', '')
            source = 'FOREIGN_PLAYER'
            print(f"→ 外国人選手（英字: {roman_name}）")
        else:
            # 日本人選手の場合は、NPB公式サイトからよみがなを取得
            name_kana, error = search_player_on_npb_site_by_name(player_name_ja, team)
            roman_name = player.get('player_name_en', '')
            
            if name_kana:
                source = 'NPB_PLAYER_PAGE'
                print(f"→ よみがな取得: {name_kana}")
            else:
                source = 'NOT_FOUND'
                print(f"→ よみがなが見つかりませんでした")
        
        results.append({
            'player_name_ja': player_name_ja,
            'team': team,
            'name_kana': name_kana or '',
            'player_name_en': roman_name,
            'is_foreign': 'Yes' if is_foreign else 'No',
            'source': source,
        })
        
        # レート制限
        time.sleep(args.rate)
    
    # 出力パスを決定
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = project_root / '_data' / 'reports'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / '2025_new_players_report.csv'
    
    # CSVに出力
    fieldnames = ['player_name_ja', 'team', 'name_kana', 'player_name_en', 'is_foreign', 'source']
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n✅ Reportを出力しました: {output_path}")
    
    # サマリーを表示
    foreign_count = sum(1 for r in results if r['is_foreign'] == 'Yes')
    japanese_count = len(results) - foreign_count
    kana_filled = sum(1 for r in results if r['name_kana'] and r['is_foreign'] == 'No')
    
    print(f"\n📊 サマリー:")
    print(f"   総新規選手数: {len(results)}件")
    print(f"   外国人選手: {foreign_count}件")
    print(f"   日本人選手: {japanese_count}件")
    print(f"   よみがな取得成功: {kana_filled}件 ({kana_filled/japanese_count*100:.1f}% if japanese_count > 0 else 0)")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
