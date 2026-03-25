#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERA異常のうち「再取得で直る可能性が高い行」だけを再取得（H/HP=0・オフセット-2済み）
して該当CSV行を更新する。

判定ルール:
  - IP>0 なのに ERA が計算値(ER*9/IP)から大きく乖離 -> 再取得対象
  - IP/ER/R の列整合が崩れている -> 再取得対象
  - IP=0 かつ ER>0 -> 「無限大ERA」カテゴリ（再取得対象外）

使い方:
  python -u scripts/fix_era_abnormal_770.py
  # 約2900行・1行あたり約0.2秒のため、完了まで約10〜15分。npb.jp へ接続できる環境で実行すること。

  python -u scripts/fix_era_abnormal_770.py --limit 500 --skip 0   # 先頭500件だけ
  python -u scripts/fix_era_abnormal_770.py --limit 500 --skip 500 # 501〜1000件目
"""
import csv
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MASTER_DIR = PROJECT_ROOT / '_data' / 'master_csv__import_1950_2024'


def safe_float(v: Any) -> Optional[float]:
    if v is None or v == '':
        return None
    try:
        return float(str(v).replace(',', ''))
    except (ValueError, TypeError):
        return None


def parse_ip_for_calc(ip_raw: Any) -> Optional[float]:
    """野球表記IP(例: 7.2=7回2/3)を計算用の十進に変換。"""
    if ip_raw is None:
        return None
    s = str(ip_raw).strip()
    if not s:
        return None
    s = s.replace(',', '')
    if '.' not in s:
        return safe_float(s)
    whole, frac = s.split('.', 1)
    if not whole:
        return None
    try:
        w = int(whole)
    except ValueError:
        return None
    # NPB投球回の小数部は 0,1,2 (= 0/3,1/3,2/3)
    if frac in ('0', '00'):
        return float(w)
    if frac == '1':
        return w + (1.0 / 3.0)
    if frac == '2':
        return w + (2.0 / 3.0)
    # 念のため通常小数にもフォールバック
    return safe_float(s)


def has_ip_er_r_integrity_issue(ip: Optional[float], er: Optional[float], r: Optional[float]) -> bool:
    """IP/ER/R の整合崩れを検知。"""
    if ip is not None and ip < 0:
        return True
    if er is not None and er < 0:
        return True
    if r is not None and r < 0:
        return True
    if er is not None and r is not None and er > r:
        return True
    return False


def is_large_era_gap(era: Optional[float], er: Optional[float], ip: Optional[float]) -> bool:
    """IP>0 のとき、ERAと計算値(ER*9/IP)の乖離を判定。"""
    if era is None or er is None or ip is None or ip <= 0:
        return False
    calc = (er * 9.0) / ip
    # 丸め誤差を避けつつ、明らかな列ずれを拾うしきい値
    return abs(era - calc) > 0.6


def collect_era_abnormal_rows() -> Tuple[List[Tuple[Path, int, Dict[str, Any]]], int]:
    """
    全CSVから以下を収集:
      - 再取得対象: (path, row_idx, row)
      - 無限大ERAカテゴリ件数: ip=0 かつ er>0
    """
    out: List[Tuple[Path, int, Dict[str, Any]]] = []
    infinite_era_count = 0
    for path in sorted(MASTER_DIR.glob("pitching_*_*_from_master.csv")):
        with open(path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        for i, row in enumerate(rows):
            era = safe_float(row.get('ERA'))
            er = safe_float(row.get('ER'))
            r = safe_float(row.get('R'))
            ip = parse_ip_for_calc(row.get('IP'))
            pid = (row.get('player_id') or '').strip()
            if not pid:
                continue

            if ip is not None and ip == 0 and er is not None and er > 0:
                infinite_era_count += 1
                continue

            if has_ip_er_r_integrity_issue(ip, er, r) or is_large_era_gap(era, er, ip):
                out.append((path, i, row))
    return out, infinite_era_count


def main():
    import argparse
    parser = argparse.ArgumentParser(description='ERA異常行を再取得してCSVを更新')
    parser.add_argument('--limit', type=int, default=None, help='処理する最大行数（未指定で全件）')
    parser.add_argument('--skip', type=int, default=0, help='先頭からスキップする行数')
    parser.add_argument('--min-year', type=int, default=None, help='この年度以上のみ処理')
    parser.add_argument('--max-year', type=int, default=None, help='この年度以下のみ処理')
    args = parser.parse_args()

    sys.path.insert(0, str(PROJECT_ROOT))
    _get_2004 = _get_2025 = None

    def get_fresh(pid: str, name: str, team: str, league: str, year: int):
        nonlocal _get_2004, _get_2025
        if year >= 2025:
            if _get_2025 is None:
                from scripts.scrape_2025_pitching_via_roster import get_player_pitching_for_year as _get_2025
            return _get_2025(pid, name, team, league, year)
        if _get_2004 is None:
            from scripts.scrape_2004_pitching_via_all_players import get_player_pitching_for_year as _get_2004
        return _get_2004(pid, name, team, league, year)

    items, infinite_era_count = collect_era_abnormal_rows()
    if args.min_year is not None:
        items = [x for x in items if int((x[2].get('year') or '0')) >= args.min_year]
    if args.max_year is not None:
        items = [x for x in items if int((x[2].get('year') or '0')) <= args.max_year]
    if args.skip > 0 or (args.limit is not None and args.limit < len(items)):
        end = (args.skip + args.limit) if args.limit is not None else None
        items = items[args.skip:end]
    print(
        f"再取得対象: {len(items)} 行 (skip={args.skip}, limit={args.limit if args.limit is not None else 'all'}) / "
        f"無限大ERAカテゴリ(IP=0,ER>0): {infinite_era_count} 行",
        flush=True,
    )

    # ファイルごとに 行インデックス -> 再取得した1行（辞書）
    updates_by_path: Dict[Path, Dict[int, Dict[str, Any]]] = {}
    failed = 0

    for idx, (path, row_idx, row) in enumerate(items):
        year = int((row.get('year') or '').strip())
        league = (row.get('league') or '').strip()
        team = (row.get('team') or '').strip()
        pid = (row.get('player_id') or '').strip()
        name = (row.get('player_name_ja') or '').strip()
        if not pid or not name:
            continue

        fresh = get_fresh(pid, name, team, league, year)
        if fresh is None:
            time.sleep(0.5)
            fresh = get_fresh(pid, name, team, league, year)
        if fresh is None:
            failed += 1
            if failed <= 20:
                print(f"  取得失敗: {year} {league} {name} ({pid})", flush=True)
            continue

        if path not in updates_by_path:
            updates_by_path[path] = {}
        updates_by_path[path][row_idx] = fresh

        if (idx + 1) % 100 == 0:
            print(f"  ... {idx + 1}/{len(items)} 完了")
        time.sleep(0.18)

    print(f"再取得成功: {sum(len(u) for u in updates_by_path.values())} 行  失敗: {failed} 件", flush=True)

    # 該当CSVを読み、該当行だけ fresh で上書きして保存
    for path, updates in updates_by_path.items():
        with open(path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)
        for row_idx, fresh in updates.items():
            if row_idx >= len(rows):
                continue
            row = rows[row_idx]
            for k in fieldnames:
                if k in fresh:
                    v = fresh[k]
                    row[k] = '' if v is None else str(v)
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            w.writeheader()
            w.writerows(rows)
        print(f"  更新: {path.name} ({len(updates)} 行)", flush=True)
    print("完了。", flush=True)


if __name__ == '__main__':
    main()
