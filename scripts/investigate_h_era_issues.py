#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H欠損とERA異常値の原因究明スクリプト。
該当行を抽出し、パターン分析を行う。
"""
import csv
import sys
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MASTER_DIR = PROJECT_ROOT / '_data' / 'master_csv__import_1950_2024'

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def safe_int(v):
    if v is None or v == '':
        return None
    try:
        return int(float(str(v).replace(',', '')))
    except (ValueError, TypeError):
        return None


def safe_float(v):
    if v is None or v == '':
        return None
    try:
        return float(str(v).replace(',', ''))
    except (ValueError, TypeError):
        return None


def main():
    print("=" * 70)
    print("H欠損・ERA異常値 原因究明")
    print("=" * 70)

    h_empty_samples = []   # (year, league, row)
    era_abnormal_samples = []  # (year, league, row, era_val)
    era_values_dist = defaultdict(int)
    h_empty_by_year_league = defaultdict(int)

    for path in sorted(MASTER_DIR.glob("pitching_*_*_from_master.csv")):
        m = __import__('re').match(r'pitching_(\d{4})_(PL|CL)_from_master\.csv', path.name)
        if not m:
            continue
        year, league = m.group(1), m.group(2)
        year_int = int(year)

        with open(path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            for ri, row in enumerate(reader):
                h_raw = (row.get('H') or '').strip()
                era_val = safe_float(row.get('ERA'))
                g = safe_int(row.get('G'))
                ip = safe_float(row.get('IP'))
                er = safe_int(row.get('ER'))
                bf = safe_int(row.get('BF'))
                name = (row.get('player_name_ja') or '').strip()

                # H欠損
                if not h_raw:
                    h_empty_by_year_league[(year, league)] += 1
                    if len(h_empty_samples) < 25:
                        h_empty_samples.append({
                            'year': year, 'league': league, 'row': ri + 2,
                            'name': name[:16], 'G': g, 'IP': ip, 'ER': er, 'BF': bf,
                            'BB': row.get('BB'), 'SO': row.get('SO'), 'HR': row.get('HR'),
                            'ERA': row.get('ERA'),
                        })

                # ERA異常 (0未満 or 50超)
                if era_val is not None and (era_val < 0 or era_val > 50):
                    era_values_dist[era_val] += 1
                    if len(era_abnormal_samples) < 30:
                        era_abnormal_samples.append({
                            'year': year, 'league': league, 'row': ri + 2,
                            'name': name[:16], 'G': g, 'IP': ip, 'ER': er, 'BF': bf,
                            'ERA': era_val, 'ERA_raw': row.get('ERA'),
                        })

    # --- H欠損 分析 ---
    print("\n" + "-" * 70)
    print("【1】H欠損 サンプル（最大25件）")
    print("-" * 70)
    for s in h_empty_samples[:25]:
        print(f"  {s['year']} {s['league']} 行{s['row']}: {s['name']:16} G={s['G']} IP={s['IP']} ER={s['ER']} BF={s['BF']} BB={s['BB']} SO={s['SO']} ERA={s['ERA']}")

    print("\n  H欠損の年度・リーグ別件数:")
    for (y, l), cnt in sorted(h_empty_by_year_league.items(), key=lambda x: (-int(x[0][0]), x[0][1])):
        print(f"    {y} {l}: {cnt}件")

    # H欠損の特徴: IP=0 の行か？ G=0 か？
    ip_zero = sum(1 for s in h_empty_samples if s['IP'] == 0 or s['IP'] is None)
    g_small = sum(1 for s in h_empty_samples if s['G'] is not None and s['G'] <= 2)
    print(f"\n  H欠損サンプル内: IP=0/None={ip_zero}件, G<=2={g_small}件")

    # --- ERA異常 分析 ---
    print("\n" + "-" * 70)
    print("【2】ERA異常値 サンプル（最大30件）")
    print("-" * 70)
    for s in era_abnormal_samples[:30]:
        print(f"  {s['year']} {s['league']} 行{s['row']}: {s['name']:16} G={s['G']} IP={s['IP']} ER={s['ER']} ERA={s['ERA']} (raw={s['ERA_raw']})")

    print("\n  ERA異常値の分布（値 -> 件数）:")
    for val in sorted(era_values_dist.keys(), key=lambda x: (x < 0, abs(x))):
        print(f"    ERA={val} -> {era_values_dist[val]}件")

    # ERA異常の特徴: IP=0 かつ ER>0 か？（無限大ERA）
    ip0_er_pos = [s for s in era_abnormal_samples if (s['IP'] == 0 or s['IP'] is None) and s['ER'] and s['ER'] > 0]
    print(f"\n  ERA異常サンプル内で IP=0/None かつ ER>0（無限大ERA想定）: {len(ip0_er_pos)}件")
    if ip0_er_pos:
        for s in ip0_er_pos[:5]:
            print(f"    {s['year']} {s['league']}: {s['name']} G={s['G']} IP={s['IP']} ER={s['ER']} ERA={s['ERA']}")

    # ERA異常で IP>0 のケース（列ずれの可能性）
    ip_pos_era_high = [s for s in era_abnormal_samples if s['IP'] and s['IP'] > 0 and s['ERA'] and s['ERA'] > 50]
    print(f"\n  ERA異常かつ IP>0（列ずれ・他原因の可能性）: {len(ip_pos_era_high)}件")
    if ip_pos_era_high:
        for s in ip_pos_era_high[:10]:
            print(f"    {s['year']} {s['league']}: {s['name']} G={s['G']} IP={s['IP']} ER={s['ER']} ERA={s['ERA']}")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
