#!/usr/bin/env python3
"""
investigate_1937_season_balance.py

1937年の春秋のデータバランスを詳細に調査
重複が多かっただけなのか、実際に秋の方が多いのかを確認
"""

import csv
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
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


def create_stats_key(row: Dict[str, Any]) -> Tuple:
    """統計データからキーを生成"""
    key_fields = ['G', 'PA', 'AB', 'H', 'HR', 'RBI', 'team']
    key_values = []
    for field in key_fields:
        val = str(row.get(field, '')).strip()
        key_values.append(val if val else '0')
    return tuple(key_values)


def safe_float(value: Any) -> float:
    """安全にfloatに変換"""
    try:
        return float(value) if value else 0.0
    except:
        return 0.0


def main():
    base_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting")
    
    # 現在の分割データ
    current_spring_path = base_path / "data" / "batting" / "yearly_from_master_dedup" / "batting_1937_spring_PRE.csv"
    current_fall_path = base_path / "data" / "batting" / "yearly_from_master_dedup" / "batting_1937_fall_PRE.csv"
    
    # バックアップファイル（元データ）
    backup_path = base_path / "data" / "batting" / "backups" / "20251222_014659" / "yearly_from_master" / "batting_1937_PRE_from_master.csv"
    
    # jbl参照データ
    jbl_spring_path = base_path / "data" / "batting" / "jbl" / "batting_1937S_from_individual.csv"
    jbl_fall_path = base_path / "data" / "batting" / "jbl" / "batting_1937A_from_individual.csv"
    
    print("=" * 80)
    print("1937年 春秋データバランス詳細調査")
    print("=" * 80)
    
    # 1. 現在の分割データを確認
    print("\n[1] 現在の分割データ")
    current_spring_data = load_csv_with_encoding(current_spring_path)
    current_fall_data = load_csv_with_encoding(current_fall_path)
    
    print(f"  春: {len(current_spring_data)}行")
    print(f"  秋: {len(current_fall_data)}行")
    print(f"  比率: 春{len(current_spring_data) / (len(current_spring_data) + len(current_fall_data)) * 100:.1f}% vs 秋{len(current_fall_data) / (len(current_spring_data) + len(current_fall_data)) * 100:.1f}%")
    
    # 2. jbl参照データを確認
    print("\n[2] jbl参照データ（スクレイピング済みの分割データ）")
    jbl_spring_data = load_csv_with_encoding(jbl_spring_path) if jbl_spring_path.exists() else []
    jbl_fall_data = load_csv_with_encoding(jbl_fall_path) if jbl_fall_path.exists() else []
    
    print(f"  jbl春: {len(jbl_spring_data)}行")
    print(f"  jbl秋: {len(jbl_fall_data)}行")
    if jbl_spring_data and jbl_fall_data:
        print(f"  比率: 春{len(jbl_spring_data) / (len(jbl_spring_data) + len(jbl_fall_data)) * 100:.1f}% vs 秋{len(jbl_fall_data) / (len(jbl_spring_data) + len(jbl_fall_data)) * 100:.1f}%")
        print(f"  合計: {len(jbl_spring_data) + len(jbl_fall_data)}行")
    
    # 3. バックアップデータ（重複除去前）を分析
    print("\n[3] バックアップデータ（重複除去前）の分析")
    backup_data = load_csv_with_encoding(backup_path)
    backup_1937_data = [row for row in backup_data if '1937' in str(row.get('year', '')).strip()]
    
    print(f"  総行数: {len(backup_1937_data)}行")
    
    # player_id + yearでグループ化
    key_to_rows = defaultdict(list)
    for row in backup_1937_data:
        player_id = str(row.get('player_id', '')).strip()
        year_val = str(row.get('year', '')).strip()
        key = (player_id, year_val)
        key_to_rows[key].append(row)
    
    print(f"  ユニークキー数（player_id + year）: {len(key_to_rows)}個")
    
    # 重複パターンの分析
    duplicate_patterns = defaultdict(int)
    for key, rows in key_to_rows.items():
        pattern = len(rows)
        duplicate_patterns[pattern] += 1
    
    print(f"\n  重複パターンの分布:")
    for pattern in sorted(duplicate_patterns.keys()):
        count = duplicate_patterns[pattern]
        total_rows = pattern * count
        print(f"    {pattern}行のキー: {count}個（合計{total_rows}行）")
    
    # 重複除去後の推定データ数
    print(f"\n  重複除去後の推定データ数（各キー1行と仮定）: {len(key_to_rows)}行")
    print(f"  実際の重複除去後のデータ数: {len(current_spring_data) + len(current_fall_data)}行")
    
    # 4. 統計データで重複除去した場合の分析
    print("\n[4] 統計データで重複除去した場合の分析")
    
    # 各キーについて統計データで重複除去
    deduplicated_by_stats = {}
    for key, rows in key_to_rows.items():
        seen_stats = {}
        deduplicated = []
        for row in rows:
            stats_key = create_stats_key(row)
            if stats_key not in seen_stats:
                seen_stats[stats_key] = row
                deduplicated.append(row)
        deduplicated_by_stats[key] = deduplicated
    
    total_deduplicated = sum(len(rows) for rows in deduplicated_by_stats.values())
    print(f"  統計データで重複除去後: {total_deduplicated}行")
    print(f"  重複除去された行数: {len(backup_1937_data) - total_deduplicated}行")
    
    # 各パターンごとの重複除去後の行数
    print(f"\n  各パターンごとの重複除去後の行数:")
    for pattern in sorted(duplicate_patterns.keys()):
        count = duplicate_patterns[pattern]
        keys_with_pattern = [key for key, rows in key_to_rows.items() if len(rows) == pattern]
        deduplicated_rows_for_pattern = sum(len(deduplicated_by_stats[key]) for key in keys_with_pattern)
        original_rows_for_pattern = pattern * count
        print(f"    {pattern}行のキー: {original_rows_for_pattern}行 -> {deduplicated_rows_for_pattern}行（{original_rows_for_pattern - deduplicated_rows_for_pattern}行除去）")
    
    # 5. 重複除去後のデータが2行（春秋）になるキーの分析
    print("\n[5] 重複除去後のデータが2行（春秋）になるキーの分析")
    
    two_row_keys = {key: rows for key, rows in deduplicated_by_stats.items() if len(rows) == 2}
    one_row_keys = {key: rows for key, rows in deduplicated_by_stats.items() if len(rows) == 1}
    three_plus_row_keys = {key: rows for key, rows in deduplicated_by_stats.items() if len(rows) >= 3}
    
    print(f"  1行のキー: {len(one_row_keys)}個")
    print(f"  2行のキー: {len(two_row_keys)}個（春秋が正しく分かれている）")
    print(f"  3行以上のキー: {len(three_plus_row_keys)}個（追加データあり）")
    
    if three_plus_row_keys:
        print(f"\n  3行以上のキーの詳細（最初の5個）:")
        for i, (key, rows) in enumerate(list(three_plus_row_keys.items())[:5], 1):
            player_id = key[0]
            print(f"    {i}. player_id: {player_id}")
            print(f"       行数: {len(rows)}行")
            for j, row in enumerate(rows, 1):
                g = safe_float(row.get('G', 0))
                pa = safe_float(row.get('PA', 0))
                h = safe_float(row.get('H', 0))
                print(f"         行{j}: G={g:.0f}, PA={pa:.0f}, H={h:.0f}")
    
    # 6. 理想的な分割（2行のキーは1行ずつ、1行のキーは適切に分割）を計算
    print("\n[6] 理想的な春秋分割の推定")
    
    # 2行のキー: 1行ずつ
    ideal_spring_from_2row = len(two_row_keys)
    ideal_fall_from_2row = len(two_row_keys)
    
    # 1行のキー: どちらかに分類（ここでは統計データで判定）
    ideal_spring_from_1row = 0
    ideal_fall_from_1row = 0
    
    for key, rows in one_row_keys.items():
        row = rows[0]
        g_value = safe_float(row.get('G', 0))
        pa_value = safe_float(row.get('PA', 0))
        
        if g_value < 30 and pa_value < 100:
            ideal_spring_from_1row += 1
        else:
            ideal_fall_from_1row += 1
    
    # 3行以上のキー: 適切に分割（実際のデータに基づく）
    ideal_spring_from_3plus = 0
    ideal_fall_from_3plus = 0
    
    for key, rows in three_plus_row_keys.items():
        # G+PAの合計が小さい順に並べて、上位2つを選ぶ
        sorted_rows = sorted(rows, key=lambda r: safe_float(r.get('G', 0)) + safe_float(r.get('PA', 0)))
        # 最小の1つを春、残りを秋とする
        ideal_spring_from_3plus += 1
        ideal_fall_from_3plus += len(sorted_rows) - 1
    
    ideal_spring_total = ideal_spring_from_2row + ideal_spring_from_1row + ideal_spring_from_3plus
    ideal_fall_total = ideal_fall_from_2row + ideal_fall_from_1row + ideal_fall_from_3plus
    
    print(f"  理想的な分割（推定）:")
    print(f"    2行のキーから: 春{ideal_spring_from_2row}行、秋{ideal_fall_from_2row}行")
    print(f"    1行のキーから: 春{ideal_spring_from_1row}行、秋{ideal_fall_from_1row}行")
    print(f"    3行以上のキーから: 春{ideal_spring_from_3plus}行、秋{ideal_fall_from_3plus}行")
    print(f"    合計: 春{ideal_spring_total}行、秋{ideal_fall_total}行")
    print(f"    比率: 春{ideal_spring_total / (ideal_spring_total + ideal_fall_total) * 100:.1f}% vs 秋{ideal_fall_total / (ideal_spring_total + ideal_fall_total) * 100:.1f}%")
    
    # 7. 現在のデータとの比較
    print("\n[7] 現在のデータとの比較")
    print(f"  現在のデータ:")
    print(f"    春: {len(current_spring_data)}行")
    print(f"    秋: {len(current_fall_data)}行")
    print(f"    比率: 春{len(current_spring_data) / (len(current_spring_data) + len(current_fall_data)) * 100:.1f}% vs 秋{len(current_fall_data) / (len(current_spring_data) + len(current_fall_data)) * 100:.1f}%")
    
    print(f"\n  理想的な分割（推定）:")
    print(f"    春: {ideal_spring_total}行")
    print(f"    秋: {ideal_fall_total}行")
    print(f"    比率: 春{ideal_spring_total / (ideal_spring_total + ideal_fall_total) * 100:.1f}% vs 秋{ideal_fall_total / (ideal_spring_total + ideal_fall_total) * 100:.1f}%")
    
    print(f"\n  差分:")
    spring_diff = len(current_spring_data) - ideal_spring_total
    fall_diff = len(current_fall_data) - ideal_fall_total
    print(f"    春: {spring_diff:+d}行")
    print(f"    秋: {fall_diff:+d}行")
    
    # 8. 結論
    print("\n" + "=" * 80)
    print("結論")
    print("=" * 80)
    
    print(f"\n[秋が多かった原因の分析]")
    
    # 元のバックアップデータでの分布を確認
    original_ratio_spring = ideal_spring_total / (ideal_spring_total + ideal_fall_total) * 100
    original_ratio_fall = ideal_fall_total / (ideal_spring_total + ideal_fall_total) * 100
    
    if original_ratio_fall > original_ratio_spring + 10:
        print(f"  1. 元のデータ（重複除去後）でも、秋の方が多い傾向がある")
        print(f"     理想的な分割: 春{original_ratio_spring:.1f}% vs 秋{original_ratio_fall:.1f}%")
    else:
        print(f"  1. 元のデータ（重複除去後）では、春秋のバランスは比較的均等")
        print(f"     理想的な分割: 春{original_ratio_spring:.1f}% vs 秋{original_ratio_fall:.1f}%")
    
    # jblデータとの比較
    if jbl_spring_data and jbl_fall_data:
        jbl_ratio_spring = len(jbl_spring_data) / (len(jbl_spring_data) + len(jbl_fall_data)) * 100
        jbl_ratio_fall = len(jbl_fall_data) / (len(jbl_spring_data) + len(jbl_fall_data)) * 100
        print(f"\n  2. jbl参照データ（スクレイピング済み）:")
        print(f"     春{len(jbl_spring_data)}行 vs 秋{len(jbl_fall_data)}行")
        print(f"     比率: 春{jbl_ratio_spring:.1f}% vs 秋{jbl_ratio_fall:.1f}%")
        
        if jbl_ratio_fall > jbl_ratio_spring:
            print(f"     → jblデータでも秋の方が多い傾向")
        else:
            print(f"     → jblデータでは春の方が多い傾向")
    
    # 重複の影響
    print(f"\n  3. 重複の影響:")
    print(f"     バックアップデータ（重複除去前）: {len(backup_1937_data)}行")
    print(f"     統計データで重複除去後: {total_deduplicated}行")
    print(f"     重複除去された行数: {len(backup_1937_data) - total_deduplicated}行")
    print(f"     この重複が、特に秋シーズンに偏って発生していた可能性")
    
    print(f"\n[最終的な結論]")
    if ideal_fall_total > ideal_spring_total:
        print(f"  → 元のデータでも秋の方がやや多いが、重複によりさらに偏りが大きくなっていた")
    else:
        print(f"  → 元のデータでは春秋のバランスは比較的均等で、重複が秋に集中していたため偏りが生じた")
    
    return 0


if __name__ == '__main__':
    exit(main())





















