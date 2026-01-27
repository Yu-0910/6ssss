#!/usr/bin/env python3
"""
find_duplicate_player_names_in_rankings.py

1950年から2025年のすべてのランキングページにおいて、
同一年度・同一リーグに2つ名前がある選手を検出してCSVファイルにまとめる
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

def find_ranking_files(rankings_dir: Path, start_year: int = 1950, end_year: int = 2025) -> List[Tuple[int, str, Path]]:
    """
    ランキングファイルを探索
    
    Returns:
        List of (year, league, file_path)
    """
    files = []
    
    for year in range(start_year, end_year + 1):
        year_dir = rankings_dir / str(year)
        if not year_dir.exists():
            continue
        
        # リーグディレクトリを探索
        for league_dir in year_dir.iterdir():
            if not league_dir.is_dir():
                continue
            
            league = league_dir.name
            
            # その年度・リーグのすべてのJSONファイルを取得
            for json_file in league_dir.glob("*.json"):
                # __qualifiedや_allなどのサフィックスを除外し、基本指標ファイルのみを対象
                if json_file.name.endswith("__qualified.json") or json_file.name.endswith("_all.json"):
                    continue
                
                files.append((year, league, json_file))
    
    return files

def find_duplicates_in_file(file_path: Path) -> Dict[str, List[Dict]]:
    """
    1つのランキングJSONファイル内で重複する選手名を検出
    
    Returns:
        {player_name: [player_data1, player_data2, ...]}
    """
    duplicates = defaultdict(list)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            return {}
        
        # 選手名でグループ化
        name_to_players = defaultdict(list)
        for player in data:
            if not isinstance(player, dict):
                continue
            
            # nameフィールドを取得（playerフィールドもフォールバック）
            player_name = player.get('name') or player.get('player', '')
            if player_name:
                name_to_players[player_name].append(player)
        
        # 2つ以上出現する選手名を記録
        for name, players in name_to_players.items():
            if len(players) >= 2:
                duplicates[name] = players
    
    except Exception as e:
        print(f"⚠️  エラー: {file_path} の読み込みに失敗: {e}")
    
    return dict(duplicates)

def main():
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent.resolve()
    rankings_dir = project_root / 'public' / 'data' / 'rankings'
    output_dir = project_root / 'output' / 'reports'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'duplicate_player_names_in_rankings.csv'
    
    print("=" * 80)
    print("ランキング内の重複選手名検出")
    print("=" * 80)
    print(f"スクリプトディレクトリ: {script_dir}")
    print(f"プロジェクトルート: {project_root}")
    print(f"対象ディレクトリ: {rankings_dir}")
    print(f"出力ファイル: {output_file}")
    
    # パスの存在確認
    if not rankings_dir.exists():
        print(f"[エラー] ランキングディレクトリが見つかりません: {rankings_dir}")
        return 1
    
    print()
    
    # ランキングファイルを探索
    print("ランキングファイルを探索中...")
    ranking_files = find_ranking_files(rankings_dir, start_year=1950, end_year=2025)
    print(f"  見つかったファイル数: {len(ranking_files)}")
    print()
    
    # 年度・リーグごとに重複を検出
    all_duplicates = []
    year_league_processed = set()
    
    print("重複選手名を検出中...")
    for year, league, file_path in ranking_files:
        year_league_key = (year, league)
        
        # 各年度・リーグは1つの指標ファイルで代表してチェック（すべての指標ファイルで同じ重複が発生するため）
        if year_league_key in year_league_processed:
            continue
        
        year_league_processed.add(year_league_key)
        
        # 重複を検出
        duplicates = find_duplicates_in_file(file_path)
        
        if duplicates:
            for player_name, players in duplicates.items():
                # 各重複エントリを記録
                for idx, player in enumerate(players):
                    all_duplicates.append({
                        'year': year,
                        'league': league,
                        'player_name': player_name,
                        'duplicate_count': len(players),
                        'entry_index': idx + 1,
                        'team': player.get('team', ''),
                        'playerId': player.get('playerId', ''),
                        'romanName': player.get('romanName', ''),
                        'metric': player.get('metric', ''),
                        'rank': player.get('rank', ''),
                        'value': player.get('value', ''),
                        'source_file': file_path.name
                    })
    
    # CSVに出力
    if all_duplicates:
        print(f"\n重複が見つかりました: {len(all_duplicates)} 件")
        print(f"CSVファイルに出力中: {output_file}")
        
        fieldnames = [
            'year', 'league', 'player_name', 'duplicate_count', 'entry_index',
            'team', 'playerId', 'romanName', 'metric', 'rank', 'value', 'source_file'
        ]
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_duplicates)
        
        print(f"[完了] 出力完了: {output_file}")
        
        # 統計情報を表示
        unique_players = set()
        year_league_with_duplicates = set()
        for dup in all_duplicates:
            unique_players.add((dup['year'], dup['league'], dup['player_name']))
            year_league_with_duplicates.add((dup['year'], dup['league']))
        
        print()
        print("統計情報:")
        print(f"  重複している選手数（年度・リーグ・選手名の組み合わせ）: {len(unique_players)}")
        print(f"  重複が発生している年度・リーグの組み合わせ: {len(year_league_with_duplicates)}")
        
    else:
        print("\n[完了] 重複は見つかりませんでした。")
    
    print()
    print("=" * 80)
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
