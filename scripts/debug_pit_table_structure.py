#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pit_*.html の表構造と選手リンクの有無を確認するデバッグ用スクリプト"""
import re
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
from bs4 import BeautifulSoup

def main():
    url = "https://npb.jp/bis/2024/stats/pit_p.html"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or 'utf-8'
    html = r.text

    # 選手リンクの有無
    player_links = re.findall(r'href=["\']([^"\']*?/bis/players/\d+(?:\.html)?)[^"\']*["\']', html, re.I)
    print("=== /bis/players/ リンク数 ===")
    print(len(player_links))
    if player_links:
        print("例:", player_links[:3])
    else:
        print("(0件: 成績表に選手リンクが無い可能性)")

    soup = BeautifulSoup(html, 'lxml')
    tables = soup.find_all('table')
    print("\n=== テーブル数 ===")
    print(len(tables))

    for ti, table in enumerate(tables):
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue
        # ヘッダー行を探す
        header_idx = None
        for i, row in enumerate(rows):
            cells = row.find_all(['th', 'td'])
            texts = [c.get_text(strip=True) for c in cells]
            joined = ''.join(texts).replace(' ', '').replace('\u3000', '')
            if '投手' in joined and '投球回' in joined and '防御率' in joined:
                header_idx = i
                break
        if header_idx is None:
            continue

        header_cells = rows[header_idx].find_all(['th', 'td'])
        print(f"\n--- テーブル {ti+1} (投手成績表) ---")
        print(f"ヘッダー行のセル数: {len(header_cells)}")
        print("ヘッダー 0-4:", [header_cells[j].get_text(strip=True)[:8] for j in range(min(5, len(header_cells)))])
        # 打者・投球回の位置を表示
        for j in range(len(header_cells)):
            t = header_cells[j].get_text(strip=True).replace(' ', '')
            if '打者' in t or '投球回' in t or '安打' in t or '本塁打' in t:
                print(f"  インデックス {j}: {repr(header_cells[j].get_text(strip=True))}")

        # 先頭3データ行のセル数と 14,15,16,17,18 の値
        for ri in range(header_idx + 1, min(header_idx + 4, len(rows))):
            cells = rows[ri].find_all(['td', 'th'])
            print(f"\nデータ行 {ri - header_idx} セル数: {len(cells)}")
            if len(cells) >= 20:
                # 名前(1), チーム(2), 防御率(3), 登板(4), 勝利(5), 敗北(6), セ(7), ブ(8), ホ(9), ル(10), HP(11), 完投(12), 完封(13), 無四球(14), 勝率(15), 打者(16), 投球回(17), 安打(18), 本塁打(19), 四球(20)
                for idx in [1, 2, 3, 4, 11, 12, 13, 14, 15, 16, 17, 18, 19]:
                    if idx < len(cells):
                        print(f"  [{idx}] = {repr(cells[idx].get_text(strip=True))}")
            print(f"  名前(1): {repr(cells[1].get_text(strip=True)) if len(cells) > 1 else 'N/A'}")
        break  # 最初の投手表のみ

if __name__ == '__main__':
    main()
