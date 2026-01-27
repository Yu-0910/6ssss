#!/usr/bin/env python3
"""
remove_duplicate_players_from_rankings.py

ランキングJSONファイルから重複選手を削除するスクリプト
重複している2つのエントリのうち、ランクが高い方（rankが小さい方）を残し、
ランクが低い方（rankが大きい方）を削除する。

重要: 両方とも削除することは絶対に禁止
"""

import json
import csv
import shutil
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
from datetime import datetime

def load_duplicate_list(csv_path: Path) -> Dict[Tuple[int, str, str], List[Dict]]:
    """
    重複リストCSVを読み込む
    
    Returns:
        {(year, league, player_name): [entry1, entry2, ...]}
    """
    duplicates = defaultdict(list)
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            year = int(row['year'])
            league = row['league']
            player_name = row['player_name']
            key = (year, league, player_name)
            
            duplicates[key].append({
                'rank': int(row['rank']),
                'playerId': row['playerId'],
                'team': row['team'],
                'value': float(row['value']) if row['value'] else 0.0,
                'entry_index': int(row['entry_index']),
            })
    
    return dict(duplicates)

def determine_removal_targets(duplicates: Dict[Tuple[int, str, str], List[Dict]]) -> Dict[Tuple[int, str, str], Dict]:
    """
    削除対象を決定
    
    基準: rankが小さい方（上位）を残す、大きい方を削除
    重要: 必ず片方だけを残す（両方削除しない）
    
    Returns:
        {(year, league, player_name): {'keep': entry, 'remove': [entry]}}
    """
    removal_targets = {}
    
    for key, entries in duplicates.items():
        if len(entries) < 2:
            continue
        
        # rankでソート（小さい順）
        sorted_entries = sorted(entries, key=lambda x: x['rank'])
        
        # 最初（rankが最小）を残す、残りを削除
        keep = sorted_entries[0]
        remove = sorted_entries[1:]
        
        # 安全チェック: 必ず1つは残す
        if not keep:
            print(f"[警告] {key} で保持するエントリが見つかりません。スキップします。")
            continue
        
        removal_targets[key] = {
            'keep': keep,
            'remove': remove
        }
    
    return removal_targets

def extract_file_info(file_path: Path) -> Tuple[int, str, str]:
    """
    ファイルパスから年度・リーグ・指標を抽出
    
    Example: public/data/rankings/1973/PL/BABIP.json
    -> (1973, 'PL', 'BABIP')
    """
    parts = file_path.parts
    # parts: ('public', 'data', 'rankings', '1973', 'PL', 'BABIP.json')
    year = int(parts[-3])
    league = parts[-2]
    metric = parts[-1].replace('.json', '')
    return year, league, metric

def should_remove(player: Dict[str, Any], remove_list: List[Dict]) -> bool:
    """
    この選手が削除対象かどうかを判定
    
    判定基準:
    1. playerIdが一致する
    2. rankが一致する
    3. teamが一致する（オプション）
    """
    player_id = player.get('playerId', '')
    rank = player.get('rank', 0)
    team = player.get('team', '')
    
    for remove_entry in remove_list:
        if (player_id == remove_entry['playerId'] and 
            rank == remove_entry['rank']):
            return True
    
    return False

def recalculate_ranks(players: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    選手リストのランクを再計算
    
    1. value（指標値）でソート（降順）
    2. 1から連番でrankを割り当て
    3. playerIdを更新
    """
    # valueでソート（降順）
    sorted_players = sorted(
        players,
        key=lambda x: x.get('value', 0),
        reverse=True
    )
    
    # ランクを再割り当て
    for new_rank, player in enumerate(sorted_players, start=1):
        player['rank'] = new_rank
        player['playerId'] = f"player-{new_rank}"
    
    return sorted_players

def process_ranking_file(
    file_path: Path,
    removal_targets: Dict[Tuple[int, str, str], Dict],
    dry_run: bool = False
) -> Tuple[int, List[Dict]]:
    """
    1つのランキングJSONファイルを処理
    
    Returns:
        (削除した選手数, 削除した選手のリスト)
    """
    # JSON読み込み
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            players = json.load(f)
    except Exception as e:
        print(f"[エラー] {file_path} の読み込みに失敗: {e}")
        return 0, []
    
    if not isinstance(players, list):
        print(f"[警告] {file_path} は配列形式ではありません。スキップします。")
        return 0, []
    
    # 年度・リーグ・指標を取得
    try:
        year, league, metric = extract_file_info(file_path)
    except Exception as e:
        print(f"[警告] {file_path} から情報を抽出できません: {e}")
        return 0, []
    
    # 削除対象を特定
    players_to_remove = []
    removed_entries = []
    
    for player in players:
        player_name = player.get('name', '') or player.get('player', '')
        if not player_name:
            continue
        
        key = (year, league, player_name)
        
        if key in removal_targets:
            remove_list = removal_targets[key]['remove']
            if should_remove(player, remove_list):
                players_to_remove.append(player)
                removed_entries.append({
                    'player_name': player_name,
                    'rank': player.get('rank'),
                    'playerId': player.get('playerId'),
                    'team': player.get('team'),
                })
    
    if not players_to_remove:
        return 0, []
    
    # ドライランの場合は削除しない
    if dry_run:
        return len(players_to_remove), removed_entries
    
    # 削除（必ず片方だけを削除）
    original_count = len(players)
    players = [p for p in players if p not in players_to_remove]
    removed_count = original_count - len(players)
    
    # 安全チェック: すべての選手を削除していないか確認
    if len(players) == 0:
        print(f"[エラー] {file_path} で全選手が削除されそうになりました。処理を中止します。")
        return 0, []
    
    # ランク再計算
    players = recalculate_ranks(players)
    
    # 保存
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(players, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[エラー] {file_path} の保存に失敗: {e}")
        return 0, []
    
    return removed_count, removed_entries

def create_backup(rankings_dir: Path, backup_dir: Path) -> bool:
    """ランキングディレクトリをバックアップ"""
    try:
        if backup_dir.exists():
            print(f"[警告] バックアップディレクトリが既に存在します: {backup_dir}")
            response = input("上書きしますか？ (yes/no): ")
            if response.lower() != 'yes':
                return False
            shutil.rmtree(backup_dir)
        
        print(f"バックアップを作成中: {backup_dir}")
        shutil.copytree(rankings_dir, backup_dir)
        print(f"[完了] バックアップ完了: {backup_dir}")
        return True
    except Exception as e:
        print(f"[エラー] バックアップの作成に失敗: {e}")
        return False

def find_ranking_files(rankings_dir: Path, year: int = None, league: str = None) -> List[Path]:
    """ランキングファイルを探索"""
    files = []
    
    for year_dir in sorted(rankings_dir.iterdir()):
        if not year_dir.is_dir():
            continue
        
        try:
            file_year = int(year_dir.name)
        except ValueError:
            continue
        
        if year is not None and file_year != year:
            continue
        
        for league_dir in year_dir.iterdir():
            if not league_dir.is_dir():
                continue
            
            if league is not None and league_dir.name != league:
                continue
            
            # すべてのJSONファイルを取得（__qualifiedや_allも含む）
            for json_file in league_dir.glob("*.json"):
                files.append(json_file)
    
    return files

def main():
    parser = argparse.ArgumentParser(description='ランキングから重複選手を削除')
    parser.add_argument('--dry-run', action='store_true', help='ドライラン（実際には削除しない）')
    parser.add_argument('--year', type=int, help='対象年度（指定しない場合は全年度）')
    parser.add_argument('--league', type=str, help='対象リーグ（指定しない場合は全リーグ）')
    parser.add_argument('--no-backup', action='store_true', help='バックアップを作成しない（非推奨）')
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent.resolve()
    rankings_dir = project_root / 'public' / 'data' / 'rankings'
    duplicate_csv = project_root / 'output' / 'reports' / 'duplicate_player_names_in_rankings.csv'
    output_dir = project_root / 'output' / 'reports'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = project_root / 'output' / 'backups' / f'rankings_backup_{timestamp}'
    log_file = output_dir / f'duplicate_removal_log_{timestamp}.csv'
    
    print("=" * 80)
    print("ランキング内の重複選手削除")
    print("=" * 80)
    print(f"対象ディレクトリ: {rankings_dir}")
    print(f"重複リスト: {duplicate_csv}")
    if args.dry_run:
        print("[モード] ドライラン（実際には削除しません）")
    else:
        print("[モード] 本番実行")
    if args.year:
        print(f"対象年度: {args.year}")
    if args.league:
        print(f"対象リーグ: {args.league}")
    print()
    
    # 重複リストの読み込み
    if not duplicate_csv.exists():
        print(f"[エラー] 重複リストが見つかりません: {duplicate_csv}")
        print("先に find_duplicate_player_names_in_rankings.py を実行してください。")
        return 1
    
    print("重複リストを読み込み中...")
    duplicates = load_duplicate_list(duplicate_csv)
    print(f"  重複グループ数: {len(duplicates)}")
    
    # 削除対象の決定
    print("削除対象を決定中...")
    removal_targets = determine_removal_targets(duplicates)
    print(f"  削除対象グループ数: {len(removal_targets)}")
    
    # バックアップ
    if not args.dry_run and not args.no_backup:
        if not create_backup(rankings_dir, backup_dir):
            print("[エラー] バックアップの作成に失敗しました。処理を中止します。")
            return 1
    
    # ランキングファイルを探索
    print("\nランキングファイルを探索中...")
    ranking_files = find_ranking_files(rankings_dir, args.year, args.league)
    print(f"  見つかったファイル数: {len(ranking_files)}")
    
    # 処理
    print("\n重複選手を削除中...")
    total_removed = 0
    processed_files = 0
    log_entries = []
    
    for file_path in ranking_files:
        removed_count, removed_entries = process_ranking_file(
            file_path, removal_targets, args.dry_run
        )
        
        if removed_count > 0:
            total_removed += removed_count
            processed_files += 1
            year, league, metric = extract_file_info(file_path)
            
            for entry in removed_entries:
                log_entries.append({
                    'year': year,
                    'league': league,
                    'metric': metric,
                    'player_name': entry['player_name'],
                    'rank': entry['rank'],
                    'playerId': entry['playerId'],
                    'team': entry['team'],
                    'file': str(file_path.relative_to(project_root)),
                })
            
            if processed_files % 100 == 0:
                print(f"  処理中... {processed_files} ファイル処理済み")
    
    # ログを保存
    if log_entries:
        with open(log_file, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = ['year', 'league', 'metric', 'player_name', 'rank', 'playerId', 'team', 'file']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(log_entries)
        print(f"\n[完了] ログを保存: {log_file}")
    
    # 結果表示
    print()
    print("=" * 80)
    print("処理結果")
    print("=" * 80)
    print(f"処理したファイル数: {processed_files}")
    print(f"削除した選手数: {total_removed}")
    if not args.dry_run:
        print(f"バックアップ: {backup_dir}")
    print(f"ログファイル: {log_file}")
    print()
    
    if args.dry_run:
        print("[注意] ドライランモードでした。実際には削除していません。")
        print("本番実行する場合は --dry-run を外してください。")
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
