#!/usr/bin/env python3
"""
evaluate_1937_seasons.py

1937年の春・秋シーズンのデータを評価する
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


def safe_int(value: Any, default: int = 0) -> int:
    """安全にintに変換"""
    if value is None or value == '':
        return default
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """安全にfloatに変換"""
    if value is None or value == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def analyze_data_quality(data: List[Dict[str, Any]], season_name: str) -> Dict[str, Any]:
    """データの品質を分析"""
    if not data:
        return {
            'season': season_name,
            'row_count': 0,
            'error': 'データが空です'
        }
    
    # 基本統計
    unique_players = set()
    teams = set()
    total_games = 0
    total_pa = 0
    total_ab = 0
    total_hits = 0
    total_hr = 0
    
    player_id_counts = defaultdict(int)
    duplicate_players = []
    
    for row in data:
        player_id = str(row.get('player_id', '')).strip()
        if player_id:
            unique_players.add(player_id)
            player_id_counts[player_id] += 1
            if player_id_counts[player_id] > 1:
                duplicate_players.append(player_id)
        
        team = str(row.get('team', '')).strip()
        if team:
            teams.add(team)
        
        total_games += safe_int(row.get('G', 0))
        total_pa += safe_int(row.get('PA', 0))
        total_ab += safe_int(row.get('AB', 0))
        total_hits += safe_int(row.get('H', 0))
        total_hr += safe_int(row.get('HR', 0))
    
    # 重複チェック
    has_duplicates = len(duplicate_players) > 0
    
    return {
        'season': season_name,
        'row_count': len(data),
        'unique_players': len(unique_players),
        'duplicate_players_count': len(set(duplicate_players)),
        'has_duplicates': has_duplicates,
        'teams': sorted(teams),
        'team_count': len(teams),
        'total_games': total_games,
        'total_pa': total_pa,
        'total_ab': total_ab,
        'total_hits': total_hits,
        'total_hr': total_hr,
        'avg_hits_per_player': total_hits / len(unique_players) if unique_players else 0,
        'avg_games_per_player': total_games / len(unique_players) if unique_players else 0
    }


def compare_with_reference(current_data: List[Dict[str, Any]], reference_data: List[Dict[str, Any]], 
                          current_name: str, reference_name: str) -> Dict[str, Any]:
    """参照データと比較"""
    current_player_ids = {str(row.get('player_id', '')).strip() for row in current_data if str(row.get('player_id', '')).strip()}
    reference_player_ids = {str(row.get('player_id', '')).strip() for row in reference_data if str(row.get('player_id', '')).strip()}
    
    in_current_not_ref = current_player_ids - reference_player_ids
    in_ref_not_current = reference_player_ids - current_player_ids
    in_both = current_player_ids & reference_player_ids
    
    return {
        'current_name': current_name,
        'reference_name': reference_name,
        'current_count': len(current_player_ids),
        'reference_count': len(reference_player_ids),
        'in_both': len(in_both),
        'only_in_current': len(in_current_not_ref),
        'only_in_reference': len(in_ref_not_current),
        'coverage': len(in_both) / len(reference_player_ids) * 100 if reference_player_ids else 0
    }


def main():
    base_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting")
    
    # 評価対象ファイル
    current_spring_path = base_path / "data" / "batting" / "yearly_from_master_dedup" / "batting_1937_spring_PRE.csv"
    current_fall_path = base_path / "data" / "batting" / "yearly_from_master_dedup" / "batting_1937_fall_PRE.csv"
    
    # 参照ファイル（jblの元データ）
    jbl_spring_path = base_path / "data" / "batting" / "jbl" / "batting_1937S_from_individual.csv"
    jbl_fall_path = base_path / "data" / "batting" / "jbl" / "batting_1937A_from_individual.csv"
    
    # バックアップファイル（比較用）
    backup_path = base_path / "data" / "batting" / "backups" / "20251222_014659" / "yearly_from_master" / "batting_1937_PRE_from_master.csv"
    
    print("=" * 80)
    print("1937年 春・秋シーズンデータ 評価レポート")
    print("=" * 80)
    
    # 現在のデータを読み込む
    print("\n[読み込み] 現在のデータ")
    current_spring_data = load_csv_with_encoding(current_spring_path) if current_spring_path.exists() else []
    current_fall_data = load_csv_with_encoding(current_fall_path) if current_fall_path.exists() else []
    
    print(f"  春: {len(current_spring_data)}行")
    print(f"  秋: {len(current_fall_data)}行")
    print(f"  合計: {len(current_spring_data) + len(current_fall_data)}行")
    
    # データ品質分析
    print("\n" + "=" * 80)
    print("データ品質分析")
    print("=" * 80)
    
    spring_quality = analyze_data_quality(current_spring_data, "1937年春")
    fall_quality = analyze_data_quality(current_fall_data, "1937年秋")
    
    print(f"\n[1937年春]")
    print(f"  行数: {spring_quality['row_count']}行")
    print(f"  ユニークプレイヤー数: {spring_quality['unique_players']}人")
    print(f"  重複プレイヤー: {'あり' if spring_quality['has_duplicates'] else 'なし'} ({spring_quality['duplicate_players_count']}人)")
    print(f"  チーム数: {spring_quality['team_count']}チーム")
    print(f"  チーム一覧: {', '.join(spring_quality['teams'])}")
    print(f"  合計試合数: {spring_quality['total_games']}")
    print(f"  合計打席数: {spring_quality['total_pa']}")
    print(f"  合計打数: {spring_quality['total_ab']}")
    print(f"  合計安打数: {spring_quality['total_hits']}")
    print(f"  合計本塁打数: {spring_quality['total_hr']}")
    print(f"  1人あたり平均安打: {spring_quality['avg_hits_per_player']:.2f}")
    print(f"  1人あたり平均試合: {spring_quality['avg_games_per_player']:.2f}")
    
    print(f"\n[1937年秋]")
    print(f"  行数: {fall_quality['row_count']}行")
    print(f"  ユニークプレイヤー数: {fall_quality['unique_players']}人")
    print(f"  重複プレイヤー: {'あり' if fall_quality['has_duplicates'] else 'なし'} ({fall_quality['duplicate_players_count']}人)")
    print(f"  チーム数: {fall_quality['team_count']}チーム")
    print(f"  チーム一覧: {', '.join(fall_quality['teams'])}")
    print(f"  合計試合数: {fall_quality['total_games']}")
    print(f"  合計打席数: {fall_quality['total_pa']}")
    print(f"  合計打数: {fall_quality['total_ab']}")
    print(f"  合計安打数: {fall_quality['total_hits']}")
    print(f"  合計本塁打数: {fall_quality['total_hr']}")
    print(f"  1人あたり平均安打: {fall_quality['avg_hits_per_player']:.2f}")
    print(f"  1人あたり平均試合: {fall_quality['avg_games_per_player']:.2f}")
    
    # 合計データ
    total_players = spring_quality['unique_players'] + fall_quality['unique_players']
    total_rows = spring_quality['row_count'] + fall_quality['row_count']
    
    print(f"\n[合計]")
    print(f"  総行数: {total_rows}行")
    print(f"  総プレイヤー数（重複カウント）: {total_players}人")
    print(f"  総試合数: {spring_quality['total_games'] + fall_quality['total_games']}")
    print(f"  総打席数: {spring_quality['total_pa'] + fall_quality['total_pa']}")
    print(f"  総安打数: {spring_quality['total_hits'] + fall_quality['total_hits']}")
    print(f"  総本塁打数: {spring_quality['total_hr'] + fall_quality['total_hr']}")
    
    # jbl参照データと比較
    print("\n" + "=" * 80)
    print("jbl参照データとの比較")
    print("=" * 80)
    
    if jbl_spring_path.exists() and jbl_fall_path.exists():
        jbl_spring_data = load_csv_with_encoding(jbl_spring_path)
        jbl_fall_data = load_csv_with_encoding(jbl_fall_path)
        
        spring_compare = compare_with_reference(current_spring_data, jbl_spring_data, "現在の春", "jbl春")
        fall_compare = compare_with_reference(current_fall_data, jbl_fall_data, "現在の秋", "jbl秋")
        
        print(f"\n[春シーズン]")
        print(f"  現在のデータ: {spring_compare['current_count']}人")
        print(f"  jbl参照データ: {spring_compare['reference_count']}人")
        print(f"  共通: {spring_compare['in_both']}人")
        print(f"  現在のみ: {spring_compare['only_in_current']}人")
        print(f"  jblのみ: {spring_compare['only_in_reference']}人")
        print(f"  カバレッジ: {spring_compare['coverage']:.1f}%")
        
        print(f"\n[秋シーズン]")
        print(f"  現在のデータ: {fall_compare['current_count']}人")
        print(f"  jbl参照データ: {fall_compare['reference_count']}人")
        print(f"  共通: {fall_compare['in_both']}人")
        print(f"  現在のみ: {fall_compare['only_in_current']}人")
        print(f"  jblのみ: {fall_compare['only_in_reference']}人")
        print(f"  カバレッジ: {fall_compare['coverage']:.1f}%")
    
    # バックアップファイルとの比較
    print("\n" + "=" * 80)
    print("バックアップファイル（dedup前）との比較")
    print("=" * 80)
    
    if backup_path.exists():
        backup_data = load_csv_with_encoding(backup_path)
        backup_1937_data = [row for row in backup_data if '1937' in str(row.get('year', '')).strip()]
        
        current_all_player_ids = set()
        for row in current_spring_data + current_fall_data:
            player_id = str(row.get('player_id', '')).strip()
            if player_id:
                current_all_player_ids.add(player_id)
        
        backup_player_ids = {str(row.get('player_id', '')).strip() for row in backup_1937_data if str(row.get('player_id', '')).strip()}
        
        in_current_not_backup = current_all_player_ids - backup_player_ids
        in_backup_not_current = backup_player_ids - current_all_player_ids
        in_both = current_all_player_ids & backup_player_ids
        
        print(f"\n[全体比較]")
        print(f"  現在のデータ（春+秋）: {len(current_all_player_ids)}人")
        print(f"  バックアップ（dedup前）: {len(backup_player_ids)}人")
        print(f"  共通: {len(in_both)}人")
        print(f"  現在のみ: {len(in_current_not_backup)}人")
        print(f"  バックアップのみ: {len(in_backup_not_current)}人")
        print(f"  カバレッジ: {len(in_both) / len(backup_player_ids) * 100:.1f}%" if backup_player_ids else "N/A")
        
        print(f"\n  現在のデータ総行数: {len(current_spring_data) + len(current_fall_data)}行")
        print(f"  バックアップ総行数: {len(backup_1937_data)}行")
        print(f"  行数の差: {len(current_spring_data) + len(current_fall_data) - len(backup_1937_data)}行")
    
    # 評価と推奨事項
    print("\n" + "=" * 80)
    print("評価と推奨事項")
    print("=" * 80)
    
    issues = []
    positives = []
    
    # データ量の評価
    if total_rows >= 300:
        positives.append(f"[OK] データ量が豊富（{total_rows}行）")
    elif total_rows >= 200:
        positives.append(f"[注意] データ量は中程度（{total_rows}行）")
    else:
        issues.append(f"[問題] データ量が少ない（{total_rows}行）")
    
    # 重複チェック
    if spring_quality['has_duplicates']:
        issues.append(f"[問題] 春シーズンに重複プレイヤーが{spring_quality['duplicate_players_count']}人存在")
    else:
        positives.append(f"[OK] 春シーズンに重複なし")
    
    if fall_quality['has_duplicates']:
        issues.append(f"[問題] 秋シーズンに重複プレイヤーが{fall_quality['duplicate_players_count']}人存在")
    else:
        positives.append(f"[OK] 秋シーズンに重複なし")
    
    # バランスチェック
    ratio = spring_quality['row_count'] / fall_quality['row_count'] if fall_quality['row_count'] > 0 else 0
    if ratio < 0.5 or ratio > 2.0:
        issues.append(f"[注意] 春と秋のデータ量のバランスが不均等（春:{spring_quality['row_count']}行 vs 秋:{fall_quality['row_count']}行、比:{ratio:.2f}）")
    else:
        positives.append(f"[OK] 春と秋のデータ量のバランスが良好")
    
    # 結果表示
    print("\n[良い点]")
    for item in positives:
        print(f"  {item}")
    
    if issues:
        print("\n[問題点・注意点]")
        for item in issues:
            print(f"  {item}")
    else:
        print("\n[問題点] なし")
    
    print("\n[総合評価]")
    if len(issues) == 0:
        print("  [OK] データ品質は良好です")
    elif len(issues) <= 2:
        print("  [注意] データ品質は概ね良好ですが、いくつかの注意点があります")
    else:
        print("  [問題] データ品質に問題があります。改善が必要です")
    
    return 0


if __name__ == '__main__':
    exit(main())

