#!/usr/bin/env python3
"""
build_rankings_all_years.py

将来用：全年度・全リーグのランキングを一括生成するスクリプト
_data/master_csv/ 内の batting_????_(PL|CL)_from_master.csv をglobで列挙し、
各年度・リーグごとにランキングJSONを生成する

注意：このスクリプトは現時点では未使用です（将来の全年度対応用の足場として作成）
"""

import csv
import json
import math
import re
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple

# 既存スクリプトから関数をインポート（再利用）
# 実際には同じ関数をコピーするか、共通モジュール化する必要がある
# ここでは将来の実装のための骨組みのみ提供


def find_file_with_fallback(filename: str, search_paths: List[Path]) -> Optional[Path]:
    """ファイルを複数のパスから順に探す"""
    for search_path in search_paths:
        file_path = search_path / filename
        if file_path.exists():
            return file_path
    return None


def parse_year_and_league_from_filename(filename: str) -> Optional[Tuple[int, str]]:
    """
    ファイル名から年度とリーグをパース
    例: batting_2025_PL_from_master.csv -> (2025, 'PL')
    """
    pattern = r'batting_(\d{4})_(PL|CL)_from_master\.csv'
    match = re.match(pattern, filename)
    if match:
        year = int(match.group(1))
        league = match.group(2)
        return (year, league)
    return None


def find_all_batting_csv_files(data_dir: Path) -> List[Tuple[Path, int, str]]:
    """
    _data/master_csv/ 内の batting_????_(PL|CL)_from_master.csv を列挙
    戻り値: [(ファイルパス, 年度, リーグ), ...]
    """
    results = []
    
    # globで検索
    for pattern_single in [str(data_dir / 'batting_*_PL_from_master.csv'), 
                           str(data_dir / 'batting_*_CL_from_master.csv')]:
        for file_path_str in glob.glob(pattern_single):
            file_path = Path(file_path_str)
            filename = file_path.name
            parsed = parse_year_and_league_from_filename(filename)
            if parsed:
                year, league = parsed
                results.append((file_path, year, league))
    
    return results


def main():
    """
    メイン処理（将来実装用の骨組み）
    現時点では実行しません
    """
    print("⚠️  このスクリプトは将来用の足場として作成されています")
    print("   現時点では実行されません")
    print("   実装が必要になった際に、build_rankings_2025_PL_full.py の処理を")
    print("   再利用して全年度・全リーグ対応を実装してください")
    
    # スクリプトのディレクトリを基準にパスを設定
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_master_csv_dir = project_root / '_data' / 'master_csv'
    
    # 将来の実装イメージ：
    # 1. _data/master_csv/ 内のCSVファイルを列挙
    # 2. 各ファイルから年度・リーグを抽出
    # 3. Record.csv を読み込み（既存の探索ロジックを使用）
    # 4. 各年度・リーグごとに generate_ranking_for_metric() を呼び出し
    # 5. public/data/rankings/{year}/{league}/ に出力
    
    if not data_master_csv_dir.exists():
        print(f"\n📁 _data/master_csv/ ディレクトリが存在しません")
        print(f"   パス: {data_master_csv_dir}")
        return 0
    
    # デモ：見つかったファイルを表示（実際の処理はしない）
    csv_files = find_all_batting_csv_files(data_master_csv_dir)
    if csv_files:
        print(f"\n📄 見つかったCSVファイル: {len(csv_files)}件")
        for file_path, year, league in sorted(csv_files):
            print(f"   - {file_path.name} → 年度: {year}, リーグ: {league}")
    else:
        print(f"\n📄 CSVファイルが見つかりませんでした")
        print(f"   探索パス: {data_master_csv_dir}")
    
    return 0


if __name__ == '__main__':
    exit(main())

