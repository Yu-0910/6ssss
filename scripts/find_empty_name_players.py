#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
find_empty_name_players.py

成績CSVに存在するが、名前（player_name_ja）が空になっている選手を探すスクリプト
"""

import csv
import sys
from pathlib import Path
from typing import List, Dict
from collections import defaultdict

# WindowsでのUnicode出力対応
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# プロジェクトルートを取得
script_dir = Path(__file__).parent
project_root = script_dir.parent


def find_empty_name_players(csv_path: Path) -> List[Dict]:
    """CSVファイルから名前が空の選手を探す"""
    empty_name_players = []
    
    if not csv_path.exists():
        return empty_name_players
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            # BOMを手動で除去
            content = f.read()
            if content.startswith('\ufeff'):
                content = content[1:]
            
            reader = csv.DictReader(content.splitlines())
            
            # 名前カラムを探す
            name_columns = ['player_name_ja', 'name_ja', 'name', '選手名']
            name_col = None
            for col in reader.fieldnames or []:
                if col in name_columns:
                    name_col = col
                    break
            
            if not name_col:
                return empty_name_players
            
            # player_idカラムを探す
            player_id_columns = ['player_id', 'playerId']
            player_id_col = None
            for col in reader.fieldnames or []:
                if col in player_id_columns:
                    player_id_col = col
                    break
            
            # year, league, teamカラムを探す
            year_col = None
            league_col = None
            team_col = None
            for col in reader.fieldnames or []:
                if col.lower() in ['year', '年度']:
                    year_col = col
                elif col.lower() in ['league', 'リーグ']:
                    league_col = col
                elif col.lower() in ['team', 'チーム']:
                    team_col = col
            
            for row in reader:
                player_id = row.get(player_id_col, '').strip() if player_id_col else ''
                name = row.get(name_col, '').strip() if name_col else ''
                
                # player_idは存在するが、名前が空の場合
                if player_id and player_id != 'nan' and player_id != '':
                    if not name or name == '' or name == 'nan':
                        empty_name_players.append({
                            'player_id': player_id,
                            'name': name,
                            'year': row.get(year_col, '') if year_col else '',
                            'league': row.get(league_col, '') if league_col else '',
                            'team': row.get(team_col, '') if team_col else '',
                            'file': csv_path.name,
                        })
    
    except Exception as e:
        print(f"⚠️ CSV読み込みエラー ({csv_path}): {e}")
    
    return empty_name_players


def main():
    print(f"\n{'='*60}")
    print(f"=== 名前が空の選手を検索 ===")
    print(f"{'='*60}\n")
    
    # 検索対象のディレクトリ
    search_dirs = [
        project_root / '_data' / 'master_csv__import_1950_2024',
        project_root / '_data' / 'master_csv',
        project_root / '_data' / 'master_csv_calculated',
    ]
    
    all_empty_name_players = []
    files_checked = 0
    
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        
        print(f"📂 {search_dir.name} を検索中...")
        
        csv_files = list(search_dir.glob('batting_*_from_master.csv'))
        files_checked += len(csv_files)
        
        for csv_file in csv_files:
            empty_players = find_empty_name_players(csv_file)
            if empty_players:
                all_empty_name_players.extend(empty_players)
                print(f"  ⚠️ {csv_file.name}: {len(empty_players)}人の名前が空の選手を発見")
    
    print(f"\n✅ 検索完了: {files_checked}ファイルを確認")
    
    if not all_empty_name_players:
        print("\n✅ 名前が空の選手は見つかりませんでした")
        return
    
    print(f"\n{'='*60}")
    print(f"=== 検出結果: {len(all_empty_name_players)}人の名前が空の選手 ===")
    print(f"{'='*60}\n")
    
    # player_idごとに集計
    players_by_id = defaultdict(list)
    for player in all_empty_name_players:
        players_by_id[player['player_id']].append(player)
    
    print(f"ユニークなplayer_id数: {len(players_by_id)}人\n")
    
    # 結果を表示（最初の30件）
    count = 0
    for player_id, occurrences in sorted(players_by_id.items()):
        if count >= 30:
            break
        
        print(f"player_id: {player_id}")
        print(f"  出現回数: {len(occurrences)}回")
        for occ in occurrences[:3]:  # 最初の3件のみ表示
            print(f"    - {occ['year']}年 {occ['league']} {occ['team']} ({occ['file']})")
        if len(occurrences) > 3:
            print(f"    ... 他 {len(occurrences) - 3}件")
        print()
        count += 1
    
    if len(players_by_id) > 30:
        print(f"... 他 {len(players_by_id) - 30}人の選手")
    
    # CSV形式で保存
    output_dir = project_root / 'output' / 'reports'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'empty_name_players.csv'
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['player_id', 'year', 'league', 'team', 'file'])
        writer.writeheader()
        for player in all_empty_name_players:
            writer.writerow({
                'player_id': player['player_id'],
                'year': player['year'],
                'league': player['league'],
                'team': player['team'],
                'file': player['file'],
            })
    
    print(f"\n✅ 結果をCSV形式で保存しました: {output_file}")
    
    # player_idごとの集計も保存
    summary_file = output_dir / 'empty_name_players_summary.csv'
    with open(summary_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['player_id', 'occurrence_count'])
        writer.writeheader()
        for player_id, occurrences in sorted(players_by_id.items()):
            writer.writerow({
                'player_id': player_id,
                'occurrence_count': len(occurrences),
            })
    
    print(f"✅ 集計結果をCSV形式で保存しました: {summary_file}")


if __name__ == '__main__':
    main()
