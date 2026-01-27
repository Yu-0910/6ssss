#!/usr/bin/env python3
"""
validate_outputs.py

生成物のバリデーションスクリプト

1) _data/master_csv_calculated/ に入力CSV分の計算済みCSVが存在（除外分を除く）
2) public/data/rankings/{YEAR}/{LEAGUE_KEY}/ に指標分のJSONが存在（除外分を除く）
3) 各JSONが0件でない（0件なら原因をログ）
"""

import argparse
import json
import re
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set

# 共通パーサーをインポート
try:
    from lib.filename_parser import parse_batting_filename, build_calculated_filename, build_rankings_output_path
except ImportError:
    # フォールバック: scripts/lib/filename_parser.py
    sys.path.insert(0, os.path.dirname(__file__))
    from lib.filename_parser import parse_batting_filename, build_calculated_filename, build_rankings_output_path

# build_rankings_2025_PL_full.py から sanitize_filename をインポート
try:
    sys.path.insert(0, os.path.dirname(__file__))
    from build_rankings_2025_PL_full import sanitize_filename, load_metric_map
except ImportError:
    # フォールバック: 直接定義
    def sanitize_filename(metric: str) -> str:
        """ファイル名用に指標名をサニタイズ（生成側と同じロジック）"""
        if not metric:
            return metric
        file_metric = metric.strip()
        forbidden_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
        for char in forbidden_chars:
            file_metric = file_metric.replace(char, '_')
        file_metric = file_metric.rstrip('.')
        if not file_metric:
            return metric.strip()
        return file_metric
    
    def load_metric_map(project_root: Path) -> Dict[str, str]:
        """config/metric_map.json を読み込む"""
        metric_map_path = project_root / 'config' / 'metric_map.json'
        if not metric_map_path.exists():
            return {}
        with open(metric_map_path, 'r', encoding='utf-8') as f:
            return json.load(f)


def parse_year_and_league_from_filename(filename: str) -> Optional[Tuple[int, str]]:
    """
    ファイル名から年度とリーグをパース（後方互換性のため残す）
    
    @deprecated: parse_batting_filename() を直接使用してください
    """
    parsed = parse_batting_filename(filename)
    if parsed:
        return (parsed["year"], parsed["league"])
    return None


def resolve_metric_filename(metric_display_name: str, metric_map: Optional[Dict[str, str]] = None) -> str:
    """
    指標表示名からファイル名を生成（生成側と同じロジック）
    
    @param metric_display_name: 指標表示名（Record.csvから抽出された表示名、例: "BB/K", "打率", "BB%"）
    @param metric_map: metric_map.json の内容（オプション、使用しない）
    @returns: ファイル名（例: "BB_K", "打率", "BB%"）
    
    注意: 実際の出力ファイル名は Record.csv の表示名を sanitize_filename() で変換したもの
    - metric_map.json は使用しない（表示名をそのまま使う）
    - 生成側の sanitize_filename() と同じロジックを使用
    """
    if not metric_display_name:
        return ""
    
    # 前後の空白を除去
    metric = metric_display_name.strip()
    
    # 表示名をそのまま sanitize_filename() で変換（metric_map は使わない）
    # 実際の出力ファイル名は Record.csv の表示名を sanitize_filename() で変換したもの
    return sanitize_filename(metric)


def parse_exclude_pattern(exclude_str: str) -> List[Tuple[int, str]]:
    """除外パターンをパース"""
    patterns = []
    for part in exclude_str.split(','):
        part = part.strip()
        if ':' in part:
            year_str, league_str = part.split(':', 1)
            try:
                year = int(year_str.strip())
                league = league_str.strip().upper()
                patterns.append((year, league))
            except ValueError:
                pass
    return patterns


def extract_metrics_from_record_csv(record_csv_path: Path) -> List[str]:
    """Record.csvから指標リストを抽出"""
    encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
    first_line = None
    
    for encoding in encodings:
        try:
            with open(record_csv_path, 'r', encoding=encoding) as f:
                first_line = f.readline()
                if first_line:
                    break
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    
    if not first_line:
        return []
    
    first_line = first_line.rstrip('\r\n')
    metrics_raw = first_line.split(',')
    if len(metrics_raw) == 1:
        metrics_raw = first_line.split('\t')
    
    exclude_cols = {'id', 'name', 'label', 'desc', 'description', '単位', '備考', 'unit', 'note', 'memo'}
    metrics = []
    for metric in metrics_raw:
        metric = metric.lstrip('\ufeff').strip().replace('\u3000', ' ').strip()
        if metric and metric.lower() not in exclude_cols:
            metrics.append(metric)
    
    return metrics


def validate_outputs(
    master_csv_dir: Path,
    calculated_csv_dir: Path,
    rankings_dir: Path,
    record_csv_path: Path,
    exclude_patterns: List[Tuple[int, str]],
    max_year: Optional[int] = None,
    metric_map: Optional[Dict[str, str]] = None
) -> Tuple[bool, List[str]]:
    """
    生成物をバリデーション
    
    @returns: (すべてOKの場合True, エラーメッセージのリスト)
    """
    errors = []
    
    print("\n" + "="*60)
    print("🔍 バリデーション開始")
    print("="*60)
    
    # 指標リストを取得
    metrics = extract_metrics_from_record_csv(record_csv_path)
    if not metrics:
        errors.append("Record.csvから指標リストを抽出できません")
        return False, errors
    
    print(f"\n✅ 指標リスト: {len(metrics)}件")
    
    # 1) 計算済みCSVの存在確認
    print("\n1. 計算済みCSVの存在確認:")
    # すべてのbatting CSVファイルを探索（from_master形式と戦前春秋シーズンの両方）
    master_csv_files = []
    master_csv_files.extend(master_csv_dir.glob('batting_*_*_from_master.csv'))
    master_csv_files.extend(master_csv_dir.glob('batting_*_spring_PRE.csv'))
    master_csv_files.extend(master_csv_dir.glob('batting_*_fall_PRE.csv'))
    
    missing_calculated = []
    processed_count = 0
    
    for master_csv in master_csv_files:
        parsed_info = parse_batting_filename(master_csv.name)
        if not parsed_info:
            # パース失敗は理由付きでエラー
            errors.append(f"ファイル名パース失敗: {master_csv.name} (命名規則を確認してください)")
            continue
        
        year = parsed_info["year"]
        league = parsed_info["league"]
        league_key = parsed_info["league_key"]
        
        if (year, league) in exclude_patterns:
            continue
        
        # max-yearフィルタチェック
        if max_year is not None and year > max_year:
            continue
        
        processed_count += 1
        
        # 計算済みCSVのファイル名を生成（league_keyを使用）
        calculated_filename = build_calculated_filename(parsed_info)
        calculated_csv = calculated_csv_dir / calculated_filename
        
        if not calculated_csv.exists():
            missing_calculated.append((year, league, league_key, master_csv.name, calculated_filename))
            errors.append(f"計算済みCSVが見つかりません: {calculated_filename} (元ファイル: {master_csv.name}, 年度: {year}, リーグ: {league}, リーグキー: {league_key})")
    
    # 対象CSVが0件の場合はエラー
    if processed_count == 0:
        errors.append("❌ 検査対象CSVが0件です。master_csv_dir と命名規則を確認してください")
        print(f"   ❌ 検査対象CSV: 0件")
    else:
        print(f"   ✅ 検査対象CSV: {processed_count}件")
    
    if missing_calculated:
        print(f"   ❌ 欠損: {len(missing_calculated)}件")
        for year, league, league_key, orig_filename, calc_filename in missing_calculated[:5]:
            season_info = f", リーグキー: {league_key}" if league_key != league else ""
            print(f"      - {calc_filename} (元: {orig_filename}, 年度: {year}, リーグ: {league}{season_info})")
        if len(missing_calculated) > 5:
            print(f"      ... 他 {len(missing_calculated) - 5}件")
    else:
        print(f"   ✅ すべて存在します")
    
    # 2) ランキングJSONの存在確認
    print("\n2. ランキングJSONの存在確認:")
    missing_rankings = []
    empty_rankings = []
    
    # すべての計算済みCSVファイルを探索
    calculated_csv_files = []
    calculated_csv_files.extend(calculated_csv_dir.glob('batting_*_*_from_master.csv'))
    
    for calculated_csv in calculated_csv_files:
        parsed_info = parse_batting_filename(calculated_csv.name)
        if not parsed_info:
            # パース失敗は理由付きでエラー
            errors.append(f"ファイル名パース失敗: {calculated_csv.name} (命名規則を確認してください)")
            continue
        
        year = parsed_info["year"]
        league = parsed_info["league"]
        league_key = parsed_info["league_key"]
        
        if (year, league) in exclude_patterns:
            continue
        
        # max-yearフィルタチェック
        if max_year is not None and year > max_year:
            continue
        
        # ランキングディレクトリの決定（実在するディレクトリを優先）
        # PRE_spring/PRE_fall の場合、PRE ディレクトリが存在するか確認
        ranking_dir = None
        if league_key.startswith("PRE_"):
            # PRE_spring や PRE_fall の場合、まず PRE ディレクトリを確認
            pre_dir = rankings_dir / str(year) / "PRE"
            if pre_dir.exists():
                ranking_dir = pre_dir
            else:
                # PRE が存在しない場合は、league_key のまま確認
                ranking_dir = rankings_dir / str(year) / league_key
        else:
            # 通常の場合は league_key を使用
            ranking_dir = rankings_dir / str(year) / league_key
        
        if not ranking_dir or not ranking_dir.exists():
            missing_rankings.append((year, league))
            errors.append(f"ランキングディレクトリが存在しません: {ranking_dir}")
            continue
        
        # 各指標のJSONファイルを確認
        for metric in metrics:
            # ファイル名を生成（生成側と同じロジック、metric_map.jsonを使用）
            file_metric = resolve_metric_filename(metric, metric_map)
            
            if not file_metric:
                errors.append(f"指標名からファイル名を生成できません: {metric} (年度: {year}, リーグ: {league})")
                continue
            
            # 生成側と同じファイル名を使用
            json_path = ranking_dir / f"{file_metric}.json"
            json_all_path = ranking_dir / f"{file_metric}_all.json"
            
            # 存在確認
            if not json_path.exists():
                errors.append(f"ランキングJSONが見つかりません: {json_path} (年度: {year}, リーグ: {league}, 指標: {metric})")
                continue
            
            # _all版の存在確認
            if not json_all_path.exists():
                errors.append(f"ランキングJSON(_all)が見つかりません: {json_all_path} (年度: {year}, リーグ: {league}, 指標: {metric})")
            
            # 0件チェック
            for json_file in [json_path, json_all_path]:
                if json_file.exists():
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        if not isinstance(data, list) or len(data) == 0:
                            empty_rankings.append((year, league, json_file.name))
                            errors.append(f"ランキングJSONが0件です: {json_file} (年度: {year}, リーグ: {league})")
                    except Exception as e:
                        errors.append(f"ランキングJSONの読み込みエラー: {json_file} - {e}")
    
    if missing_rankings:
        print(f"   ❌ 欠損ディレクトリ: {len(missing_rankings)}件")
    if empty_rankings:
        print(f"   ❌ 0件JSON: {len(empty_rankings)}件")
        for year, league, filename in empty_rankings[:5]:
            print(f"      - {filename} (年度: {year}, リーグ: {league})")
        if len(empty_rankings) > 5:
            print(f"      ... 他 {len(empty_rankings) - 5}件")
    
    if not missing_rankings and not empty_rankings:
        print(f"   ✅ すべて存在し、0件ではありません")
    
    print("\n" + "="*60)
    if errors:
        print(f"❌ バリデーション失敗: {len(errors)}件のエラー")
    else:
        print("✅ バリデーション成功: すべてOK")
    print("="*60)
    
    return len(errors) == 0, errors


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='生成物のバリデーション')
    parser.add_argument(
        '--master_csv_dir',
        type=str,
        default='_data/master_csv',
        help='入力CSVディレクトリ（デフォルト: _data/master_csv）'
    )
    parser.add_argument(
        '--calculated_csv_dir',
        type=str,
        default='_data/master_csv_calculated',
        help='計算済みCSVディレクトリ（デフォルト: _data/master_csv_calculated）'
    )
    parser.add_argument(
        '--rankings_dir',
        type=str,
        default='public/data/rankings',
        help='ランキングJSONディレクトリ（デフォルト: public/data/rankings）'
    )
    parser.add_argument(
        '--exclude',
        type=str,
        default='2025:PL',
        help='除外パターン（デフォルト: "2025:PL"）'
    )
    parser.add_argument(
        '--max-year',
        type=int,
        help='最大年度（この年度以下のみ検査、例: --max-year 2024）'
    )
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    master_csv_dir = project_root / args.master_csv_dir
    calculated_csv_dir = project_root / args.calculated_csv_dir
    rankings_dir = project_root / args.rankings_dir
    
    print(f"📁 プロジェクトルート: {project_root}")
    print(f"📁 入力CSVディレクトリ: {master_csv_dir}")
    print(f"📁 計算済みCSVディレクトリ: {calculated_csv_dir}")
    print(f"📁 ランキングJSONディレクトリ: {rankings_dir}")
    
    # 除外パターンをパース
    exclude_patterns = parse_exclude_pattern(args.exclude)
    if exclude_patterns:
        print(f"🚫 除外パターン: {exclude_patterns}")
    
    # max-yearの表示
    if args.max_year:
        print(f"📅 最大年度フィルタ: {args.max_year}年以下のみ検査")
    
    # Record.csvを探す
    record_search_paths = [
        project_root,
        project_root / '_data' / 'master_csv',
    ]
    record_csv_path = None
    for search_path in record_search_paths:
        record_path = search_path / 'Record.csv'
        if record_path.exists():
            record_csv_path = record_path
            break
    
    if not record_csv_path:
        print(f"❌ エラー: Record.csvが見つかりません")
        return 1
    
    print(f"✅ Record.csv: {record_csv_path}")
    
    # metric_map.jsonを読み込む（単一ソース化）
    metric_map_path = project_root / "config" / "metric_map.json"
    metric_map = {}
    if metric_map_path.exists():
        try:
            metric_map = json.loads(metric_map_path.read_text(encoding="utf-8"))
            print(f"✅ metric_map.json: {len(metric_map)}件")
        except Exception as e:
            print(f"⚠️  metric_map.jsonの読み込みに失敗: {e}（フォールバックを使用）")
    else:
        print(f"⚠️  metric_map.json が見つかりません: {metric_map_path}（フォールバックを使用）")
    
    # バリデーション実行
    is_valid, errors = validate_outputs(
        master_csv_dir,
        calculated_csv_dir,
        rankings_dir,
        record_csv_path,
        exclude_patterns,
        args.max_year,
        metric_map
    )
    
    if errors:
        print(f"\n❌ エラー詳細:")
        for error in errors[:20]:  # 最初の20件のみ表示
            print(f"   - {error}")
        if len(errors) > 20:
            print(f"   ... 他 {len(errors) - 20}件")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

