#!/usr/bin/env python3
"""
STEP 3: 2025年の全identifierについて、NPB公式サイトから読み仮名（かな）と英字表記（roman_official）を収集
2025年対応: player_idが空の場合は、成績ページから直接スクレイピング
"""

import csv
import re
import time
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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


def fetch_html(url: str, timeout: Tuple[int, int] = (5, 15)) -> Tuple[Optional[str], int, Optional[str]]:
    """HTMLを取得（HTTP statusも返す）"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        
        # bytesを取得
        raw = response.content
        
        # エンコーディングを自動検出（UTF-8を優先）
        encodings_to_try = ['utf-8', 'cp932', 'shift_jis', 'euc-jp']
        text = None
        
        for enc in encodings_to_try:
            try:
                test_text = raw.decode(enc, errors='strict')
                # 日本語が含まれているか確認（正しくデコードできたか）
                if re.search(r'[あ-んア-ン一-龠]', test_text):
                    text = test_text
                    break
            except (UnicodeDecodeError, LookupError):
                continue
        
        if not text:
            # すべて失敗した場合はutf-8でreplace
            try:
                text = raw.decode('utf-8', errors='replace')
            except Exception:
                return None, response.status_code, 'DECODE_FAIL'
        
        return text, response.status_code, None
    except requests.exceptions.Timeout:
        return None, 0, 'TIMEOUT'
    except requests.exceptions.RequestException as e:
        status_code = getattr(e.response, 'status_code', 0) if hasattr(e, 'response') else 0
        return None, status_code, 'NETWORK_ERROR'


def find_kana_name_from_stats_page(html: str, player_name_ja: str) -> Optional[str]:
    """
    成績ページのHTMLから選手名のひらがなを探す
    注意: 2025年の成績ページにはひらがなが含まれていない可能性が高い
    """
    if not html or not player_name_ja:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # 成績ページのテーブルから選手名を探す
        # 選手名のセルを探し、その近くにひらがながあるか確認
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                for i, cell in enumerate(cells):
                    cell_text = cell.get_text(strip=True)
                    # 選手名が見つかった場合
                    if player_name_ja in cell_text or cell_text in player_name_ja:
                        # 同じ行の他のセルを確認
                        for j, other_cell in enumerate(cells):
                            if i != j:
                                other_text = other_cell.get_text(strip=True)
                                # ひらがなのみの場合は優先
                                if re.match(r'^[あ-ん・\s]+$', other_text) and not re.search(r'[ア-ン一-龠A-Za-z]', other_text):
                                    if 2 <= len(other_text) <= 30:
                                        return other_text
                        # 次の行を確認（選手名の下にひらがながある場合）
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


def find_roman_name_from_stats_page(html: str, player_name_ja: str) -> Optional[str]:
    """
    成績ページのHTMLから選手名の英字表記を探す
    注意: 2025年の成績ページには英字表記が含まれていない可能性が高い
    """
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
                        # 同じセル内に括弧内の英字があるか確認
                        match = re.search(r'[（(]([A-Za-z\s\.\-\']+)[）)]', cell_text)
                        if match:
                            roman_name = match.group(1).strip()
                            # 組織名を除外
                            if not any(exclude in roman_name.upper() for exclude in ['NIPPON', 'PROFESSIONAL', 'BASEBALL', 'ORGANIZATION']):
                                if 2 <= len(roman_name) <= 50:
                                    # Title Caseに変換
                                    return ' '.join(word.capitalize() for word in roman_name.split())
                        # 同じ行の他のセルを確認
                        for j, other_cell in enumerate(cells):
                            if i != j:
                                other_text = other_cell.get_text(strip=True)
                                # 英字のみの場合はスペルとして扱う
                                if re.match(r'^[A-Za-z\s\.\-\']+$', other_text) and not re.search(r'[あ-んア-ン一-龠]', other_text):
                                    if 2 <= len(other_text) <= 50:
                                        # 組織名を除外
                                        if not any(exclude in other_text.upper() for exclude in ['NIPPON', 'PROFESSIONAL', 'BASEBALL', 'ORGANIZATION']):
                                            # Title Caseに変換
                                            return ' '.join(word.capitalize() for word in other_text.split())
    except Exception:
        pass
    
    return None


def scrape_from_stats_page(year: int, league: str, player_name_ja: str, team: str) -> Tuple[Optional[str], Optional[str]]:
    """
    NPB公式サイトの成績ページから選手名のひらがなと英字表記を取得
    """
    # リーグコードを取得
    league_code = 'c' if league.upper() == 'CL' else 'p'
    
    # 成績ページのURL
    url = f"https://npb.jp/bis/{year}/stats/bat_{league_code}.html"
    
    html, status_code, error_type = fetch_html(url, timeout=(5, 15))
    
    if not html or status_code != 200:
        return None, None
    
    # ひらがなを探す
    name_kana = find_kana_name_from_stats_page(html, player_name_ja)
    
    # 英字表記を探す
    roman_official = find_roman_name_from_stats_page(html, player_name_ja)
    
    return name_kana, roman_official


def load_existing_results(output_path: Path) -> set:
    """既存の結果CSVから処理済みidentifierを読み込む"""
    if not output_path.exists():
        return set()
    
    processed_identifiers = set()
    try:
        with open(output_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                identifier = row.get('identifier', '').strip()
                if identifier:
                    processed_identifiers.add(identifier)
    except Exception:
        pass
    
    return processed_identifiers


def main():
    import argparse
    parser = argparse.ArgumentParser(description='2025年の全identifierで公式かな＋（あれば）公式英字を収集')
    parser.add_argument('--ids', '--input', type=str, default=None, help='入力CSVファイル（デフォルト: output/master/all_player_ids_2025.csv）')
    parser.add_argument('--out', '--output', type=str, default=None, help='出力CSVファイル（デフォルト: output/master/player_id_name_kana_official_2025.csv）')
    parser.add_argument('--rate', '--rate-limit', type=float, default=1.0, help='レート制限（秒、デフォルト: 1.0）')
    parser.add_argument('--resume', action='store_true', default=True, help='既存の結果を読み込んで続きから実行（デフォルト: True）')
    parser.add_argument('--no-resume', action='store_true', help='resumeを無効化')
    parser.add_argument('--limit', type=int, default=None, help='処理件数の上限（デバッグ用）')
    args = parser.parse_args()
    
    # 入力パスを決定
    if args.ids:
        input_path = Path(args.ids)
    else:
        input_path = project_root / 'output' / 'master' / 'all_player_ids_2025.csv'
    
    if not input_path.exists():
        print(f"❌ 入力ファイルが見つかりません: {input_path}")
        return 1
    
    # 出力パスを決定
    if args.out:
        output_path = Path(args.out)
    else:
        output_path = project_root / 'output' / 'master' / 'player_id_name_kana_official_2025.csv'
    
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # オプション処理
    resume = args.resume and not args.no_resume
    
    # identifierを読み込む
    identifiers = []
    with open(input_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            identifier = row.get('identifier', '').strip()
            player_id = row.get('player_id', '').strip()
            player_name_ja = row.get('player_name_ja', '').strip()
            team = row.get('team', '').strip()
            
            if identifier:
                identifiers.append({
                    'identifier': identifier,
                    'player_id': player_id,
                    'player_name_ja': player_name_ja,
                    'team': team,
                })
    
    # limitオプション
    if args.limit:
        identifiers = identifiers[:args.limit]
    
    print(f"✅ {len(identifiers)}件のidentifierを読み込みました")
    
    # 既存の結果を読み込む（resumeオプション）
    processed_identifiers = set()
    if resume:
        processed_identifiers = load_existing_results(output_path)
        print(f"📋 既存の結果から {len(processed_identifiers)}件のidentifierをスキップします")
    
    # 未処理のidentifierをフィルタ
    remaining_identifiers = [ident for ident in identifiers if ident['identifier'] not in processed_identifiers]
    print(f"🔍 処理対象: {len(remaining_identifiers)}件")
    
    if not remaining_identifiers:
        print("✅ すべてのidentifierが処理済みです")
        return 0
    
    # 結果を追記モードで開く
    file_exists = output_path.exists()
    with open(output_path, 'a', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['identifier', 'player_id', 'player_name_ja', 'team', 'name_kana', 'roman_official', 'url_used', 'http_status', 'outcome'])
        
        if not file_exists:
            writer.writeheader()
        
        # 統計
        ok_count = 0
        fail_count = 0
        
        # 各identifierを処理
        for i, ident in enumerate(remaining_identifiers, 1):
            identifier = ident['identifier']
            player_id = ident.get('player_id', '')
            player_name_ja = ident.get('player_name_ja', '')
            team = ident.get('team', '')
            
            # リーグを判定（チーム名から）
            league = 'CL' if any(t in team for t in ['巨人', '阪神', 'DeNA', '横浜', '広島', '中日', 'ヤクルト']) else 'PL'
            
            try:
                # 成績ページからスクレイピング
                name_kana, roman_official = scrape_from_stats_page(2025, league, player_name_ja, team)
                
                # outcome分類
                if roman_official and name_kana:
                    outcome = "OK"
                elif roman_official:
                    outcome = "OK"
                elif name_kana:
                    outcome = "OK"
                else:
                    outcome = "NO_DATA"
                
                result = {
                    'identifier': identifier,
                    'player_id': player_id,
                    'player_name_ja': player_name_ja,
                    'team': team,
                    'name_kana': name_kana or '',
                    'roman_official': roman_official or '',
                    'url_used': f"https://npb.jp/bis/2025/stats/bat_{'c' if league == 'CL' else 'p'}.html",
                    'http_status': 200,
                    'outcome': outcome,
                }
                writer.writerow(result)
                f.flush()  # 即座に書き込み
                
                # 統計更新
                if result['outcome'] == 'OK':
                    ok_count += 1
                else:
                    fail_count += 1
                
                # 進捗表示（10件ごと）
                if i % 10 == 0 or i == len(remaining_identifiers):
                    print(f"[{i}/{len(remaining_identifiers)}] processed: {i}, OK: {ok_count}, FAIL: {fail_count}")
            except KeyboardInterrupt:
                print(f"\n⚠️  中断されました。{i-1}件まで処理済み。--resume で続きから実行できます。")
                return 1
            except Exception as e:
                # 予期しないエラーも記録
                result = {
                    'identifier': identifier,
                    'player_id': player_id,
                    'player_name_ja': player_name_ja,
                    'team': team,
                    'name_kana': '',
                    'roman_official': '',
                    'url_used': '',
                    'http_status': 0,
                    'outcome': 'UNKNOWN',
                }
                writer.writerow(result)
                f.flush()
                fail_count += 1
                print(f"⚠️  予期しないエラー ({identifier}): {e}")
            
            # レート制限
            time.sleep(args.rate)
    
    print(f"\n✅ 結果を出力しました: {output_path}")
    
    # 最終サマリーを表示
    with open(output_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        results = list(reader)
    
    outcome_counts = {}
    name_kana_filled = 0
    roman_official_filled = 0
    
    for result in results:
        outcome = result['outcome']
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        
        if result.get('name_kana', '').strip():
            name_kana_filled += 1
        if result.get('roman_official', '').strip():
            roman_official_filled += 1
    
    print(f"\n📊 最終サマリー:")
    print(f"   総identifier数: {len(results)}件")
    print(f"   name_kana 非空率: {name_kana_filled}件 ({name_kana_filled/len(results)*100:.1f}%)")
    print(f"   roman_official 非空率: {roman_official_filled}件 ({roman_official_filled/len(results)*100:.1f}%)")
    print(f"   outcome別件数:")
    for outcome, count in sorted(outcome_counts.items()):
        percentage = (count / len(results)) * 100
        print(f"      {outcome}: {count}件 ({percentage:.1f}%)")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
