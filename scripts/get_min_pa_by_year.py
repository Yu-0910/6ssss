#!/usr/bin/env python3
"""
get_min_pa_by_year.py

年度からNPB公式ページを取得してチーム試合数(G)を取得し、
規定打席(min_pa)を計算する関数を提供する。

min_pa = round(G * 3.1)
"""

import re
import urllib.request
import urllib.error
from typing import Tuple, Optional
from html.parser import HTMLParser


class GamesTableParser(HTMLParser):
    """勝敗表から試合数を抽出するパーサー"""
    
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row = []
        self.current_cell_text = []
        self.games_value = None
        self.found_games_header = False
        self.games_col_index = None
        self.row_count = 0
        
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.in_table = True
        elif tag == 'tr' and self.in_table:
            self.in_row = True
            self.current_row = []
            self.current_cell_text = []
        elif tag in ('td', 'th') and self.in_row:
            self.in_cell = True
            self.current_cell_text = []
            
    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
        elif tag == 'tr' and self.in_row:
            self.in_row = False
            # セルのテキストを結合して行に追加
            if self.current_cell_text:
                cell_text = ' '.join(self.current_cell_text).strip()
                if cell_text:
                    self.current_row.append(cell_text)
            # 試合数列の値を取得（最初のデータ行）
            if self.current_row and self.games_col_index is not None:
                if self.row_count > 0 and len(self.current_row) > self.games_col_index:
                    games_text = self.current_row[self.games_col_index].strip()
                    # "120/143" や "143" のような形式から数値を取得
                    # スラッシュがある場合は後ろの数値（総試合数）を優先
                    if '/' in games_text:
                        match = re.search(r'/(\d+)', games_text)
                        if match:
                            self.games_value = int(match.group(1))
                    else:
                        match = re.search(r'(\d+)', games_text)
                        if match:
                            self.games_value = int(match.group(1))
            self.current_row = []
            self.current_cell_text = []
            self.row_count += 1
        elif tag in ('td', 'th') and self.in_cell:
            self.in_cell = False
            # セルのテキストを結合
            if self.current_cell_text:
                cell_text = ' '.join(self.current_cell_text).strip()
                if cell_text:
                    self.current_row.append(cell_text)
                self.current_cell_text = []
            
    def handle_data(self, data):
        if self.in_cell:
            text = data.strip()
            if text:
                self.current_cell_text.append(text)
                # ヘッダー行で「試合」列を探す
                if self.row_count == 0 and not self.found_games_header:
                    if '試合' in text or text.strip().upper() == 'G':
                        # 現在のセルがヘッダー行の何列目かを計算
                        self.games_col_index = len(self.current_row)
                        self.found_games_header = True


def get_games_from_url(url: str) -> Optional[int]:
    """
    NPB公式ページのURLから試合数を取得
    
    Args:
        url: NPB公式ページのURL
        
    Returns:
        試合数（取得失敗時はNone）
    """
    try:
        # User-Agentを設定（403エラー回避）
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        parser = GamesTableParser()
        parser.feed(html)
        
        return parser.games_value
        
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
        print(f"   ⚠️  URL取得エラー ({url}): {e}")
        return None


def get_min_pa_by_year(year: int, league: str = "PL") -> Tuple[int, int, str]:
    """
    年度からチーム試合数と規定打席を取得
    
    Args:
        year: 年度（例: 2025）
        league: リーグ（"PL" または "CL"、デフォルトは"PL"）
        
    Returns:
        (games, min_pa, source_url) のタプル
        
    Raises:
        ValueError: 試合数の取得に失敗した場合
    """
    # 優先順位A: https://npb.jp/bis/yearly/centralleague_{year}.html または pacificleague_{year}.html
    league_name = "centralleague" if league == "CL" else "pacificleague"
    url_a = f"https://npb.jp/bis/yearly/{league_name}_{year}.html"
    
    games = get_games_from_url(url_a)
    source_url = url_a
    
    # フォールバックB: https://npb.jp/bis/{year}/stats/
    if games is None:
        url_b = f"https://npb.jp/bis/{year}/stats/"
        games = get_games_from_url(url_b)
        source_url = url_b
    
    if games is None:
        raise ValueError(
            f"❌ {year}年の試合数を取得できませんでした。\n"
            f"   試したURL:\n"
            f"   - {url_a}\n"
            f"   - {url_b}\n"
            f"   NPB公式ページの構造が変わった可能性があります。"
        )
    
    # min_pa = round(games * 3.1)
    min_pa = int(round(games * 3.1))
    
    return games, min_pa, source_url


if __name__ == '__main__':
    """テスト実行"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python get_min_pa_by_year.py <year> [league]")
        print("Example: python get_min_pa_by_year.py 2025 PL")
        sys.exit(1)
    
    year = int(sys.argv[1])
    league = sys.argv[2] if len(sys.argv) > 2 else "PL"
    
    try:
        games, min_pa, source_url = get_min_pa_by_year(year, league)
        print(f"✅ {year}年{league}リーグ:")
        print(f"   試合数(G): {games}")
        print(f"   規定打席(min_pa): {min_pa}")
        print(f"   取得元URL: {source_url}")
    except ValueError as e:
        print(e)
        sys.exit(1)

