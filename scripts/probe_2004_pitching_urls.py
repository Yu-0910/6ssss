#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2004年 全投手成績取得の原因究明: 取得可能なURLと年度別ページの構造を調査する。
"""
import re
import sys
from pathlib import Path

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
from bs4 import BeautifulSoup

YEAR = 2004
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def probe(url: str) -> tuple[int, int, str]:
    """URLにGETし (status_code, len(body), 先頭200文字) を返す。"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        return r.status_code, len(r.text), (r.text[:200] if r.text else "")
    except Exception as e:
        return -1, 0, str(e)

def main():
    print("=== 2004年 投手成績 取得原因究明 ===\n")

    # 1) 候補URLのプローブ
    candidates = [
        ("新形式 本表 PL", f"https://npb.jp/bis/{YEAR}/stats/pit_p.html"),
        ("新形式 本表 CL", f"https://npb.jp/bis/{YEAR}/stats/pit_c.html"),
        ("旧形式 stats/年/pl pitching", f"https://npb.jp/bis/stats/{YEAR}/pl/pitching.html"),
        ("旧形式 stats/年/cl pitching", f"https://npb.jp/bis/stats/{YEAR}/cl/pitching.html"),
        ("球団別 idp1_h (PL)", f"https://npb.jp/bis/{YEAR}/stats/idp1_h.html"),
        ("球団別 idp1_t (CL)", f"https://npb.jp/bis/{YEAR}/stats/idp1_t.html"),
        ("参考: 野手 2004 PL", f"https://npb.jp/bis/stats/{YEAR}/pl/batting.html"),
        ("参考: 野手 2004 CL", f"https://npb.jp/bis/stats/{YEAR}/cl/batting.html"),
        ("年度別 PL", f"https://npb.jp/bis/yearly/pacificleague_{YEAR}.html"),
        ("年度別 CL", f"https://npb.jp/bis/yearly/centralleague_{YEAR}.html"),
    ]
    print("--- 候補URLの応答 ---")
    for name, url in candidates:
        code, length, _ = probe(url)
        ok = "OK" if code == 200 else "FAIL"
        print(f"  [{ok}] {code}  len={length:6}  {name}")
        print(f"       {url}")

    # 2) 年度別ページの構造: テーブル数・個人投手成績の行数・ページ内リンク
    print("\n--- 年度別ページ（PL）の構造 ---")
    url_pl = f"https://npb.jp/bis/yearly/pacificleague_{YEAR}.html"
    code, length, _ = probe(url_pl)
    if code != 200:
        print(f"  取得失敗: {code}")
    else:
        r = requests.get(url_pl, headers=HEADERS, timeout=15)
        r.encoding = r.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(r.text, 'lxml')
        tables = soup.find_all('table')
        print(f"  テーブル数: {len(tables)}")
        for i, t in enumerate(tables):
            rows = t.find_all('tr')
            # ヘッダー行で「個人投手」「選 手」「防御率」を含むか
            is_pitching = False
            for row in rows[:3]:
                cells = row.find_all(['th', 'td'])
                texts = ''.join(c.get_text(strip=True) for c in cells).replace(' ', '')
                if '個人投手' in texts or ('選手' in texts and '防御率' in texts and '試合' in texts):
                    is_pitching = True
                    break
            data_rows = max(0, len(rows) - 1)
            tag = " [個人投手成績と推定]" if is_pitching else ""
            print(f"    テーブル{i+1}: {len(rows)}行 (データ行約{data_rows}){tag}")
            # テーブル3の先頭2行を表示（全投手表の構造確認）
            if i == 2 and len(rows) >= 2:
                print(f"      --- テーブル3 先頭2行（ヘッダー＋1行目）---")
                for ri, row in enumerate(rows[:2]):
                    cells = row.find_all(['th', 'td'])
                    cell_texts = [c.get_text(strip=True) for c in cells]
                    print(f"        行{ri}: 列数={len(cell_texts)}  {cell_texts[:15]}")
            # テーブル8・9（実際に取得している表）のヘッダーと行数
            if i in (7, 8) and len(rows) >= 1:
                cells0 = rows[0].find_all(['th', 'td'])
                print(f"      --- テーブル{i+1} ヘッダー 列数={len(cells0)} ---")
                print(f"         {[c.get_text(strip=True) for c in cells0]}")

        # ページ内のリンクで stats/ や idp / pit を含むもの
        links = []
        for a in soup.find_all('a', href=True):
            h = a.get('href', '')
            if not h.startswith('http'):
                h = 'https://npb.jp' + (h if h.startswith('/') else '/' + h)
            if 'stats' in h or 'idp' in h or 'pit' in h or 'pitching' in h or 'batting' in h:
                links.append((h, a.get_text(strip=True)[:40]))
        seen = set()
        for href, text in links:
            if href not in seen:
                seen.add(href)
                print(f"  リンク: {href}")
                print(f"    テキスト: {text}")

    # 3) 2024年と比較: 本表・球団別が存在するか
    print("\n--- 比較: 2024年 同じURL形式 ---")
    for name, path_suffix in [
        ("本表 PL", f"https://npb.jp/bis/2024/stats/pit_p.html"),
        ("球団別 idp1_h", f"https://npb.jp/bis/2024/stats/idp1_h.html"),
    ]:
        code, length, _ = probe(path_suffix)
        print(f"  2024 {name}: {code}  len={length}")

    print("\n--- 結論用: 2004で全投手が取れない原因 ---")
    print("  上記のプローブ結果を参照し、利用可能なURLと行数から原因を記載すること。")

if __name__ == "__main__":
    main()
