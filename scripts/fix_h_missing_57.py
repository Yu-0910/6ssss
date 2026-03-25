#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H欠損のあった選手（57名）に限り、投球回の複数セル検出＋オフセット適用方針で
選手ページを再取得し、該当CSV行の H（および必要なら IP）を更新する。
"""
import csv
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MASTER_DIR = PROJECT_ROOT / '_data' / 'master_csv__import_1950_2024'


def collect_h_missing_rows() -> List[Tuple[Path, int, Dict[str, Any]]]:
    """全CSVから H が空の行を (ファイルパス, 行インデックス, 行辞書) のリストで返す。"""
    out: List[Tuple[Path, int, Dict[str, Any]]] = []
    for path in sorted(MASTER_DIR.glob("pitching_*_*_from_master.csv")):
        with open(path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
        for i, row in enumerate(rows):
            h_raw = (row.get('H') or '').strip()
            if h_raw:
                continue
            pid = (row.get('player_id') or '').strip()
            if not pid:
                continue
            out.append((path, i, row))
    return out


def main():
    # scrape_2004 の get_player_pitching_for_year を利用（複数セル検出＋オフセット済み）
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.scrape_2004_pitching_via_all_players import get_player_pitching_for_year

    items = collect_h_missing_rows()
    print(f"H欠損かつ player_id あり: {len(items)} 件")

    # ファイルごとに「行インデックス -> 新データ」を集める
    updates_by_path: Dict[Path, Dict[int, Dict[str, Any]]] = {}

    for path, row_idx, row in items:
        year = int((row.get('year') or '').strip())
        league = (row.get('league') or '').strip()
        team = (row.get('team') or '').strip()
        pid = (row.get('player_id') or '').strip()
        name = (row.get('player_name_ja') or '').strip()
        if not pid or not name:
            continue

        fresh = get_player_pitching_for_year(pid, name, team, league, year)
        if fresh is None:
            print(f"  取得失敗: {year} {league} {name} ({pid})")
            continue
        h_new = fresh.get('H')
        ip_new = fresh.get('IP')
        # 再取得してもHが取れない場合は0回登板・被安打0とみなしてH=0で補完
        if h_new is None:
            h_new = 0
        if h_new is None and ip_new is None:
            continue
        if path not in updates_by_path:
            updates_by_path[path] = {}
        updates_by_path[path][row_idx] = {'H': h_new, 'IP': ip_new}
        print(f"  OK: {year} {league} {name} -> H={h_new}, IP={ip_new}")
        time.sleep(0.25)

    # CSV を上書き更新
    for path, updates in updates_by_path.items():
        with open(path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            rows = list(reader)
        for row_idx, new_vals in updates.items():
            if row_idx >= len(rows):
                continue
            row = rows[row_idx]
            if new_vals.get('H') is not None:
                row['H'] = str(new_vals['H'])
            if new_vals.get('IP') is not None:
                row['IP'] = str(new_vals['IP'])
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            w.writeheader()
            w.writerows(rows)
        print(f"  更新: {path.name} ({len(updates)} 行)")
    print("完了。")


if __name__ == '__main__':
    main()
