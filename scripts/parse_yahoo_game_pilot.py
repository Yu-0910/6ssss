#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_yahoo_game_pilot.py

個人ページ作成計画書 Phase 2: _data/yahoo_games_pilot/ のHTMLをパースし、
打席単位のテーブルに変換する。
"""

import csv
import re
import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ pip install beautifulsoup4 lxml")
    sys.exit(1)

PLAYER_ID_PATTERN = re.compile(r'/npb/player/(\d+)/top')
INNING_PATTERN = re.compile(r'^(\d+)回(表|裏)$')


def parse_game_meta(top_path: Path) -> dict | None:
    """試合トップHTMLからメタデータを抽出"""
    html = top_path.read_text(encoding='utf-8')
    soup = BeautifulSoup(html, 'lxml')
    game_id = top_path.stem.replace('_top', '')

    meta = {"game_id": game_id, "date": "", "stadium": "", "game_time": "", "home": "", "away": "", "home_score": "", "away_score": ""}

    # タイトル: 2026年3月4日 オリックス・バファローズvs.広島東洋カープ
    title = soup.find('title')
    if title:
        t = title.get_text()
        m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', t)
        if m:
            meta["date"] = f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
        # 日付の直後から vs. までが後攻(ホーム)、vs. の次から「 - 」や「一球速報」等までが先攻(アウェイ)
        vs = re.search(r'\d{4}年\d{1,2}月\d{1,2}日\s*(.+?)vs\.?(.+?)(?:\s+[一試]|\s+-|$)', t)
        if vs:
            meta["home"] = vs.group(1).strip()   # オリックス・バファローズ
            meta["away"] = vs.group(2).strip()   # 広島東洋カープ

    # 球場・試合時刻（timeの隣に球場名がある構造）
    for p in soup.find_all('p'):
        t = p.get_text()
        if re.search(r'\d{1,2}:\d{2}', t) and len(t) < 80:
            # "18:00 京セラD大阪" 等
            m = re.search(r'(\d{1,2}):(\d{2})\s*(.+)', t)
            if m:
                meta["game_time"] = f"{m.group(1)}:{m.group(2)}"
                meta["stadium"] = m.group(3).strip().split()[0][:30]
            break
    if not meta["stadium"]:
        for s in soup.find_all(string=re.compile(r'京セラ|マツダ|甲子園|横浜|エスコン|静岡|春野')):
            meta["stadium"] = s.strip()[:30]
            break
    if not meta.get("game_time"):
        for time_el in soup.find_all('time'):
            tt = time_el.get_text().strip()
            if re.match(r'\d{1,2}:\d{2}$', tt):
                meta["game_time"] = tt
                break

    # スコア: bb-gameScoreTable__total の計列から
    for row in soup.find_all('tr', class_='bb-gameScoreTable__row'):
        tds = row.find_all('td', class_='bb-gameScoreTable__total')
        team_a = row.find('a', class_='bb-gameScoreTable__team')
        if team_a and tds:
            team = team_a.get_text().strip()
            total = tds[0].get_text().strip()
            if total.isdigit():
                if '広島' in team or team == '広島':
                    meta["away_score"] = total
                elif 'オリックス' in team or team == 'オリックス':
                    meta["home_score"] = total

    return meta


def _parse_home_away_from_text(soup) -> tuple[str, str]:
    """テキストHTMLのタイトルから home/away を取得"""
    title = soup.find('title')
    if not title:
        return "", ""
    t = title.get_text()
    vs = re.search(r'\d{4}年\d{1,2}月\d{1,2}日\s*(.+?)vs\.?(.+?)(?:\s+[一試]|\s+-|$)', t)
    if vs:
        return vs.group(1).strip(), vs.group(2).strip()
    return "", ""


def _parse_starting_pitchers(soup, home_team: str, away_team: str) -> tuple[str, str]:
    """試合前情報から先発投手IDを取得 (home_sp, away_sp)。先発は「〇〇がA、△△がB」で最初がホーム側"""
    home_sp, away_sp = "", ""
    for section in soup.find_all('section', class_='bb-liveText'):
        head = section.find('h1', class_='bb-liveText__inning')
        if not head or '試合前' not in (head.get_text() or ''):
            continue
        for p in section.find_all('p', class_='bb-liveText__summary'):
            if '先発ピッチャー' not in (p.get_text() or ""):
                continue
            links = p.find_all('a', href=PLAYER_ID_PATTERN)
            if len(links) >= 2:
                m1 = PLAYER_ID_PATTERN.search(links[0].get('href', ''))
                m2 = PLAYER_ID_PATTERN.search(links[1].get('href', ''))
                if m1:
                    home_sp = m1.group(1)
                if m2:
                    away_sp = m2.group(1)
            elif len(links) == 1:
                m = PLAYER_ID_PATTERN.search(links[0].get('href', ''))
                if m:
                    home_sp = m.group(1)
        break
    return home_sp, away_sp


def parse_plate_appearances(text_path: Path) -> list[dict]:
    """テキスト速報HTMLから打席単位のデータを抽出"""
    html = text_path.read_text(encoding='utf-8')
    soup = BeautifulSoup(html, 'lxml')
    game_id = text_path.stem.replace('_text', '')

    home_team, away_team = _parse_home_away_from_text(soup)
    home_pitcher, away_pitcher = _parse_starting_pitchers(soup, home_team, away_team)

    rows = []
    current_inning = 0
    current_top_bottom = ""
    current_home_pitcher = home_pitcher
    current_away_pitcher = away_pitcher

    first_inning_done = False
    for section in soup.find_all('section', class_='bb-liveText'):
        head = section.find('h1', class_='bb-liveText__inning')
        if head:
            inn_text = head.get_text().strip()
            mm = INNING_PATTERN.match(inn_text)
            if mm:
                current_inning = int(mm.group(1))
                current_top_bottom = mm.group(2)
                if not first_inning_done:
                    current_home_pitcher = home_pitcher
                    current_away_pitcher = away_pitcher
                    first_inning_done = True

        for li in section.find_all('li', class_='bb-liveText__item'):
            content = li.find('div', class_='bb-liveText__content')
            if not content:
                continue

            for summ in content.find_all('p', class_='bb-liveText__summary'):
                cls = summ.get('class') or []
                if 'bb-liveText__summary--change' in cls and '投手交代' in (summ.get_text() or ''):
                    links = summ.find_all('a', href=PLAYER_ID_PATTERN)
                    if len(links) >= 2:
                        pm = PLAYER_ID_PATTERN.search(links[-1].get('href', ''))
                        if pm:
                            new_pid = pm.group(1)
                            if current_top_bottom == "表":
                                current_home_pitcher = new_pid
                            else:
                                current_away_pitcher = new_pid
                    elif len(links) == 1:
                        pm = PLAYER_ID_PATTERN.search(links[0].get('href', ''))
                        if pm:
                            new_pid = pm.group(1)
                            if current_top_bottom == "表":
                                current_home_pitcher = new_pid
                            else:
                                current_away_pitcher = new_pid
                    break

            pitcher_id = current_home_pitcher if current_top_bottom == "表" else current_away_pitcher

            num_el = content.find('p', class_='bb-liveText__number')
            bat_num = num_el.get_text().strip().rstrip('：') if num_el else ""

            batter_el = content.find('p', class_='bb-liveText__batter')
            batter_id = ""
            base_state = ""
            if batter_el:
                a = batter_el.find('a', href=PLAYER_ID_PATTERN)
                if a:
                    m = PLAYER_ID_PATTERN.search(a.get('href', ''))
                    if m:
                        batter_id = m.group(1)
                for span in batter_el.find_all('span', class_='bb-liveText__state'):
                    state = span.get_text().strip()
                    if '死' in state or '塁' in state or '走者' in state:
                        base_state = state
                        break

            result_raw = ""
            for summ in content.find_all('p', class_='bb-liveText__summary'):
                cls = summ.get('class') or []
                if 'bb-liveText__summary--change' in cls:
                    continue
                for span in summ.find_all('span', class_='bb-liveText__state'):
                    result_raw = span.get_text().strip()
                    break
                if result_raw:
                    break

            if current_inning == 0:
                continue
            if not batter_id:
                continue
            if '先発' in str(content.get_text()) or 'スタメン' in str(content.get_text()):
                continue

            rows.append({
                "game_id": game_id,
                "inning": current_inning,
                "top_bottom": current_top_bottom,
                "bat_order": bat_num,
                "batter_id": batter_id,
                "pitcher_id": pitcher_id,
                "base_state": base_state,
                "result_raw": result_raw[:200] if result_raw else "",
            })

    return rows


def main():
    # スクリプトからプロジェクトルートを推定
    root = Path(__file__).resolve().parent.parent
    data_dir = root / "_data" / "yahoo_games_pilot"
    out_dir = root / "_data" / "yahoo_games_pilot"
    if not data_dir.exists():
        print(f"❌ {data_dir} が存在しません。Phase 1 を先に実行してください。")
        sys.exit(1)

    top_files = sorted(data_dir.glob("*_top.html"))
    if not top_files:
        print("❌ *_top.html が見つかりません")
        sys.exit(1)

    all_meta = []
    all_plate = []

    for top_path in top_files:
        gid = top_path.stem.replace('_top', '')
        text_path = data_dir / f"{gid}_text.html"
        if not text_path.exists():
            print(f"  ⚠ {gid}: text.html なし")
            continue

        meta = parse_game_meta(top_path)
        if meta:
            all_meta.append(meta)

        plates = parse_plate_appearances(text_path)
        all_plate.extend(plates)
        print(f"  {gid}: メタ取得, 打席 {len(plates)}件")

    # CSV出力
    meta_path = out_dir / "games_meta.csv"
    plate_path = out_dir / "plate_appearances.csv"

    if all_meta:
        with open(meta_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["game_id", "date", "stadium", "game_time", "home", "away", "home_score", "away_score"])
            w.writeheader()
            w.writerows(all_meta)
        print(f"\n✅ games_meta.csv: {len(all_meta)}試合 -> {meta_path}")

    if all_plate:
        with open(plate_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["game_id", "inning", "top_bottom", "bat_order", "batter_id", "pitcher_id", "base_state", "result_raw"])
            w.writeheader()
            w.writerows(all_plate)
        print(f"✅ plate_appearances.csv: {len(all_plate)}打席 -> {plate_path}")


if __name__ == "__main__":
    main()
