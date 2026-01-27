#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fact_check_external_source.py

NPB公式サイトなどの外部データソースから選手リストを取得し、
自分のCSVファイルと比較して、抜けている選手を特定するスクリプト
"""

import sys
import io
import csv
import re
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
import json

# WindowsでのUnicode出力対応
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ エラー: requests または beautifulsoup4 がインストールされていません")
    print("   インストール方法: pip install requests beautifulsoup4")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("❌ エラー: pandasがインストールされていません")
    print("   インストール方法: pip install pandas")
    sys.exit(1)

# プロジェクトルートを取得
script_dir = Path(__file__).parent
project_root = script_dir.parent


def fetch_html(url: str, timeout: Tuple[int, int] = (10, 30)) -> Tuple[Optional[str], int, Optional[str]]:
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


def get_npb_batting_url(year: int, league: str) -> str:
    """NPB公式サイトの打撃成績ページのURLを生成"""
    league_lower = league.lower()
    # NPB公式サイトのURL構造（例: https://npb.jp/bis/stats/2025/pl/batting.html）
    base_url = "https://npb.jp/bis/stats"
    return f"{base_url}/{year}/{league_lower}/batting.html"


def extract_players_from_npb_html(html: str, year: int, league: str) -> List[Dict[str, str]]:
    """
    NPB公式サイトのHTMLから選手リストを抽出
    
    Returns:
        List[Dict]: 選手情報のリスト [{'name': '選手名', 'team': 'チーム名', 'player_id': 'ID'}, ...]
    """
    players = []
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # テーブルを探す（NPB公式サイトの構造に応じて調整が必要）
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:
                    continue
                
                # 選手名を探す（リンクがある場合）
                name_link = row.find('a', href=re.compile(r'/bis/players/'))
                if name_link:
                    player_name = name_link.get_text().strip()
                    href = name_link.get('href', '')
                    
                    # player_idを抽出
                    player_id_match = re.search(r'/bis/players/(\d+)', href)
                    player_id = player_id_match.group(1) if player_id_match else ''
                    
                    # チーム名を探す（テーブルの構造に応じて調整）
                    team = ''
                    for cell in cells:
                        cell_text = cell.get_text().strip()
                        # チーム名のパターン（例: 巨人、阪神、など）
                        if cell_text and len(cell_text) < 20 and not cell_text.isdigit():
                            # 数値でない短い文字列をチーム名候補とする
                            if not re.match(r'^\d+\.?\d*$', cell_text):
                                team = cell_text
                                break
                    
                    if player_name:
                        players.append({
                            'name': player_name,
                            'team': team,
                            'player_id': player_id,
                            'source': 'NPB_OFFICIAL'
                        })
        
        # 重複を除去（player_idで）
        seen_ids = set()
        unique_players = []
        for player in players:
            if player['player_id'] and player['player_id'] not in seen_ids:
                seen_ids.add(player['player_id'])
                unique_players.append(player)
            elif not player['player_id'] and player['name'] not in [p['name'] for p in unique_players]:
                unique_players.append(player)
        
        return unique_players
        
    except Exception as e:
        print(f"⚠️ HTML解析エラー: {e}")
        return []


def get_players_from_npb_official(year: int, league: str) -> List[Dict[str, str]]:
    """NPB公式サイトから選手リストを取得"""
    url = get_npb_batting_url(year, league)
    print(f"📡 NPB公式サイトから選手リストを取得中: {url}")
    
    html, status_code, error = fetch_html(url)
    
    if error or not html:
        print(f"❌ エラー: HTMLの取得に失敗しました (status: {status_code}, error: {error})")
        return []
    
    if status_code != 200:
        print(f"⚠️ HTTPステータス: {status_code}")
        return []
    
    players = extract_players_from_npb_html(html, year, league)
    print(f"✅ {len(players)}人の選手を取得しました")
    
    return players


def load_csv_players(csv_path: Path) -> List[Dict[str, str]]:
    """CSVファイルから選手リストを読み込む"""
    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return []
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        
        # 選手名カラムを探す
        name_col = None
        for col in df.columns:
            if 'name' in col.lower() and 'ja' in col.lower():
                name_col = col
                break
            elif 'name' in col.lower():
                name_col = col
                break
        
        if not name_col:
            print("⚠️ 選手名カラムが見つかりません")
            return []
        
        # チーム名カラムを探す
        team_col = None
        for col in df.columns:
            if 'team' in col.lower():
                team_col = col
                break
        
        # player_idカラムを探す
        player_id_col = None
        for col in df.columns:
            if 'player_id' in col.lower():
                player_id_col = col
                break
        
        players = []
        for _, row in df.iterrows():
            name = str(row.get(name_col, '')).strip()
            if not name or name == 'nan':
                continue
            
            player = {
                'name': name,
                'team': str(row.get(team_col, '')).strip() if team_col else '',
                'player_id': str(row.get(player_id_col, '')).strip() if player_id_col else '',
                'source': 'CSV'
            }
            players.append(player)
        
        return players
        
    except Exception as e:
        print(f"❌ CSV読み込みエラー: {e}")
        return []


def normalize_name(name: str) -> str:
    """選手名を正規化（比較用）"""
    if not name:
        return ''
    # 全角スペース、半角スペース、・などを統一
    name = re.sub(r'[　\s・]+', '', name)
    # 全角英数字を半角に変換（必要に応じて）
    return name.strip()


def compare_players(external_players: List[Dict], csv_players: List[Dict], 
                   all_player_ids: Set[str] = None, fetch_failed: List[Dict] = None) -> Dict:
    """
    外部データソースとCSVの選手を比較
    
    Args:
        external_players: 外部データソースから取得できた選手
        csv_players: CSVファイルから読み込んだ選手
        all_player_ids: 全player_idリスト（基準となるリスト）
        fetch_failed: 取得に失敗した年度・リーグのリスト
    """
    result = {
        'external_count': len(external_players),
        'csv_count': len(csv_players),
        'missing_in_csv': [],
        'extra_in_csv': [],
        'matched': [],
        'failed_to_fetch': [],  # CSVにあるが取得できなかった選手
        'fetch_failed_count': len(fetch_failed) if fetch_failed else 0
    }
    
    # 名前で正規化して比較
    external_names = {normalize_name(p['name']): p for p in external_players}
    external_ids = {p.get('player_id', ''): p for p in external_players if p.get('player_id')}
    
    csv_names = {normalize_name(p['name']): p for p in csv_players}
    csv_ids = {p.get('player_id', ''): p for p in csv_players if p.get('player_id')}
    
    # CSVに存在しない選手（取得できた選手のうち）
    for norm_name, player in external_names.items():
        if norm_name not in csv_names:
            result['missing_in_csv'].append(player)
        else:
            result['matched'].append({
                'external': player,
                'csv': csv_names[norm_name]
            })
    
    # CSVにのみ存在する選手を分類
    for norm_name, player in csv_names.items():
        if norm_name not in external_names:
            player_id = player.get('player_id', '')
            
            # player_idがある場合、取得できなかった可能性をチェック
            if player_id and all_player_ids:
                # 全player_idリストに存在するが、取得できなかった場合
                if player_id in all_player_ids and player_id not in external_ids:
                    result['failed_to_fetch'].append({
                        'player': player,
                        'reason': 'NOT_FETCHED_FROM_NPB',
                        'note': '全player_idリストには存在するが、NPB公式サイトから取得できなかった'
                    })
                else:
                    result['extra_in_csv'].append(player)
            else:
                result['extra_in_csv'].append(player)
    
    return result


def main():
    if len(sys.argv) < 3:
        print("使用方法: python fact_check_external_source.py <YEAR> <LEAGUE> [CSV_PATH]")
        print("例: python fact_check_external_source.py 2025 PL")
        print("例: python fact_check_external_source.py 2025 PL _data/master_csv_calculated/batting_2025_PL_from_master.csv")
        sys.exit(1)
    
    year = int(sys.argv[1])
    league = sys.argv[2].upper()
    
    # CSVパスを決定
    if len(sys.argv) > 3:
        csv_path = Path(sys.argv[3])
    else:
        csv_path = project_root / '_data' / 'master_csv_calculated' / f'batting_{year}_{league}_from_master.csv'
    
    print(f"\n{'='*60}")
    print(f"=== 外部データソースとのファクトチェック ===")
    print(f"{'='*60}\n")
    print(f"年度: {year}")
    print(f"リーグ: {league}")
    print(f"CSVファイル: {csv_path}\n")
    
    # 全player_idリストを読み込む（基準となるリスト）
    print("📖 全player_idリストを読み込み中...")
    all_player_ids_path = project_root / 'output' / 'master' / 'all_player_ids.csv'
    all_player_ids = set()
    if all_player_ids_path.exists():
        try:
            with open(all_player_ids_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    player_id = row.get('player_id', '').strip()
                    if player_id:
                        all_player_ids.add(player_id)
            print(f"✅ {len(all_player_ids)}件のplayer_idを読み込みました")
        except Exception as e:
            print(f"⚠️ player_idリストの読み込みエラー: {e}")
    else:
        print("⚠️ player_idリストが見つかりません（取得失敗の判定ができません）")
    
    # 外部データソースから選手リストを取得
    fetch_failed = []
    external_players = get_players_from_npb_official(year, league)
    
    if not external_players:
        print("⚠️ 外部データソースから選手を取得できませんでした")
        fetch_failed.append({
            'year': year,
            'league': league,
            'reason': 'FETCH_FAILED',
            'note': 'NPB公式サイトから選手を取得できなかった'
        })
        print("   手動で確認するか、別のデータソースを使用してください")
        # 取得失敗でも続行（CSVのみの情報を表示）
    
    # CSVから選手リストを読み込む
    print(f"\n📖 CSVファイルから選手リストを読み込み中...")
    csv_players = load_csv_players(csv_path)
    print(f"✅ {len(csv_players)}人の選手を読み込みました\n")
    
    # 比較
    print("🔍 選手リストを比較中...\n")
    comparison = compare_players(external_players, csv_players, all_player_ids, fetch_failed)
    
    # 結果を表示
    print(f"{'='*60}")
    print(f"=== 比較結果 ===")
    print(f"{'='*60}\n")
    print(f"外部データソース（取得成功）: {comparison['external_count']}人")
    print(f"取得失敗した年度・リーグ: {comparison['fetch_failed_count']}件")
    print(f"CSVファイル: {comparison['csv_count']}人")
    print(f"一致: {len(comparison['matched'])}人")
    print(f"CSVに不足（取得できたがCSVにない）: {len(comparison['missing_in_csv'])}人")
    print(f"CSVにのみ存在: {len(comparison['extra_in_csv'])}人")
    print(f"CSVにあるが取得できなかった: {len(comparison['failed_to_fetch'])}人\n")
    
    # 重要な警告
    if comparison['fetch_failed_count'] > 0 or len(comparison['failed_to_fetch']) > 0:
        print(f"{'='*60}")
        print(f"⚠️ 重要な注意事項")
        print(f"{'='*60}\n")
        print(f"取得できなかった選手が {len(comparison['failed_to_fetch'])}人存在します。")
        print(f"これらの選手は、NPB公式サイトから取得できませんでしたが、")
        print(f"CSVには存在するため、取得方法を確認する必要があります。\n")
        print(f"「CSVに不足」と表示された選手のうち、")
        print(f"実際には取得できなかっただけの可能性があります。\n")
    
    # 不足している選手を表示
    if comparison['missing_in_csv']:
        print(f"⚠️ CSVに存在しない選手（取得できたがCSVにない） ({len(comparison['missing_in_csv'])}人):\n")
        for i, player in enumerate(comparison['missing_in_csv'][:30], 1):
            print(f"  {i:3d}. {player['name']:20s} ({player.get('team', 'N/A'):15s}, ID: {player.get('player_id', 'N/A')})")
        if len(comparison['missing_in_csv']) > 30:
            print(f"  ... 他 {len(comparison['missing_in_csv']) - 30}件")
        
        # CSV形式で保存
        output_dir = project_root / 'output' / 'reports' / 'fact_check'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f'missing_players_{year}_{league}_external.csv'
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'team', 'player_id', 'source'])
            writer.writeheader()
            writer.writerows(comparison['missing_in_csv'])
        
        print(f"\n✅ 不足している選手をCSV形式で保存しました: {output_file}")
    else:
        print("✅ 取得できたすべての選手がCSVファイルに含まれています\n")
    
    # CSVにあるが取得できなかった選手を表示
    if comparison['failed_to_fetch']:
        print(f"⚠️ CSVにあるが取得できなかった選手 ({len(comparison['failed_to_fetch'])}人):\n")
        print(f"  これらの選手は、NPB公式サイトから取得できませんでしたが、")
        print(f"  CSVには存在するため、取得方法を確認する必要があります。\n")
        for i, item in enumerate(comparison['failed_to_fetch'][:30], 1):
            player = item['player']
            print(f"  {i:3d}. {player.get('player_id', 'N/A'):10s} - {player.get('name', 'N/A'):20s} ({item.get('note', '')})")
        if len(comparison['failed_to_fetch']) > 30:
            print(f"  ... 他 {len(comparison['failed_to_fetch']) - 30}件")
        
        # CSV形式で保存
        output_dir = project_root / 'output' / 'reports' / 'fact_check'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f'failed_to_fetch_{year}_{league}_external.csv'
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['player_id', 'name', 'team', 'reason', 'note'])
            writer.writeheader()
            for item in comparison['failed_to_fetch']:
                player = item['player']
                writer.writerow({
                    'player_id': player.get('player_id', ''),
                    'name': player.get('name', ''),
                    'team': player.get('team', ''),
                    'reason': item.get('reason', ''),
                    'note': item.get('note', '')
                })
        
        print(f"\n✅ 取得できなかった選手をCSV形式で保存しました: {output_file}\n")
    
    # 結果をJSON形式で保存
    output_dir = project_root / 'output' / 'reports' / 'fact_check'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    result_json = {
        'year': year,
        'league': league,
        'check_date': datetime.now().isoformat(),
        'external_count': comparison['external_count'],
        'fetch_failed_count': comparison['fetch_failed_count'],
        'csv_count': comparison['csv_count'],
        'matched_count': len(comparison['matched']),
        'missing_in_csv': comparison['missing_in_csv'],
        'extra_in_csv': comparison['extra_in_csv'],
        'failed_to_fetch': comparison['failed_to_fetch'],
        'warnings': []
    }
    
    # 警告を追加
    if comparison['fetch_failed_count'] > 0:
        result_json['warnings'].append('NPB公式サイトから選手を取得できなかった年度・リーグがあります')
    if len(comparison['failed_to_fetch']) > 0:
        result_json['warnings'].append(f'CSVにあるが取得できなかった選手が{len(comparison["failed_to_fetch"])}人存在します')
    
    json_file = output_dir / f'fact_check_{year}_{league}_external.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result_json, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 結果をJSON形式で保存しました: {json_file}\n")
    
    if comparison['missing_in_csv']:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()

