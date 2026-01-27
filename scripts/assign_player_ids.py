#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
assign_player_ids.py

既存のCSVファイルにplayer_idを割り当てるスクリプト
NPB公式サイトのHTMLからplayer_idを抽出して、選手名とマッチング
"""

import argparse
import csv
import sys
import io
import re
import time
from pathlib import Path
from typing import Dict, Optional

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


def get_known_player_ids() -> Dict[str, str]:
    """
    既知のplayer_idを返す（手動で管理）
    """
    return {
        'ファビアン': '2114882',
        'サンドロ・ファビアン': '2114882',
        '西川史礁': '1950286',
        '西川 史礁': '1950286',
    }


def fetch_html_with_player_ids(year: int, league: str) -> Dict[str, str]:
    """
    NPB公式サイトからHTMLを取得し、選手名とplayer_idのマッピングを作成
    
    Returns:
        {選手名: player_id} の辞書
    """
    # 2025年以降はURL構造が変更されている
    if year >= 2025:
        league_code = 'p' if league.upper() == 'PL' else 'c'
        url = f"https://npb.jp/bis/{year}/stats/bat_{league_code}.html"
    else:
        league_lower = league.lower()
        url = f"https://npb.jp/bis/stats/{year}/{league_lower}/batting.html"
    
    print(f"📡 NPB公式サイトからplayer_idを取得中: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or 'utf-8'
        html = response.text
        
        player_id_map = {}
        
        # デバッグ: HTML内の/bis/players/の出現箇所を確認
        player_id_matches = re.findall(r'/bis/players/(\d+)', html)
        print(f"  📊 HTML内の '/bis/players/' パターン: {len(player_id_matches)}件見つかりました")
        if player_id_matches:
            print(f"      例: {player_id_matches[:5]}")
        
        if '/bis/players/' in html:
            # パターン1: <a href="/bis/players/数字">選手名</a>
            link_pattern1 = r'<a[^>]*href=["\']([^"\']*\/bis\/players\/(\d+)[^"\']*)["\'][^>]*>([^<]+)<\/a>'
            matches1 = list(re.finditer(link_pattern1, html, re.IGNORECASE))
            print(f"  📊 パターン1（<a>タグ）: {len(matches1)}件見つかりました")
            
            # パターン2: 選手名列のセル内にリンクがある場合
            # テーブル行を探して、選手名列のセル内のリンクを抽出
            soup = BeautifulSoup(html, 'lxml')
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    for cell in cells:
                        # セル内のリンクを探す
                        links = cell.find_all('a', href=lambda x: x and '/bis/players/' in x if x else False)
                        for link in links:
                            href = link.get('href', '')
                            player_id_match = re.search(r'/bis/players/(\d+)', href)
                            if player_id_match:
                                player_id = player_id_match.group(1)
                                player_name = link.get_text(strip=True)
                                # 括弧内のチーム名を除去
                                player_name_clean = re.sub(r'\([^)]+\)', '', player_name).strip()
                                if player_name_clean and len(player_name_clean) < 50:
                                    # 選手名を正規化（全角スペースを統一）
                                    player_name_normalized = player_name_clean.replace('\u3000', ' ').replace('　', ' ')
                                    if player_name_normalized not in player_id_map:
                                        player_id_map[player_name_normalized] = player_id
            
            # パターン1の結果も追加
            for match in matches1:
                player_id = match.group(2)
                player_name = match.group(3).strip()
                # 括弧内のチーム名を除去
                player_name_clean = re.sub(r'\([^)]+\)', '', player_name).strip()
                if player_name_clean and len(player_name_clean) < 50:
                    # 選手名を正規化（全角スペースを統一）
                    player_name_normalized = player_name_clean.replace('\u3000', ' ').replace('　', ' ')
                    if player_name_normalized not in player_id_map:
                        player_id_map[player_name_normalized] = player_id
            
            print(f"  ✅ {len(player_id_map)}個のplayer_idマッピングを作成しました")
            if player_id_map:
                # 最初の5件を表示
                sample_items = list(player_id_map.items())[:5]
                for name, pid in sample_items:
                    print(f"      例: {name} -> {pid}")
        else:
            print(f"  ⚠️ HTMLに '/bis/players/' が含まれていません")
        
        return player_id_map
        
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return {}


def assign_player_ids_to_csv(csv_path: Path, player_id_map: Dict[str, str], year: int, league: str):
    """
    CSVファイルにplayer_idを割り当て
    """
    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return
    
    # CSVを読み込む
    rows = []
    headers = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)
    
    print(f"📖 CSVファイルを読み込みました: {len(rows)}件")
    
    # player_idカラムが存在しない場合は追加
    if 'player_id' not in headers:
        headers.append('player_id')
    
    # 各選手にplayer_idを割り当て
    assigned_count = 0
    updated_count = 0
    
    for row in rows:
        player_name_ja = str(row.get('player_name_ja', '')).strip()
        existing_player_id = str(row.get('player_id', '')).strip()
        
        if not player_name_ja:
            continue
        
        # 選手名を正規化
        player_name_normalized = player_name_ja.replace('\u3000', ' ').replace('　', ' ')
        
        # player_idを検索
        new_player_id = None
        if player_name_normalized in player_id_map:
            new_player_id = player_id_map[player_name_normalized]
        else:
            # 部分マッチングを試行
            for mapped_name, mapped_id in player_id_map.items():
                if player_name_normalized in mapped_name or mapped_name in player_name_normalized:
                    new_player_id = mapped_id
                    break
        
        if new_player_id:
            if existing_player_id != new_player_id:
                row['player_id'] = new_player_id
                updated_count += 1
                if assigned_count < 5:
                    print(f"  ✅ player_idを割り当て: {player_name_ja} -> {new_player_id}")
            assigned_count += 1
    
    print(f"📊 割り当て結果: {assigned_count}件の選手にplayer_idを割り当て（更新: {updated_count}件）")
    
    # バックアップを作成
    backup_path = csv_path.with_suffix(csv_path.suffix + '.backup')
    if csv_path.exists():
        import shutil
        shutil.copy2(csv_path, backup_path)
        print(f"💾 バックアップを作成しました: {backup_path}")
    
    # CSVを保存
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✅ CSVファイルを更新しました: {csv_path}")


def main():
    parser = argparse.ArgumentParser(description='既存CSVファイルにplayer_idを割り当て')
    parser.add_argument('--year', type=int, required=True, help='年度（例: 2025）')
    parser.add_argument('--league', type=str, required=True, choices=['PL', 'CL'], help='リーグ（PL/CL）')
    
    args = parser.parse_args()
    
    # プロジェクトルートを取得
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # CSVファイルのパス
    csv_path = project_root / '_data' / 'master_csv' / f'batting_{args.year}_{args.league}_from_master.csv'
    
    print(f"\n{'='*60}")
    print(f"=== player_id割り当て ===")
    print(f"{'='*60}\n")
    print(f"年度: {args.year}")
    print(f"リーグ: {args.league}")
    print(f"CSVファイル: {csv_path}\n")
    
    # HTMLからplayer_idマッピングを取得
    player_id_map = fetch_html_with_player_ids(args.year, args.league)
    
    # 既知のplayer_idを追加
    known_ids = get_known_player_ids()
    player_id_map.update(known_ids)
    print(f"  📝 既知のplayer_id: {len(known_ids)}件を追加しました")
    
    if not player_id_map:
        print("⚠️ player_idマッピングが空です。既知のplayer_idのみを使用します")
    
    # CSVにplayer_idを割り当て
    assign_player_ids_to_csv(csv_path, player_id_map, args.year, args.league)
    
    print(f"\n📋 次のステップ:")
    print(f"   1. 指標計算を再実行: py scripts/compute_metrics_all_seasons.py --year {args.year} --league {args.league} --overwrite")
    print(f"   2. 検証: node scripts/fact_check_npb_official.mjs {args.year} {args.league}")


if __name__ == '__main__':
    main()
