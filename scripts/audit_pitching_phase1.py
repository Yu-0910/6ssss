#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1 投手CSV 監査・検証スクリプト
以前発生した課題（打者混入、BB/SO/H欠損、ERA異常等）を中心に全年度を監査する。
"""
import csv
import io
import sys
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MASTER_DIR = PROJECT_ROOT / '_data' / 'master_csv__import_1950_2024'

if sys.platform == 'win32':
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


def audit_file(path: Path) -> dict:
    """1ファイルを監査。以前の課題観点でチェック"""
    result = {
        'path': path.name,
        'year': '',
        'league': '',
        'total': 0,
        'issues': [],
        'stats': {},
    }
    try:
        with open(path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        result['issues'].append(f'読み込みエラー: {e}')
        return result

    result['total'] = len(rows)
    m = __import__('re').match(r'pitching_(\d{4})_(PL|CL)_from_master\.csv', path.name)
    if m:
        result['year'] = m.group(1)
        result['league'] = m.group(2)
    year_int = int(result['year']) if result['year'].isdigit() else 0

    # 課題1: 打者混入（GとIP両方空でBF>0）
    empty_g_ip = 0
    empty_g_ip_bf = 0
    empty_bb = 0
    empty_so = 0
    empty_h = 0
    empty_g = 0
    empty_ip = 0
    abnormal_era = 0
    logic_hr_gt_h = 0
    empty_player_id = 0
    batter_names = set()  # 打者混入の疑いがある選手名

    for row in rows:
        g = safe_int(row.get('G'))
        ip = safe_float(row.get('IP'))
        h = safe_int(row.get('H'))
        bb = safe_int(row.get('BB'))
        so = safe_int(row.get('SO'))
        bf = safe_int(row.get('BF'))
        hr = safe_int(row.get('HR'))
        era = safe_float(row.get('ERA'))
        pid = (row.get('player_id') or '').strip()
        name = (row.get('player_name_ja') or '').strip()

        if (g is None or row.get('G','').strip() == '') and (ip is None or row.get('IP','').strip() == ''):
            empty_g_ip += 1
            if bf is not None and bf > 0:
                empty_g_ip_bf += 1
                batter_names.add(name[:20])

        if not (row.get('G') or '').strip():
            empty_g += 1
        if not (row.get('IP') or '').strip():
            empty_ip += 1
        if not (row.get('BB') or '').strip():
            empty_bb += 1
        if not (row.get('SO') or '').strip():
            empty_so += 1
        if not (row.get('H') or '').strip():
            empty_h += 1
        if not pid:
            empty_player_id += 1

        if era is not None and (era < 0 or era > 50):
            abnormal_era += 1
        if h is not None and hr is not None and h >= 0 and hr > h:
            logic_hr_gt_h += 1

    result['stats'] = {
        'empty_G_IP_bf': empty_g_ip_bf,
        'empty_BB': empty_bb,
        'empty_SO': empty_so,
        'empty_H': empty_h,
        'empty_G': empty_g,
        'empty_IP': empty_ip,
        'abnormal_ERA': abnormal_era,
        'logic_HR_gt_H': logic_hr_gt_h,
        'empty_player_id': empty_player_id,
        'batter_names': list(batter_names)[:5],
    }

    # 課題に該当するか判定
    if empty_g_ip_bf > 0:
        result['issues'].append(f'打者混入疑い: {empty_g_ip_bf}件 (G,IP空かつBF>0)')
    if empty_bb > 0 and year_int >= 2005:
        result['issues'].append(f'BB欠損: {empty_bb}件')
    if empty_so > 0 and year_int >= 2005:
        result['issues'].append(f'SO欠損: {empty_so}件')
    if empty_h > 0:
        result['issues'].append(f'H欠損: {empty_h}件')
    if abnormal_era > 0:
        result['issues'].append(f'ERA異常値: {abnormal_era}件')
    if logic_hr_gt_h > 0:
        result['issues'].append(f'H<HR矛盾: {logic_hr_gt_h}件')
    if empty_player_id == len(rows) and len(rows) > 0:
        result['issues'].append('player_id全空')

    return result


def main():
    print("=" * 70)
    print("Phase 1 投手CSV 監査・検証（以前発生した課題を中心に）")
    print("=" * 70)
    print(f"対象: {MASTER_DIR}")
    if not MASTER_DIR.exists():
        print("対象ディレクトリが存在しません")
        return

    files = sorted(MASTER_DIR.glob("pitching_*_*_from_master.csv"))
    print(f"ファイル数: {len(files)}")

    # 年度別・リーグ別に監査
    by_year = defaultdict(dict)
    for path in files:
        r = audit_file(path)
        y, l = r['year'], r['league']
        if y and l:
            by_year[y][l] = r

    # 2005年以降と2004年以前で分けて集計
    years_sorted = sorted(by_year.keys(), key=int, reverse=True)
    issues_2005plus = []
    issues_2004minus = []
    ok_2005plus = []
    ok_2004minus = []

    for year in years_sorted:
        for league in ('PL', 'CL'):
            r = by_year[year].get(league)
            if not r:
                continue
            y = int(year)
            line = f"{year} {league}: {r['total']}件"
            if r['issues']:
                line += " | " + "; ".join(r['issues'])
                if y >= 2005:
                    issues_2005plus.append(line)
                else:
                    issues_2004minus.append(line)
            else:
                if y >= 2005:
                    ok_2005plus.append(f"{year} {league}: {r['total']}件")
                else:
                    ok_2004minus.append(f"{year} {league}: {r['total']}件")

    print("\n" + "-" * 70)
    print("【2005年以降】")
    print("-" * 70)
    if issues_2005plus:
        print("課題あり:")
        for ln in issues_2005plus[:30]:
            print("  [!]", ln)
        if len(issues_2005plus) > 30:
            print(f"  ... 他 {len(issues_2005plus)-30} 件")
    print(f"問題なし: {len(ok_2005plus)} ファイル")
    if ok_2005plus and len(ok_2005plus) <= 10:
        for ln in ok_2005plus:
            print("  [OK]", ln)

    print("\n" + "-" * 70)
    print("【2004年以前】")
    print("-" * 70)
    if issues_2004minus:
        print("課題あり:")
        for ln in issues_2004minus[:30]:
            print("  [!]", ln)
        if len(issues_2004minus) > 30:
            print(f"  ... 他 {len(issues_2004minus)-30} 件")
    print(f"問題なし: {len(ok_2004minus)} ファイル")
    if ok_2004minus and len(ok_2004minus) <= 10:
        for ln in ok_2004minus[:10]:
            print("  [OK]", ln)
    elif len(ok_2004minus) > 10:
        print(f"  (例) {ok_2004minus[0]}, ...")

    # 打者混入チェック: 先頭行の様子
    for sample in ["2024_CL", "2024_PL", "2004_CL", "2004_PL"]:
        parts = sample.split("_")
        if len(parts) == 2:
            y, l = parts[0], parts[1]
            p = MASTER_DIR / f"pitching_{y}_{l}_from_master.csv"
            if p.exists():
                print(f"\n--- {sample} 先頭5行 G,IP,H,BB,SO ---")
                with open(p, encoding='utf-8-sig') as f:
                    for i, row in enumerate(csv.DictReader(f)):
                        if i >= 5:
                            break
                        g = row.get('G','') or ''
                        ip = row.get('IP','') or ''
                        h = row.get('H','') or ''
                        bb = row.get('BB','') or ''
                        so = row.get('SO','') or ''
                        name = (row.get('player_name_ja') or '')[:14]
                        print(f"  {i+1}: {name:14} G={str(g):4} IP={str(ip):6} H={str(h):4} BB={str(bb):4} SO={str(so):4}")

    print("\n" + "=" * 70)
    print("監査完了")
    print("=" * 70)


if __name__ == '__main__':
    main()
