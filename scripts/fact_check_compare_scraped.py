#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fact_check_compare_scraped.py

スクレイピングデータと現在のデータを比較し、抜けている選手を特定するスクリプト
"""

import sys
import io
from pathlib import Path
from datetime import datetime
import json

# WindowsでのUnicode出力対応
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import pandas as pd
except ImportError:
    print("❌ エラー: pandasがインストールされていません")
    print("   インストール方法: pip install pandas")
    sys.exit(1)

def find_name_column(df):
    """選手名カラムを探す"""
    for col in df.columns:
        if 'name' in col.lower() or '選手' in col:
            return col
    return None

def find_team_column(df):
    """チーム名カラムを探す"""
    for col in df.columns:
        if 'team' in col.lower() or 'チーム' in col:
            return col
    return None

def find_pa_column(df):
    """打席数カラムを探す"""
    for col in df.columns:
        if col.upper() == 'PA' or col == '打席':
            return col
    return None

def compare_scraped_vs_current(year, league, output_dir=None):
    """
    スクレイピングデータと現在のデータを比較
    
    Args:
        year: 年度
        league: リーグ（PL/CL）
        output_dir: 出力ディレクトリ（Noneの場合は結果を表示のみ）
    """
    # スクレイピングデータ（参照用）
    scraped_path = Path(f'_data/master_csv__import_1950_2024/batting_{year}_{league}_from_master.csv')
    
    # 現在のデータ
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
    
    try:
        # データを読み込む
        print(f"\n{'='*60}")
        print(f"=== {year}年{league}リーグ データ比較 ===")
        print(f"{'='*60}\n")
        
        df_scraped = pd.read_csv(scraped_path, encoding='utf-8-sig')
        df_current = pd.read_csv(current_path, encoding='utf-8-sig')
        
        result['scraped_count'] = len(df_scraped)
        result['current_count'] = len(df_current)
        
        # 選手数の比較
        print(f"スクレイピングデータ: {len(df_scraped)}件")
        print(f"現在のデータ: {len(df_current)}件")
        diff = len(df_scraped) - len(df_current)
        print(f"差分: {diff}件\n")
        
        # 選手名カラムを特定
        name_col_scraped = find_name_column(df_scraped)
        name_col_current = find_name_column(df_current)
        
        if not name_col_scraped:
            error_msg = "⚠️ スクレイピングデータに選手名カラムが見つかりません"
            print(error_msg)
            result['errors'].append(error_msg)
            return result
        
        if not name_col_current:
            error_msg = "⚠️ 現在のデータに選手名カラムが見つかりません"
            print(error_msg)
            result['errors'].append(error_msg)
            return result
        
        print(f"スクレイピングデータの選手名カラム: {name_col_scraped}")
        print(f"現在のデータの選手名カラム: {name_col_current}\n")
        
        # チーム名カラムを特定
        team_col_scraped = find_team_column(df_scraped)
        team_col_current = find_team_column(df_current)
        
        # PAカラムを特定
        pa_col_scraped = find_pa_column(df_scraped)
        pa_col_current = find_pa_column(df_current)
        
        # スクレイピングデータに存在するが、現在のデータに存在しない選手
        scraped_names = set(df_scraped[name_col_scraped].dropna().astype(str).str.strip())
        current_names = set(df_current[name_col_current].dropna().astype(str).str.strip())
        
        missing_names = scraped_names - current_names
        
        if missing_names:
            print(f"⚠️ 現在のデータに存在しない選手: {len(missing_names)}件\n")
            print("抜けている選手:")
            
            missing_players_list = []
            for i, name in enumerate(sorted(missing_names), 1):
                # 該当選手の情報を取得
                player_rows = df_scraped[df_scraped[name_col_scraped].astype(str).str.strip() == name]
                if len(player_rows) > 0:
                    player_row = player_rows.iloc[0]
                    team = 'N/A'
                    pa = 'N/A'
                    
                    if team_col_scraped:
                        team = str(player_row.get(team_col_scraped, 'N/A'))
                    if pa_col_scraped:
                        pa_val = player_row.get(pa_col_scraped, None)
                        if pa_val is not None:
                            try:
                                pa = int(float(pa_val))
                            except:
                                pa = str(pa_val)
                    
                    player_info = {
                        'name': name,
                        'team': team,
                        'pa': pa,
                        'row_number': int(player_rows.index[0]) + 2  # CSVの行番号（ヘッダー+1）
                    }
                    missing_players_list.append(player_info)
                    
                    print(f"  {i:3d}. {name:20s} ({team:15s}, PA={pa})")
            
            result['missing_players'] = missing_players_list
        else:
            print("✅ すべての選手が現在のデータに含まれています\n")
        
        # チーム別選手数の比較
        if team_col_scraped and team_col_current:
            print("=== チーム別選手数比較 ===\n")
            scraped_teams = df_scraped[team_col_scraped].value_counts().sort_index()
            current_teams = df_current[team_col_current].value_counts().sort_index()
            
            print("スクレイピングデータ:")
            for team, count in scraped_teams.items():
                print(f"  {team}: {count}件")
            
            print("\n現在のデータ:")
            for team, count in current_teams.items():
                print(f"  {team}: {count}件")
            
            # 差分を確認
            print("\nチーム別差分:")
            team_comparison = {}
            for team in scraped_teams.index:
                scraped_count = int(scraped_teams.get(team, 0))
                current_count = int(current_teams.get(team, 0))
                diff = scraped_count - current_count
                
                team_comparison[str(team)] = {
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
                df_missing = pd.DataFrame(missing_players_list)
                df_missing.to_csv(csv_file, index=False, encoding='utf-8-sig')
                print(f"✅ 抜けている選手をCSV形式で保存しました: {csv_file}")
        
        return result
        
    except Exception as e:
        error_msg = f"❌ エラーが発生しました: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        result['errors'].append(error_msg)
        return result

def main():
    if len(sys.argv) < 3:
        print("使用方法: python fact_check_compare_scraped.py <YEAR> <LEAGUE> [OUTPUT_DIR]")
        print("例: python fact_check_compare_scraped.py 2025 PL")
        print("例: python fact_check_compare_scraped.py 2025 PL output/reports")
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

