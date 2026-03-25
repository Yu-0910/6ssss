#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_qualifying_csv_2025.py

2025年セ・パ成績CSVから、規定打席到達者だけを抽出した「規定打席到達版CSV」を作成する。

入力: _data/master_csv_calculated/batting_2025_CL_from_master.csv
      _data/master_csv_calculated/batting_2025_PL_from_master.csv
出力: _data/master_csv_calculated/batting_2025_CL_qualifying.csv
      _data/master_csv_calculated/batting_2025_PL_qualifying.csv

規定打席: 2025年は143試合 × 3.1 = 443（四捨五入）
"""

import csv
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


# 2025年規定打席（143試合 × 3.1 四捨五入）
MIN_PA_2025 = 443


def load_csv_with_encoding(csv_path: str) -> List[Dict[str, Any]]:
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


def get_pa_value(row: Dict[str, Any]) -> Optional[int]:
    """行からPA（打席）の値を取得。列は PA または 打席 を探す。"""
    for col in ('PA', 'pa', '打席'):
        if col in row and row[col] not in (None, ''):
            try:
                return int(float(str(row[col]).strip()))
            except (ValueError, TypeError):
                pass
    return None


def filter_qualifying_rows(
    rows: List[Dict[str, Any]],
    min_pa: int,
) -> List[Dict[str, Any]]:
    """PA >= min_pa の行のみを返す。"""
    result = []
    for row in rows:
        pa = get_pa_value(row)
        if pa is not None and pa >= min_pa:
            result.append(row)
    return result


def write_csv_with_same_columns(
    filepath: Path,
    rows: List[Dict[str, Any]],
    fieldnames: Optional[List[str]] = None,
    encoding: str = 'utf-8-sig',
) -> None:
    """同じ列順でCSVを書き出す。fieldnamesがNoneの場合は最初の行のキーを使用。"""
    if not rows:
        raise ValueError("書き出す行がありません")
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with open(filepath, 'w', encoding=encoding, newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def process_league(
    project_root: Path,
    league: str,
    min_pa: int = MIN_PA_2025,
) -> Tuple[int, int, Path]:
    """
    1リーグ分の規定打席到達版CSVを作成する。

    Returns:
        (元の行数, 規定到達者数, 出力ファイルパス)
    """
    data_dir = project_root / '_data' / 'master_csv_calculated'
    input_name = f'batting_2025_{league}_from_master.csv'
    output_name = f'batting_2025_{league}_qualifying.csv'
    input_path = data_dir / input_name
    output_path = data_dir / output_name

    if not input_path.exists():
        raise FileNotFoundError(f"入力ファイルがありません: {input_path}")

    rows = load_csv_with_encoding(str(input_path))
    fieldnames = list(rows[0].keys()) if rows else []
    qualified = filter_qualifying_rows(rows, min_pa)

    write_csv_with_same_columns(output_path, qualified, fieldnames=fieldnames)
    return len(rows), len(qualified), output_path


def main() -> int:
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    print("規定打席到達版CSV作成（2025年セ・パ）")
    print(f"規定打席: PA >= {MIN_PA_2025}")
    print()

    total_before = 0
    total_after = 0

    for league in ('CL', 'PL'):
        try:
            n_before, n_after, out_path = process_league(project_root, league)
            total_before += n_before
            total_after += n_after
            print(f"  {league}: {n_before}件 → {n_after}件（規定到達） → {out_path}")
        except FileNotFoundError as e:
            print(f"  {league}: スキップ - {e}")
        except Exception as e:
            print(f"  {league}: エラー - {e}")
            import traceback
            traceback.print_exc()
            return 1

    print()
    print(f"完了: 合計 {total_before}件 → {total_after}件（規定打席到達者のみ）")
    return 0


if __name__ == '__main__':
    sys.exit(main())
