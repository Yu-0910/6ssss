#!/usr/bin/env python3
"""
analyze_1937_data_completeness.py

1937年のデータの完全性を分析し、より完全なデータソースを探す
"""

import csv
from pathlib import Path
from typing import List, Dict, Any, Set
from collections import defaultdict


def load_csv_with_encoding(csv_path: Path) -> List[Dict[str, Any]]:
    """CSVファイルを読み込む（文字コード自動判定）"""
    encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
    for encoding in encodings:
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                return list(reader)
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    raise ValueError(f"Failed to read {csv_path} with any encoding")


def get_unique_players(data: List[Dict[str, Any]], player_id_column: str = 'player_id') -> Set[str]:
    """ユニークなplayer_idのセットを取得"""
    player_ids = set()
    for row in data:
        player_id = str(row.get(player_id_column, '')).strip()
        if player_id:
            player_ids.add(player_id)
    return player_ids


def analyze_file(csv_path: Path, description: str):
    """ファイルを分析"""
    if not csv_path.exists():
        print(f"\n[{description}]")
        print(f"  ファイルが見つかりません: {csv_path}")
        return None
    
    try:
        data = load_csv_with_encoding(csv_path)
    except Exception as e:
        print(f"\n[{description}]")
        print(f"  読み込みエラー: {e}")
        return None
    
    # player_id列を探す
    player_id_column = None
    if data:
        for col in ['player_id', 'playerId', 'id', '選手ID']:
            if col in data[0]:
                player_id_column = col
                break
    
    # year列を探す
    year_column = None
    if data:
        for col in data[0].keys():
            if 'year' in col.lower():
                year_column = col
                break
    
    # 1937年のデータをフィルタ
    filtered_data = []
    if year_column:
        for row in data:
            year_val = str(row.get(year_column, '')).strip()
            if '1937' in year_val:
                filtered_data.append(row)
    else:
        filtered_data = data
    
    unique_players = get_unique_players(filtered_data, player_id_column) if player_id_column else set()
    
    # 重複チェック
    duplicate_info = None
    if player_id_column and year_column:
        key_to_rows = defaultdict(list)
        for row in filtered_data:
            key = (str(row.get(player_id_column, '')).strip(), str(row.get(year_column, '')).strip())
            key_to_rows[key].append(row)
        
        duplicates = {k: rows for k, rows in key_to_rows.items() if len(rows) > 1}
        duplicate_info = {
            'duplicate_count': len(duplicates),
            'total_keys': len(key_to_rows),
            'has_duplicates': len(duplicates) > 0
        }
    
    # season列をチェック
    season_column = None
    season_values = set()
    if data:
        for col in data[0].keys():
            if 'season' in col.lower():
                season_column = col
                for row in filtered_data:
                    val = str(row.get(col, '')).strip()
                    if val:
                        season_values.add(val)
                break
    
    result = {
        'path': str(csv_path),
        'description': description,
        'total_rows': len(data),
        'filtered_rows': len(filtered_data),
        'unique_players': len(unique_players),
        'player_id_column': player_id_column,
        'year_column': year_column,
        'duplicate_info': duplicate_info,
        'season_column': season_column,
        'season_values': sorted(season_values) if season_values else None,
        'columns': list(data[0].keys()) if data else []
    }
    
    return result


def print_analysis(result: Dict[str, Any]):
    """分析結果を表示"""
    if not result:
        return
    
    print(f"\n[{result['description']}]")
    print(f"  パス: {Path(result['path']).name}")
    print(f"  全行数: {result['total_rows']:,}行")
    print(f"  1937年フィルタ後: {result['filtered_rows']:,}行")
    print(f"  ユニークプレイヤー数: {result['unique_players']}人")
    
    if result['duplicate_info']:
        dup_info = result['duplicate_info']
        print(f"  重複キー数: {dup_info['duplicate_count']}件")
        print(f"  総キー数: {dup_info['total_keys']}件")
        if dup_info['has_duplicates']:
            print(f"    -> 春秋分割の可能性あり（重複あり）")
    
    if result['season_column']:
        print(f"  season列: {result['season_column']}")
        if result['season_values']:
            print(f"    値: {', '.join(result['season_values'])}")
    
    print(f"  列数: {len(result['columns'])}列")


def main():
    base_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting")
    
    print("=" * 80)
    print("1937年データ完全性分析")
    print("=" * 80)
    
    # 分析対象ファイル
    files_to_analyze = [
        # 現在使用中のファイル
        (base_path / "data" / "batting" / "yearly_from_master_dedup" / "batting_1937_spring_PRE.csv", "現在使用中: 1937春"),
        (base_path / "data" / "batting" / "yearly_from_master_dedup" / "batting_1937_fall_PRE.csv", "現在使用中: 1937秋"),
        
        # jblディレクトリ（元のソース）
        (base_path / "data" / "batting" / "jbl" / "batting_1937S_from_individual.csv", "jbl: 1937春"),
        (base_path / "data" / "batting" / "jbl" / "batting_1937A_from_individual.csv", "jbl: 1937秋"),
        
        # バックアップ（dedup前）
        (base_path / "data" / "batting" / "backups" / "20251222_014605" / "yearly_from_master" / "batting_1937_PRE_from_master.csv", "バックアップ1: dedup前"),
        (base_path / "data" / "batting" / "backups" / "20251222_014659" / "yearly_from_master" / "batting_1937_PRE_from_master.csv", "バックアップ2: dedup前"),
        
        # masterディレクトリ（もしあれば）
        (base_path / "data" / "batting" / "master" / "batting_1937_PRE.csv", "master: 1937"),
    ]
    
    results = []
    for file_path, description in files_to_analyze:
        result = analyze_file(file_path, description)
        if result:
            results.append(result)
            print_analysis(result)
    
    # 比較分析
    print("\n" + "=" * 80)
    print("比較分析")
    print("=" * 80)
    
    # 現在使用中のファイルの合計
    current_spring = next((r for r in results if '現在使用中: 1937春' in r['description']), None)
    current_fall = next((r for r in results if '現在使用中: 1937秋' in r['description']), None)
    
    if current_spring and current_fall:
        current_total = current_spring['filtered_rows'] + current_fall['filtered_rows']
        current_unique = current_spring['unique_players'] + current_fall['unique_players']
        print(f"\n[現在使用中のファイル合計]")
        print(f"  総行数: {current_total}行")
        print(f"  ユニークプレイヤー数: {current_unique}人（重複カウント含む）")
    
    # バックアップファイルと比較
    backup_files = [r for r in results if 'バックアップ' in r['description']]
    if backup_files:
        backup = backup_files[0]  # 最初のバックアップを使用
        print(f"\n[バックアップファイル（dedup前）]")
        print(f"  総行数: {backup['filtered_rows']}行")
        print(f"  ユニークプレイヤー数: {backup['unique_players']}人")
        if backup['duplicate_info']:
            print(f"  重複キー数: {backup['duplicate_info']['duplicate_count']}件")
            print(f"    -> これらは春秋分割可能（1人の選手が2行ある）")
        
        if current_spring and current_fall:
            print(f"\n[比較]")
            print(f"  現在使用中: {current_total}行")
            print(f"  バックアップ: {backup['filtered_rows']}行")
            print(f"  差分: {backup['filtered_rows'] - current_total}行（{backup['filtered_rows'] - current_total}行分のデータが失われている可能性）")
    
    # 推奨事項
    print("\n" + "=" * 80)
    print("推奨事項")
    print("=" * 80)
    
    if backup_files:
        backup = backup_files[0]
        if backup['filtered_rows'] > (current_total if current_spring and current_fall else 0):
            print("\n[推奨] バックアップファイルの方がデータが多いです。")
            print(f"  バックアップファイル: {backup['filtered_rows']}行")
            if current_spring and current_fall:
                print(f"  現在使用中: {current_total}行")
            print(f"\n  次のステップ:")
            print(f"  1. バックアップファイルから春秋に分割する")
            print(f"  2. 分割後のファイルを yearly_from_master_dedup に配置する")
            print(f"  3. 現在のファイル（{current_total}行）より多くのデータが得られる可能性がある")
    else:
        print("\n[情報] バックアップファイルが見つかりませんでした。")
        print("  現在のデータが最良の可能性があります。")
    
    return 0


if __name__ == '__main__':
    exit(main())





















