#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_qualifying_pa_table.py

_data/qualifying_pa_table.csv のスキーマとデータ整合性を検証するスクリプト
"""

import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("エラー: pandas が必要です。以下のコマンドでインストールしてください:")
    print("   pip install pandas")
    sys.exit(1)

# プロジェクトルートを取得
script_dir = Path(__file__).parent
project_root = script_dir.parent

# 必須列定義
REQUIRED_COLUMNS = ["season_key", "year", "league", "team", "games", "qual_type", "qual_value"]


def validate_qualifying_pa_table(csv_path: Path) -> int:
    """
    qualifying_pa_table.csv を検証
    
    Returns:
        0: 成功
        1: 失敗
    """
    if not csv_path.exists():
        print(f"エラー: CSVファイルが見つかりません: {csv_path}")
        return 1
    
    try:
        # CSVを読み込み
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        
        # 検証1: 必須列が全て存在
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            print(f"エラー: 必須列が欠けています: {missing_columns}")
            print(f"  必須列: {REQUIRED_COLUMNS}")
            print(f"  実際の列: {list(df.columns)}")
            return 1
        
        # 検証2: games, qual_value は欠損なし・数値変換できること
        for col in ["games", "qual_value"]:
            if df[col].isna().any():
                print(f"エラー: {col} に欠損値があります")
                missing_rows = df[df[col].isna()]
                print(f"  欠損行数: {len(missing_rows)}")
                return 1
            
            try:
                df[col] = pd.to_numeric(df[col], errors='raise')
            except (ValueError, TypeError) as e:
                print(f"エラー: {col} を数値に変換できません: {e}")
                invalid_rows = df[pd.to_numeric(df[col], errors='coerce').isna()]
                print(f"  無効な行数: {len(invalid_rows)}")
                if len(invalid_rows) <= 10:
                    print(f"  無効な行:")
                    for idx, row in invalid_rows.iterrows():
                        print(f"    行{idx+2}: {row.to_dict()}")
                return 1
        
        # 検証3: (season_key, team) の重複がないこと
        duplicates = df[df.duplicated(subset=["season_key", "team"], keep=False)]
        if len(duplicates) > 0:
            print(f"エラー: (season_key, team) の重複があります")
            print(f"  重複行数: {len(duplicates)}")
            if len(duplicates) <= 20:
                print(f"  重複行:")
                for idx, row in duplicates.iterrows():
                    print(f"    行{idx+2}: season_key={row['season_key']}, team={row['team']}")
            return 1
        
        # 検証4: year が 1936〜2025 をすべて含むこと（整数として比較）
        df['year_int'] = pd.to_numeric(df['year'], errors='coerce')
        
        # まず範囲外の年がないか確認
        invalid_years = df[df['year_int'].isna() | (df['year_int'] < 1936) | (df['year_int'] > 2025)]
        if len(invalid_years) > 0:
            print(f"エラー: year が 1936〜2025 の範囲外です")
            print(f"  無効な行数: {len(invalid_years)}")
            if len(invalid_years) <= 10:
                print(f"  無効な行:")
                for idx, row in invalid_years.iterrows():
                    print(f"    行{idx+2}: year={row['year']}")
            return 1
        
        # すべての年（1936〜2025）が含まれているか確認
        unique_years = set(df['year_int'].dropna().astype(int))
        expected_years = set(range(1936, 2026))
        missing_years = expected_years - unique_years
        
        if missing_years:
            print(f"エラー: year が 1936〜2025 をすべて含んでいません")
            print(f"  欠けている年: {sorted(missing_years)}")
            print(f"  含まれている年: {sorted(unique_years)}")
            return 1
        
        min_year = int(df['year_int'].min())
        max_year = int(df['year_int'].max())
        
        # 検証5: league は {"PRE","CL","PL"} のいずれかのみ
        valid_leagues = {"PRE", "CL", "PL"}
        invalid_leagues = set(df['league'].unique()) - valid_leagues
        if invalid_leagues:
            print(f"エラー: league に無効な値があります: {invalid_leagues}")
            print(f"  有効な値: {valid_leagues}")
            invalid_rows = df[df['league'].isin(invalid_leagues)]
            print(f"  無効な行数: {len(invalid_rows)}")
            if len(invalid_rows) <= 10:
                print(f"  無効な行:")
                for idx, row in invalid_rows.iterrows():
                    print(f"    行{idx+2}: league={row['league']}")
            return 1
        
        # 検証6: qual_type は {"PA","AB"} のいずれかのみ
        valid_qual_types = {"PA", "AB"}
        invalid_qual_types = set(df['qual_type'].unique()) - valid_qual_types
        if invalid_qual_types:
            print(f"エラー: qual_type に無効な値があります: {invalid_qual_types}")
            print(f"  有効な値: {valid_qual_types}")
            invalid_rows = df[df['qual_type'].isin(invalid_qual_types)]
            print(f"  無効な行数: {len(invalid_rows)}")
            if len(invalid_rows) <= 10:
                print(f"  無効な行:")
                for idx, row in invalid_rows.iterrows():
                    print(f"    行{idx+2}: qual_type={row['qual_type']}")
            return 1
        
        # 検証7: 行数が900未満ならWARNINGをprint（ただしexitは0のまま）
        row_count = len(df)
        if row_count < 900:
            print(f"警告: 行数が900未満です: {row_count}行")
        
        # すべての検証を通過
        print(f"OK: qualifying_pa_table validation passed")
        print(f"  行数: {row_count}")
        if min_year is not None and max_year is not None:
            print(f"  年度範囲: {min_year}〜{max_year}")
        print(f"  リーグ: {sorted(df['league'].unique())}")
        print(f"  qual_type: {sorted(df['qual_type'].unique())}")
        return 0
        
    except Exception as e:
        print(f"エラー: 予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """メイン処理"""
    csv_path = project_root / '_data' / 'qualifying_pa_table.csv'
    exit_code = validate_qualifying_pa_table(csv_path)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()


