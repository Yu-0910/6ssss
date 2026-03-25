#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H または BB が空の選手の共通特徴を分析"""
import csv
import re
from pathlib import Path

data_dir = Path(__file__).parent.parent / '_data' / 'master_csv__import_1950_2024'
empty_rows = []
for f in sorted(data_dir.glob('pitching_*_*_from_master.csv')):
    m = re.match(r'pitching_(\d{4})_(PL|CL)', f.name)
    if not m:
        continue
    year, league = int(m.group(1)), m.group(2)
    with open(f, 'r', encoding='utf-8-sig') as fp:
        for row in csv.DictReader(fp):
            h = (row.get('H') or '').strip()
            bb = (row.get('BB') or '').strip()
            ip_s = (row.get('IP') or '').strip()
            g_s = (row.get('G') or '').strip()
            if not h or not bb:
                try:
                    ip = float(ip_s) if ip_s and ip_s != '-' else None
                except (ValueError, TypeError):
                    ip = None
                try:
                    g = int(float(g_s)) if g_s and g_s != '-' else None
                except (ValueError, TypeError):
                    g = None
                empty_rows.append({
                    'year': year, 'league': league,
                    'name': row.get('player_name_ja', ''),
                    'team': row.get('team', ''),
                    'G': g, 'IP': ip, 'H': h, 'BB': bb,
                })

print('=== H または BB が空の選手 (n=%d) ===' % len(empty_rows))
g_vals = [r['G'] for r in empty_rows if r['G'] is not None]
ip_vals = [r['IP'] for r in empty_rows if r['IP'] is not None]

print('\n【G（登板試合数）】')
if g_vals:
    print('  最小: %s  最大: %s  平均: %.1f' % (min(g_vals), max(g_vals), sum(g_vals)/len(g_vals)))
    print('  G<=1: %d名  G<=5: %d名  G<=10: %d名  G<=20: %d名' % (
        sum(1 for x in g_vals if x <= 1),
        sum(1 for x in g_vals if x <= 5),
        sum(1 for x in g_vals if x <= 10),
        sum(1 for x in g_vals if x <= 20),
    ))

print('\n【IP（投球回）】')
if ip_vals:
    print('  最小: %.1f  最大: %.1f  平均: %.1f' % (min(ip_vals), max(ip_vals), sum(ip_vals)/len(ip_vals)))
    print('  IP<1: %d名  IP<5: %d名  IP<10: %d名  IP<20: %d名' % (
        sum(1 for x in ip_vals if x < 1),
        sum(1 for x in ip_vals if x < 5),
        sum(1 for x in ip_vals if x < 10),
        sum(1 for x in ip_vals if x < 20),
    ))

print('\n【サンプル（G 小さい順 8件）】')
s = sorted([r for r in empty_rows if r['G'] is not None], key=lambda x: x['G'])[:8]
for r in s:
    print('  %d %s %s: G=%s IP=%s' % (r['year'], r['league'], r['name'], r['G'], r['IP']))

print('\n【サンプル（IP 小さい順 8件）】')
s2 = sorted([r for r in empty_rows if r['IP'] is not None], key=lambda x: x['IP'])[:8]
for r in s2:
    print('  %d %s %s: G=%s IP=%s' % (r['year'], r['league'], r['name'], r['G'], r['IP']))

# 直近5年（2021-2025）の該当例
print('\n\n=== 直近5年の該当例（G/IP 少ない順に各年5件ずつ） ===')
recent = [r for r in empty_rows if r['year'] >= 2021]
for year in [2021, 2022, 2023, 2024, 2025]:
    y_list = sorted([r for r in recent if r['year'] == year], key=lambda x: (x['G'] or 999, x['IP'] or 999))[:5]
    print('\n%s年 (%d件中サンプル5件):' % (year, len([r for r in recent if r['year'] == year])))
    for r in y_list:
        print('  %s %s | %s | %s | G=%s IP=%s' % (r['league'], r['name'], r.get('team',''), r['year'], r['G'], r['IP']))
