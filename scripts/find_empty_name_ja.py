#!/usr/bin/env python3
"""
player_name_jaが空の選手を探す
"""
import csv
import sys
from pathlib import Path

def find_empty_name_ja(csv_path: Path, limit: int = 10):
    """player_name_jaが空の選手を探す"""
    empty_players = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                player_id = row.get('player_id', '').strip()
                name_ja = row.get('player_name_ja', '').strip()
                year = row.get('year', '').strip()
                league = row.get('league', '').strip()
                team = row.get('team', '').strip()
                
                if not name_ja or name_ja == 'nan' or name_ja == '':
                    empty_players.append({
                        'player_id': player_id,
                        'name_ja': name_ja,
                        'year': year,
                        'league': league,
                        'team': team
                    })
                    if len(empty_players) >= limit:
                        break
    except Exception as e:
        print(f"❌ エラー: {e}", file=sys.stderr)
        return []
    
    return empty_players

if __name__ == '__main__':
    # 2025年PLをチェック
    csv_path = Path('_data/master_csv_calculated/batting_2025_PL_from_master.csv')
    
    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        sys.exit(1)
    
    empty_players = find_empty_name_ja(csv_path, limit=10)
    
    if empty_players:
        print(f"✅ player_name_jaが空の選手を {len(empty_players)}件 見つけました（最初の10件）:\n")
        for i, p in enumerate(empty_players, 1):
            print(f"{i}. player_id: {p['player_id']:10s} | year: {p['year']} | league: {p['league']} | team: {p['team']} | name_ja: '{p['name_ja']}'")
    else:
        print("✅ player_name_jaが空の選手は見つかりませんでした")
        # 他の年度・リーグもチェック
        print("\n他の年度・リーグをチェック中...")
        for year in [2024, 2023, 2022]:
            for league in ['PL', 'CL']:
                csv_path = Path(f'_data/master_csv_calculated/batting_{year}_{league}_from_master.csv')
                if csv_path.exists():
                    empty_players = find_empty_name_ja(csv_path, limit=5)
                    if empty_players:
                        print(f"\n{year}年 {league}リーグで空の選手を {len(empty_players)}件 見つけました:")
                        for p in empty_players:
                            print(f"  player_id: {p['player_id']:10s} | name_ja: '{p['name_ja']}'")
                        break
            if empty_players:
                break




