#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2025年新規NPB加入選手の成績を、バックアップからCLの from_master に組み込む。

- 報告書（2025_new_players_report.csv）に載っているCL所属の新選手のうち、
  batting_2025_CL_from_master.csv にいない者について、
  _backup_2025_from_master/batting_2025_CL_from_master.csv から該当行を取得し、
  現在のCL from_master の列形式に変換して追加する。
- 現在のCL CSVは npb_batting 形式（列: 1B, IsoP, IsoD, IOPS, BB%, K%, BB/K, BABIP, GPA, NOI, SecA, TA）。
- バックアップは TopPage 形式（列: 打率, 安打, 単打, IsoP, IsoD, ...）なのでマッピングする。
"""

import csv
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# 追加する新選手 (player_name_ja, team)
NEW_CL_PLAYERS = [
    ('ファビアン', '広島東洋カープ'),
    ('キャベッジ', '読売ジャイアンツ'),
    ('ボスラー', '中日ドラゴンズ'),
]

# バックアップ列名 -> 現在列名（同じなら省略可）
BACKUP_TO_CURRENT = {
    '単打': '1B',
    '打率': 'AVG',
    '出塁率': 'OBP',
    '長打率': 'SLG',
}


def load_csv(path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    for enc in ('utf-8-sig', 'utf-8', 'shift_jis', 'cp932'):
        try:
            with open(path, 'r', encoding=enc) as f:
                r = csv.DictReader(f)
                header = list(r.fieldnames or [])
                rows = list(r)
                return (header, rows)
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    raise ValueError(f"Cannot read {path}")


def normalize_name(name: str) -> str:
    if not name:
        return ''
    n = (name or '').strip().replace('\u3000', ' ').replace('　', ' ')
    return re.sub(r'\s+', ' ', n)


def find_row(rows: List[Dict], name: str, team: str) -> Optional[Dict[str, Any]]:
    key_name = normalize_name(name)
    for r in rows:
        r_name = normalize_name(r.get('player_name_ja') or r.get('name') or '')
        r_team = (r.get('team') or r.get('Team') or '').strip()
        if r_name == key_name and r_team == team:
            return r
    return None


def map_backup_row_to_current(backup_row: Dict, current_header: List[str]) -> Dict[str, Any]:
    """バックアップの1行を現在のCL CSVの列形式に変換する。"""
    row = {}
    for col in current_header:
        if col in backup_row and backup_row[col] != '':
            row[col] = backup_row[col]
            continue
        src = BACKUP_TO_CURRENT.get(col)
        if src and src in backup_row and backup_row[src] != '':
            row[col] = backup_row[src]
            continue
        if col == 'year':
            row[col] = 2025
        elif col == 'league':
            row[col] = 'CL'
        elif col == 'team':
            row[col] = backup_row.get('team', '')
        elif col == 'player_name_ja':
            row[col] = backup_row.get('player_name_ja', '')
        elif col == 'player_name_en':
            row[col] = backup_row.get('player_name_en', '')
        elif col == '1B':
            try:
                h = float(backup_row.get('H') or backup_row.get('安打') or 0)
                d2 = float(backup_row.get('2B') or backup_row.get('二塁打') or 0)
                d3 = float(backup_row.get('3B') or backup_row.get('三塁打') or 0)
                hr = float(backup_row.get('HR') or backup_row.get('本塁打') or 0)
                row[col] = int(h - d2 - d3 - hr) if h else ''
            except (TypeError, ValueError):
                row[col] = backup_row.get('単打', '')
        elif col == 'IOPS':
            try:
                iso = float(backup_row.get('IsoP') or 0)
                isod = float(backup_row.get('IsoD') or 0)
                row[col] = round(iso + isod, 4) if (iso or isod) else ''
            except (TypeError, ValueError):
                row[col] = ''
        else:
            row[col] = backup_row.get(col, '')
    return row


def main() -> int:
    calculated_dir = PROJECT_ROOT / '_data' / 'master_csv_calculated'
    backup_path = calculated_dir / '_backup_2025_from_master' / 'batting_2025_CL_from_master.csv'
    current_path = calculated_dir / 'batting_2025_CL_from_master.csv'

    if not backup_path.exists():
        print(f"ERROR: バックアップが見つかりません: {backup_path}")
        return 1
    if not current_path.exists():
        print(f"ERROR: 現在のCL CSVが見つかりません: {current_path}")
        return 1

    backup_header, backup_rows = load_csv(backup_path)
    current_header, current_rows = load_csv(current_path)

    existing = set()
    for r in current_rows:
        name = normalize_name(r.get('player_name_ja') or r.get('name') or '')
        team = (r.get('team') or r.get('Team') or '').strip()
        if name and team:
            existing.add((name, team))

    added = 0
    for name, team in NEW_CL_PLAYERS:
        if (normalize_name(name), team) in existing:
            print(f"  スキップ（既に存在）: {name} ({team})")
            continue
        backup_row = find_row(backup_rows, name, team)
        if not backup_row:
            print(f"  WARN: バックアップに成績なし: {name} ({team}) → 0で追加は行いません")
            continue
        new_row = map_backup_row_to_current(backup_row, current_header)
        current_rows.append(new_row)
        existing.add((normalize_name(name), team))
        added += 1
        print(f"  追加: {name} ({team})")

    if added == 0:
        print("追加する新選手はいませんでした。")
        return 0

    with open(current_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=current_header, extrasaction='ignore')
        w.writeheader()
        w.writerows(current_rows)
    print(f"保存: {current_path.name} ({len(current_rows)}行, +{added}件)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
