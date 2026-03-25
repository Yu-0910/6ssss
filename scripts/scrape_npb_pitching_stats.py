#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrape_npb_pitching_stats.py

NPB公式サイトから投手成績をスクレイピングして生CSVを出力するスクリプト。
Phase 1 前段階・Phase 1-a（2024年テスト）・Phase 1-b（2023年〜1950年）で使用。

URL（要確認済み）:
- 2024年以降: https://npb.jp/bis/{year}/stats/pit_{p|c}.html （PL=p, CL=c）
- 2023年以前: https://npb.jp/bis/stats/{year}/{pl|cl}/pitching.html （要検証）

出力先: _data/master_csv__import_1950_2024/pitching_{year}_{league}_from_master.csv

フォールバック（表が取れない場合）: pandas.read_html を使用。要 pip install pandas。
"""

import argparse
import csv
import sys
import time
import io
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

# WindowsでのUnicode出力対応
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ エラー: 必要なライブラリがインストールされていません")
    print("   インストール方法: pip install requests beautifulsoup4 lxml")
    sys.exit(1)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


def safe_float(value: Any) -> Optional[float]:
    if value is None or value == '' or value == 'nan':
        return None
    try:
        return float(str(value).replace(',', ''))
    except (ValueError, TypeError):
        return None


def safe_int(value: Any) -> Optional[int]:
    if value is None or value == '' or value == 'nan':
        return None
    try:
        fval = safe_float(value)
        return int(fval) if fval is not None else None
    except (ValueError, TypeError):
        return None


def normalize_team_name(team: str) -> str:
    """チーム名を正規化（野手版と同様）"""
    team_mapping = {
        '巨人': '読売ジャイアンツ', '阪神': '阪神タイガース', 'DeNA': '横浜DeNAベイスターズ',
        '横浜': '横浜DeNAベイスターズ', '広島': '広島東洋カープ', '中日': '中日ドラゴンズ',
        'ヤクルト': '東京ヤクルトスワローズ', 'オリックス': 'オリックス・バファローズ',
        '西武': '埼玉西武ライオンズ', 'ロッテ': '千葉ロッテマリーンズ',
        '楽天': '東北楽天ゴールデンイーグルス', 'ソフトバンク': '福岡ソフトバンクホークス',
        '日本ハム': '北海道日本ハムファイターズ', '北海道日本ハム': '北海道日本ハムファイターズ',
    }
    for key, value in team_mapping.items():
        if key in team:
            return value
    return team


TEAM_CODE_MAP = {
    '巨': '読売ジャイアンツ', '神': '阪神タイガース', 'デ': '横浜DeNAベイスターズ',
    '横': '横浜DeNAベイスターズ', '広': '広島東洋カープ', '中': '中日ドラゴンズ',
    'ヤ': '東京ヤクルトスワローズ', 'オ': 'オリックス・バファローズ',
    '西': '埼玉西武ライオンズ', 'ロ': '千葉ロッテマリーンズ',
    '楽': '東北楽天ゴールデンイーグルス', 'ソ': '福岡ソフトバンクホークス',
    '日': '北海道日本ハムファイターズ', 'ハ': '北海道日本ハムファイターズ',
    # 年度別ページ (巨 人) 等の略称（スペース除去でマッチ）
    '巨人': '読売ジャイアンツ', '阪神': '阪神タイガース', '広島': '広島東洋カープ',
    '中日': '中日ドラゴンズ', 'ヤクルト': '東京ヤクルトスワローズ', '横浜': '横浜DeNAベイスターズ',
    '西武': '埼玉西武ライオンズ', 'ロッテ': '千葉ロッテマリーンズ', '楽天': '東北楽天ゴールデンイーグルス',
    'ダイエー': '福岡ソフトバンクホークス', '日本ハム': '北海道日本ハムファイターズ',
    'オリックス': 'オリックス・バファローズ', '近鉄': 'オリックス・バファローズ',  # 近鉄は合併でオリックス
}

# 球団別個人成績 idp1_{team_id}.html 用（規定未到達含む全投手取得）
TEAM_IDS_BY_LEAGUE = {
    'PL': ['h', 'l', 'f', 'e', 'm', 'b'],   # ソ,西,日,楽,ロ,オ
    'CL': ['t', 'c', 'db', 'g', 's', 'd'],  # 神,広,デ,巨,ヤ,中
}
TEAM_ID_TO_NAME = {
    'h': '福岡ソフトバンクホークス', 'l': '埼玉西武ライオンズ',
    'f': '北海道日本ハムファイターズ', 'e': '東北楽天ゴールデンイーグルス',
    'm': '千葉ロッテマリーンズ', 'b': 'オリックス・バファローズ',
    't': '阪神タイガース', 'c': '広島東洋カープ', 'db': '横浜DeNAベイスターズ',
    'g': '読売ジャイアンツ', 's': '東京ヤクルトスワローズ', 'd': '中日ドラゴンズ',
}


def extract_player_id_from_url(url: str) -> Optional[str]:
    """URL（/bis/players/12345 または /bis/players/12345.html）から player_id を抽出"""
    if not url:
        return None
    match = re.search(r'/bis/players/(\d+)(?:\.html)?', url)
    return match.group(1) if match else None


def _parse_pitching_with_pandas(
    html: str, year: int, league: str, player_id_map: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    pandas.read_html でHTMLから表を取得し、投手成績らしい表を選んで
    既存仕様の row_data リストに変換する。フォールバック用。
    """
    if not PANDAS_AVAILABLE:
        print("[デバッグ] フォールバックに pandas が必要です: pip install pandas")
        return []

    try:
        tables_pd = pd.read_html(io.StringIO(html))
    except Exception as e:
        print(f"[デバッグ] pd.read_html 失敗: {e}")
        return []

    if not tables_pd:
        print("[デバッグ] pd.read_html で取得した表の数: 0")
        return []

    print(f"[デバッグ] pd.read_html で取得した表の数: {len(tables_pd)}")

    # 投手成績らしい列（投球回・防御率・奪三振など）を含む表を選択
    PITCHING_KEYWORDS = ('投球回', '防御率', '奪三振', '登板', '投手', '選手')
    for idx, df in enumerate(tables_pd):
        if df.empty or len(df) < 2:
            continue
        col_str = ' '.join(str(c) for c in df.columns)
        if not any(kw in col_str for kw in PITCHING_KEYWORDS):
            continue

        # 列名 -> 我々のキー
        col_map: Dict[str, int] = {}
        for i, label in enumerate(df.columns):
            s = str(label).replace('　', '').replace(' ', '')
            if '投手' in str(label) or '選手' in str(label):
                col_map['name'] = i
            elif 'チーム' in str(label) or re.match(r'^\([^)]+\)$', str(label).strip()):
                col_map['team'] = i
            elif '防御率' in str(label) or str(label) == 'ERA':
                col_map['ERA'] = i
            elif '登板' in str(label) or str(label) in ('G',):
                col_map['G'] = i
            elif '勝利' in str(label) or str(label) == 'W':
                col_map['W'] = i
            elif '敗北' in str(label) or str(label) == 'L':
                col_map['L'] = i
            elif 'セーブ' in str(label) or 'セ' in s or str(label) == 'SV':
                col_map['SV'] = i
            elif '投球回' in str(label) or str(label) in ('IP', 'IPouts'):
                col_map['IP'] = i
            elif '打者' in str(label) or str(label) == 'BF':
                col_map['BF'] = i
            elif '安打' in str(label) or str(label) == 'H':
                col_map['H'] = i
            elif '本塁打' in str(label) or str(label) == 'HR':
                col_map['HR'] = i
            elif ('四球' in str(label) or '四　球' in str(label)) and '故意' not in str(label):
                col_map['BB'] = i
            elif '故意' in str(label) or str(label) == 'IBB':
                col_map['IBB'] = i
            elif '死球' in str(label) or str(label) == 'HBP':
                col_map['HBP'] = i
            elif '三振' in str(label) or str(label) in ('SO', 'K'):
                col_map['SO'] = i
            elif '自責' in str(label) or str(label) == 'ER':
                col_map['ER'] = i
            elif '失点' in str(label) or str(label) == 'R':
                col_map['R'] = i
            elif 'ホールド' in str(label) or ('ホ' in str(label) and 'HP' not in str(label)):
                col_map['HOLD'] = i
            elif 'ＨＰ' in str(label) or str(label) == 'HP':
                col_map['HP'] = i
            elif '完投' in str(label):
                col_map['CG'] = i
            elif '完封' in str(label):
                col_map['SHO'] = i
            elif '勝率' in str(label):
                col_map['WPCT'] = i
            elif '暴投' in str(label):
                col_map['WP'] = i
            elif 'ボーク' in str(label) or 'ボ' in s:
                col_map['BK'] = i

        if 'name' not in col_map:
            continue

        def get_cell(row, key: str):
            if key not in col_map or col_map[key] >= len(row):
                return None
            v = row.iloc[col_map[key]]
            if pd.isna(v):
                return None
            return str(v).strip()

        players: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            name_val = get_cell(row, 'name')
            if not name_val or name_val in ('投手', '選手', '順位', '順　位') or name_val.isdigit():
                continue
            # 次の列が (略称) ならチームとして結合
            team_val = get_cell(row, 'team') if 'team' in col_map else None
            if team_val and re.match(r'^\([^)]+\)$', team_val):
                player_name_with_team = name_val + team_val
            else:
                player_name_with_team = name_val
            team_match = re.search(r'\(([^)]+)\)', player_name_with_team)
            if team_match:
                team_code = team_match.group(1).strip()
                team = TEAM_CODE_MAP.get(team_code, '')
                player_name_ja = re.sub(r'\([^)]+\)', '', player_name_with_team).strip()
            else:
                team = team_val or ''
                player_name_ja = name_val
            if team and team not in TEAM_CODE_MAP.values():
                team = normalize_team_name(team)

            player_id = ''
            if player_name_ja:
                name_norm = player_name_ja.replace('\u3000', ' ').replace('　', ' ')
                if name_norm in player_id_map:
                    player_id = player_id_map[name_norm]
                else:
                    for k, v in player_id_map.items():
                        if name_norm in k or k in name_norm:
                            player_id = v
                            break

            row_data: Dict[str, Any] = {
                'year': year,
                'league': league,
                'team': team,
                'player_id': player_id,
                'player_name_ja': player_name_ja,
                'player_name_en': '',
                'G': safe_int(get_cell(row, 'G')),
                'IP': safe_float(get_cell(row, 'IP')),
                'W': safe_int(get_cell(row, 'W')),
                'L': safe_int(get_cell(row, 'L')),
                'SV': safe_int(get_cell(row, 'SV')),
                'ERA': safe_float(get_cell(row, 'ERA')),
                'BF': safe_int(get_cell(row, 'BF')),
                'H': safe_int(get_cell(row, 'H')),
                'HR': safe_int(get_cell(row, 'HR')),
                'BB': safe_int(get_cell(row, 'BB')),
                'IBB': safe_int(get_cell(row, 'IBB')),
                'HBP': safe_int(get_cell(row, 'HBP')),
                'SO': safe_int(get_cell(row, 'SO')),
                'ER': safe_int(get_cell(row, 'ER')),
                'R': safe_int(get_cell(row, 'R')),
            }
            for key, ckey in [('HOLD', 'HOLD'), ('HP', 'HP'), ('CG', 'CG'), ('SHO', 'SHO'), ('WPCT', 'WPCT'), ('WP', 'WP'), ('BK', 'BK')]:
                if ckey in col_map:
                    if key == 'WPCT':
                        row_data[key] = safe_float(get_cell(row, ckey))
                    else:
                        row_data[key] = safe_int(get_cell(row, ckey))
            players.append(row_data)

        if players:
            print(f"  📈 pandas フォールバック: 表 {idx + 1} から {len(players)}件の投手データを取得")
            return players

    print("[デバッグ] 失敗: 投手成績らしい列（投球回・防御率・奪三振等）を含む表がありませんでした。")
    return []


def _norm(s: str) -> str:
    """ヘッダーセル正規化（比較用）"""
    return s.replace('\u3000', '').replace('　', '').replace(' ', '').replace('\n', '')


# NPB 2024 投手成績ページの列順（0始まり）。規定以上・セーブ上位・ホールド上位で共通。
# データ行の列数でマップを切り替え: 25列〜28列（HTMLの表によってセル数が異なる）
FIXED_COL_MAP_25: Dict[str, int] = {
    'name': 1, 'team': 2, 'ERA': 3, 'G': 4, 'W': 5, 'L': 6, 'SV': 7,
    'HOLD': 9, 'HP': 11, 'CG': 12, 'SHO': 13, 'WPCT': 15,
    'BF': 13, 'IP': 14, 'H': 15, 'HR': 16, 'BB': 17, 'IBB': 18, 'HBP': 19,
    'SO': 20, 'WP': 21, 'BK': 22, 'R': 23, 'ER': 24,
}
FIXED_COL_MAP_26: Dict[str, int] = {
    'name': 1, 'team': 2, 'ERA': 3, 'G': 4, 'W': 5, 'L': 6, 'SV': 7,
    'HOLD': 9, 'HP': 11, 'CG': 12, 'SHO': 13, 'WPCT': 15,
    'BF': 14, 'IP': 15, 'H': 16, 'HR': 17, 'BB': 18, 'IBB': 19, 'HBP': 20,
    'SO': 21, 'WP': 22, 'BK': 23, 'R': 24, 'ER': 25,
}
# 実HTML: データ行27セル時 完投=11, 完封=12, 勝率=13, 打者=14, 投球回=15, (16=空または.1), 安打=17, 本塁打=18
FIXED_COL_MAP_27: Dict[str, int] = {
    'name': 1, 'team': 2, 'ERA': 3, 'G': 4, 'W': 5, 'L': 6, 'SV': 7,
    'HOLD': 9, 'HP': 11, 'CG': 11, 'SHO': 12, 'WPCT': 13,
    'BF': 14, 'IP': 15, 'H': 17, 'HR': 18, 'BB': 19, 'IBB': 20, 'HBP': 21,
    'SO': 22, 'WP': 23, 'BK': 24, 'R': 25, 'ER': 26,
}
# 実HTML: データ行28セル時 同様、自責点=27
FIXED_COL_MAP_28: Dict[str, int] = {
    'name': 1, 'team': 2, 'ERA': 3, 'G': 4, 'W': 5, 'L': 6, 'SV': 7,
    'HOLD': 9, 'HP': 11, 'CG': 11, 'SHO': 12, 'WPCT': 13,
    'BF': 14, 'IP': 15, 'H': 17, 'HR': 18, 'BB': 19, 'IBB': 20, 'HBP': 21,
    'SO': 22, 'WP': 23, 'BK': 24, 'R': 26, 'ER': 27,
}

# 球団別ページ idp1_*.html の表。26列: (空),投手,登板,… 投球回(13), 小数/空(14), 安打(15), 本塁打(16), 四球(17), 故意四(18), 死球(19), 三振(20),…
# 列14は常に投球回の小数(.1/.2)または空のため、H〜SOは常に15〜20で固定（シフト不要）
FIXED_COL_MAP_TEAM: Dict[str, int] = {
    'name': 1, 'G': 2, 'W': 3, 'L': 4, 'SV': 5, 'HOLD': 6, 'HP': 7,
    'CG': 8, 'SHO': 9, 'WPCT': 11, 'BF': 12, 'IP': 13, 'H': 15, 'HR': 16,
    'BB': 17, 'IBB': 18, 'HBP': 19, 'SO': 20, 'WP': 21, 'BK': 22,
    'R': 23, 'ER': 24, 'ERA': 25,
}


def _build_col_map_by_scanning(header_cells: List[str]) -> Dict[str, int]:
    """ヘッダーを1〜3セルずつ結合してスキャンし、キーごとに最初にマッチした列インデックスを返す"""
    col_map: Dict[str, int] = {}
    # キーと、そのキーでマッチさせる正規化文字列のリスト（先にマッチした方を採用）
    SCAN_KEYS = [
        ('name', ['投手', '選手']),
        ('team', ['(ソ)', '(西)', '(日)', '(楽)', '(ロ)', '(オ)']),
        ('ERA', ['防御率']),
        ('G', ['登板']),
        ('W', ['勝利']),
        ('L', ['敗北']),
        ('SV', ['セーブ', 'セ']),
        ('IP', ['投球回']),
        ('BF', ['打者']),
        ('H', ['安打']),
        ('HR', ['本塁打']),
        ('BB', ['四球']),
        ('IBB', ['故意四']),
        ('HBP', ['死球']),
        ('SO', ['三振']),
        ('ER', ['自責点']),
        ('R', ['失点']),
        ('HOLD', ['ホールド', 'ホ']),
        ('HP', ['ＨＰ', 'HP']),
        ('CG', ['完投']),
        ('SHO', ['完封勝', '完封']),
        ('WPCT', ['勝率']),
        ('WP', ['暴投']),
        ('BK', ['ボーク', 'ボ']),
    ]
    for idx in range(len(header_cells)):
        for length in range(min(4, len(header_cells) - idx), 0, -1):
            merged = _norm(''.join(header_cells[idx:idx + length]))
            if not merged:
                continue
            for key, patterns in SCAN_KEYS:
                if key in col_map:
                    continue
                for pat in patterns:
                    if merged == pat or (key == 'team' and re.match(r'^\([^)]+\)$', merged)):
                        col_map[key] = idx
                        break
            else:
                continue
            break
    return col_map


def _build_col_map_from_merged_header(header_cells: List[str]) -> Optional[Dict[str, int]]:
    """
    ヘッダーが1文字ずつ分割されている場合に、連続セルを結合して列マッピングを構築する。
    NPB 2024 の表順: 順位, 投手, (ソ), 防御率, 登板, 勝利, 敗北, セ, ブ, ホ, ル, ＨＰ, 完投, 完封勝, 無四球, 勝率, 打者, 投球回, 安打, 本塁打, 四球, 故意四, 死球, 三振, 暴投, ボーク, 失点, 自責点
    """
    # (key, マッチする正規化文字列のリスト). None key はスキップ用。
    MERGE_ORDER: List[tuple] = [
        (None, ['順位']),
        ('name', ['投手', '選手']),
        ('team', ['(ソ)', '(西)', '(日)', '(楽)', '(ロ)', '(オ)', '(神)', '(巨)', '(中)', '(広)', '(ヤ)', '(デ)', '(横)']),
        ('ERA', ['防御率']),
        ('G', ['登板']),
        ('W', ['勝利']),
        ('L', ['敗北']),
        ('SV', ['セーブ', 'セ']),
        (None, ['ブ']),
        ('HOLD', ['ホールド', 'ホ']),
        (None, ['ル']),
        ('HP', ['ＨＰ', 'HP']),
        ('CG', ['完投']),
        ('SHO', ['完封勝', '完封']),
        (None, ['無四球']),
        ('WPCT', ['勝率']),
        ('BF', ['打者']),
        ('IP', ['投球回']),
        ('H', ['安打']),
        ('HR', ['本塁打']),
        ('BB', ['四球']),
        ('IBB', ['故意四']),
        ('HBP', ['死球']),
        ('SO', ['三振']),
        ('WP', ['暴投']),
        ('BK', ['ボーク', 'ボ']),
        ('R', ['失点']),
        ('ER', ['自責点']),
    ]
    col_map: Dict[str, int] = {}
    i = 0
    logical_col = 0  # データ行は論理列ごとに1セルなので、このインデックスでデータを読む
    pattern_idx = 0
    while i < len(header_cells) and pattern_idx < len(MERGE_ORDER):
        key, patterns = MERGE_ORDER[pattern_idx]
        matched = False
        for length in range(min(5, len(header_cells) - i + 1), 0, -1):
            merged = _norm(''.join(header_cells[i:i + length]))
            if not merged:
                continue
            for pat in patterns:
                if merged == pat:
                    if key:
                        col_map[key] = logical_col
                    i += length
                    logical_col += 1
                    matched = True
                    break
            if matched:
                break
            # チームは (〇) の1セル
            if key == 'team' and length == 1 and re.match(r'^\([^)]+\)$', header_cells[i].strip()):
                col_map['team'] = logical_col
                i += 1
                logical_col += 1
                matched = True
                break
        if not matched:
            i += 1
            logical_col += 1
        else:
            pattern_idx += 1
    return col_map if 'name' in col_map and 'G' in col_map and 'IP' in col_map else None


def get_pitching_url(year: int, league: str) -> str:
    """年度・リーグからNPB投手成績ページのURLを返す。年度でURLを分岐。"""
    league_upper = league.upper()
    if year >= 2025:
        # 新URL: bis/{year}/stats/pit_{p|c}.html
        code = 'p' if league_upper == 'PL' else 'c'
        return f"https://npb.jp/bis/{year}/stats/pit_{code}.html"
    # 2024年以前: 年度別ページ（個人投手成績を含む）
    if league_upper == 'PL':
        return f"https://npb.jp/bis/yearly/pacificleague_{year}.html"
    return f"https://npb.jp/bis/yearly/centralleague_{year}.html"


def get_team_pitching_url(year: int, team_id: str) -> str:
    """年度・球団IDから球団別個人投手成績ページのURLを返す（規定未到達含む）。year>=2023で同一URL形式。"""
    return f"https://npb.jp/bis/{year}/stats/idp1_{team_id}.html"


def _cell_val(cells: List, col_map: Dict[str, int], key: str, as_float: bool = False) -> Any:
    """セルから値を取得。IPは '145' + '.1' の2セルになる場合を結合してパースする。"""
    if key not in col_map or col_map[key] >= len(cells):
        return None
    val = cells[col_map[key]].get_text(strip=True).replace(',', '')
    if as_float:
        # 次のセルが .1 のような小数部だけの場合は結合
        if col_map[key] + 1 < len(cells):
            next_t = cells[col_map[key] + 1].get_text(strip=True)
            if re.match(r'^\.\d+$', next_t):
                val = val + next_t
        return safe_float(val)
    return safe_int(val)


def _build_player_id_map_from_html(html: str) -> Dict[str, str]:
    """HTML内の /bis/players/ リンクから 名前 -> player_id のマップを構築。BeautifulSoupでネストしたタグ内のテキストも取得。"""
    player_id_map: Dict[str, str] = {}
    if '/bis/players/' not in html:
        return player_id_map
    try:
        soup = BeautifulSoup(html, 'lxml')
        for a in soup.find_all('a', href=re.compile(r'/bis/players/\d+(?:\.html)?')):
            href = a.get('href') or ''
            mid = re.search(r'/bis/players/(\d+)(?:\.html)?', href)
            if not mid:
                continue
            pid = mid.group(1)
            name_raw = a.get_text(strip=True)
            name_clean = re.sub(r'\([^)]+\)', '', name_raw).strip().replace('\u3000', ' ').replace('　', ' ')
            name_clean = re.sub(r'^\s*\*\s*', '', name_clean)  # 左投 * を除去
            if name_clean and len(name_clean) < 50 and name_clean not in player_id_map:
                player_id_map[name_clean] = pid
    except Exception:
        pass
    # 正規表現フォールバック（BeautifulSoupで取れない場合）
    if not player_id_map:
        link_pattern = r'<a[^>]*href=["\']([^"\']*\/bis\/players\/(\d+)[^"\']*)["\'][^>]*>([^<]+)<\/a>'
        for match in re.finditer(link_pattern, html, re.IGNORECASE):
            pid, name_raw = match.group(2), match.group(3).strip()
            name_clean = re.sub(r'\([^)]+\)', '', name_raw).strip().replace('\u3000', ' ').replace('　', ' ')
            name_clean = re.sub(r'^\s*\*\s*', '', name_clean)
            if name_clean and len(name_clean) < 50 and name_clean not in player_id_map:
                player_id_map[name_clean] = pid
    return player_id_map


def _scrape_team_pitching_page(
    year: int,
    league: str,
    team_id: str,
    seen: Set[tuple],
    retry: int = 2,
) -> List[Dict[str, Any]]:
    """
    球団別個人成績 idp1_{team_id}.html を取得し、規定未到達を含む投手行をパースする。
    既に seen に含まれる選手はスキップし、新規のみ返す。
    """
    url = get_team_pitching_url(year, team_id)
    team_name = TEAM_ID_TO_NAME.get(team_id, '')
    if not team_name:
        return []

    html = None
    for attempt in range(retry):
        try:
            if attempt > 0:
                time.sleep(1)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            html = response.text
            break
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️ 球団 {team_id} 取得失敗: {e}")
            if attempt == retry - 1:
                return []

    if not html:
        return []
    player_id_map = _build_player_id_map_from_html(html)
    soup = BeautifulSoup(html, 'lxml')
    tables = soup.find_all('table')
    result: List[Dict[str, Any]] = []

    for table in tables:
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue
        header_row_idx = None
        for i, row in enumerate(rows):
            cells = row.find_all(['th', 'td'])
            cell_texts = [c.get_text(strip=True) for c in cells]
            joined_norm = ''.join(cell_texts).replace('\u3000', '').replace('　', '').replace(' ', '').replace('\n', '')
            if '投手' in joined_norm and '投球回' in joined_norm and '防御率' in joined_norm and len(cell_texts) >= 20:
                header_row_idx = i
                break
        if header_row_idx is None:
            continue

        base_map = dict(FIXED_COL_MAP_TEAM)
        processed = 0
        for row in rows[header_row_idx + 1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 18:
                continue
            # 球団別ページ: name=1, 列14は投球回小数/空で固定のため H=15, BB=17, SO=20 でシフト不要
            row_col_map = base_map

            name_raw = cells[row_col_map['name']].get_text(strip=True)
            player_name_ja = re.sub(r'^\s*\*\s*', '', name_raw).replace('\u3000', ' ').replace('　', ' ').strip()
            if not player_name_ja:
                continue

            player_link = row.find('a', href=lambda x: x and '/bis/players/' in (x or ''))
            player_id = extract_player_id_from_url(player_link.get('href', '')) if player_link else None
            if not player_id and player_name_ja:
                name_norm = player_name_ja.replace('\u3000', ' ').replace('　', ' ')
                if name_norm in player_id_map:
                    player_id = player_id_map[name_norm]
                else:
                    for k, v in player_id_map.items():
                        if name_norm in k or k in name_norm:
                            player_id = v
                            break

            dedupe_key = (player_id,) if player_id else ('', player_name_ja, team_name)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            row_data: Dict[str, Any] = {
                'year': year,
                'league': league,
                'team': team_name,
                'player_id': player_id or '',
                'player_name_ja': player_name_ja,
                'player_name_en': '',
                'G': _cell_val(cells, row_col_map, 'G'),
                'IP': _cell_val(cells, row_col_map, 'IP', as_float=True),
                'W': _cell_val(cells, row_col_map, 'W'),
                'L': _cell_val(cells, row_col_map, 'L'),
                'SV': _cell_val(cells, row_col_map, 'SV'),
                'ERA': _cell_val(cells, row_col_map, 'ERA', as_float=True),
                'BF': _cell_val(cells, row_col_map, 'BF'),
                'H': _cell_val(cells, row_col_map, 'H'),
                'HR': _cell_val(cells, row_col_map, 'HR'),
                'BB': _cell_val(cells, row_col_map, 'BB'),
                'IBB': _cell_val(cells, row_col_map, 'IBB'),
                'HBP': _cell_val(cells, row_col_map, 'HBP'),
                'SO': _cell_val(cells, row_col_map, 'SO'),
                'ER': _cell_val(cells, row_col_map, 'ER'),
                'R': _cell_val(cells, row_col_map, 'R'),
            }
            for key, ckey in [('HOLD', 'HOLD'), ('HP', 'HP'), ('CG', 'CG'), ('SHO', 'SHO'), ('WPCT', 'WPCT'), ('WP', 'WP'), ('BK', 'BK')]:
                if ckey in row_col_map and row_col_map[ckey] < len(cells):
                    row_data[key] = _cell_val(cells, row_col_map, ckey, as_float=(key == 'WPCT'))
            result.append(row_data)
            processed += 1

        if processed > 0:
            print(f"  📈 球団別 {team_id} ({team_name}): {processed}件追加（規定未到達含む）")
            break

    return result


def scrape_pitching_stats(year: int, league: str, retry: int = 3) -> List[Dict[str, Any]]:
    """
    NPB公式サイトから投手成績をスクレイピング。
    規定投球回以上・規定未到達・セーブ上位・ホールド上位など、同形式の全テーブルから取得し、
    同一選手は先に出た行のみ採用して1つのリストにまとめる。
    """
    url = get_pitching_url(year, league)
    print(f"📡 NPB公式サイトから投手成績を取得中: {url}")

    for attempt in range(retry):
        try:
            if attempt > 0:
                time.sleep(2 ** attempt)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            html = response.text

            # デバッグ出力（取得直後）
            print("[デバッグ] status_code:", response.status_code)
            print("[デバッグ] final_url:", response.url)
            print("[デバッグ] len(res.text):", len(response.text))
            print("[デバッグ] res.text 先頭300文字:", repr(response.text[:300]))

            # player_id マッピング（HTML内の /bis/players/ リンクから。BeautifulSoupで確実に取得）
            player_id_map = _build_player_id_map_from_html(html)
            if player_id_map:
                print(f"  ✅ {len(player_id_map)}個のplayer_idマッピングを作成")

            soup = BeautifulSoup(html, 'lxml')
            tables = soup.find_all('table')
            print("[デバッグ] soup.find_all('table') 件数:", len(tables))
            # 2005〜2024 は年度別ページの「個人投手成績（上位10前後）」を使わず、
            # 球団別 idp1 の全投手データのみを採用する。
            if 2005 <= year <= 2024:
                print("  ⏭️ 年度別ページ上位表はスキップ（球団別 idp1 のみで取得）")
                tables = []

            players: List[Dict[str, Any]] = []
            seen: Set[tuple] = set()  # (player_id or ('', player_name_ja, team)) で重複排除。規定以上の表を優先。
            for table_idx, table in enumerate(tables):
                rows = table.find_all('tr')
                if len(rows) < 2:
                    continue

                header_row_idx = None
                header_cells = None
                for i, row in enumerate(rows):
                    cells = row.find_all(['th', 'td'])
                    cell_texts = [c.get_text(strip=True) for c in cells]
                    joined = ' '.join(cell_texts)
                    joined_norm = joined.replace('\u3000', '').replace('　', '').replace(' ', '').replace('\n', '')
                    # 投手成績: 「投手」or「選手」と「投球回」「防御率」の両方を含む行のみ採用（打者表を除外）
                    # 打者表は「選手」「順位」はあるが「投球回」が無いため、この条件で除外される
                    is_header = (
                        ('投手' in joined_norm or '選手' in joined_norm) and
                        '投球回' in joined_norm and
                        '防御率' in joined_norm
                    ) and len(cell_texts) >= 10
                    if is_header:
                        header_row_idx = i
                        header_cells = cell_texts
                        break

                if header_row_idx is None or not header_cells:
                    continue

                # ヘッダーに投手・投球回があればNPB 2024形式とみなし固定マッピングを使用（列ずれ防止）
                header_joined_norm = _norm(''.join(header_cells))
                use_fixed_28 = ('投手' in header_joined_norm and '投球回' in header_joined_norm)

                # 列マッピング（投手用）。スペース入り「投 手」「登 板」等は ht_norm で判定
                col_map: Dict[str, int] = {}
                for idx, ht in enumerate(header_cells):
                    ht_norm = ht.replace('\u3000', '').replace('　', '').replace(' ', '').replace('\n', '')
                    if '投手' in ht_norm or '選手' in ht_norm or 'name' in ht.lower():
                        col_map['name'] = idx
                    elif 'チーム' in ht_norm or re.match(r'^\([^)]+\)$', ht.strip()) or 'team' in ht.lower():
                        col_map['team'] = idx
                    elif '防御率' in ht_norm or ht == 'ERA':
                        col_map['ERA'] = idx
                    elif '登板' in ht_norm or ht in ('G', '登　板'):
                        col_map['G'] = idx
                    elif '勝利' in ht_norm or ht == 'W':
                        col_map['W'] = idx
                    elif '敗北' in ht_norm or ht == 'L':
                        col_map['L'] = idx
                    elif 'セーブ' in ht_norm or ('セ' in ht_norm and 'ブ' in ht_norm) or ht == 'SV':
                        col_map['SV'] = idx
                    elif '投球回' in ht_norm or ht in ('IP', 'IPouts'):
                        col_map['IP'] = idx
                    elif '打者' in ht_norm or ht == 'BF':
                        col_map['BF'] = idx
                    elif '安打' in ht_norm or ht == 'H':
                        col_map['H'] = idx
                    elif '本塁打' in ht_norm or ht == 'HR':
                        col_map['HR'] = idx
                    elif ('四球' in ht_norm or '四　球' in ht_norm) and '故意' not in ht_norm:
                        col_map['BB'] = idx
                    elif '故意' in ht_norm or ht == 'IBB':
                        col_map['IBB'] = idx
                    elif '死球' in ht_norm or '死　球' in ht_norm or ht == 'HBP':
                        col_map['HBP'] = idx
                    elif '三振' in ht_norm or '三　振' in ht_norm or ht in ('SO', 'K'):
                        col_map['SO'] = idx
                    elif '自責' in ht_norm or ht == 'ER':
                        col_map['ER'] = idx
                    elif '失点' in ht_norm or '失　点' in ht_norm or ht == 'R':
                        col_map['R'] = idx
                    elif 'ホールド' in ht_norm or ('ホ' in ht_norm and 'ル' in ht_norm):
                        col_map['HOLD'] = idx
                    elif 'ＨＰ' in ht or 'HP' in ht or ('Ｈ' in ht and 'Ｐ' in ht):
                        col_map['HP'] = idx
                    elif '完投' in ht_norm:
                        col_map['CG'] = idx
                    elif '完封' in ht_norm:
                        col_map['SHO'] = idx
                    elif '勝率' in ht_norm or '勝　率' in ht_norm:
                        col_map['WPCT'] = idx
                    elif '暴投' in ht_norm:
                        col_map['WP'] = idx
                    elif 'ボーク' in ht_norm or 'ボ' in ht_norm:
                        col_map['BK'] = idx

                # NPB 2024 形式（データ行26〜28列）の場合は固定マッピングで列ずれを防ぐ
                if use_fixed_28:
                    col_map = dict(FIXED_COL_MAP_28)  # 行処理時に len(cells) で26/27/28を切り替え
                # それ以外でヘッダーが十分な列数なら、結合マッピングで論理列を統一（分割ヘッダー対応）
                elif len(header_cells) >= 15:
                    merged_map = _build_col_map_from_merged_header(header_cells)
                    if merged_map:
                        col_map = merged_map
                    else:
                        scan_map = _build_col_map_by_scanning(header_cells)
                        if (scan_map.get('name') is not None and scan_map.get('G') is not None and
                                scan_map.get('IP') is not None and scan_map.get('name') >= 1 and scan_map.get('G') >= 1):
                            col_map = scan_map

                if 'name' not in col_map:
                    continue

                processed = 0
                # 固定マップ時はER(27)まで読めればよい。行によって列数が揃わない場合もあるので20以上で受ける
                min_cells = 20 if use_fixed_28 else 3
                for row in rows[header_row_idx + 1:]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < min_cells:
                        continue

                    # 固定マップ時: データ行の列数で25/26/27/28列マップを選択。投球回が「.1」別セルの行はIP以降+1
                    if use_fixed_28:
                        if len(cells) == 25:
                            base_map = FIXED_COL_MAP_25
                        elif len(cells) == 26:
                            base_map = FIXED_COL_MAP_26
                        elif len(cells) == 27:
                            base_map = FIXED_COL_MAP_27
                        else:
                            base_map = FIXED_COL_MAP_28
                        row_col_map = dict(base_map)
                        # 27セル行では .1 が16番目で安打は17番目のためシフトしない。28セル以上のときのみIP次が.1ならシフト
                        if (base_map.get('IP') is not None and base_map['IP'] + 1 < len(cells)
                                and len(cells) >= 28):
                            next_t = cells[base_map['IP'] + 1].get_text(strip=True)
                            if re.match(r'^\.\d+$', next_t):
                                for k in row_col_map:
                                    if row_col_map[k] > base_map['IP']:
                                        row_col_map[k] = row_col_map[k] + 1
                    else:
                        row_col_map = dict(col_map)
                        if col_map.get('IP') is not None and col_map['IP'] + 1 < len(cells):
                            next_t = cells[col_map['IP'] + 1].get_text(strip=True)
                            if re.match(r'^\.\d+$', next_t):
                                for k in row_col_map:
                                    if row_col_map[k] > col_map['IP']:
                                        row_col_map[k] = row_col_map[k] + 1

                    name_cell_idx = row_col_map.get('name', 0)
                    if name_cell_idx >= len(cells):
                        continue

                    name_cell = cells[name_cell_idx]
                    player_name_with_team = name_cell.get_text(strip=True)

                    # 次のセルが (略称) の場合はチームとして結合
                    if name_cell_idx + 1 < len(cells):
                        next_text = cells[name_cell_idx + 1].get_text(strip=True)
                        if re.match(r'^\([^)]+\)$', next_text):
                            player_name_with_team = player_name_with_team + next_text

                    player_link = name_cell.find('a', href=lambda x: x and '/bis/players/' in (x or ''))
                    if not player_link:
                        player_link = row.find('a', href=lambda x: x and '/bis/players/' in (x or ''))
                    player_id = extract_player_id_from_url(player_link.get('href', '')) if player_link else None

                    if not player_name_with_team:
                        continue

                    team_match = re.search(r'\(([^)]+)\)', player_name_with_team)
                    if team_match:
                        team_code = team_match.group(1).strip()
                        team_code_norm = team_code.replace(' ', '').replace('　', '')
                        team = TEAM_CODE_MAP.get(team_code_norm) or TEAM_CODE_MAP.get(team_code) or TEAM_CODE_MAP.get(team_code_norm[:1] if team_code_norm else '', '')
                        player_name_ja = re.sub(r'\([^)]+\)', '', player_name_with_team).strip()
                    else:
                        team = ''
                        player_name_ja = player_name_with_team

                    if not team and 'team' in row_col_map and row_col_map['team'] < len(cells):
                        team = normalize_team_name(cells[row_col_map['team']].get_text(strip=True))

                    if not player_id and player_name_ja:
                        name_norm = player_name_ja.replace('\u3000', ' ').replace('　', ' ')
                        if name_norm in player_id_map:
                            player_id = player_id_map[name_norm]
                        else:
                            for k, v in player_id_map.items():
                                if name_norm in k or k in name_norm:
                                    player_id = v
                                    break

                    # 規定以上・規定未到達の全テーブルから取得し、同一選手は先に出た行のみ採用
                    dedupe_key = (player_id,) if player_id else ('', player_name_ja, team)
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)

                    row_data: Dict[str, Any] = {
                        'year': year,
                        'league': league,
                        'team': team,
                        'player_id': player_id or '',
                        'player_name_ja': player_name_ja,
                        'player_name_en': '',
                        'G': _cell_val(cells, row_col_map, 'G'),
                        'IP': _cell_val(cells, row_col_map, 'IP', as_float=True),
                        'W': _cell_val(cells, row_col_map, 'W'),
                        'L': _cell_val(cells, row_col_map, 'L'),
                        'SV': _cell_val(cells, row_col_map, 'SV'),
                        'ERA': _cell_val(cells, row_col_map, 'ERA', as_float=True),
                        'BF': _cell_val(cells, row_col_map, 'BF'),
                        'H': _cell_val(cells, row_col_map, 'H'),
                        'HR': _cell_val(cells, row_col_map, 'HR'),
                        'BB': _cell_val(cells, row_col_map, 'BB'),
                        'IBB': _cell_val(cells, row_col_map, 'IBB'),
                        'HBP': _cell_val(cells, row_col_map, 'HBP'),
                        'SO': _cell_val(cells, row_col_map, 'SO'),
                        'ER': _cell_val(cells, row_col_map, 'ER'),
                        'R': _cell_val(cells, row_col_map, 'R'),
                    }
                    # オプション列
                    for key, ckey in [('HOLD', 'HOLD'), ('HP', 'HP'), ('CG', 'CG'), ('SHO', 'SHO'), ('WPCT', 'WPCT'), ('WP', 'WP'), ('BK', 'BK')]:
                        if ckey in row_col_map and row_col_map[ckey] < len(cells):
                            row_data[key] = _cell_val(cells, row_col_map, ckey, as_float=(key == 'WPCT'))

                    players.append(row_data)
                    processed += 1

                if processed > 0:
                    print(f"  📈 テーブル {table_idx + 1}: {processed}件を取得（累計 {len(players)}件）")

            # 2005年以降: 球団別ページ(idp1_*.html)から全投手を取得（計画書では球団別のみで全選手取得）
            if year >= 2005 and league in TEAM_IDS_BY_LEAGUE:
                print(f"  📡 球団別ページから全投手を取得中…")
                for team_id in TEAM_IDS_BY_LEAGUE[league]:
                    new_rows = _scrape_team_pitching_page(year, league, team_id, seen)
                    players.extend(new_rows)
                    time.sleep(0.3)

            if players:
                return players

            # BeautifulSoup でテーブルが取れない、または有効な表が見つからない場合のフォールバック
            if not players:
                print("⚠️ BeautifulSoup で投手成績表を取得できませんでした。pandas.read_html をフォールバックとして試行します。")
                players = _parse_pitching_with_pandas(html, year, league, player_id_map)
                if players:
                    return players
                print("[デバッグ] 失敗: pandas でも投手成績表を選択できませんでした。")
                return []

        except requests.exceptions.RequestException as e:
            print(f"⚠️ リクエストエラー (試行 {attempt + 1}/{retry}): {e}")
            if attempt == retry - 1:
                return []
        except Exception as e:
            print(f"❌ エラー: {e}")
            import traceback
            traceback.print_exc()
            return []

    return []


def _is_pitcher_row(row: Dict[str, Any]) -> bool:
    """G と IP が両方空の行（打者データ混入）は除外"""
    g = row.get('G')
    ip = row.get('IP')
    g_ok = g is not None and str(g).strip() != ''
    ip_ok = ip is not None and str(ip).strip() != ''
    return g_ok or ip_ok


def _write_pitching_csv(data: List[Dict[str, Any]], out_path: Path) -> None:
    """取得した投手成績をCSVに書き出す。G と IP が両方空の行（打者混入）は除外する。"""
    if not data:
        return
    filtered = [r for r in data if _is_pitcher_row(r)]
    skipped = len(data) - len(filtered)
    if skipped > 0:
        print(f"  📋 打者行を除外: {skipped}件")
    data = filtered
    if not data:
        return
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
    print(f"✅ 保存しました: {out_path} （{len(data)}件）")


def main():
    parser = argparse.ArgumentParser(description='NPB公式サイトから投手成績をスクレイピング')
    parser.add_argument('--year', type=int, default=None, help='年度（例: 2024）。--batch-to 使用時は開始年度')
    parser.add_argument('--league', type=str, choices=['PL', 'CL'], default=None, help='リーグ（PL/CL）。--batch-to 使用時は省略可（両方実行）')
    parser.add_argument('--batch-to', type=int, default=None,
                        help='Phase 1-b: この年度まで遡って一括取得（例: --year 2023 --batch-to 1950 で 2023〜1950）')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='出力ディレクトリ（省略時: _data/master_csv__import_1950_2024）')
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    out_dir = Path(args.output_dir) if args.output_dir else (project_root / '_data' / 'master_csv__import_1950_2024')
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.batch_to is not None:
        # Phase 1-b 一括: year から batch_to まで降順、PL/CL 両方
        if args.year is None:
            args.year = 2023
        start_year = args.year
        end_year = args.batch_to
        if start_year < end_year:
            start_year, end_year = end_year, start_year
        total = (start_year - end_year + 1) * 2  # 年度数 × PL,CL
        progress_log = out_dir / 'phase1b_progress.log'
        with open(progress_log, 'w', encoding='utf-8') as plog:
            plog.write(f"Phase 1-b 開始: {start_year} → {end_year} （{total} ファイル）\n")
        print(f"\n=== Phase 1-b 一括スクレイピング ===\n年度: {start_year} → {end_year}  リーグ: PL, CL  計{total}件\n出力: {out_dir}\n進捗ログ: {progress_log}\n")
        failed: List[tuple] = []
        current = 0
        for year in range(start_year, end_year - 1, -1):  # start_year から end_year まで含む（例: 2023→1950）
            for league in ('PL', 'CL'):
                current += 1
                out_path = out_dir / f'pitching_{year}_{league}_from_master.csv'
                print(f"\n[{current}/{total}] {year} {league} 取得中...")
                data = scrape_pitching_stats(year, league)
                if not data:
                    print(f"❌ データを取得できませんでした: {year} {league}")
                    failed.append((year, league))
                    with open(progress_log, 'a', encoding='utf-8') as plog:
                        plog.write(f"{year} {league} FAILED\n")
                    continue
                _write_pitching_csv(data, out_path)
                with open(progress_log, 'a', encoding='utf-8') as plog:
                    plog.write(f"{year} {league} {len(data)}件 OK\n")
                time.sleep(1)
        with open(progress_log, 'a', encoding='utf-8') as plog:
            plog.write(f"Phase 1-b 終了. 失敗: {len(failed)}件 {failed}\n")
        if failed:
            print(f"\n⚠️ 取得失敗: {failed}")
            sys.exit(1)
        print(f"\n✅ Phase 1-b 一括完了（{total} ファイル）")
        return

    if args.year is None or args.league is None:
        parser.error('--year と --league を指定するか、--batch-to で一括実行してください')
    out_path = out_dir / f'pitching_{args.year}_{args.league}_from_master.csv'
    print(f"\n=== NPB 投手成績スクレイピング ===\n年度: {args.year}  リーグ: {args.league}\n出力: {out_path}\n")
    data = scrape_pitching_stats(args.year, args.league)
    if not data:
        print("❌ データを取得できませんでした")
        sys.exit(1)
    _write_pitching_csv(data, out_path)


if __name__ == '__main__':
    main()
