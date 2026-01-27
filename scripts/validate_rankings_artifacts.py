#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_rankings_artifacts.py

ランキング生成物（JSONファイル）の整合性を検証するスクリプト

- ディレクトリ構造の検証
- ファイル欠損チェック
- 異常値検知
- 期待件数チェック
- UIメタの存在チェック
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional


def parse_args() -> argparse.Namespace:
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(
        description="ランキング生成物の整合性を検証"
    )
    parser.add_argument(
        '--root',
        type=str,
        default='public/data/rankings',
        help='ランキングディレクトリのルート（デフォルト: public/data/rankings）'
    )
    parser.add_argument(
        '--min-year',
        type=int,
        default=1936,
        help='最小年度（デフォルト: 1936）'
    )
    parser.add_argument(
        '--max-year',
        type=int,
        default=2025,
        help='最大年度（デフォルト: 2025）'
    )
    parser.add_argument(
        '--leagues',
        type=str,
        default='PRE,CL,PL',
        help='対象リーグ（カンマ区切り、デフォルト: PRE,CL,PL）'
    )
    parser.add_argument(
        '--prewar-splits',
        type=str,
        default='PRE_spring,PRE_fall',
        help='戦前の分割（カンマ区切り、デフォルト: PRE_spring,PRE_fall）'
    )
    parser.add_argument(
        '--qualified-suffix',
        type=str,
        default='__qualified.json',
        help='qualifiedファイルのサフィックス（デフォルト: __qualified.json）'
    )
    parser.add_argument(
        '--expected-qualified',
        type=int,
        default=2640,
        help='期待されるqualifiedファイル数（デフォルト: 2640）'
    )
    parser.add_argument(
        '--report',
        type=str,
        default='output/reports/ranking_generation_from_calculated_report.md',
        help='レポートファイルパス（デフォルト: output/reports/ranking_generation_from_calculated_report.md）'
    )
    parser.add_argument(
        '--metric-map',
        type=str,
        default='public/data/metric_map.json',
        help='metric_map.jsonのパス（デフォルト: public/data/metric_map.json）'
    )
    parser.add_argument(
        '--index',
        type=str,
        default='public/data/rankings/index.json',
        help='index.jsonのパス（デフォルト: public/data/rankings/index.json）'
    )
    parser.add_argument(
        '--min-metrics',
        type=int,
        default=10,
        help='通常JSONファイルの最小数（デフォルト: 10）'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='厳格モード（WARNINGをERRORとして扱う）'
    )
    return parser.parse_args()


def get_expected_directories(
    min_year: int,
    max_year: int,
    leagues: List[str],
    prewar_splits: List[str],
    root: Path
) -> List[Tuple[int, str, Path]]:
    """
    期待されるディレクトリのリストを生成
    
    Returns:
        List of (year, league_key, path)
    """
    expected = []
    
    for year in range(min_year, max_year + 1):
        if year < 1950:
            # 戦前: PRE
            if 'PRE' in leagues:
                # 1945は戦時中で試合なし（除外）
                if year == 1945:
                    continue
                # 1936-1937は春秋分割も必須
                if year in [1936, 1937]:
                    for split in prewar_splits:
                        expected.append((year, split, root / str(year) / split))
                    # PRE 自体は任意（あればOK、存在チェックはしない）
                else:
                    # 1938-1944, 1946-1949は PRE のみ
                    expected.append((year, 'PRE', root / str(year) / 'PRE'))
        else:
            # 戦後: CL, PL
            for league in leagues:
                if league in ['CL', 'PL']:
                    expected.append((year, league, root / str(year) / league))
    
    return expected


def check_directory_structure(
    expected_dirs: List[Tuple[int, str, Path]],
    root: Path
) -> Tuple[List[Path], List[Tuple[int, str, Path]]]:
    """
    ディレクトリ構造をチェック
    
    Returns:
        (checked_dirs, missing_dirs)
    """
    checked_dirs = []
    missing_dirs = []
    
    for year, league_key, dir_path in expected_dirs:
        if dir_path.exists() and dir_path.is_dir():
            checked_dirs.append(dir_path)
        else:
            missing_dirs.append((year, league_key, dir_path))
    
    return checked_dirs, missing_dirs


def count_rows_in_json(data: Any) -> int:
    """
    JSONデータから行数相当を取得
    
    - 配列なら len
    - dictなら items数
    - それ以外は 0
    """
    if isinstance(data, list):
        return len(data)
    elif isinstance(data, dict):
        return len(data)
    else:
        return 0


def check_directory_files(
    dir_path: Path,
    qualified_suffix: str,
    min_metrics: int
) -> Dict[str, Any]:
    """
    ディレクトリ内のファイルをチェック
    
    Returns:
        {
            'normal_files': [...],
            'qualified_files': [...],
            'normal_count': int,
            'qualified_count': int,
            'empty_qualified': int,
            'parse_errors': List[str],
            'sample_rows': int  # サンプルファイルの行数合計
        }
    """
    result = {
        'normal_files': [],
        'qualified_files': [],
        'normal_count': 0,
        'qualified_count': 0,
        'empty_qualified': 0,
        'parse_errors': [],
        'sample_rows': 0
    }
    
    if not dir_path.exists():
        return result
    
    # 通常JSONとqualified JSONを分類
    for json_path in dir_path.glob('*.json'):
        if json_path.name.endswith(qualified_suffix):
            result['qualified_files'].append(json_path)
            result['qualified_count'] += 1
        else:
            result['normal_files'].append(json_path)
            result['normal_count'] += 1
    
    # qualifiedファイルの空チェックとパースチェック
    for qualified_path in result['qualified_files']:
        try:
            with open(qualified_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content == "" or content == "[]" or content == "{}":
                    result['empty_qualified'] += 1
                else:
                    # パースチェック
                    try:
                        json.loads(content)
                    except json.JSONDecodeError as e:
                        result['parse_errors'].append(f"{qualified_path.name}: {str(e)}")
        except Exception as e:
            result['parse_errors'].append(f"{qualified_path.name}: {str(e)}")
    
    # 通常JSONのパースチェックとサンプル行数取得
    sample_count = 0
    for normal_path in result['normal_files'][:3]:  # 最大3つ
        try:
            with open(normal_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                rows = count_rows_in_json(data)
                if rows == 0:
                    result['parse_errors'].append(f"{normal_path.name}: 行数が0")
                result['sample_rows'] += rows
                sample_count += 1
        except json.JSONDecodeError as e:
            result['parse_errors'].append(f"{normal_path.name}: {str(e)}")
        except Exception as e:
            result['parse_errors'].append(f"{normal_path.name}: {str(e)}")
    
    # qualifiedファイルのサンプル行数取得
    for qualified_path in result['qualified_files'][:3]:  # 最大3つ
        try:
            with open(qualified_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                rows = count_rows_in_json(data)
                result['sample_rows'] += rows
        except Exception:
            pass  # パースエラーは既に記録済み
    
    return result


def check_anomalies(
    checked_dirs: List[Path],
    root: Path,
    strict: bool
) -> Tuple[List[str], List[str]]:
    """
    異常値検知（急減検知）
    
    Returns:
        (warnings, errors)
    """
    warnings = []
    errors = []
    
    # リーグごとに前年のファイル数を記録
    prev_counts: Dict[str, Dict[int, int]] = {}  # {league: {year: count}}
    
    for dir_path in sorted(checked_dirs):
        # ディレクトリ構造から year と league を抽出
        parts = dir_path.relative_to(root).parts
        if len(parts) >= 2:
            try:
                year = int(parts[0])
                league = parts[1]
                
                # 通常JSONファイル数を取得
                normal_count = len([f for f in dir_path.glob('*.json') 
                                   if not f.name.endswith('__qualified.json')])
                
                # 前年との比較
                if league in prev_counts and (year - 1) in prev_counts[league]:
                    prev_count = prev_counts[league][year - 1]
                    if prev_count > 0 and normal_count < prev_count * 0.5:
                        msg = f"{year}/{league}: 通常JSONファイル数が急減 ({normal_count} < {prev_count} * 0.5)"
                        if strict:
                            errors.append(msg)
                        else:
                            warnings.append(msg)
                
                # 記録
                if league not in prev_counts:
                    prev_counts[league] = {}
                prev_counts[league][year] = normal_count
                
            except ValueError:
                pass  # 年が数値でない場合はスキップ
    
    return warnings, errors


def check_expected_qualified(
    root: Path,
    qualified_suffix: str,
    expected_count: int,
    report_path: Optional[Path]
) -> Tuple[List[str], List[str]]:
    """
    期待件数チェック
    
    Returns:
        (warnings, errors)
    """
    warnings = []
    errors = []
    
    # 実測qualifiedファイル数をカウント
    actual_count = 0
    empty_count = 0
    
    for qualified_path in root.rglob(f"*{qualified_suffix}"):
        actual_count += 1
        try:
            with open(qualified_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content == "" or content == "[]" or content == "{}":
                    empty_count += 1
        except Exception:
            pass
    
    # 期待件数チェック
    if actual_count < expected_count:
        errors.append(f"qualifiedファイル数が期待値を下回る: {actual_count} < {expected_count}")
    
    # 空ファイルチェック
    if empty_count > 0:
        errors.append(f"空のqualifiedファイルが存在: {empty_count}件")
    
    # レポートとの整合性チェック
    if report_path and report_path.exists():
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
                
            # COMPLETION_CHECK 行を探す
            for line in report_content.split('\n'):
                if line.startswith('COMPLETION_CHECK'):
                    # COMPLETION_CHECK qualified_files=2640 zero_files=0 の形式
                    if 'qualified_files=' in line and 'zero_files=' in line:
                        try:
                            # qualified_files=2640 を抽出
                            qual_part = line.split('qualified_files=')[1].split()[0]
                            report_qualified = int(qual_part)
                            
                            # zero_files=0 を抽出
                            zero_part = line.split('zero_files=')[1].split()[0]
                            report_zero = int(zero_part)
                            
                            # zero_files > 0 はERROR
                            if report_zero > 0:
                                errors.append(f"レポートに空qualifiedファイルが記録: {report_zero}件")
                            
                            # 期待値を下回る場合はERROR
                            if report_qualified < expected_count:
                                errors.append(f"レポートのqualifiedファイル数が期待値を下回る: {report_qualified} < {expected_count}")
                            
                            # 実測とレポートのズレチェック（10%以上）
                            if actual_count > 0:
                                diff_ratio = abs(actual_count - report_qualified) / actual_count
                                if diff_ratio > 0.1:
                                    msg = f"実測とレポートのqualifiedファイル数が大きくズレ: 実測={actual_count}, レポート={report_qualified}"
                                    if strict:
                                        errors.append(msg)
                                    else:
                                        warnings.append(msg)
                        except (ValueError, IndexError):
                            pass
                    elif 'failed:' in line:
                        errors.append(f"レポートのCOMPLETION_CHECKが失敗: {line}")
                    break
        except Exception as e:
            warnings.append(f"レポート読み込みエラー: {str(e)}")
    
    return warnings, errors


def check_ui_metadata(
    metric_map_path: Path,
    index_path: Path
) -> Tuple[List[str], List[str]]:
    """
    UIメタの存在チェック
    
    Returns:
        (warnings, errors)
    """
    warnings = []
    errors = []
    
    # metric_map.json のチェック
    if not metric_map_path.exists():
        warnings.append(f"metric_map.jsonが存在しません: {metric_map_path} (オプショナル)")
    else:
        try:
            with open(metric_map_path, 'r', encoding='utf-8') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"metric_map.jsonのパースエラー: {str(e)}")
        except Exception as e:
            errors.append(f"metric_map.jsonの読み込みエラー: {str(e)}")
    
    # index.json のチェック
    if not index_path.exists():
        warnings.append(f"index.jsonが存在しません: {index_path} (オプショナル)")
    else:
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"index.jsonのパースエラー: {str(e)}")
        except Exception as e:
            errors.append(f"index.jsonの読み込みエラー: {str(e)}")
    
    return warnings, errors


def main() -> int:
    """メイン処理"""
    args = parse_args()
    
    # パスを解決
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    root = project_root / args.root
    report_path = project_root / args.report if args.report else None
    metric_map_path = project_root / args.metric_map
    index_path = project_root / args.index
    
    # 引数をパース
    leagues = [l.strip() for l in args.leagues.split(',')]
    prewar_splits = [s.strip() for s in args.prewar_splits.split(',')]
    
    # 統計カウンタ
    checked_dirs = []
    missing_dirs = []
    json_files_total = 0
    normal_files_total = 0
    qualified_files_total = 0
    empty_qualified_files = 0
    parse_errors = []
    warnings = []
    errors = []
    
    print(f"検証開始: root={root}, year={args.min_year}-{args.max_year}, leagues={leagues}")
    print("")
    
    # B) ディレクトリ期待値チェック
    print("## ディレクトリ構造チェック")
    expected_dirs = get_expected_directories(
        args.min_year, args.max_year, leagues, prewar_splits, root
    )
    checked_dirs, missing_dirs = check_directory_structure(expected_dirs, root)
    
    print(f"  期待ディレクトリ数: {len(expected_dirs)}")
    print(f"  存在: {len(checked_dirs)}")
    print(f"  欠損: {len(missing_dirs)}")
    
    if missing_dirs:
        for year, league_key, dir_path in missing_dirs:
            errors.append(f"欠損ディレクトリ: {year}/{league_key} ({dir_path})")
            print(f"  [ERROR] 欠損: {year}/{league_key}")
    
    print("")
    
    # C) ファイル欠損チェック
    print("## ファイルチェック")
    for dir_path in checked_dirs:
        dir_result = check_directory_files(
            dir_path, args.qualified_suffix, args.min_metrics
        )
        
        json_files_total += dir_result['normal_count'] + dir_result['qualified_count']
        normal_files_total += dir_result['normal_count']
        qualified_files_total += dir_result['qualified_count']
        empty_qualified_files += dir_result['empty_qualified']
        parse_errors.extend(dir_result['parse_errors'])
        
        # 通常JSONが少なすぎる場合はERROR
        if dir_result['normal_count'] < args.min_metrics:
            errors.append(f"{dir_path}: 通常JSONファイル数が少なすぎる ({dir_result['normal_count']} < {args.min_metrics})")
        
        # 空のqualifiedファイルはERROR
        if dir_result['empty_qualified'] > 0:
            errors.append(f"{dir_path}: 空のqualifiedファイルが {dir_result['empty_qualified']}件")
        
        # パースエラーはERROR
        if dir_result['parse_errors']:
            for err in dir_result['parse_errors']:
                errors.append(f"{dir_path}/{err}")
    
    print(f"  通常JSONファイル総数: {normal_files_total}")
    print(f"  qualifiedファイル総数: {qualified_files_total}")
    print(f"  空qualifiedファイル: {empty_qualified_files}")
    print(f"  パースエラー: {len(parse_errors)}件")
    print("")
    
    # D) 異常値検知
    print("## 異常値検知")
    anomaly_warnings, anomaly_errors = check_anomalies(checked_dirs, root, args.strict)
    warnings.extend(anomaly_warnings)
    errors.extend(anomaly_errors)
    
    print(f"  警告: {len(anomaly_warnings)}件")
    print(f"  エラー: {len(anomaly_errors)}件")
    print("")
    
    # E) 期待件数チェック
    print("## 期待件数チェック")
    expected_warnings, expected_errors = check_expected_qualified(
        root, args.qualified_suffix, args.expected_qualified, report_path
    )
    warnings.extend(expected_warnings)
    errors.extend(expected_errors)
    
    print(f"  警告: {len(expected_warnings)}件")
    print(f"  エラー: {len(expected_errors)}件")
    print("")
    
    # F) UIメタの存在チェック
    print("## UIメタチェック")
    ui_warnings, ui_errors = check_ui_metadata(metric_map_path, index_path)
    warnings.extend(ui_warnings)
    errors.extend(ui_errors)
    
    print(f"  警告: {len(ui_warnings)}件")
    print(f"  エラー: {len(ui_errors)}件")
    print("")
    
    # G) 出力サマリ
    print("=" * 60)
    print("検証サマリ")
    print("=" * 60)
    print(f"checked_dirs: {len(checked_dirs)}")
    print(f"missing_dirs: {len(missing_dirs)}")
    print(f"json_files_total: {json_files_total}")
    print(f"normal_files_total: {normal_files_total}")
    print(f"qualified_files_total: {qualified_files_total}")
    print(f"empty_qualified_files: {empty_qualified_files}")
    print(f"parse_errors: {len(parse_errors)}")
    print(f"warnings_count: {len(warnings)}")
    print(f"errors_count: {len(errors)}")
    print("")
    
    # 警告とエラーの詳細表示
    if warnings:
        print("警告:")
        for w in warnings[:20]:  # 最大20件
            print(f"  [WARNING] {w}")
        if len(warnings) > 20:
            print(f"  ... 他 {len(warnings) - 20}件")
        print("")
    
    if errors:
        print("エラー:")
        for e in errors[:20]:  # 最大20件
            print(f"  [ERROR] {e}")
        if len(errors) > 20:
            print(f"  ... 他 {len(errors) - 20}件")
        print("")
    
    # 終了コード
    if len(errors) > 0:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())


