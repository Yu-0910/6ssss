#!/usr/bin/env python3
"""
build_games_per_team_map.py

my favorite giants の「NPB 各年度試合方式」ページから
年度別試合数をスクレイプしてJSON化するスクリプト

出力: config/games_per_team_by_season.json
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser


class GamesTableParser(HTMLParser):
    """試合数テーブルをパースするHTMLパーサー"""
    
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row = []
        self.rows = []
        self.current_tag = None
        
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            # 試合方式のテーブルを探す（class属性などで絞り込む）
            self.in_table = True
        elif tag == 'tr' and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag in ['td', 'th'] and self.in_row:
            self.in_cell = True
            self.current_tag = tag
            
    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
        elif tag == 'tr' and self.in_row:
            if self.current_row:
                self.rows.append(self.current_row)
            self.in_row = False
            self.current_row = []
        elif tag in ['td', 'th']:
            self.in_cell = False
            self.current_tag = None
            
    def handle_data(self, data):
        if self.in_cell:
            text = data.strip()
            if text:
                self.current_row.append(text)


def parse_games_string(games_str: str) -> Optional[int]:
    """
    試合数文字列をパース（例: "143", "26/24/99", "56/49"）
    
    @param games_str: 試合数文字列
    @returns: 試合数（分割シーズンの場合は最初の値、パース失敗時はNone）
    """
    if not games_str or games_str.strip() == '':
        return None
    
    # 数値のみの場合
    if re.match(r'^\d+$', games_str):
        return int(games_str)
    
    # 分割シーズン（例: "26/24/99", "56/49"）
    if '/' in games_str:
        parts = games_str.split('/')
        # 最初の値を返す（または合計を返す？仕様に合わせる）
        # ここでは最初の値を返す（春の試合数）
        try:
            return int(parts[0].strip())
        except ValueError:
            return None
    
    # その他の形式（例: "開催なし"）
    return None


def extract_season_key(year: int, season_suffix: Optional[str] = None) -> str:
    """
    シーズンキーを生成
    
    @param year: 年度
    @param season_suffix: シーズンサフィックス（"S"=春, "U"=夏, "F"=秋）
    @returns: シーズンキー（例: "2025", "1936S", "1937F"）
    """
    if season_suffix:
        return f"{year}{season_suffix}"
    return str(year)


def scrape_games_per_team() -> Dict[str, Dict[str, int]]:
    """
    my favorite giants の試合方式ページから試合数をスクレイプ
    
    @returns: {seasonKey: {league: games_per_team}}
    """
    url = "https://www.my-favorite-giants.net/npb/method.htm"
    
    print(f"📡 スクレイプ開始: {url}")
    
    try:
        with urlopen(url, timeout=10) as response:
            html = response.read().decode('shift_jis', errors='ignore')
    except (URLError, HTTPError) as e:
        print(f"❌ エラー: ページの取得に失敗しました: {e}")
        print(f"   手動で試合数マップを作成してください")
        return {}
    
    parser = GamesTableParser()
    parser.feed(html)
    
    result: Dict[str, Dict[str, int]] = {}
    
    # パースしたテーブル行を処理
    # 実際のHTML構造に合わせて調整が必要
    for row in parser.rows:
        if len(row) < 2:
            continue
        
        # 年度列と試合数列を探す
        # 実際のHTML構造に合わせて調整
        year_str = row[0].strip()
        games_str = row[1].strip() if len(row) > 1 else ""
        
        # 年度を抽出
        year_match = re.match(r'(\d{4})', year_str)
        if not year_match:
            continue
        
        year = int(year_match.group(1))
        
        # 試合数をパース
        games = parse_games_string(games_str)
        if games is None:
            continue
        
        # 1950以降は2リーグ、それ以前は1リーグ（PRE）
        if year >= 1950:
            # 2リーグ制（CL/PL）
            # 実際のHTMLにはCL/PLの試合数が別々に記載されている可能性
            # ここでは仮に同じ値を使用（実際のHTML構造に合わせて調整）
            result[str(year)] = {
                "CL": games,
                "PL": games
            }
        else:
            # 1リーグ制（PRE）
            result[str(year)] = {
                "PRE": games
            }
    
    # 分割シーズンの処理（1936-1938）
    # 実際のHTML構造に合わせて調整
    # 例: 1936は "26/24/99" → 1936S: 26, 1936U: 24, 1936F: 99
    
    print(f"✅ スクレイプ完了: {len(result)}件のシーズンを取得")
    
    return result


def smoke_test(games_map: Dict[str, Dict[str, int]]) -> bool:
    """
    スモークテスト: 重要なシーズンが正しく取得できているか検証
    
    @param games_map: 試合数マップ
    @returns: すべてのテストがパスした場合True
    """
    print("\n" + "="*60)
    print("🧪 スモークテスト実行中...")
    print("="*60)
    
    all_passed = True
    
    # 1936S/1936U/1936F の確認
    print("\n1. 1936年分割シーズン（3季）:")
    for suffix in ['S', 'U', 'F']:
        season_key = f"1936{suffix}"
        if season_key in games_map and 'PRE' in games_map[season_key]:
            games = games_map[season_key]['PRE']
            print(f"   ✅ {season_key}: PRE = {games}")
        else:
            print(f"   ❌ {season_key}: PRE が見つかりません")
            all_passed = False
    
    # 1937S/1937F の確認
    print("\n2. 1937年分割シーズン（2季）:")
    for suffix in ['S', 'F']:
        season_key = f"1937{suffix}"
        if season_key in games_map and 'PRE' in games_map[season_key]:
            games = games_map[season_key]['PRE']
            print(f"   ✅ {season_key}: PRE = {games}")
        else:
            print(f"   ❌ {season_key}: PRE が見つかりません")
            all_passed = False
    
    # 1938S/1938F の確認
    print("\n3. 1938年分割シーズン（2季）:")
    for suffix in ['S', 'F']:
        season_key = f"1938{suffix}"
        if season_key in games_map and 'PRE' in games_map[season_key]:
            games = games_map[season_key]['PRE']
            print(f"   ✅ {season_key}: PRE = {games}")
        else:
            print(f"   ❌ {season_key}: PRE が見つかりません")
            all_passed = False
    
    # 1950年の2リーグ制確認
    print("\n4. 1950年（2リーグ制開始）:")
    if '1950' in games_map:
        if 'CL' in games_map['1950'] and 'PL' in games_map['1950']:
            cl_games = games_map['1950']['CL']
            pl_games = games_map['1950']['PL']
            print(f"   ✅ 1950: CL = {cl_games}, PL = {pl_games}")
        else:
            print(f"   ❌ 1950: CL/PL のいずれかが見つかりません")
            all_passed = False
    else:
        print(f"   ❌ 1950: シーズンキーが見つかりません")
        all_passed = False
    
    # 2025年の2リーグ制確認
    print("\n5. 2025年（最新）:")
    if '2025' in games_map:
        if 'CL' in games_map['2025'] and 'PL' in games_map['2025']:
            cl_games = games_map['2025']['CL']
            pl_games = games_map['2025']['PL']
            print(f"   ✅ 2025: CL = {cl_games}, PL = {pl_games}")
        else:
            print(f"   ❌ 2025: CL/PL のいずれかが見つかりません")
            all_passed = False
    else:
        print(f"   ❌ 2025: シーズンキーが見つかりません")
        all_passed = False
    
    # 1945年（開催なし）の確認
    print("\n6. 1945年（開催なし）:")
    if '1945' in games_map:
        if 'PRE' in games_map['1945'] and games_map['1945']['PRE'] is None:
            print(f"   ✅ 1945: PRE = null (開催なしとして正しく記録)")
        elif 'PRE' in games_map['1945']:
            print(f"   ⚠️  1945: PRE = {games_map['1945']['PRE']} (nullが期待されますが、値が入っています)")
        else:
            print(f"   ⚠️  1945: PRE が見つかりません")
    else:
        print(f"   ⚠️  1945: シーズンキーが見つかりません（開催なしなのでスキップでもOK）")
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ スモークテスト: すべてパス")
    else:
        print("❌ スモークテスト: 一部失敗")
    print("="*60)
    
    return all_passed


def main():
    """メイン処理"""
    import argparse
    parser = argparse.ArgumentParser(description='試合数マップを生成')
    parser.add_argument('--smoke', action='store_true', help='スモークテストのみ実行（出力しない）')
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    output_path = project_root / 'config' / 'games_per_team_by_season.json'
    
    print(f"📁 プロジェクトルート: {project_root}")
    
    # スクレイプ実行
    games_map = scrape_games_per_team()
    
    if not games_map:
        print("❌ エラー: 試合数マップが空です")
        print("   手動で試合数マップを作成してください")
        return 1
    
    # スモークテスト
    if args.smoke:
        if smoke_test(games_map):
            return 0
        else:
            print("\n❌ スモークテストが失敗しました。ページ構造が変更されている可能性があります。")
            return 1
    
    # 通常実行: スモークテストも実行してから出力
    if not smoke_test(games_map):
        print("\n⚠️  警告: スモークテストが失敗しましたが、続行します...")
    
    print(f"\n📁 出力先: {output_path}")
    
    # 出力ディレクトリを作成
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # JSONファイルに出力
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(games_map, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 試合数マップを出力しました: {output_path}")
    print(f"   シーズン数: {len(games_map)}")
    
    return 0


if __name__ == '__main__':
    exit(main())

