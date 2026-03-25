#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""報告書の player_name_en を batting_2025_*_from_master.csv に反映する。"""
import csv
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


def normalize(s: str) -> str:
    return re.sub(r'[\s　\u3000]+', '', (s or '').strip())


def main():
    report_path = PROJECT_ROOT / '_data' / 'reports' / '2025_new_players_report.csv'
    calculated_dir = PROJECT_ROOT / '_data' / 'master_csv_calculated'
    report_en = {}
    for enc in ('utf-8-sig', 'utf-8'):
        try:
            with open(report_path, 'r', encoding=enc) as f:
                for row in csv.DictReader(f):
                    name = (row.get('player_name_ja') or '').strip()
                    team = (row.get('team') or '').strip()
                    en = (row.get('player_name_en') or '').strip()
                    if name and team and en:
                        report_en[(normalize(name), team)] = en
            break
        except Exception:
            continue
    for league in ('CL', 'PL'):
        path = calculated_dir / f'batting_2025_{league}_from_master.csv'
        if not path.exists():
            continue
        with open(path, 'r', encoding='utf-8-sig') as f:
            r = csv.DictReader(f)
            h = list(r.fieldnames or [])
            rows = list(r)
        if 'player_name_en' not in h:
            h.append('player_name_en')
        n = 0
        for row in rows:
            name = normalize((row.get('player_name_ja') or '').strip())
            team = (row.get('team') or row.get('Team') or '').strip()
            if (name, team) in report_en:
                row['player_name_en'] = report_en[(name, team)]
                n += 1
        if n > 0:
            with open(path, 'w', encoding='utf-8-sig', newline='') as f:
                w = csv.DictWriter(f, fieldnames=h, extrasaction='ignore')
                w.writeheader()
                w.writerows(rows)
            print(f"{path.name}: {n} 行を報告書の英字名で更新")


if __name__ == '__main__':
    main()
