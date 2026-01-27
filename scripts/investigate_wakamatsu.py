#!/usr/bin/env python3
"""
若松勉が存在しない原因を調査する
"""
import csv
import sys
from pathlib import Path
import re

# プロジェクトルート
script_dir = Path(__file__).parent
project_root = script_dir.parent

def search_in_csv(csv_path: Path, search_term: str, column_name: str = None) -> list:
    """CSVファイルから検索"""
    if not csv_path.exists():
        return []
    
    results = []
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if column_name:
                    if search_term in str(row.get(column_name, '')):
                        results.append(row)
                else:
                    # 全カラムを検索
                    for key, value in row.items():
                        if search_term in str(value):
                            results.append(row)
                            break
    except Exception as e:
        print(f"❌ エラー ({csv_path}): {e}", file=sys.stderr)
    
    return results

def search_in_html_cache(player_id: str) -> dict:
    """HTMLキャッシュを検索"""
    html_cache_dir = project_root / 'output' / 'html_cache' / 'players'
    html_path = html_cache_dir / f"{player_id}.html"
    
    result = {
        'exists': False,
        'content': None,
        'has_name': False
    }
    
    if html_path.exists():
        result['exists'] = True
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
                result['content'] = content
                if '若松' in content or '勉' in content:
                    result['has_name'] = True
        except Exception as e:
            print(f"❌ HTML読み込みエラー: {e}", file=sys.stderr)
    
    return result

def main():
    print("\n" + "="*60)
    print("=== 若松勉が存在しない原因調査 ===")
    print("="*60 + "\n")
    
    # 1. 全CSVファイルから「若松」を検索
    print("📖 ステップ1: 全CSVファイルから「若松」を検索中...")
    
    search_dirs = [
        project_root / '_data' / 'master_csv',
        project_root / '_data' / 'master_csv_calculated',
        project_root / 'output' / 'master',
    ]
    
    found_in_csvs = []
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        
        for csv_file in search_dir.rglob('*.csv'):
            if 'node_modules' in str(csv_file):
                continue
            
            results = search_in_csv(csv_file, '若松')
            if results:
                found_in_csvs.append({
                    'file': csv_file,
                    'results': results
                })
    
    if found_in_csvs:
        print(f"  ✅ {len(found_in_csvs)}個のCSVファイルで「若松」を発見")
        for item in found_in_csvs[:5]:  # 最初の5件
            print(f"    - {item['file'].name}: {len(item['results'])}件")
            for result in item['results'][:3]:
                player_id = result.get('player_id', 'N/A')
                name_ja = result.get('player_name_ja', result.get('name_ja', 'N/A'))
                print(f"      player_id: {player_id}, name: {name_ja}")
    else:
        print("  ❌ CSVファイルで「若松」が見つかりませんでした")
    
    # 2. player_id_name_kana_official.csvを確認
    print("\n📖 ステップ2: player_id_name_kana_official.csv を確認中...")
    official_csv = project_root / 'output' / 'master' / 'player_id_name_kana_official.csv'
    wakamatsu_results = search_in_csv(official_csv, '若松', 'name_ja')
    
    if wakamatsu_results:
        print(f"  ✅ {len(wakamatsu_results)}件の「若松」を発見")
        for result in wakamatsu_results[:10]:
            player_id = result.get('player_id', 'N/A')
            name_ja = result.get('name_ja', 'N/A')
            name_kana = result.get('name_kana', 'N/A')
            http_status = result.get('http_status', 'N/A')
            outcome = result.get('outcome', 'N/A')
            print(f"    player_id: {player_id}")
            print(f"      name_ja: {name_ja}")
            print(f"      name_kana: {name_kana}")
            print(f"      http_status: {http_status}, outcome: {outcome}")
            
            # 「勉」が含まれているか確認
            if '勉' in name_ja or '勉' in name_kana:
                print(f"      ⭐ 「勉」を含む行を発見！")
                # HTMLキャッシュを確認
                html_info = search_in_html_cache(player_id)
                if html_info['exists']:
                    print(f"      HTMLキャッシュ: 存在する")
                    if html_info['has_name']:
                        print(f"      HTMLに名前が含まれている")
                else:
                    print(f"      HTMLキャッシュ: 存在しない")
    else:
        print("  ❌ player_id_name_kana_official.csv で「若松」が見つかりませんでした")
    
    # 3. player_id_to_roman_full.csvを確認
    print("\n📖 ステップ3: player_id_to_roman_full.csv を確認中...")
    roman_csv = project_root / 'output' / 'master' / 'player_id_to_roman_full.csv'
    roman_results = search_in_csv(roman_csv, '若松', 'name_ja')
    
    if roman_results:
        print(f"  ✅ {len(roman_results)}件の「若松」を発見")
        for result in roman_results[:5]:
            player_id = result.get('player_id', 'N/A')
            name_ja = result.get('name_ja', 'N/A')
            roman_name = result.get('romanName', 'N/A')
            print(f"    player_id: {player_id}, name_ja: {name_ja}, romanName: {roman_name}")
    else:
        print("  ❌ player_id_to_roman_full.csv で「若松」が見つかりませんでした")
    
    # 4. 年度別CSVを確認（1970-1989年）
    print("\n📖 ステップ4: 年度別CSV（1970-1989年）を確認中...")
    years_to_check = list(range(1970, 1990))
    found_in_years = []
    
    for year in years_to_check:
        for league in ['PL', 'CL']:
            csv_path = project_root / '_data' / 'master_csv_calculated' / f'batting_{year}_{league}_from_master.csv'
            if csv_path.exists():
                results = search_in_csv(csv_path, '若松', 'player_name_ja')
                if results:
                    found_in_years.append({
                        'year': year,
                        'league': league,
                        'results': results
                    })
    
    if found_in_years:
        print(f"  ✅ {len(found_in_years)}年度で「若松」を発見")
        for item in found_in_years:
            print(f"    {item['year']}年 {item['league']}リーグ:")
            for result in item['results'][:3]:
                player_id = result.get('player_id', 'N/A')
                name_ja = result.get('player_name_ja', 'N/A')
                team = result.get('team', 'N/A')
                print(f"      player_id: {player_id}, name: {name_ja}, team: {team}")
    else:
        print("  ❌ 年度別CSVで「若松」が見つかりませんでした")
    
    # 5. まとめ
    print("\n" + "="*60)
    print("=== 調査結果サマリー ===")
    print("="*60 + "\n")
    
    if not found_in_csvs and not wakamatsu_results and not roman_results and not found_in_years:
        print("❌ 「若松勉」は全データソースで見つかりませんでした")
        print("\n考えられる原因:")
        print("  1. スクレイピング対象に含まれていない（OB選手のため）")
        print("  2. 年度範囲が若松氏の現役時代（1971-1989年）をカバーしていない")
        print("  3. HTML取得に失敗している")
        print("  4. 名前の表記が異なる（空白文字、旧字体など）")
    else:
        print("✅ 「若松」を含むデータが見つかりました")
        print("  詳細は上記を確認してください")

if __name__ == '__main__':
    main()




