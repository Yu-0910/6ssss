# -*- coding: utf-8 -*-
# Expected 2025: BF=497, IP=111.2, H=8, HR=46, BB=2, HBP=8, SO=87, WP=2, BK=0, R=58, ER=51, ERA=4.14
import sys
sys.path.insert(0, '.')
import requests
from bs4 import BeautifulSoup
url = "https://npb.jp/bis/players/41045138.html"
r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
r.encoding = r.apparent_encoding or 'utf-8'
soup = BeautifulSoup(r.text, 'lxml')
for ti, table in enumerate(soup.find_all('table')):
    rows = table.find_all('tr')
    if len(rows) < 2:
        continue
    hcells = rows[0].find_all(['th', 'td'])
    htext = [c.get_text(strip=True) for c in hcells]
    joined = ''.join(htext).replace(' ', '')
    if '投球回' not in joined or '防御率' not in joined:
        continue
    want = {'打者':497,'安打':8,'本塁打':46,'四球':2,'三振':87,'暴投':2,'失点':58,'自責':51,'防御率':4.14}
    for row in rows[1:]:
        cells = row.find_all(['th', 'td'])
        if not cells or '2025' not in cells[0].get_text(strip=True):
            continue
        vals = [c.get_text(strip=True) for c in cells]
        for label, v in want.items():
            try:
                i = vals.index(str(v))
                print(label, v, 'at index', i)
            except ValueError:
                if isinstance(v, float) and str(v) not in vals:
                    for i, c in enumerate(vals):
                        try:
                            if abs(float(c) - v) < 0.01:
                                print(label, v, '~at', i, 'val', c)
                                break
                        except: pass
    break
    break
