#!/usr/bin/env python3
"""
split_1936_1937.py

1936年・1937年のデータを春秋に分割するスクリプト
audit結果に基づいて、season列やURL列などから春秋を識別して分割する
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


def determine_season_by_column(row: Dict[str, Any], season_column: str) -> Optional[str]:
    """season列から春秋を判定"""
    if season_column not in row:
        return None
    
    val = str(row[season_column]).strip().lower()
    if 'spring' in val or '春' in val or val == '1' or val == '1st':
        return 'spring'
    elif 'fall' in val or 'autumn' in val or '秋' in val or val == '2' or val == '2nd':
        return 'fall'
    
    return None


def determine_season_by_url(row: Dict[str, Any], url_column: str) -> Optional[str]:
    """URL列から春秋を判定"""
    if url_column not in row:
        return None
    
    url = str(row[url_column]).strip().lower()
    spring_keywords = ['spring', '春', '前半', '1st', '1936春', '1937春', 'spring1936', 'spring1937']
    fall_keywords = ['fall', 'autumn', '秋', '後半', '2nd', '1936秋', '1937秋', 'fall1936', 'fall1937']
    
    if any(keyword in url for keyword in spring_keywords):
        return 'spring'
    elif any(keyword in url for keyword in fall_keywords):
        return 'fall'
    
    return None


def determine_season_by_year_value(row: Dict[str, Any], year_column: str) -> Optional[str]:
    """year列の値から春秋を判定（1936春、1936秋などの形式）"""
    if year_column not in row:
        return None
    
    val = str(row[year_column]).strip()
    if '春' in val or 'spring' in val.lower():
        return 'spring'
    elif '秋' in val or 'fall' in val.lower() or 'autumn' in val.lower():
        return 'fall'
    
    return None


def split_data_by_season(
    data: List[Dict[str, Any]],
    year: int,
    season_column: Optional[str] = None,
    url_column: Optional[str] = None,
    year_column: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """データを春秋に分割"""
    spring_data = []
    fall_data = []
    unknown_data = []
    
    for row in data:
        season = None
        
        # 1. season列から判定
        if season_column:
            season = determine_season_by_column(row, season_column)
        
        # 2. URL列から判定
        if not season and url_column:
            season = determine_season_by_url(row, url_column)
        
        # 3. year列の値から判定
        if not season and year_column:
            season = determine_season_by_year_value(row, year_column)
        
        if season == 'spring':
            spring_data.append(row)
        elif season == 'fall':
            fall_data.append(row)
        else:
            unknown_data.append(row)
    
    if unknown_data:
        print(f"⚠️  警告: {year}年のデータで春秋が判定できない行が {len(unknown_data)}件あります")
    
    return {
        'spring': spring_data,
        'fall': fall_data,
        'unknown': unknown_data
    }


def split_from_dedup_file(
    source_path: Path,
    year: int,
    output_dir: Path,
    season_column: Optional[str] = None,
    url_column: Optional[str] = None
):
    """dedup済みファイルから分割（重複がない場合は分割不可）"""
    data = load_csv_with_encoding(source_path)
    
    # year列を探す
    year_column = None
    if 'year' in data[0]:
        year_column = 'year'
    else:
        for col in data[0].keys():
            if 'year' in col.lower():
                year_column = col
                break
    
    if not year_column:
        raise ValueError(f"year列が見つかりません: {source_path}")
    
    # 対象年度のデータをフィルタ
    filtered_data = []
    for row in data:
        try:
            year_val = str(row.get(year_column, '')).strip()
            if year_val == str(year) or year_val.startswith(str(year)):
                filtered_data.append(row)
        except:
            pass
    
    print(f"\n📊 {year}年のデータ: {len(filtered_data)}行")
    
    # 春秋に分割
    split_result = split_data_by_season(
        filtered_data,
        year,
        season_column=season_column,
        url_column=url_column,
        year_column=year_column
    )
    
    # ファイル名を決定
    league_suffix = 'PRE'  # 戦前はPRE
    
    # 保存
    if split_result['spring']:
        spring_path = output_dir / f"batting_{year}_spring_{league_suffix}.csv"
        save_csv(split_result['spring'], spring_path, fieldnames=list(data[0].keys()))
    
    if split_result['fall']:
        fall_path = output_dir / f"batting_{year}_fall_{league_suffix}.csv"
        save_csv(split_result['fall'], fall_path, fieldnames=list(data[0].keys()))
    
    if split_result['unknown']:
        unknown_path = output_dir / f"batting_{year}_unknown_{league_suffix}.csv"
        save_csv(split_result['unknown'], unknown_path, fieldnames=list(data[0].keys()))
        print(f"⚠️  注意: 春秋が判定できなかったデータは {unknown_path} に保存されました")
    
    return split_result


def split_from_pre_dedup_file(
    source_path: Path,
    year: int,
    output_dir: Path,
    player_id_column: str = 'player_id',
    year_column: str = 'year'
):
    """dedup前のファイルから分割（重複行を利用）"""
    data = load_csv_with_encoding(source_path)
    
    # 対象年度のデータをフィルタ
    filtered_data = []
    for row in data:
        try:
            year_val = str(row.get(year_column, '')).strip()
            if year_val == str(year) or year_val.startswith(str(year)):
                filtered_data.append(row)
        except:
            pass
    
    print(f"\n📊 {year}年のデータ: {len(filtered_data)}行")
    
    # player_id + year で重複を検出
    key_to_rows = defaultdict(list)
    for row in filtered_data:
        player_id = str(row.get(player_id_column, '')).strip()
        year_val = str(row.get(year_column, '')).strip()
        key = (player_id, year_val)
        key_to_rows[key].append(row)
    
    # 重複があるキーを抽出
    duplicates = {k: rows for k, rows in key_to_rows.items() if len(rows) > 1}
    
    if not duplicates:
        print(f"⚠️  警告: {year}年のデータに重複がありません。season列やURL列を使った分割を試してください。")
        return None
    
    print(f"✅ 重複キーが {len(duplicates)}件見つかりました（春秋分割の可能性）")
    
    # URL列やseason列を使って重複行を分類
    season_column = None
    url_column = None
    for col in filtered_data[0].keys():
        if 'season' in col.lower():
            season_column = col
        elif 'url' in col.lower() or 'source' in col.lower():
            url_column = col
    
    spring_data = []
    fall_data = []
    single_data = []  # 重複がない行
    
    # 重複がある行を処理
    for key, rows in duplicates.items():
        if len(rows) == 2:
            # 2行なら春秋の可能性が高い
            row1, row2 = rows
            season1 = None
            season2 = None
            
            if season_column:
                season1 = determine_season_by_column(row1, season_column)
                season2 = determine_season_by_column(row2, season_column)
            elif url_column:
                season1 = determine_season_by_url(row1, url_column)
                season2 = determine_season_by_url(row2, url_column)
            
            if season1 == 'spring' or season2 == 'fall':
                spring_data.append(row1 if season1 == 'spring' else row2)
                fall_data.append(row2 if season1 == 'spring' else row1)
            elif season1 == 'fall' or season2 == 'spring':
                fall_data.append(row1 if season1 == 'fall' else row2)
                spring_data.append(row2 if season1 == 'fall' else row1)
            else:
                # 判定できない場合は両方に含める（後で手動確認が必要）
                spring_data.append(row1)
                fall_data.append(row2)
        else:
            # 2行以外はそのまま処理
            for row in rows:
                single_data.append(row)
    
    # 重複がない行を処理
    for key, rows in key_to_rows.items():
        if len(rows) == 1:
            single_data.append(rows[0])
    
    # 保存
    league_suffix = 'PRE'
    
    if spring_data:
        spring_path = output_dir / f"batting_{year}_spring_{league_suffix}.csv"
        save_csv(spring_data, spring_path, fieldnames=list(filtered_data[0].keys()))
    
    if fall_data:
        fall_path = output_dir / f"batting_{year}_fall_{league_suffix}.csv"
        save_csv(fall_data, fall_path, fieldnames=list(filtered_data[0].keys()))
    
    if single_data:
        single_path = output_dir / f"batting_{year}_single_{league_suffix}.csv"
        save_csv(single_data, single_path, fieldnames=list(filtered_data[0].keys()))
        print(f"ℹ️  重複がない行は {single_path} に保存されました")
    
    return {
        'spring': spring_data,
        'fall': fall_data,
        'single': single_data
    }


def main():
    # パス設定
    base_dedup_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting\data\batting\yearly_from_master_dedup")
    source_files = {
        1936: base_dedup_path / "batting_1936_PRE_from_master.csv",
        1937: base_dedup_path / "batting_1937_PRE_from_master.csv"
    }
    
    # 出力ディレクトリ
    output_dir = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting\data\batting\yearly_prewar_split")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("1936/1937年 春秋分割スクリプト")
    print("=" * 80)
    
    # auditレポートを読んで、分割方法を決定
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    audit_report_path = project_root / 'output' / 'reports' / 'audit_1936_1937_split.md'
    
    if audit_report_path.exists():
        print(f"\n📄 auditレポートを確認: {audit_report_path}")
        # レポートから情報を読み取る（簡易版）
        print("   レポートの内容を確認して、分割方法を決定してください。")
    else:
        print(f"\n⚠️  auditレポートが見つかりません: {audit_report_path}")
        print("   まず audit_1936_1937_split.py を実行してください。")
        return 1
    
    # 各年度を分割
    for year in [1936, 1937]:
        source_path = source_files[year]
        
        if not source_path.exists():
            print(f"\n⚠️  ファイルが見つかりません: {source_path}")
            continue
        
        print(f"\n{'='*80}")
        print(f"処理中: {year}年")
        print(f"{'='*80}")
        
        try:
            # まず、dedup前のファイルを探す
            base_path = source_path.parent.parent
            pre_dedup_path = base_path / 'yearly_from_master' / f"batting_{year}_PRE_from_master.csv"
            
            if pre_dedup_path.exists():
                print(f"✅ dedup前のファイルを使用: {pre_dedup_path}")
                split_from_pre_dedup_file(pre_dedup_path, year, output_dir)
            else:
                print(f"ℹ️  dedup前のファイルが見つかりません。dedup済みファイルを使用します。")
                # season列やURL列の情報をauditレポートから読み取る必要がある
                # ここでは簡易的に実行（実際の使用時はaudit結果に基づいてパラメータを調整）
                split_from_dedup_file(source_path, year, output_dir)
        except Exception as e:
            print(f"❌ エラー: {year}年の処理中にエラーが発生しました")
            import traceback
            traceback.print_exc()
            continue
    
    print("\n" + "=" * 80)
    print("分割完了")
    print("=" * 80)
    print(f"\n📁 出力先: {output_dir}")
    
    return 0


if __name__ == '__main__':
    exit(main())





















