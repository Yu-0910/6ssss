# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')
from scripts.scrape_2025_pitching_via_roster import get_player_pitching_for_year
r = get_player_pitching_for_year('41045138', '戸郷　翔征', '読売ジャイアンツ', 'CL', 2025)
if r:
    print('IP', r.get('IP'), 'ER', r.get('ER'), 'ERA', r.get('ERA'), 'H', r.get('H'), 'R', r.get('R'))
else:
    print('None')
