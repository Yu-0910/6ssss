#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""球団別ページ idp1_*.html のテーブル構造を確認し、パースで何件取れるか検証する"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import requests
from bs4 import BeautifulSoup

def main():
    url = 'https://npb.jp/bis/2024/stats/idp1_h.html'
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
    r.encoding = r.apparent_encoding or 'utf-8'
    soup = BeautifulSoup(r.text, 'lxml')
    tables = soup.find_all('table')
    print('Total tables:', len(tables))
    for ti, t in enumerate(tables):
        rows = t.find_all('tr')
        print(f'\nTable {ti}: {len(rows)} rows')
        header_row_idx = None
        for i, row in enumerate(rows):
            cells = row.find_all(['th', 'td'])
            cell_texts = [c.get_text(strip=True) for c in cells]
            joined = ''.join(cell_texts).replace('\u3000', '').replace(' ', '').replace('\n', '')
            has = '投手' in joined and '投球回' in joined and '防御率' in joined and len(cell_texts) >= 20
            if has:
                header_row_idx = i
                print(f'  row {i}: HEADER (cells={len(cells)})')
                break
        if header_row_idx is None:
            for i, row in enumerate(rows[:3]):
                cells = row.find_all(['th', 'td'])
                print(f'  row {i}: cells={len(cells)}')
            continue
        data_rows = rows[header_row_idx + 1:]
        added = 0
        skipped_cells = 0
        skipped_name = 0
        for ri, row in enumerate(data_rows):
            cells = row.find_all(['td', 'th'])
            if len(cells) < 18:
                skipped_cells += 1
                continue
            name_idx = 1
            name_raw = cells[name_idx].get_text(strip=True) if name_idx < len(cells) else ''
            c0 = cells[0].get_text(strip=True)[:20] if cells else ''
            c1 = cells[1].get_text(strip=True)[:20] if len(cells) > 1 else ''
            if not name_raw or not name_raw.strip():
                skipped_name += 1
                if skipped_name <= 3:
                    print(f'    row{ri}: cells[0]={repr(c0)}, cells[1]={repr(c1)}, len(cells)={len(cells)}')
                continue
            added += 1
        print(f'  Data rows: {len(data_rows)}, added={added}, skipped(cells<18)={skipped_cells}, skipped(no name)={skipped_name}')
        # header row cell count and first 5 headers
        hrow = rows[header_row_idx]
        hcells = hrow.find_all(['th', 'td'])
        htexts = [c.get_text(strip=True)[:10] for c in hcells[:8]]
        print(f'  Header: {len(hcells)} cells, first 8: {htexts}')

if __name__ == '__main__':
    main()
