#!/usr/bin/env python3
"""
rebuild_1936_1937_with_season.py

1936年・1937年のデータを season列を保持した形で再生成するスクリプト
dedupで春秋が潰れてしまった場合に使用する
"""

import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict
import re


def load_csv_with_encoding(csv_path: Path) -> List[Dict[str, Any]]:
    """CSVファイルを読み込む（文字コード自動判定）"""
    encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
    for encoding in encodings:
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                return list(reader)
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    raise ValueError(f"Failed to read {csv_path} with any encoding")


def save_csv(data: List[Dict[str, Any]], output_path: Path, fieldnames: Optional[List[str]] = None):
    """CSVファイルを保存"""
    if not data:
        print(f"⚠️  警告: {output_path.name} に書き込むデータがありません")
        return
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if fieldnames is None:
        fieldnames = list(data[0].keys())
    
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✅ 保存: {output_path} ({len(data)}行)")


def determine_season_from_url(url: str) -> Optional[str]:
    """URLから春秋を判定"""
    url_lower = url.lower()
    
    spring_keywords = ['spring', '春', '前半', '1st', '1936春', '1937春', 'spring1936', 'spring1937']
    fall_keywords = ['fall', 'autumn', '秋', '後半', '2nd', '1936秋', '1937秋', 'fall1936', 'fall1937']
    
    if any(keyword in url_lower for keyword in spring_keywords):
        return 'spring'
    elif any(keyword in url_lower for keyword in fall_keywords):
        return 'fall'
    
    return None


def determine_season_from_source_info(row: Dict[str, Any]) -> Optional[str]:
    """source情報から春秋を判定"""
    # URL列を探す
    url_columns = [col for col in row.keys() if 'url' in col.lower() or 'source' in col.lower() or 'page' in col.lower()]
    
    for col in url_columns:
        url = str(row.get(col, '')).strip()
        if url:
            season = determine_season_from_url(url)
            if season:
                return season
    
    return None


def add_season_column(data: List[Dict[str, Any]], year: int) -> List[Dict[str, Any]]:
    """season列を追加（source情報から判定）"""
    result = []
    
    for row in data:
        row_copy = row.copy()  # 行をコピー
        season = determine_season_from_source_info(row_copy)
        
        if not season:
            # 判定できない場合は警告を出すが、行は保持
            print(f"⚠️  警告: seasonが判定できない行があります (player_id: {row_copy.get('player_id', 'N/A')})")
            season = 'unknown'
        
        row_copy['season'] = season
        result.append(row_copy)
    
    return result


def rebuild_with_season_from_master(
    master_data: List[Dict[str, Any]],
    year: int,
    output_path: Path
) -> List[Dict[str, Any]]:
    """masterデータからseason列付きのデータを生成"""
    # 対象年度のデータをフィルタ
    filtered_data = []
    year_column = None
    
    # year列を探す
    for col in master_data[0].keys():
        if 'year' in col.lower():
            year_column = col
            break
    
    if not year_column:
        raise ValueError("year列が見つかりません")
    
    for row in master_data:
        try:
            year_val = str(row.get(year_column, '')).strip()
            if year_val == str(year) or year_val.startswith(str(year)):
                filtered_data.append(row)
        except:
            pass
    
    print(f"📊 {year}年のデータ: {len(filtered_data)}行")
    
    # season列を追加
    data_with_season = add_season_column(filtered_data, year)
    
    # 保存
    fieldnames = list(master_data[0].keys())
    if 'season' not in fieldnames:
        fieldnames.append('season')
    
    save_csv(data_with_season, output_path, fieldnames=fieldnames)
    
    return data_with_season


def rebuild_with_season_from_yearly(
    yearly_data: List[Dict[str, Any]],
    year: int,
    output_path: Path
) -> List[Dict[str, Any]]:
    """yearlyデータからseason列付きのデータを生成"""
    # 対象年度のデータをフィルタ
    filtered_data = []
    year_column = None
    
    for col in yearly_data[0].keys():
        if 'year' in col.lower():
            year_column = col
            break
    
    if not year_column:
        raise ValueError("year列が見つかりません")
    
    for row in yearly_data:
        try:
            year_val = str(row.get(year_column, '')).strip()
            if year_val == str(year) or year_val.startswith(str(year)):
                filtered_data.append(row)
        except:
            pass
    
    print(f"📊 {year}年のデータ: {len(filtered_data)}行")
    
    # season列が既にあればそのまま、なければ追加
    if 'season' in filtered_data[0]:
        print("ℹ️  season列が既に存在します")
        data_with_season = filtered_data
    else:
        data_with_season = add_season_column(filtered_data, year)
    
    # 保存
    fieldnames = list(yearly_data[0].keys())
    if 'season' not in fieldnames:
        fieldnames.append('season')
    
    save_csv(data_with_season, output_path, fieldnames=fieldnames)
    
    return data_with_season


def main():
    # パス設定
    base_data_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting\data\batting")
    
    # 入力パス（優先順位: master > yearly_from_master > yearly_from_master_dedup）
    master_dir = base_data_path / 'master'
    yearly_dir = base_data_path / 'yearly_from_master'
    dedup_dir = base_data_path / 'yearly_from_master_dedup'
    
    # 出力パス
    output_dir = base_data_path / 'yearly_prewar_split'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("1936/1937年 season列付きデータ再生成スクリプト")
    print("=" * 80)
    
    target_years = [1936, 1937]
    
    for year in target_years:
        print(f"\n{'='*80}")
        print(f"処理中: {year}年")
        print(f"{'='*80}")
        
        source_data = None
        source_path = None
        
        # masterデータを優先的に使用
        if master_dir.exists():
            master_files = list(master_dir.glob(f"*{year}*.csv"))
            if master_files:
                source_path = master_files[0]
                print(f"📄 masterデータを使用: {source_path}")
                source_data = load_csv_with_encoding(source_path)
        elif yearly_dir.exists():
            yearly_files = list(yearly_dir.glob(f"batting_{year}_PRE_from_master.csv"))
            if yearly_files:
                source_path = yearly_files[0]
                print(f"📄 yearly_from_masterデータを使用: {source_path}")
                source_data = load_csv_with_encoding(source_path)
        elif dedup_dir.exists():
            dedup_files = list(dedup_dir.glob(f"batting_{year}_PRE_from_master.csv"))
            if dedup_files:
                source_path = dedup_files[0]
                print(f"📄 yearly_from_master_dedupデータを使用: {source_path}")
                source_data = load_csv_with_encoding(source_path)
        
        if not source_data:
            print(f"⚠️  {year}年のソースデータが見つかりません")
            continue
        
        try:
            # season列付きデータを生成
            output_path = output_dir / f"batting_{year}_PRE_with_season.csv"
            
            if 'master' in str(source_path):
                rebuild_with_season_from_master(source_data, year, output_path)
            else:
                rebuild_with_season_from_yearly(source_data, year, output_path)
            
            print(f"✅ {year}年の処理が完了しました")
            
        except Exception as e:
            print(f"❌ エラー: {year}年の処理中にエラーが発生しました")
            import traceback
            traceback.print_exc()
            continue
    
    print("\n" + "=" * 80)
    print("再生成完了")
    print("=" * 80)
    print(f"\n📁 出力先: {output_dir}")
    print("\n⚠️  注意: 生成されたデータを確認し、season列が正しく設定されているか確認してください。")
    print("   その後、split_1936_1937.py を使用して春秋に分割してください。")
    
    return 0


if __name__ == '__main__':
    exit(main())

