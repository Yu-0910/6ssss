#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fact_check_external_simple.py

既存のplayer_idリストとCSVファイルを比較して、
CSVに存在しない選手を特定するスクリプト（簡易版）

使用方法:
    python scripts/fact_check_external_simple.py <YEAR> <LEAGUE>
"""

import sys
import io
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set

# WindowsでのUnicode出力対応
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import pandas as pd
except ImportError:
    print("❌ エラー: pandasがインストールされていません")
    print("   インストール方法: pip install pandas")
    sys.exit(1)

# プロジェクトルートを取得
script_dir = Path(__file__).parent
project_root = script_dir.parent


def load_all_player_ids() -> Set[str]:
    """全player_idリストを読み込む"""
    player_ids_path = project_root / 'output' / 'master' / 'all_player_ids.csv'
    
    if not player_ids_path.exists():
        print(f"⚠️ player_idリストが見つかりません: {player_ids_path}")
        return set()
    
    player_ids = set()
    try:
        with open(player_ids_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                player_id = row.get('player_id', '').strip()
                if player_id:
                    player_ids.add(player_id)
        
        print(f"✅ {len(player_ids)}件のplayer_idを読み込みました")
        return player_ids
    except Exception as e:
        print(f"❌ player_idリストの読み込みエラー: {e}")
        return set()


def load_csv_player_ids(csv_path: Path) -> Set[str]:
    """CSVファイルからplayer_idを読み込む"""
    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return set()
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        
        # player_idカラムを探す
        player_id_col = None
        for col in df.columns:
            if 'player_id' in col.lower():
                player_id_col = col
                break
        
        if not player_id_col:
            print("⚠️ CSVにplayer_idカラムが見つかりません")
            return set()
        
        player_ids = set()
        for _, row in df.iterrows():
            player_id = str(row.get(player_id_col, '')).strip()
            if player_id and player_id != 'nan':
                player_ids.add(player_id)
        
        print(f"✅ CSVから{len(player_ids)}件のplayer_idを読み込みました")
        return player_ids
        
    except Exception as e:
        print(f"❌ CSV読み込みエラー: {e}")
        return set()


def get_player_info_from_master(player_id: str) -> Dict:
    """master辞書から選手情報を取得"""
    # player_id_to_roman_full.csvから情報を取得
    master_path = project_root / 'output' / 'master' / 'player_id_to_roman_full.csv'
    
    if not master_path.exists():
        return {'name_ja': '', 'roman_name': ''}
    
    try:
        with open(master_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('player_id', '').strip() == player_id:
                    return {
                        'name_ja': row.get('name_ja', '').strip(),
                        'roman_name': row.get('romanName', '').strip()
                    }
    except Exception:
        pass
    
    return {'name_ja': '', 'roman_name': ''}


def main():
    if len(sys.argv) < 3:
        print("使用方法: python fact_check_external_simple.py <YEAR> <LEAGUE>")
        print("例: python fact_check_external_simple.py 2025 PL")
        sys.exit(1)
    
    year = int(sys.argv[1])
    league = sys.argv[2].upper()
    
    csv_path = project_root / '_data' / 'master_csv_calculated' / f'batting_{year}_{league}_from_master.csv'
    
    print(f"\n{'='*60}")
    print(f"=== 外部データソースとのファクトチェック（簡易版） ===")
    print(f"{'='*60}\n")
    print(f"年度: {year}")
    print(f"リーグ: {league}")
    print(f"CSVファイル: {csv_path}\n")
    
    # 全player_idリストを読み込む
    print("📖 全player_idリストを読み込み中...")
    all_player_ids = load_all_player_ids()
    
    if not all_player_ids:
        print("⚠️ player_idリストが空です。別の方法で確認してください。")
        sys.exit(1)
    
    # CSVからplayer_idを読み込む
    print(f"\n📖 CSVファイルからplayer_idを読み込み中...")
    csv_player_ids = load_csv_player_ids(csv_path)
    
    if not csv_player_ids:
        print("⚠️ CSVからplayer_idを読み込めませんでした。")
        sys.exit(1)
    
    # 比較
    print(f"\n🔍 player_idを比較中...\n")
    missing_ids = all_player_ids - csv_player_ids
    extra_ids = csv_player_ids - all_player_ids
    
    print(f"{'='*60}")
    print(f"=== 比較結果 ===")
    print(f"{'='*60}\n")
    print(f"全player_id数: {len(all_player_ids)}")
    print(f"CSV内player_id数: {len(csv_player_ids)}")
    print(f"一致: {len(all_player_ids & csv_player_ids)}")
    print(f"CSVに不足（全リストにあるがCSVにない）: {len(missing_ids)}")
    print(f"CSVにのみ存在（CSVにあるが全リストにない）: {len(extra_ids)}\n")
    
    # 不足しているplayer_idの詳細を表示
    if missing_ids:
        print(f"⚠️ CSVに存在しないplayer_id ({len(missing_ids)}件):\n")
        
        missing_players = []
        for i, player_id in enumerate(sorted(missing_ids), 1):
            player_info = get_player_info_from_master(player_id)
            name_ja = player_info.get('name_ja', 'N/A')
            roman_name = player_info.get('roman_name', 'N/A')
            
            missing_players.append({
                'player_id': player_id,
                'name_ja': name_ja,
                'roman_name': roman_name
            })
            
            if i <= 50:  # 最初の50件のみ表示
                print(f"  {i:3d}. {player_id:10s} - {name_ja:20s} ({roman_name})")
            elif i == 51:
                print(f"  ... 他 {len(missing_ids) - 50}件")
        
        # CSV形式で保存
        output_dir = project_root / 'output' / 'reports' / 'fact_check'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f'missing_players_{year}_{league}_external.csv'
        df_missing = pd.DataFrame(missing_players)
        df_missing.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n✅ 不足しているplayer_idをCSV形式で保存しました: {output_file}")
    else:
        print("✅ すべてのplayer_idがCSVファイルに含まれています\n")
    
    # 結果をJSON形式で保存
    output_dir = project_root / 'output' / 'reports' / 'fact_check'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    result_json = {
        'year': year,
        'league': league,
        'check_date': datetime.now().isoformat(),
        'all_player_ids_count': len(all_player_ids),
        'csv_player_ids_count': len(csv_player_ids),
        'matched_count': len(all_player_ids & csv_player_ids),
        'missing_in_csv_count': len(missing_ids),
        'extra_in_csv_count': len(extra_ids),
        'missing_player_ids': sorted(list(missing_ids))
    }
    
    json_file = output_dir / f'fact_check_{year}_{league}_external.json'
    import json
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result_json, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 結果をJSON形式で保存しました: {json_file}\n")
    
    if missing_ids:
        print(f"⚠️ {len(missing_ids)}件のplayer_idがCSVに不足しています")
        sys.exit(1)
    else:
        print("✅ すべてのplayer_idがCSVに含まれています")
        sys.exit(0)


if __name__ == '__main__':
    main()




