#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投手CSVの品質調査スクリプト。
欠損値・異常値・論理矛盾・重複・データソース別の傾向をチェックする。
"""
import csv
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import sys
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MASTER_DIR = PROJECT_ROOT / '_data' / 'master_csv__import_1950_2024'
CALC_DIR = PROJECT_ROOT / '_data' / 'master_csv_calculated'


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


def analyze_file(path: Path, is_calculated: bool) -> dict:
    """1ファイルを分析"""
    issues = defaultdict(list)
    stats = defaultdict(int)
    with open(path, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames or []

    stats['total_rows'] = len(rows)
    year = path.stem.split('_')[1] if '_' in path.stem else ''
    league = path.stem.split('_')[2] if '_' in path.stem else ''

    # 必須列
    num_cols = ['G', 'IP', 'H', 'BB', 'SO', 'BF', 'ER', 'R', 'W', 'L']
    for ri, row in enumerate(rows):
        row_id = f"{row.get('player_name_ja','')}({row.get('team','')})"

        # 1. 欠損: 投手として必須の列が空
        g = safe_int(row.get('G'))
        ip = safe_float(row.get('IP'))
        h = safe_int(row.get('H'))
        bb = safe_int(row.get('BB'))
        so = safe_int(row.get('SO'))
        bf = safe_int(row.get('BF'))

        empty_g = g is None or row.get('G','').strip() == ''
        empty_ip = ip is None or row.get('IP','').strip() == ''
        empty_h = h is None or row.get('H','').strip() == ''
        empty_bb = bb is None or row.get('BB','').strip() == ''
        empty_so = so is None or row.get('SO','').strip() == ''

        if empty_g:
            stats['empty_G'] += 1
        if empty_ip:
            stats['empty_IP'] += 1
        if empty_h:
            stats['empty_H'] += 1
        if empty_bb:
            stats['empty_BB'] += 1
        if empty_so:
            stats['empty_SO'] += 1

        # 投手なのに G,IP が両方空 → 打者データ混入の疑い（打者表の行が誤って取り込まれた）
        if empty_g and empty_ip:
            if bf is not None and bf > 0:
                stats['suspected_batter_rows'] += 1
                if len(issues['suspected_batter']) < 5:
                    issues['suspected_batter'].append(f"行{ri+2}: {row_id} G/IP空だがBF={bf}")

        # 2. 異常値
        if ip is not None and (ip < 0 or ip > 500):
            stats['abnormal_IP'] += 1
            issues['abnormal_IP'].append(f"行{ri+2}: {row_id} IP={ip}")

        if g is not None and (g < 0 or g > 100):
            stats['abnormal_G'] += 1

        era_val = safe_float(row.get('ERA'))
        if era_val is not None and (era_val < 0 or era_val > 100):
            stats['abnormal_ERA'] += 1
            if len(issues['abnormal_ERA']) < 5:
                issues['abnormal_ERA'].append(f"行{ri+2}: {row_id} ERA={era_val}")

        # 3. 論理矛盾
        if g is not None and ip is not None and ip > 0:
            # 1試合あたり平均30球以下は稀、0.1未満/IPは異常
            if ip > 0 and g > 0 and ip / g < 0.1:
                stats['logic_IP_per_G'] += 1

        if h is not None and h >= 0:
            hr_val = safe_int(row.get('HR'))
            if hr_val is not None and hr_val > h:
                stats['logic_HR_gt_H'] += 1
                issues['logic_HR_gt_H'].append(f"行{ri+2}: {row_id} H={h} < HR={hr_val}")

        if bf is not None and so is not None and bf > 0 and so > bf:
            stats['logic_SO_gt_BF'] += 1

        # 4. player_id 空
        if not (row.get('player_id') or '').strip():
            stats['empty_player_id'] += 1

        # 5. 投球回の野球表記 (.1/.2) 検出
        if ip is not None and ip > 0:
            whole = int(ip)
            frac = ip - whole
            if abs(frac - 0.1) < 0.01 or abs(frac - 0.2) < 0.01:
                stats['baseball_IP_notation'] += 1

    # 6. 重複（名前+チーム+年度で同一）
    seen = {}
    for ri, row in enumerate(rows):
        key = (row.get('player_name_ja',''), row.get('team',''))
        if key in seen:
            stats['duplicates'] += 1
            if len(issues['duplicates']) < 3:
                issues['duplicates'].append(f"{key} が重複")
        seen[key] = ri

    # 7. year/league とファイル名の一致
    for row in rows:
        ry = row.get('year','')
        rl = row.get('league','')
        if year and ry and str(ry) != str(year):
            stats['year_mismatch'] += 1
            break
        if league and rl and rl != league:
            stats['league_mismatch'] += 1
            break

    return {
        'path': str(path),
        'year': year,
        'league': league,
        'is_calculated': is_calculated,
        'stats': dict(stats),
        'issues': {k: v for k, v in issues.items() if v}
    }


def main():
    print("=" * 60)
    print("投手CSV 品質調査")
    print("=" * 60)

    # サンプル: 直近数年 + 数年の古い年度
    sample_years = [2024, 2023, 2022, 2021, 2015, 2010, 2005, 2004]
    all_results = []
    summary = defaultdict(lambda: defaultdict(int))

    for base_dir, is_calc in [(MASTER_DIR, False), (CALC_DIR, True)]:
        label = "計算済み" if is_calc else "生データ"
        if not base_dir.exists():
            print(f"\n⚠️ {base_dir} が存在しません")
            continue

        print(f"\n--- {label} ({base_dir.name}) ---")
        for year in sample_years:
            for league in ('CL', 'PL'):
                fname = f"pitching_{year}_{league}_from_master.csv"
                path = base_dir / fname
                if not path.exists():
                    continue
                r = analyze_file(path, is_calc)
                all_results.append(r)
                s = r['stats']
                print(f"\n{year} {league}: {s.get('total_rows',0)}件", end="")
                problems = []
                if s.get('empty_BB', 0) or s.get('empty_SO', 0):
                    problems.append(f"BB空{s.get('empty_BB',0)} SO空{s.get('empty_SO',0)}")
                if s.get('empty_H', 0):
                    problems.append(f"H空{s.get('empty_H',0)}")
                if s.get('suspected_batter_rows', 0):
                    problems.append(f"打者混入疑い{s.get('suspected_batter_rows',0)}")
                if s.get('empty_player_id', 0) == s.get('total_rows', 0) and s.get('total_rows', 0) > 0:
                    problems.append("player_id全空")
                if s.get('abnormal_ERA', 0):
                    problems.append(f"ERA異常{s.get('abnormal_ERA',0)}")
                if s.get('logic_HR_gt_H', 0):
                    problems.append(f"H<HR矛盾{s.get('logic_HR_gt_H',0)}")
                if problems:
                    print("  [!] " + ", ".join(problems))
                else:
                    print("  ✓")
                for k, v in s.items():
                    if v > 0 and k != 'total_rows':
                        summary[k][label] += v

    # サマリー
    print("\n" + "=" * 60)
    print("全体サマリー（サンプル年度合計）")
    print("=" * 60)
    for k in sorted(summary.keys()):
        vals = summary[k]
        print(f"  {k}: {dict(vals)}")

    # 追加: 生データの先頭数行の様子（打者混入チェック）
    raw_2024 = MASTER_DIR / "pitching_2024_CL_from_master.csv"
    if raw_2024.exists():
        print("\n--- 2024 CL 生データ 先頭10行の G,IP,H,BB,SO ---")
        with open(raw_2024, encoding='utf-8-sig') as f:
            r = csv.DictReader(f)
            for i, row in enumerate(r):
                if i >= 10:
                    break
                g, ip, h, bb, so = row.get('G',''), row.get('IP',''), row.get('H',''), row.get('BB',''), row.get('SO','')
                print(f"  {i+1}: {row.get('player_name_ja','')[:12]:12} G={str(g):4} IP={str(ip):6} H={str(h):4} BB={str(bb):4} SO={str(so):4}")


if __name__ == '__main__':
    main()
