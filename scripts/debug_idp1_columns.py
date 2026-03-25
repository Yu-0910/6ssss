#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""idp1 テーブルの実際の列構造を確認し、BB/SO が正しく取れているか検証"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import requests
from bs4 import BeautifulSoup

# scrape_npb_pitching_stats と同じマップ（修正後）
FIXED_COL_MAP_TEAM = {
    'name': 1, 'G': 2, 'W': 3, 'L': 4, 'SV': 5, 'HOLD': 6, 'HP': 7,
    'CG': 8, 'SHO': 9, 'WPCT': 11, 'BF': 12, 'IP': 13, 'H': 15, 'HR': 16,
    'BB': 17, 'IBB': 18, 'HBP': 19, 'SO': 20, 'WP': 21, 'BK': 22,
    'R': 23, 'ER': 24, 'ERA': 25,
}


def main():
    url = 'https://npb.jp/bis/2024/stats/idp1_h.html'
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
    r.encoding = r.apparent_encoding or 'utf-8'
    soup = BeautifulSoup(r.text, 'lxml')
    tables = soup.find_all('table')

    for ti, t in enumerate(tables):
        rows = t.find_all('tr')
        header_row_idx = None
        for i, row in enumerate(rows):
            cells = row.find_all(['th', 'td'])
            cell_texts = [c.get_text(strip=True) for c in cells]
            joined = ''.join(cell_texts).replace('\u3000', '').replace(' ', '').replace('\n', '')
            if '投手' in joined and '投球回' in joined and '防御率' in joined and len(cell_texts) >= 20:
                header_row_idx = i
                break
        if header_row_idx is None:
            continue

        hrow = rows[header_row_idx]
        hcells = hrow.find_all(['th', 'td'])
        print(f'=== Table {ti}: Header row ({len(hcells)} cells) ===')
        for i, c in enumerate(hcells):
            txt = c.get_text(strip=True).replace('\u3000', ' ')[:12]
            print(f'  [{i:2d}] {txt}')

        # 四球・三振の列を探す
        bb_idx = so_idx = None
        for i, c in enumerate(hcells):
            t = c.get_text(strip=True).replace('\u3000', '')
            if '四球' in t and '故意' not in t:
                bb_idx = i
            if '三振' in t:
                so_idx = i
        print(f'\n  実際の列: 四球=index {bb_idx}, 三振=index {so_idx}')
        print(f'  FIXED_COL_MAP_TEAM: BB={FIXED_COL_MAP_TEAM["BB"]}, SO={FIXED_COL_MAP_TEAM["SO"]}')

        # データ行を数行サンプル
        data_rows = rows[header_row_idx + 1:]
        for ri, row in enumerate(data_rows[:5]):
            cells = row.find_all(['td', 'th'])
            if len(cells) < 18:
                continue
            name_raw = cells[1].get_text(strip=True) if len(cells) > 1 else ''
            name = name_raw.replace('\u3000', ' ').strip()
            if not name:
                continue

            row_map = FIXED_COL_MAP_TEAM
            bb_val = cells[row_map['BB']].get_text(strip=True) if row_map['BB'] < len(cells) else '?'
            so_val = cells[row_map['SO']].get_text(strip=True) if row_map['SO'] < len(cells) else '?'

            # 実際の四球・三振列の値（正しいインデックスの場合）
            bb_actual = cells[bb_idx].get_text(strip=True) if bb_idx is not None and bb_idx < len(cells) else '?'
            so_actual = cells[so_idx].get_text(strip=True) if so_idx is not None and so_idx < len(cells) else '?'

            print(f'\n  [{ri}] {name}: len(cells)={len(cells)}')
            print(f'      MAP BB(ix={row_map["BB"]})={bb_val}, SO(ix={row_map["SO"]})={so_val}')
            print(f'      ACTUAL BB(ix={bb_idx})={bb_actual}, SO(ix={so_idx})={so_actual}')
            # 全セルを表示（デバッグ用）
            vals = [cells[i].get_text(strip=True)[:8] for i in range(min(len(cells), 28))]
            print(f'      cells[0:28] = {vals}')
        break


if __name__ == '__main__':
    main()
