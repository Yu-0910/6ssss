#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fact_check_compare_simple.py

スクレイピングデータと現在のデータを比較（簡易版）
"""

import csv
import sys
import io
from pathlib import Path
from datetime import datetime
import json

# WindowsでのUnicode出力対応
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def load_csv(filename):
    """CSVファイルを読み込む"""
    try:
        with open(filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"❌ エラー: {filename} の読み込みに失敗しました: {e}")
        return None

def find_column(rows, keywords):
    """キーワードに一致するカラムを探す"""
    if not rows:
        return None
    for col in rows[0].keys():
        col_lower = col.lower()
        for keyword in keywords:
            if keyword in col_lower:
                return col
    return None

def compare_scraped_vs_current(year, league, output_dir=None):
    """スクレイピングデータと現在のデータを比較"""
    
    scraped_path = Path(f'_data/master_csv__import_1950_2024/batting_{year}_{league}_from_master.csv')
    current_path = Path(f'_data/master_csv_calculated/batting_{year}_{league}_from_master.csv')
    
    result = {
        'year': year,
        'league': league,
        'check_date': datetime.now().isoformat(),
        'scraped_exists': scraped_path.exists(),
        'current_exists': current_path.exists(),
        'scraped_count': 0,
        'current_count': 0,
        'missing_players': [],
        'team_comparison': {},
        'errors': []
    }
    
    if not scraped_path.exists():
        error_msg = f"⚠️ スクレイピングデータが見つかりません: {scraped_path}"
        print(error_msg)
        result['errors'].append(error_msg)
        return result
    
    if not current_path.exists():
        error_msg = f"⚠️ 現在のデータが見つかりません: {current_path}"
        print(error_msg)
        result['errors'].append(error_msg)
        return result
    
    # CSVを読み込む
    rows_scraped = load_csv(str(scraped_path))
    rows_current = load_csv(str(current_path))
    
    if rows_scraped is None or rows_current is None:
        return result
    
    result['scraped_count'] = len(rows_scraped)
    result['current_count'] = len(rows_current)
    
    print(f"\n{'='*60}")
    print(f"=== {year}年{league}リーグ データ比較 ===")
    print(f"{'='*60}\n")
    print(f"スクレイピングデータ: {len(rows_scraped)}件")
    print(f"現在のデータ: {len(rows_current)}件")
    print(f"差分: {len(rows_scraped) - len(rows_current)}件\n")
    
    # 選手名カラムを探す
    name_col_scraped = find_column(rows_scraped, ['name', '選手'])
    name_col_current = find_column(rows_current, ['name', '選手'])
    
    if not name_col_scraped or not name_col_current:
        error_msg = "⚠️ 選手名カラムが見つかりません"
        print(error_msg)
        result['errors'].append(error_msg)
        return result
    
    print(f"スクレイピングデータの選手名カラム: {name_col_scraped}")
    print(f"現在のデータの選手名カラム: {name_col_current}\n")
    
    # チーム名カラムを探す
    team_col_scraped = find_column(rows_scraped, ['team', 'チーム'])
    team_col_current = find_column(rows_current, ['team', 'チーム'])
    
    # PAカラムを探す
    pa_col_scraped = find_column(rows_scraped, ['pa'])
    pa_col_current = find_column(rows_current, ['pa'])
    
    # 選手名のセットを作成
    scraped_names = set()
    for row in rows_scraped:
        name = row.get(name_col_scraped, '').strip()
        if name:
            scraped_names.add(name)
    
    current_names = set()
    for row in rows_current:
        name = row.get(name_col_current, '').strip()
        if name:
            current_names.add(name)
    
    missing_names = scraped_names - current_names
    
    if missing_names:
        print(f"⚠️ 現在のデータに存在しない選手: {len(missing_names)}件\n")
        print("抜けている選手:")
        
        missing_players_list = []
        for i, name in enumerate(sorted(missing_names), 1):
            # 該当選手の情報を取得
            player_info = {'name': name, 'team': 'N/A', 'pa': 'N/A'}
            
            for row in rows_scraped:
                if row.get(name_col_scraped, '').strip() == name:
                    if team_col_scraped:
                        player_info['team'] = row.get(team_col_scraped, 'N/A')
                    if pa_col_scraped:
                        pa_val = row.get(pa_col_scraped, 'N/A')
                        try:
                            player_info['pa'] = int(float(pa_val)) if pa_val else 'N/A'
                        except:
                            player_info['pa'] = pa_val
                    break
            
            missing_players_list.append(player_info)
            print(f"  {i:3d}. {name:20s} ({player_info['team']:15s}, PA={player_info['pa']})")
        
        result['missing_players'] = missing_players_list
    else:
        print("✅ すべての選手が現在のデータに含まれています\n")
    
    # チーム別選手数の比較
    if team_col_scraped and team_col_current:
        print("=== チーム別選手数比較 ===\n")
        
        scraped_teams = {}
        for row in rows_scraped:
            team = row.get(team_col_scraped, '').strip()
            if team:
                scraped_teams[team] = scraped_teams.get(team, 0) + 1
        
        current_teams = {}
        for row in rows_current:
            team = row.get(team_col_current, '').strip()
            if team:
                current_teams[team] = current_teams.get(team, 0) + 1
        
        print("スクレイピングデータ:")
        for team in sorted(scraped_teams.keys()):
            print(f"  {team}: {scraped_teams[team]}件")
        
        print("\n現在のデータ:")
        for team in sorted(current_teams.keys()):
            print(f"  {team}: {current_teams[team]}件")
        
        print("\nチーム別差分:")
        team_comparison = {}
        all_teams = set(list(scraped_teams.keys()) + list(current_teams.keys()))
        for team in sorted(all_teams):
            scraped_count = scraped_teams.get(team, 0)
            current_count = current_teams.get(team, 0)
            diff = scraped_count - current_count
            
            team_comparison[team] = {
                'scraped': scraped_count,
                'current': current_count,
                'diff': diff
            }
            
            if diff != 0:
                print(f"  {team}: {scraped_count} → {current_count} (差分: {diff:+d})")
        
        result['team_comparison'] = team_comparison
    
    # 結果をファイルに保存
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f'fact_check_{year}_{league}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 結果を保存しました: {output_file}")
        
        # CSV形式でも保存（抜けている選手のみ）
        if missing_players_list:
            csv_file = output_dir / f'missing_players_{year}_{league}.csv'
            with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['name', 'team', 'pa'])
                writer.writeheader()
                writer.writerows(missing_players_list)
            print(f"✅ 抜けている選手をCSV形式で保存しました: {csv_file}")
    
    return result

def main():
    if len(sys.argv) < 3:
        print("使用方法: python fact_check_compare_simple.py <YEAR> <LEAGUE> [OUTPUT_DIR]")
        print("例: python fact_check_compare_simple.py 2024 PL")
        print("例: python fact_check_compare_simple.py 2024 PL output/reports/fact_check")
        sys.exit(1)
    
    year = int(sys.argv[1])
    league = sys.argv[2].upper()
    output_dir = sys.argv[3] if len(sys.argv) > 3 else 'output/reports/fact_check'
    
    result = compare_scraped_vs_current(year, league, output_dir)
    
    if result['errors']:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()






