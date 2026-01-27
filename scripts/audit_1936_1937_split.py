#!/usr/bin/env python3
"""
audit_1936_1937_split.py

1936年・1937年のデータが春秋を含んでいるかを監査し、
分割可能性を判定するスクリプト
"""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
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


def find_files_in_directory(base_dir: Path, pattern: str) -> List[Path]:
    """指定ディレクトリ配下でファイルを検索"""
    found_files = []
    if not base_dir.exists():
        return found_files
    
    for file_path in base_dir.rglob(pattern):
        if file_path.is_file():
            found_files.append(file_path)
    
    return sorted(found_files)


def check_columns_for_season_info(columns: List[str]) -> Dict[str, Any]:
    """列名から春秋を示す可能性のある列を探す"""
    season_keywords = ['season', 'split', 'phase', '半期', '春秋', 'spring', 'fall', 'autumn']
    url_keywords = ['source_url', 'source_page', 'page_title', 'url', 'source']
    year_keywords = ['year', '年度', 'season_year']
    
    result = {
        'season_columns': [],
        'url_columns': [],
        'year_columns': [],
        'all_columns': columns
    }
    
    for col in columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in season_keywords):
            result['season_columns'].append(col)
        if any(kw in col_lower for kw in url_keywords):
            result['url_columns'].append(col)
        if any(kw in col_lower for kw in year_keywords):
            result['year_columns'].append(col)
    
    return result


def analyze_year_values(data: List[Dict[str, Any]], year_column: str) -> Dict[str, Any]:
    """year列の値を分析（春秋情報が含まれていないか）"""
    values = set()
    unique_values = []
    value_counts = defaultdict(int)
    
    for row in data:
        if year_column in row:
            val = str(row[year_column]).strip()
            values.add(val)
            value_counts[val] += 1
    
    unique_values = sorted(values)
    
    # 春秋を示す可能性のある値があるかチェック
    season_patterns = ['春', '秋', 'spring', 'fall', 'autumn', '/', 'split']
    has_season_info = any(
        any(pattern in str(val).lower() for pattern in season_patterns)
        for val in unique_values
    )
    
    return {
        'unique_values': unique_values,
        'value_counts': dict(value_counts),
        'has_season_info': has_season_info,
        'total_unique_count': len(unique_values)
    }


def check_duplicates(data: List[Dict[str, Any]], key_columns: List[str]) -> Dict[str, Any]:
    """指定したキー列の組み合わせで重複をチェック"""
    key_to_rows = defaultdict(list)
    
    for idx, row in enumerate(data):
        key_parts = []
        for col in key_columns:
            if col in row:
                key_parts.append(str(row[col]).strip())
            else:
                key_parts.append('')
        key = tuple(key_parts)
        key_to_rows[key].append((idx, row))
    
    duplicates = {k: rows for k, rows in key_to_rows.items() if len(rows) > 1}
    
    return {
        'duplicate_count': len(duplicates),
        'duplicate_keys': list(duplicates.keys())[:20],  # 最初の20件
        'total_keys': len(key_to_rows),
        'has_duplicates': len(duplicates) > 0
    }


def analyze_season_column(data: List[Dict[str, Any]], season_column: str) -> Dict[str, Any]:
    """season列の値を分析"""
    values = set()
    value_counts = defaultdict(int)
    
    for row in data:
        if season_column in row:
            val = str(row[season_column]).strip().lower()
            values.add(val)
            value_counts[val] += 1
    
    return {
        'unique_values': sorted(values),
        'value_counts': dict(value_counts),
        'has_season_data': len(values) > 0
    }


def analyze_url_column(data: List[Dict[str, Any]], url_column: str, years: List[int]) -> Dict[str, Any]:
    """URL列を分析して春秋を示すパターンがあるかチェック"""
    url_patterns = defaultdict(set)
    spring_keywords = ['spring', '春', '前半', '1st']
    fall_keywords = ['fall', 'autumn', '秋', '後半', '2nd']
    
    for row in data:
        if url_column in row:
            url = str(row[url_column]).strip().lower()
            for keyword in spring_keywords:
                if keyword in url:
                    url_patterns['spring'].add(url[:100])  # 最初の100文字
            for keyword in fall_keywords:
                if keyword in url:
                    url_patterns['fall'].add(url[:100])
    
    return {
        'has_spring_urls': len(url_patterns['spring']) > 0,
        'has_fall_urls': len(url_patterns['fall']) > 0,
        'spring_url_samples': list(url_patterns['spring'])[:5],
        'fall_url_samples': list(url_patterns['fall'])[:5]
    }


def audit_file(csv_path: Path, target_years: List[int]) -> Dict[str, Any]:
    """1つのCSVファイルを監査"""
    print(f"\n[監査中] {csv_path.name}")
    
    try:
        data = load_csv_with_encoding(csv_path)
    except Exception as e:
        return {
            'file_path': str(csv_path),
            'exists': csv_path.exists(),
            'error': str(e),
            'readable': False
        }
    
    if not data:
        return {
            'file_path': str(csv_path),
            'exists': True,
            'readable': True,
            'row_count': 0,
            'empty': True
        }
    
    # 列情報を取得
    columns = list(data[0].keys())
    column_info = check_columns_for_season_info(columns)
    
    # year列を探す
    year_column = None
    if column_info['year_columns']:
        year_column = column_info['year_columns'][0]
    elif 'year' in columns:
        year_column = 'year'
    
    # 対象年度のデータをフィルタ
    filtered_data = []
    if year_column:
        for row in data:
            try:
                year_val = str(row.get(year_column, '')).strip()
                # 数値か、対象年度を含むか
                if year_val.isdigit() and int(year_val) in target_years:
                    filtered_data.append(row)
                elif any(str(y) in year_val for y in target_years):
                    filtered_data.append(row)
            except:
                pass
    
    if not filtered_data and year_column:
        # year列でフィルタできない場合は全データを使用
        filtered_data = data
    
    result = {
        'file_path': str(csv_path),
        'exists': True,
        'readable': True,
        'row_count': len(data),
        'filtered_row_count': len(filtered_data),
        'column_count': len(columns),
        'columns': columns,
        'column_info': column_info,
        'year_column': year_column
    }
    
    # year列の分析
    if year_column:
        year_analysis = analyze_year_values(filtered_data, year_column)
        result['year_analysis'] = year_analysis
    
    # player_id列を探す
    player_id_column = None
    for col in ['player_id', 'playerId', 'id', '選手ID']:
        if col in columns:
            player_id_column = col
            break
    
    # 重複チェック（player_id + year）
    if player_id_column and year_column:
        duplicate_check = check_duplicates(filtered_data, [player_id_column, year_column])
        result['duplicate_check'] = duplicate_check
        result['player_id_column'] = player_id_column
    elif player_id_column:
        duplicate_check = check_duplicates(filtered_data, [player_id_column])
        result['duplicate_check'] = duplicate_check
        result['player_id_column'] = player_id_column
    
    # season列の分析
    if column_info['season_columns']:
        season_col = column_info['season_columns'][0]
        season_analysis = analyze_season_column(filtered_data, season_col)
        result['season_analysis'] = season_analysis
        result['season_column'] = season_col
    
    # URL列の分析
    if column_info['url_columns']:
        url_col = column_info['url_columns'][0]
        url_analysis = analyze_url_column(filtered_data, url_col, target_years)
        result['url_analysis'] = url_analysis
        result['url_column'] = url_col
    
    return result


def find_related_files(base_path: Path) -> Dict[str, List[Path]]:
    """関連ファイルを探索"""
    found_files = {
        'dedup_files': [],
        'master_files': [],
        'yearly_files': [],
        'other_1936_1937': []
    }
    
    # ベースディレクトリの親を探索
    if base_path.exists():
        parent_dir = base_path.parent
        grandparent_dir = parent_dir.parent if parent_dir else None
        
        # yearly_from_master_dedup 配下
        dedup_dir = base_path.parent
        if dedup_dir.exists():
            for pattern in ['*1936*.csv', '*1937*.csv']:
                found_files['dedup_files'].extend(find_files_in_directory(dedup_dir, pattern))
        
        # yearly_from_master 配下（dedup前）
        if grandparent_dir:
            yearly_dir = grandparent_dir / 'yearly_from_master'
            if yearly_dir.exists():
                for pattern in ['*1936*.csv', '*1937*.csv']:
                    found_files['yearly_files'].extend(find_files_in_directory(yearly_dir, pattern))
            
            # master 配下
            master_dir = grandparent_dir.parent / 'master' if grandparent_dir.parent else None
            if master_dir and master_dir.exists():
                for pattern in ['*1936*.csv', '*1937*.csv', '*.csv']:
                    found_files['master_files'].extend(find_files_in_directory(master_dir, pattern))
            
            # その他の1936/1937関連
            data_dir = grandparent_dir.parent.parent if grandparent_dir.parent else None
            if data_dir and data_dir.exists():
                for pattern in ['*1936*.csv', '*1937*.csv']:
                    found_files['other_1936_1937'].extend(find_files_in_directory(data_dir, pattern))
    
    # 重複を除去
    for key in found_files:
        found_files[key] = list(set(found_files[key]))
    
    return found_files


def main():
    # パス設定
    base_dedup_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting\data\batting\yearly_from_master_dedup")
    target_files = [
        base_dedup_path / "batting_1936_PRE_from_master.csv",
        base_dedup_path / "batting_1937_PRE_from_master.csv"
    ]
    
    target_years = [1936, 1937]
    
    # 出力ディレクトリ
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    output_dir = project_root / 'output' / 'reports'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("1936/1937年 春秋分割 監査スクリプト")
    print("=" * 80)
    
    # STEP 1-A: ファイル存在チェックと同ディレクトリ探索
    print("\n【STEP 1-A】ファイル存在チェックと関連ファイル探索")
    print("-" * 80)
    
    related_files = find_related_files(target_files[0])
    
    print(f"\n[関連ファイル検索結果]")
    print(f"  - dedupファイル: {len(related_files['dedup_files'])}件")
    for f in related_files['dedup_files']:
        print(f"    {f}")
    print(f"  - yearly_from_masterファイル: {len(related_files['yearly_files'])}件")
    for f in related_files['yearly_files']:
        print(f"    {f}")
    print(f"  - masterファイル: {len(related_files['master_files'])}件")
    for f in related_files['master_files'][:10]:  # 最初の10件のみ表示
        print(f"    {f}")
    if len(related_files['master_files']) > 10:
        print(f"    ... 他 {len(related_files['master_files']) - 10}件")
    
    # STEP 1-B, 1-C: CSV監査
    print("\n【STEP 1-B, 1-C】CSVファイルの監査")
    print("-" * 80)
    
    audit_results = []
    
    for csv_path in target_files:
        if csv_path.exists():
            result = audit_file(csv_path, target_years)
            audit_results.append(result)
        else:
            print(f"\n[警告] ファイルが見つかりません: {csv_path}")
            audit_results.append({
                'file_path': str(csv_path),
                'exists': False
            })
    
    # dedup前のファイルも監査
    for csv_path in related_files['yearly_files']:
        if csv_path.exists():
            result = audit_file(csv_path, target_years)
            audit_results.append(result)
    
    # レポート生成
    print("\n【レポート生成】")
    print("-" * 80)
    
    # Markdownレポート
    report_md_path = output_dir / 'audit_1936_1937_split.md'
    with open(report_md_path, 'w', encoding='utf-8') as f:
        f.write("# 1936/1937年 春秋分割 監査レポート\n\n")
        f.write(f"生成日時: {Path(__file__).stat().st_mtime}\n\n")
        
        f.write("## 1. 発見した関連ファイル\n\n")
        f.write("### dedupファイル\n")
        for file_path in related_files['dedup_files']:
            f.write(f"- {file_path}\n")
        f.write("\n### yearly_from_masterファイル（dedup前）\n")
        for file_path in related_files['yearly_files']:
            f.write(f"- {file_path}\n")
        f.write("\n### masterファイル\n")
        for file_path in related_files['master_files'][:20]:
            f.write(f"- {file_path}\n")
        if len(related_files['master_files']) > 20:
            f.write(f"- ... 他 {len(related_files['master_files']) - 20}件\n")
        
        f.write("\n## 2. 各ファイルの監査結果\n\n")
        
        for result in audit_results:
            f.write(f"### {Path(result['file_path']).name}\n\n")
            f.write(f"- **パス**: `{result['file_path']}`\n")
            f.write(f"- **存在**: {'✅' if result.get('exists') else '❌'}\n")
            
            if not result.get('exists'):
                f.write("\n")
                continue
            
            if not result.get('readable', True):
                f.write(f"- **読み込みエラー**: {result.get('error', 'Unknown error')}\n\n")
                continue
            
            f.write(f"- **行数**: {result.get('row_count', 0):,}行\n")
            if result.get('filtered_row_count'):
                f.write(f"- **対象年度フィルタ後行数**: {result.get('filtered_row_count', 0):,}行\n")
            f.write(f"- **列数**: {result.get('column_count', 0)}列\n\n")
            
            # 列情報
            column_info = result.get('column_info', {})
            if column_info.get('season_columns'):
                f.write(f"- **season列**: {', '.join(column_info['season_columns'])} ✅\n")
            else:
                f.write(f"- **season列**: なし ❌\n")
            
            if column_info.get('url_columns'):
                f.write(f"- **URL列**: {', '.join(column_info['url_columns'])} ✅\n")
            else:
                f.write(f"- **URL列**: なし ❌\n")
            
            # year列の分析
            year_analysis = result.get('year_analysis')
            if year_analysis:
                f.write(f"- **year列**: {result.get('year_column')}\n")
                f.write(f"  - ユニーク値数: {year_analysis['total_unique_count']}\n")
                if year_analysis['has_season_info']:
                    f.write(f"  - **春秋情報が含まれている可能性**: ✅\n")
                else:
                    f.write(f"  - **春秋情報が含まれている可能性**: ❌\n")
            
            # 重複チェック
            duplicate_check = result.get('duplicate_check')
            if duplicate_check:
                f.write(f"- **重複チェック (player_id + year)**:\n")
                f.write(f"  - 重複キー数: {duplicate_check['duplicate_count']}\n")
                f.write(f"  - 総キー数: {duplicate_check['total_keys']}\n")
                if duplicate_check['has_duplicates']:
                    f.write(f"  - **重複あり**: ✅ (春秋分割の可能性あり)\n")
                else:
                    f.write(f"  - **重複なし**: ❌ (dedup済みの可能性)\n")
            
            # season列の分析
            if result.get('season_analysis'):
                season_analysis = result['season_analysis']
                f.write(f"- **season列の値**: {', '.join(season_analysis['unique_values'][:10])}\n")
            
            # URL列の分析
            if result.get('url_analysis'):
                url_analysis = result['url_analysis']
                f.write(f"- **URL分析**:\n")
                f.write(f"  - 春を示すURL: {'✅' if url_analysis['has_spring_urls'] else '❌'}\n")
                f.write(f"  - 秋を示すURL: {'✅' if url_analysis['has_fall_urls'] else '❌'}\n")
            
            f.write("\n")
        
        # 結論
        f.write("## 3. 結論\n\n")
        
        # 結論を判定
        can_split = False
        split_reason = ""
        cannot_split_reason = ""
        
        # dedup前のファイルで重複があるかチェック
        for result in audit_results:
            if 'yearly_from_master' in result.get('file_path', '') or 'master' in result.get('file_path', ''):
                if result.get('duplicate_check', {}).get('has_duplicates'):
                    can_split = True
                    split_reason = f"dedup前のファイル ({Path(result['file_path']).name}) に player_id+year の重複が存在"
                    break
                elif result.get('season_analysis', {}).get('has_season_data'):
                    can_split = True
                    split_reason = f"season列が存在し、春秋データが識別可能 ({Path(result['file_path']).name})"
                    break
                elif result.get('url_analysis', {}).get('has_spring_urls') and result.get('url_analysis', {}).get('has_fall_urls'):
                    can_split = True
                    split_reason = f"URL列から春秋が識別可能 ({Path(result['file_path']).name})"
                    break
        
        if not can_split:
            cannot_split_reason = "dedup前のデータで春秋を識別できる情報（season列、URL列、重複行）が見つかりませんでした。"
        
        if can_split:
            f.write("### ✅ 分割可能\n\n")
            f.write(f"**理由**: {split_reason}\n\n")
            f.write("次のステップ: `scripts/split_1936_1937.py` を実行して分割を実行してください。\n")
        else:
            f.write("### ❌ 分割不可\n\n")
            f.write(f"**理由**: {cannot_split_reason}\n\n")
            f.write("次のステップ: `scripts/rebuild_1936_1937_with_season.py` を作成して、season列を保持したデータを再生成する必要があります。\n")
    
    print(f"[完了] Markdownレポートを生成: {report_md_path}")
    
    # 列名一覧CSV
    columns_csv_path = output_dir / 'audit_1936_1937_columns.csv'
    with open(columns_csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ファイルパス', '列名'])
        for result in audit_results:
            if result.get('columns'):
                for col in result['columns']:
                    writer.writerow([Path(result['file_path']).name, col])
    
    print(f"[完了] 列名一覧CSVを生成: {columns_csv_path}")
    
    # 重複一覧CSV（重複がある場合のみ）
    duplicates_csv_path = output_dir / 'audit_1936_1937_duplicates.csv'
    has_duplicates = False
    with open(duplicates_csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        for result in audit_results:
            if result.get('duplicate_check', {}).get('has_duplicates'):
                has_duplicates = True
                file_name = Path(result['file_path']).name
                player_col = result.get('player_id_column', 'player_id')
                year_col = result.get('year_column', 'year')
                
                # 実際の重複データを読み込んで出力
                try:
                    data = load_csv_with_encoding(Path(result['file_path']))
                    if year_col:
                        filtered_data = [row for row in data if str(row.get(year_col, '')).strip() in ['1936', '1937']]
                    else:
                        filtered_data = data
                    
                    key_to_rows = defaultdict(list)
                    for row in filtered_data:
                        key_parts = []
                        for col in [player_col, year_col]:
                            if col and col in row:
                                key_parts.append(str(row[col]).strip())
                        if len(key_parts) == 2:
                            key = tuple(key_parts)
                            key_to_rows[key].append(row)
                    
                    duplicates = {k: rows for k, rows in key_to_rows.items() if len(rows) > 1}
                    
                    if writer is None:
                        writer = csv.writer(f)
                        writer.writerow(['ファイル名', player_col, year_col, '重複件数'] + 
                                      [col for col in data[0].keys() if col not in [player_col, year_col]][:10])
                    
                    for key, rows in list(duplicates.items())[:100]:  # 最初の100件
                        writer.writerow([file_name, key[0], key[1], len(rows)] + 
                                       [rows[0].get(col, '') for col in data[0].keys() if col not in [player_col, year_col]][:10])
                except Exception as e:
                    writer.writerow([file_name, 'ERROR', str(e), '', ''])
    
    if has_duplicates:
        print(f"[完了] 重複一覧CSVを生成: {duplicates_csv_path}")
    else:
        duplicates_csv_path.unlink()  # ファイルを削除
        print(f"[情報] 重複がなかったため、重複一覧CSVは生成しませんでした")
    
    print("\n" + "=" * 80)
    print("監査完了")
    print("=" * 80)
    print(f"\n[確認] レポートを確認してください: {report_md_path}")


if __name__ == '__main__':
    main()

