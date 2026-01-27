#!/usr/bin/env python3
"""
build_rankings_phase1.py

2025年パ・リーグのOPSランキングTOP100を生成するスクリプト
batting_2025_PL_from_master.csv から OPS降順TOP100を抽出し、
public/data/rankings/2025/PL/OPS.json を出力する
"""

import csv
import json
import os
from pathlib import Path
from typing import List, Dict, Any


def load_csv_data(csv_path: str) -> List[Dict[str, Any]]:
    """CSVファイルを読み込む"""
    data = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


def calculate_ops(row: Dict[str, Any]) -> float:
    """OPSを計算する（出塁率 + 長打率）"""
    try:
        obp = float(row.get('OBP', 0) or 0)
        slg = float(row.get('SLG', 0) or 0)
        return obp + slg
    except (ValueError, TypeError):
        return 0.0


def format_player_data(row: Dict[str, Any], rank: int) -> Dict[str, Any]:
    """プレイヤーデータを既存UIの形式に整形する"""
    # 既存UIの期待する形式に合わせる
    # generatePlayerData() の形式を参考にする
    
    # チーム名のマッピング（必要に応じて調整）
    team_mapping = {
        'Bs': 'オリックス',
        'F': '日本ハム',
        'E': '楽天',
        'L': '西武',
        'M': 'ロッテ',
        'Hs': 'ソフトバンク',
    }
    
    team_code = row.get('Team', '')
    team_name = team_mapping.get(team_code, team_code)
    
    # 数値フィールドの変換
    def safe_float(value, default=0.0):
        try:
            return float(value) if value else default
        except (ValueError, TypeError):
            return default
    
    def safe_int(value, default=0):
        try:
            return int(float(value)) if value else default
        except (ValueError, TypeError):
            return default
    
    def format_decimal(value, decimals=3):
        try:
            return f"{float(value):.{decimals}f}"
        except (ValueError, TypeError):
            return f"{0.0:.{decimals}f}"
    
    # 既存UIの形式に合わせて整形
    player_data = {
        'playerId': f"player-{rank}",
        'name': row.get('Name', ''),
        'romanName': row.get('RomanName', ''),
        'team': team_name,
        'age': safe_int(row.get('Age', 0)),
        'ops': format_decimal(calculate_ops(row)),
        'avg': format_decimal(row.get('AVG', 0)),
        'hits': safe_int(row.get('H', 0)),
        'hr': safe_int(row.get('HR', 0)),
        'rbi': safe_int(row.get('RBI', 0)),
        'games': safe_int(row.get('G', 0)),
        'pa': safe_int(row.get('PA', 0)),
        'ab': safe_int(row.get('AB', 0)),
        'singles': safe_int(row.get('1B', 0)),
        'doubles': safe_int(row.get('2B', 0)),
        'triples': safe_int(row.get('3B', 0)),
        'runs': safe_int(row.get('R', 0)),
        'obp': format_decimal(row.get('OBP', 0)),
        'slg': format_decimal(row.get('SLG', 0)),
        'isop': format_decimal(safe_float(row.get('SLG', 0)) - safe_float(row.get('AVG', 0))),
        'isod': format_decimal(safe_float(row.get('OBP', 0)) - safe_float(row.get('AVG', 0))),
        'bbPct': format_decimal(safe_float(row.get('BB%', 0)), 1),
        'kPct': format_decimal(safe_float(row.get('K%', 0)), 1),
        'bb': safe_int(row.get('BB', 0)),
        'ibb': safe_int(row.get('IBB', 0)),
        'hbp': safe_int(row.get('HBP', 0)),
        'so': safe_int(row.get('SO', 0)),
        'bbk': format_decimal(safe_float(row.get('BB', 0)) / safe_float(row.get('SO', 1)) if safe_float(row.get('SO', 0)) > 0 else 0.0, 2),
        'tb': safe_int(row.get('TB', 0)),
        'sb': safe_int(row.get('SB', 0)),
        'cs': safe_int(row.get('CS', 0)),
        'sh': safe_int(row.get('SH', 0)),
        'sf': safe_int(row.get('SF', 0)),
        'gidp': safe_int(row.get('GIDP', 0)),
        'rc': safe_int(row.get('RC', 0)),
        'xr': safe_int(row.get('XR', 0)),
        'babip': format_decimal(row.get('BABIP', 0)),
        'seca': format_decimal(row.get('SecA', 0)),
        'ta': format_decimal(row.get('TA', 0)),
        'noi': format_decimal(row.get('NOI', 0)),
        'gpa': format_decimal(row.get('GPA', 0)),
    }
    
    return player_data


def generate_ops_ranking(csv_path: str, output_path: str, top_n: int = 100):
    """OPS降順TOP100を生成してJSONファイルに出力"""
    # CSVファイルを読み込む
    data = load_csv_data(csv_path)
    
    # OPSでソート（降順）
    data_with_ops = []
    for row in data:
        ops = calculate_ops(row)
        if ops > 0:  # OPSが0より大きいもののみ
            data_with_ops.append((ops, row))
    
    # OPS降順でソート
    data_with_ops.sort(key=lambda x: x[0], reverse=True)
    
    # TOP100を取得
    top_players = data_with_ops[:top_n]
    
    # 既存UIの形式に整形
    players = []
    for rank, (ops, row) in enumerate(top_players, start=1):
        player_data = format_player_data(row, rank)
        players.append(player_data)
    
    # 出力ディレクトリを作成
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # JSONファイルに出力
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(players, f, ensure_ascii=False, indent=2)
    
    print(f"✅ {len(players)}件のプレイヤーデータを {output_path} に出力しました")


def main():
    # スクリプトのディレクトリを基準にパスを設定
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # CSVファイルのパス（プロジェクトルート直下を想定）
    csv_path = project_root / 'batting_2025_PL_from_master.csv'
    
    # 出力先のパス
    output_path = project_root / 'public' / 'data' / 'rankings' / '2025' / 'PL' / 'OPS.json'
    
    # CSVファイルが存在するか確認
    if not csv_path.exists():
        print(f"❌ エラー: CSVファイルが見つかりません: {csv_path}")
        print(f"   以下のパスにCSVファイルを配置してください: {csv_path}")
        return 1
    
    # ランキング生成
    try:
        generate_ops_ranking(str(csv_path), str(output_path), top_n=100)
        print(f"✅ 処理が完了しました")
        return 0
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())






















