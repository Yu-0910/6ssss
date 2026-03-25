#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
指定年度の投手成績を「全ての選手から探す」経由で全選手取得する（2004年形式）。

1. https://npb.jp/bis/players/all/index.html から 指定年度の球団URL一覧を取得
2. 各球団ページから在籍選手（player_id）一覧を取得
3. 各選手の bis/players/{id}.html から投手成績表をパースし、該当年度の行があれば取得
4. 球団をCL/PLに振り分け、pitching_YYYY_PL_from_master.csv / pitching_YYYY_CL_from_master.csv を出力

使用例: python scrape_2004_pitching_via_all_players.py --year 2003
"""
import csv
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
from bs4 import BeautifulSoup

INDEX_URL = "https://npb.jp/bis/players/all/index.html"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 球団名（NPB表記）→ (リーグ, 正式名)。1950〜2024年対応
TEAM_LEAGUE_MAP: Dict[str, Tuple[str, str]] = {
    # === セントラル・リーグ ===
    '読売ジャイアンツ': ('CL', '読売ジャイアンツ'),
    '中日ドラゴンズ': ('CL', '中日ドラゴンズ'),
    '名古屋ドラゴンズ': ('CL', '中日ドラゴンズ'),
    '阪神タイガース': ('CL', '阪神タイガース'),
    '大阪タイガース': ('CL', '阪神タイガース'),
    '広島東洋カープ': ('CL', '広島東洋カープ'),
    '広島カープ': ('CL', '広島東洋カープ'),
    '東京ヤクルトスワローズ': ('CL', '東京ヤクルトスワローズ'),
    'ヤクルトスワローズ': ('CL', '東京ヤクルトスワローズ'),
    '横浜ベイスターズ': ('CL', '横浜DeNAベイスターズ'),
    '横浜DeNAベイスターズ': ('CL', '横浜DeNAベイスターズ'),
    '大洋ホエールズ': ('CL', '大洋ホエールズ'),
    '国鉄スワローズ': ('CL', '国鉄スワローズ'),
    'サンケイスワローズ': ('CL', 'サンケイスワローズ'),
    'サンケイアトムズ': ('CL', 'サンケイアトムズ'),
    'ヤクルトアトムズ': ('CL', '東京ヤクルトスワローズ'),
    'アトムズ': ('CL', '東京ヤクルトスワローズ'),
    '松竹ロビンス': ('CL', '松竹ロビンス'),
    '大洋松竹ロビンス': ('CL', '大洋松竹ロビンス'),
    '西日本パイレーツ': ('CL', '西日本パイレーツ'),
    # === パシフィック・リーグ ===
    '埼玉西武ライオンズ': ('PL', '埼玉西武ライオンズ'),
    '西武ライオンズ': ('PL', '埼玉西武ライオンズ'),
    '福岡ソフトバンクホークス': ('PL', '福岡ソフトバンクホークス'),
    '福岡ダイエーホークス': ('PL', '福岡ソフトバンクホークス'),
    'ダイエーホークス': ('PL', '福岡ソフトバンクホークス'),
    '南海ホークス': ('PL', '南海ホークス'),
    'オリックス・バファローズ': ('PL', 'オリックス・バファローズ'),
    'オリックス・ブルーウェーブ': ('PL', 'オリックス・バファローズ'),
    '千葉ロッテマリーンズ': ('PL', '千葉ロッテマリーンズ'),
    '大阪近鉄バファローズ': ('PL', '大阪近鉄バファローズ'),
    '近鉄バファローズ': ('PL', '大阪近鉄バファローズ'),
    '近鉄パールス': ('PL', '近鉄パールス'),
    '近鉄バファロー': ('PL', '近鉄バファローズ'),
    '北海道日本ハムファイターズ': ('PL', '北海道日本ハムファイターズ'),
    '日本ハムファイターズ': ('PL', '北海道日本ハムファイターズ'),
    '日本ハム・ファイターズ': ('PL', '北海道日本ハムファイターズ'),
    '東北楽天ゴールデンイーグルス': ('PL', '東北楽天ゴールデンイーグルス'),
    '楽天': ('PL', '東北楽天ゴールデンイーグルス'),
    '西鉄ライオンズ': ('PL', '西鉄ライオンズ'),
    '西鉄クリッパース': ('PL', '西鉄クリッパース'),
    '太平洋クラブ・ライオンズ': ('PL', '埼玉西武ライオンズ'),
    '日拓ホーム・フライヤーズ': ('PL', '北海道日本ハムファイターズ'),
    '毎日オリオンズ': ('PL', '毎日オリオンズ'),
    '毎日大映オリオンズ': ('PL', '毎日大映オリオンズ'),
    '東京オリオンズ': ('PL', '東京オリオンズ'),
    'ロッテ・オリオンズ': ('PL', '千葉ロッテマリーンズ'),
    '大映スターズ': ('PL', '大映スターズ'),
    '東急フライヤーズ': ('PL', '東急フライヤーズ'),
    '急映フライヤーズ': ('PL', '急映フライヤーズ'),
    '東映フライヤーズ': ('PL', '東映フライヤーズ'),
    '阪急ブレーブス': ('PL', '阪急ブレーブス'),
    '高橋ユニオンズ': ('PL', '高橋ユニオンズ'),
    'トンボユニオンズ': ('PL', 'トンボユニオンズ'),
    '大映ユニオンズ': ('PL', '大映ユニオンズ'),
}


def _get(url: str, retry: int = 2) -> Optional[str]:
    for attempt in range(retry + 1):
        try:
            if attempt > 0:
                time.sleep(1)
            r = requests.get(url, headers=HEADERS, timeout=25)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or 'utf-8'
            return r.text
        except requests.RequestException as e:
            print(f"  ⚠️ {url}: {e}")
    return None


def get_team_urls_for_year(year: int) -> List[Tuple[str, str, str]]:
    """インデックスから指定年度の (球団表示名, league, url) を取得。"""
    html = _get(INDEX_URL)
    if not html:
        return []
    soup = BeautifulSoup(html, 'lxml')
    result: List[Tuple[str, str, str]] = []
    year_str = str(year)
    pattern = f'/bis/players/search/yearly/{year_str}/'
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        if pattern not in href:
            continue
        text = a.get_text(strip=True)
        if not text or len(text) > 50:
            continue
        # リンクテキストが球団名（括弧や「年」が含まれない、または「○○(2004)」でない）
        team_label = text.replace('(', '（').replace(')', '）')
        if '（' in team_label:
            team_label = team_label.split('（')[0].strip()
        url = href if href.startswith('http') else 'https://npb.jp' + (href if href.startswith('/') else '/' + href)
        league_name = None
        for key in sorted(TEAM_LEAGUE_MAP.keys(), key=len, reverse=True):
            if key in text or key in team_label:
                league_name = TEAM_LEAGUE_MAP[key]
                break
        if not league_name:
            if '巨人' in text or '読売' in text:
                league_name = ('CL', '読売ジャイアンツ')
            elif '西武' in text or '太平洋クラブ' in text:
                league_name = ('PL', '埼玉西武ライオンズ')
            elif '中日' in text or '名古屋' in text:
                league_name = ('CL', '中日ドラゴンズ')
            elif '阪神' in text or '大阪タイガース' in text:
                league_name = ('CL', '阪神タイガース')
            elif '広島' in text:
                league_name = ('CL', '広島東洋カープ')
            elif 'ヤクルト' in text:
                league_name = ('CL', '東京ヤクルトスワローズ')
            elif '国鉄' in text or 'サンケイ' in text or 'アトムズ' in text:
                league_name = ('CL', '国鉄スワローズ')
            elif '横浜' in text or 'ベイスターズ' in text or '大洋' in text:
                league_name = ('CL', '大洋ホエールズ')
            elif 'ダイエー' in text or 'ソフトバンク' in text or ('ホークス' in text and '南海' not in text):
                league_name = ('PL', '福岡ソフトバンクホークス')
            elif 'オリックス' in text:
                league_name = ('PL', 'オリックス・バファローズ')
            elif 'ロッテ' in text or 'マリーンズ' in text or 'オリオンズ' in text:
                league_name = ('PL', '千葉ロッテマリーンズ')
            elif '近鉄' in text:
                league_name = ('PL', '大阪近鉄バファローズ')
            elif '日本ハム' in text or ('ファイターズ' in text and '東映' in text) or '日拓' in text:
                league_name = ('PL', '北海道日本ハムファイターズ')
            elif '南海' in text:
                league_name = ('PL', '南海ホークス')
            elif '西鉄' in text or 'ライオン' in text:
                league_name = ('PL', '埼玉西武ライオンズ')
            elif '東映' in text or '東急' in text or '急映' in text:
                league_name = ('PL', '北海道日本ハムファイターズ')
            elif '阪急' in text or 'ブレーブス' in text:
                league_name = ('PL', '阪急ブレーブス')
            elif '松竹' in text or 'ロビンス' in text:
                league_name = ('CL', '松竹ロビンス')
            elif '西日本' in text or 'パイレーツ' in text:
                league_name = ('CL', '西日本パイレーツ')
            elif '楽天' in text:
                league_name = ('PL', '東北楽天ゴールデンイーグルス')
        if league_name:
            league, name = league_name
            result.append((name, league, url))
    # 重複除去（同一URL）
    seen = set()
    unique = []
    for name, league, url in result:
        if url not in seen:
            seen.add(url)
            unique.append((name, league, url))
    return unique


def get_player_list_from_team_page(team_url: str) -> List[Tuple[str, str]]:
    """球団ページから (player_id, player_name_ja) のリストを取得。"""
    html = _get(team_url)
    if not html:
        return []
    soup = BeautifulSoup(html, 'lxml')
    players: List[Tuple[str, str]] = []
    for a in soup.find_all('a', href=re.compile(r'/bis/players/\d+\.html')):
        href = a.get('href', '')
        m = re.search(r'/bis/players/(\d+)\.html', href)
        if not m:
            continue
        pid = m.group(1)
        text = a.get_text(strip=True)
        # "上原 浩治 1999年 公式戦初出場" → "上原 浩治"
        name = re.sub(r'\s*\d{4}年\s*(公式戦初出場|入団).*', '', text).strip()
        if not name or len(name) > 30:
            name = text.split()[0] + ' ' + text.split()[1] if len(text.split()) >= 2 else text
        players.append((pid, name))
    return players


def _safe_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    s = str(v).strip().replace(',', '')
    if not s or s == '-' or s == '－':
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip().replace(',', '')
    if not s or s == '-' or s == '－':
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _parse_ip_cells(cells: List, ip_idx: int) -> Tuple[Optional[float], int]:
    """
    投球回をパース。NPBは「5」+「.1」の2セル、「0」+「+」+「0」の3セル（0回0/3）などの形式あり。
    返す: (IPの値, 消費したセル数)
    """
    if ip_idx >= len(cells):
        return None, 0
    t0 = cells[ip_idx].get_text(strip=True).replace(',', '')
    if not t0:
        return None, 1
    try:
        whole = int(t0)
    except ValueError:
        return _safe_float(t0), 1

    # 次セルが .1/.2 形式（例: 5.1 = 5回1/3）
    if ip_idx + 1 < len(cells):
        t1 = cells[ip_idx + 1].get_text(strip=True)
        if re.match(r'^\.\d+$', t1):
            return _safe_float(t0 + t1), 2
        # 次が "+" でその次が 0/1/2（例: 0+0/3 = 0.0回）
        if t1 == '+' and ip_idx + 2 < len(cells):
            t2 = cells[ip_idx + 2].get_text(strip=True)
            if t2 in ('0', '1', '2'):
                frac = int(t2) / 3.0
                return whole + frac, 3
    return float(whole), 1


def get_player_pitching_for_year(player_id: str, player_name_ja: str, team: str, league: str, year: int) -> Optional[Dict[str, Any]]:
    """選手ページから指定年度の投手成績1行を取得。なければ None。"""
    url = f"https://npb.jp/bis/players/{player_id}.html"
    html = _get(url)
    if not html:
        return None
    soup = BeautifulSoup(html, 'lxml')
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue
        header_cells = rows[0].find_all(['th', 'td'])
        header_texts = [c.get_text(strip=True) for c in header_cells]
        header_joined = ''.join(header_texts).replace(' ', '')
        if '年度' not in header_joined or '防御率' not in header_joined or '投球回' not in header_joined:
            continue
        if '登板' not in header_joined and '試合' not in header_joined:
            continue
        col_map: Dict[str, int] = {}
        for i, h in enumerate(header_texts):
            h = h.replace(' ', '')
            if '年度' in h:
                col_map['year'] = i
            elif '登板' in h:
                col_map['G'] = i
            elif '勝利' in h:
                col_map['W'] = i
            elif '敗北' in h:
                col_map['L'] = i
            elif 'セーブ' in h:
                col_map['SV'] = i
            elif h == 'H' and 'HP' in header_joined:
                col_map['HOLD'] = i
            elif 'HP' in h or h == 'ＨＰ':
                col_map['HP'] = i
            elif '完投' in h:
                col_map['CG'] = i
            elif '完封' in h:
                col_map['SHO'] = i
            elif '勝率' in h:
                col_map['WPCT'] = i
            elif '打者' in h:
                col_map['BF'] = i
            elif '投球回' in h:
                col_map['IP'] = i
            elif '安打' in h:
                col_map['H'] = i
            elif '本塁打' in h:
                col_map['HR'] = i
            elif '四球' in h and '故意' not in h:
                col_map['BB'] = i
            elif '死球' in h:
                col_map['HBP'] = i
            elif '三振' in h:
                col_map['SO'] = i
            elif '暴投' in h:
                col_map['WP'] = i
            elif 'ボーク' in h:
                col_map['BK'] = i
            elif '失点' in h:
                col_map['R'] = i
            elif '自責' in h:
                col_map['ER'] = i
            elif '防御率' in h:
                col_map['ERA'] = i
        if 'year' not in col_map or 'G' not in col_map:
            continue
        # 投球回より後にある列（複数セル時にオフセットが必要）
        cols_after_ip = ['H', 'HR', 'BB', 'HBP', 'SO', 'WP', 'BK', 'R', 'ER', 'ERA']

        for row in rows[1:]:
            cells = row.find_all(['th', 'td'])
            if col_map['year'] >= len(cells):
                continue
            year_val = cells[col_map['year']].get_text(strip=True).replace(' ', '')
            year_str = str(year)
            year_zen = str(year).translate(str.maketrans('0123456789', '０１２３４５６７８９'))
            if year_val != year_str and year_val != year_zen:
                continue
            g = _safe_int(cells[col_map['G']].get_text(strip=True)) if col_map.get('G') is not None and col_map['G'] < len(cells) else None
            if g is not None and g == 0:
                continue

            # ホールド導入前行: データにH・HP列が無く2列詰まる。HOLD=0, HP=0 とし列オフセット-2を適用
            cols_need_old_offset = ['CG', 'SHO', 'WPCT', 'BF', 'IP', 'H', 'HR', 'BB', 'HBP', 'SO', 'WP', 'BK', 'R', 'ER', 'ERA']
            old_format = (col_map.get('ERA') is not None and col_map['ERA'] >= len(cells)
                          and col_map.get('CG') is not None and col_map['CG'] >= 2)

            # 投球回パース（0+0/3 等の複数セル形式に対応。1登板0回でH欠損になる原因を解消）
            ip_col_idx = (col_map['IP'] - 2) if old_format and col_map.get('IP') is not None else col_map.get('IP')
            ip_val, ip_cells = _parse_ip_cells(cells, ip_col_idx) if ip_col_idx is not None and ip_col_idx < len(cells) else (None, 1)
            ip_extra = max(0, ip_cells - 1)

            def _cell_idx(key: str) -> int:
                idx = col_map.get(key)
                if idx is None:
                    return -1
                if old_format and key in cols_need_old_offset:
                    idx = idx - 2
                if key in cols_after_ip:
                    idx = idx + ip_extra
                return idx

            def _read_cell(key: str, as_float: bool = False) -> Any:
                idx = _cell_idx(key)
                if idx < 0 or idx >= len(cells):
                    return None
                t = cells[idx].get_text(strip=True).replace(',', '')
                if not t or t in ('-', '－'):
                    return None
                return (_safe_float(t) if as_float else _safe_int(t))

            h_val = _read_cell('H')
            # IP=0/空 で H が空の場合: 0回は被安打0のケースが多いため補完
            if h_val is None and (ip_val is None or ip_val == 0) and g is not None and g <= 2:
                bf_val = _read_cell('BF')
                if bf_val is not None and bf_val > 0:
                    h_val = 0

            row_data: Dict[str, Any] = {
                'year': year,
                'league': league,
                'team': team,
                'player_id': player_id,
                'player_name_ja': player_name_ja,
                'player_name_en': '',
                'G': g,
                'IP': ip_val,
                'W': _read_cell('W'),
                'L': _read_cell('L'),
                'SV': _read_cell('SV'),
                'ERA': _read_cell('ERA', as_float=True),
                'BF': _read_cell('BF'),
                'H': h_val,
                'HR': _read_cell('HR'),
                'BB': _read_cell('BB'),
                'IBB': None,
                'HBP': _read_cell('HBP'),
                'SO': _read_cell('SO'),
                'ER': _read_cell('ER'),
                'R': _read_cell('R'),
            }
            # HOLD/HP: ホールド導入前行ではデータに無いため 0 とする
            if old_format:
                row_data['HOLD'] = 0
                row_data['HP'] = 0
            else:
                if col_map.get('HOLD') is not None and _cell_idx('HOLD') < len(cells):
                    row_data['HOLD'] = _safe_int(cells[_cell_idx('HOLD')].get_text(strip=True))
                if col_map.get('HP') is not None and _cell_idx('HP') < len(cells):
                    row_data['HP'] = _safe_int(cells[_cell_idx('HP')].get_text(strip=True))
            # CG/SHO/WPCT は投球回より前。WP/BK は投球回より後で cols_after_ip に含まれる
            if col_map.get('CG') is not None and _cell_idx('CG') < len(cells):
                row_data['CG'] = _safe_int(cells[_cell_idx('CG')].get_text(strip=True))
            if col_map.get('SHO') is not None and _cell_idx('SHO') < len(cells):
                row_data['SHO'] = _safe_int(cells[_cell_idx('SHO')].get_text(strip=True))
            if col_map.get('WPCT') is not None and _cell_idx('WPCT') < len(cells):
                row_data['WPCT'] = _safe_float(cells[_cell_idx('WPCT')].get_text(strip=True))
            if col_map.get('WP') is not None and _cell_idx('WP') < len(cells):
                row_data['WP'] = _safe_int(cells[_cell_idx('WP')].get_text(strip=True))
            if col_map.get('BK') is not None and _cell_idx('BK') < len(cells):
                row_data['BK'] = _safe_int(cells[_cell_idx('BK')].get_text(strip=True))
            return row_data
    return None


def _log_progress(log_path: Optional[Path], msg: str) -> None:
    """進捗をログファイルに追記（--progress-log 指定時）。"""
    if not log_path:
        return
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            from datetime import datetime
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, default=2004, help='取得する年度（例: 2003）')
    parser.add_argument('--test', action='store_true', help='球団URL取得のみ実行')
    parser.add_argument('--progress-log', type=str, default='', help='進捗ログを書き出すファイルパス（相対はプロジェクトの_data配下）')
    args = parser.parse_args()
    year = args.year

    project_root = Path(__file__).resolve().parents[1]
    out_dir = project_root / '_data' / 'master_csv__import_1950_2024'
    out_dir.mkdir(parents=True, exist_ok=True)

    progress_log: Optional[Path] = None
    if args.progress_log:
        progress_log = Path(args.progress_log) if os.path.isabs(args.progress_log) else out_dir / args.progress_log
        progress_log.parent.mkdir(parents=True, exist_ok=True)

    print(f"=== {year}年 投手成績（「全ての選手から探す」経由）===\n", flush=True)
    _log_progress(progress_log, f"開始 {year}年")

    teams = get_team_urls_for_year(year)
    if not teams:
        print(f"❌ {year}年の球団URLを取得できませんでした")
        sys.exit(1)
    if args.test:
        print("--test: 球団URLのみ表示して終了")
        for name, league, url in teams:
            print(f"  {league} {name} {url}")
        return
    print(f"球団数: {len(teams)}")
    for name, league, url in teams:
        print(f"  {league} {name}")

    by_league: Dict[str, List[Dict[str, Any]]] = {'PL': [], 'CL': []}
    seen_ids: Dict[str, set] = {'PL': set(), 'CL': set()}
    total_players = 0
    total_pitchers = 0

    for team_name, league, team_url in teams:
        players = get_player_list_from_team_page(team_url)
        total_players += len(players)
        print(f"\n{team_name} ({league}): {len(players)}名 → 投手成績取得中...", flush=True)
        _log_progress(progress_log, f"{year} {team_name} ({league}): {len(players)}名 取得中")
        for i, (pid, pname) in enumerate(players):
            if pid in seen_ids[league]:
                continue
            row = get_player_pitching_for_year(pid, pname, team_name, league, year)
            if row:
                seen_ids[league].add(pid)
                by_league[league].append(row)
                total_pitchers += 1
            if (i + 1) % 20 == 0:
                print(f"  ... {i+1}/{len(players)}", flush=True)
                _log_progress(progress_log, f"  ... {i+1}/{len(players)}")
            time.sleep(0.2)
        time.sleep(0.25)

    print(f"\n取得: 延べ選手 {total_players}名、{year}年投手成績あり {total_pitchers}名")
    _log_progress(progress_log, f"{year}年 完了 延べ{total_players}名 投手成績{total_pitchers}名 CL:{len(by_league['CL'])} PL:{len(by_league['PL'])}")
    print(f"  CL: {len(by_league['CL'])}名  PL: {len(by_league['PL'])}名")

    for league in ('PL', 'CL'):
        data = by_league[league]
        if not data:
            print(f"  ⚠️ {league} は0件です")
            continue
        out_path = out_dir / f'pitching_{year}_{league}_from_master.csv'
        headers = ['year', 'league', 'team', 'player_id', 'player_name_ja', 'player_name_en',
                   'G', 'IP', 'W', 'L', 'SV', 'ERA', 'BF', 'H', 'HR', 'BB', 'IBB', 'HBP', 'SO', 'ER', 'R']
        optional = ['HOLD', 'HP', 'CG', 'SHO', 'WPCT', 'WP', 'BK']
        for k in optional:
            if k in data[0]:
                headers.append(k)
        with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(data)
        print(f"✅ {out_path} （{len(data)}件）")
        _log_progress(progress_log, f"✅ {out_path.name} {len(data)}件")

    print("\n完了。")
    _log_progress(progress_log, f"{year}年 処理完了")


if __name__ == '__main__':
    main()
