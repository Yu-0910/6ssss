#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2025年の17行（IP>0, ER=0, ERA>50の列ずれ）のみ、
scrape_2025 で再取得して該当行を更新する。
"""
import csv
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MASTER_DIR = PROJECT_ROOT / '_data' / 'master_csv__import_1950_2024'


def parse_ip(s):
    if s is None or not str(s).strip():
        return None
    s = str(s).strip().replace(',', '')
    if '.' not in s:
        try:
            return float(s)
        except ValueError:
            return None
    a, b = s.split('.', 1)
    try:
        w = int(a)
    except ValueError:
        return None
    if b in ('0', '00'):
        return float(w)
    if b == '1':
        return w + 1 / 3
    if b == '2':
        return w + 2 / 3
    try:
        return float(s)
    except ValueError:
        return None


def collect_17():
    out = []
    for path in sorted(MASTER_DIR.glob("pitching_2025_*_from_master.csv")):
        with open(path, encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
        for i, row in enumerate(rows):
            if (row.get('year') or '').strip() != '2025':
                continue
            try:
                era = float((row.get('ERA') or '').replace(',', ''))
            except (ValueError, TypeError):
                continue
            if era <= 50:
                continue
            ip = parse_ip(row.get('IP'))
            er = row.get('ER')
            try:
                er_val = float(er) if (er or '').strip() else None
            except (ValueError, TypeError):
                er_val = None
            if ip is None or ip <= 0:
                continue
            if er_val is not None and er_val > 0:
                continue
            pid = (row.get('player_id') or '').strip()
            if not pid:
                continue
            out.append((path, i, row))
    return out


def main():
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.scrape_2025_pitching_via_roster import get_player_pitching_for_year

    items = collect_17()
    print(f"修正対象: {len(items)} 行", flush=True)

    updates = {}
    for path, row_idx, row in items:
        pid = (row.get('player_id') or '').strip()
        name = (row.get('player_name_ja') or '').strip()
        team = (row.get('team') or '').strip()
        league = (row.get('league') or '').strip()
        if not pid or not name:
            continue
        fresh = get_player_pitching_for_year(pid, name, team, league, 2025)
        if fresh is None:
            print(f"  取得失敗: {name} ({pid})", flush=True)
            continue
        if path not in updates:
            updates[path] = {}
        updates[path][row_idx] = fresh
        print(f"  OK: {name}", flush=True)
        time.sleep(0.2)

    for path, up in updates.items():
        with open(path, encoding='utf-8-sig') as f:
            fn = list((csv.DictReader(f).fieldnames or []))
            f.seek(0)
            rows = list(csv.DictReader(f))
        for ri, fresh in up.items():
            if ri >= len(rows):
                continue
            for k in fn:
                if k in fresh:
                    v = fresh[k]
                    rows[ri][k] = '' if v is None else str(v)
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fn, extrasaction='ignore')
            w.writeheader()
            w.writerows(rows)
        print(f"  更新: {path.name} ({len(up)} 行)", flush=True)
    print("完了。", flush=True)


if __name__ == '__main__':
    main()
