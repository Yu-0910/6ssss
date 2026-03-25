#!/usr/bin/env python3
"""
build_rankings_all_from_yearly_dir.py

全シーズンのランキングJSONを一括生成するスクリプト

入力: npb_battingのyearly_from_master_dedupディレクトリ
出力: TopPageのpublic/data/rankings/{seasonKey}/{league}/

規定打席は「試合数×3.1」で算出（games_per_team_by_season.jsonから取得）
"""

import argparse
import csv
import json
import math
import re
import shutil
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# 既存のbuild_rankings_2025_PL_full.pyから関数をインポート
# 同じディレクトリにあることを前提
sys.path.insert(0, str(Path(__file__).parent))
try:
    from build_rankings_2025_PL_full import (
        load_csv_with_encoding,
        sanitize_filename,
        get_pa_value,
        get_player_name,
        get_team_name,
        calculate_missing_values,
        get_metric_value,
        format_value,
        generate_ranking_for_metric,
        load_metric_map,
        extract_metrics_from_record_csv,
        METRICS_REQUIRE_QUALIFYING_PA_BY_NAME,
        METRICS_NO_QUALIFYING_PA_BY_NAME,
        normalize_metric_json_for_ui,
        validate_metric_json_mapping,
    )
except ImportError as e:
    print(f"❌ エラー: build_rankings_2025_PL_full.py から関数をインポートできません: {e}")
    print(f"   build_rankings_2025_PL_full.py が同じディレクトリに存在することを確認してください")
    sys.exit(1)


def safe_int(value: Any, default: int = 0) -> int:
    """安全にintに変換"""
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """安全にfloatに変換"""
    if value is None:
        return default
    try:
        val = float(value)
        if math.isnan(val) or math.isinf(val):
            return default
        return val
    except (ValueError, TypeError):
        return default


def parse_season_key_from_filename(filename: str) -> Tuple[Optional[str], Optional[str]]:
    """
    CSVファイル名からseasonKeyとleagueを抽出
    
    @param filename: CSVファイル名（例: "batting_2025_PL_from_master.csv", "batting_1936S_PRE_from_master.csv"）
    @returns: (seasonKey, league) または (None, None)
    """
    # パターン1: batting_YYYY_LEAGUE_from_master.csv
    match1 = re.match(r'batting_(\d{4})_(CL|PL|PRE)_from_master\.csv', filename)
    if match1:
        year = match1.group(1)
        league = match1.group(2)
        return year, league
    
    # パターン2: batting_YYYY[S|U|F]_LEAGUE_from_master.csv（分割シーズン）
    match2 = re.match(r'batting_(\d{4})([SUF])_(CL|PL|PRE)_from_master\.csv', filename)
    if match2:
        year = match2.group(1)
        season_suffix = match2.group(2)
        league = match2.group(3)
        season_key = f"{year}{season_suffix}"
        return season_key, league
    
    return None, None


def load_games_map(games_map_path: Path) -> Dict[str, Dict[str, int]]:
    """
    試合数マップを読み込む
    
    @param games_map_path: games_per_team_by_season.jsonのパス
    @returns: {seasonKey: {league: games_per_team}}
    """
    if not games_map_path.exists():
        print(f"⚠️  試合数マップが見つかりません: {games_map_path}")
        print(f"   先に build_games_per_team_map.py を実行してください")
        return {}
    
    with open(games_map_path, 'r', encoding='utf-8') as f:
        games_map = json.load(f)
    
    return games_map


def calculate_min_pa(
    season_key: str,
    league: str,
    games_map: Dict[str, Dict[str, int]],
    batting_data: List[Dict[str, Any]]
) -> Tuple[int, int, bool]:
    """
    規定打席を計算
    
    @param season_key: シーズンキー（例: "2025", "1936S"）
    @param league: リーグ（"CL", "PL", "PRE"）
    @param games_map: 試合数マップ
    @param batting_data: バッティングデータ（フォールバック用）
    @returns: (min_pa, team_games, is_estimated)
    """
    # games_mapから取得を試みる
    if season_key in games_map and league in games_map[season_key]:
        team_games = games_map[season_key][league]
        if team_games is not None:
            min_pa = round(team_games * 3.1)
            return min_pa, team_games, False
    
    # フォールバック: CSVのgames列のmaxから推定
    team_games_est = 0
    for row in batting_data:
        games_val = safe_int(row.get('G') or row.get('games') or row.get('Games'), 0)
        if games_val > team_games_est:
            team_games_est = games_val
    
    if team_games_est > 0:
        min_pa = round(team_games_est * 3.1)
        return min_pa, team_games_est, True
    
    # さらにフォールバック: デフォルト値
    team_games_default = 143
    min_pa_default = round(team_games_default * 3.1)
    return min_pa_default, team_games_default, True


def process_csv_file(
    csv_path: Path,
    output_base_dir: Path,
    games_map: Dict[str, Dict[str, int]],
    record_csv_path: Path,
    metric_map: Dict[str, str],
    report_data: List[Dict[str, Any]]
) -> Tuple[bool, Dict[str, Any]]:
    """
    1つのCSVファイルを処理してランキングJSONを生成
    
    @param csv_path: 入力CSVファイルのパス
    @param output_base_dir: 出力ベースディレクトリ（public/data/rankings）
    @param games_map: 試合数マップ
    @param record_csv_path: Record.csvのパス
    @param metric_map: 指標マップ
    @param report_data: レポートデータを追加するリスト
    @returns: (成功した場合True, レポートエントリ)
    """
    filename = csv_path.name
    season_key, league = parse_season_key_from_filename(filename)
    
    if not season_key or not league:
        print(f"⚠️  ファイル名からseasonKey/leagueを抽出できません: {filename}")
        report_data.append({
            "seasonKey": None,
            "league": None,
            "csv_filename": filename,
            "team_games_source": "N/A",
            "team_games": None,
            "min_pa_qual": None,
            "files_expected": 0,
            "files_written": 0,
            "status": "ERROR",
            "error": "seasonKey/league抽出失敗"
        })
        return False, {}
    
    print(f"\n{'='*60}")
    print(f"📄 処理中: {filename}")
    print(f"   シーズン: {season_key}, リーグ: {league}")
    
    # CSVを読み込む
    try:
        batting_data = load_csv_with_encoding(str(csv_path))
        print(f"   ✅ CSV読み込み完了: {len(batting_data)}件")
    except Exception as e:
        print(f"   ❌ CSV読み込みエラー: {e}")
        report_data.append({
            "seasonKey": season_key,
            "league": league,
            "csv_filename": filename,
            "team_games_source": "N/A",
            "team_games": None,
            "min_pa_qual": None,
            "files_expected": 0,
            "files_written": 0,
            "status": "ERROR",
            "error": f"CSV読み込みエラー: {e}"
        })
        return False, {}
    
    # 規定打席到達版CSV（Phase 2: 規定必須指標用）
    qualifying_filename = filename.replace("_from_master.csv", "_qualifying.csv")
    qualifying_csv_path = csv_path.parent / qualifying_filename
    batting_data_qualifying = None
    if qualifying_csv_path.exists():
        try:
            batting_data_qualifying = load_csv_with_encoding(str(qualifying_csv_path))
            print(f"   [OK] 規定打席到達版CSV読み込み: {qualifying_filename} ({len(batting_data_qualifying)}件)")
        except Exception as e:
            print(f"   [WARN] 規定打席到達版CSV読み込み失敗: {e}（規定あり版は全員用CSV+minPAで生成）")
    else:
        print(f"   [WARN] 規定打席到達版CSVなし: {qualifying_filename}（規定あり版は全員用CSV+minPAで生成）")
    
    # 規定打席を計算
    min_pa, team_games, source = calculate_min_pa(season_key, league, games_map, batting_data)
    source_label = {
        "map": "games_map",
        "fallback_max_games": "fallback_max_games",
        "default": "default"
    }.get(source, source)
    print(f"   📊 試合数: {team_games}, 規定打席: {min_pa} (source: {source_label})")
    
    # 出力ディレクトリ
    output_dir = output_base_dir / season_key / league
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 指標リストを取得
    try:
        metrics = extract_metrics_from_record_csv(str(record_csv_path))
        print(f"   ✅ 指標リスト取得: {len(metrics)}件")
    except Exception as e:
        print(f"   ❌ 指標リスト取得エラー: {e}")
        report_data.append({
            "seasonKey": season_key,
            "league": league,
            "csv_filename": filename,
            "team_games_source": source_label,
            "team_games": team_games,
            "min_pa_qual": min_pa,
            "files_expected": 0,
            "files_written": 0,
            "status": "ERROR",
            "error": f"指標リスト取得エラー: {e}"
        })
        return False, {}
    
    # 各指標のランキングを生成（規定あり版と規定なし版の両方）
    success_count = 0
    failed_metrics = []
    
    for metric in metrics:
        file_metric = sanitize_filename(metric)
        
        # 規定あり版（規定必須指標かつ規定用CSVありの場合は規定用CSVを min_pa=0 で使用）
        output_path = output_dir / f"{file_metric}.json"
        use_qualifying_csv = (
            metric in METRICS_REQUIRE_QUALIFYING_PA_BY_NAME
            and batting_data_qualifying is not None
        )
        data_for_qualifying = batting_data_qualifying if use_qualifying_csv else batting_data
        min_pa_for_qualifying = 0 if use_qualifying_csv else min_pa
        try:
            success = generate_ranking_for_metric(
                data_for_qualifying,
                metric,
                str(output_path),
                top_n=100,
                min_pa=min_pa_for_qualifying,
                metric_map=metric_map
            )
            if success:
                success_count += 1
            else:
                failed_metrics.append(metric)
        except Exception as e:
            print(f"   ⚠️  {metric} → エラー: {e}")
            failed_metrics.append(metric)
        
        # 規定なし版
        output_path_all = output_dir / f"{file_metric}_all.json"
        try:
            generate_ranking_for_metric(
                batting_data,
                metric,
                str(output_path_all),
                top_n=100,
                min_pa=0,
                metric_map=metric_map
            )
        except Exception as e:
            print(f"   ⚠️  {metric}_all → エラー: {e}")
    
    # UI用に正規化
    try:
        normalize_metric_json_for_ui(output_dir, metrics)
        print(f"   ✅ UI用正規化完了")
    except Exception as e:
        print(f"   ⚠️  UI用正規化エラー: {e}")
    
    # 検証
    try:
        validate_metric_json_mapping(output_dir, metrics, metric_map, min_pa)
        print(f"   ✅ 検証完了")
    except Exception as e:
        print(f"   ⚠️  検証エラー: {e}")
    
    # 生成されたファイル数を確認
    expected_files = len(metrics) * 2  # {metric}.json と {metric}_all.json
    actual_files = len(list(output_dir.glob("*.json")))
    
    # 欠損ファイルを検出
    missing_files = []
    for metric in metrics:
        file_metric = sanitize_filename(metric)
        if not (output_dir / f"{file_metric}.json").exists():
            missing_files.append(f"{file_metric}.json")
        if not (output_dir / f"{file_metric}_all.json").exists():
            missing_files.append(f"{file_metric}_all.json")
    
    # ステータスを決定
    if actual_files == expected_files and not failed_metrics:
        status = "OK"
    elif actual_files < expected_files:
        status = "MISSING_FILES"
    elif failed_metrics:
        status = "PARTIAL_ERROR"
    else:
        status = "OK"
    
    # レポートデータに記録
    report_entry = {
        "seasonKey": season_key,
        "league": league,
        "csv_filename": filename,
        "team_games_source": source_label,
        "team_games": team_games,
        "min_pa_qual": min_pa,
        "files_expected": expected_files,
        "files_written": actual_files,
        "status": status,
        "failed_metrics": failed_metrics,
        "missing_files": missing_files[:10] if len(missing_files) > 10 else missing_files  # 最初の10件のみ
    }
    report_data.append(report_entry)
    
    if failed_metrics:
        print(f"   ⚠️  失敗した指標: {', '.join(failed_metrics[:5])}{'...' if len(failed_metrics) > 5 else ''}")
    if missing_files:
        print(f"   ⚠️  欠損ファイル: {len(missing_files)}件")
    
    return True, report_entry


def validate_prerequisites(
    input_dir: Path,
    games_map_path: Path,
    output_base_dir: Path,
    project_root: Path
) -> Tuple[bool, Optional[str]]:
    """
    前提条件をチェック
    
    @returns: (成功した場合True, エラーメッセージ)
    """
    print("\n" + "="*60)
    print("🔍 前提条件チェック中...")
    print("="*60)
    
    # 2-1. input_dir の存在確認
    print("\n1. 入力ディレクトリの確認:")
    if not input_dir.exists():
        return False, f"入力ディレクトリが存在しません: {input_dir}"
    
    csv_files = list(input_dir.glob('batting_*_*_from_master.csv'))
    if len(csv_files) == 0:
        return False, f"入力ディレクトリにCSVファイルが見つかりません: {input_dir}"
    
    print(f"   ✅ 入力ディレクトリ: {input_dir}")
    print(f"   ✅ CSVファイル数: {len(csv_files)}")
    
    # 2-2. games_map のロード確認
    print("\n2. 試合数マップの確認:")
    if not games_map_path.exists():
        return False, f"試合数マップが存在しません: {games_map_path}\n   先に build_games_per_team_map.py を実行してください"
    
    try:
        with open(games_map_path, 'r', encoding='utf-8') as f:
            games_map = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"試合数マップのJSON解析エラー: {e}"
    except Exception as e:
        return False, f"試合数マップの読み込みエラー: {e}"
    
    if len(games_map) < 100:
        return False, f"試合数マップのキー数が少なすぎます: {len(games_map)}件（100件以上が期待されます）\n   スクレイプが失敗している可能性があります"
    
    print(f"   ✅ 試合数マップ: {games_map_path}")
    print(f"   ✅ シーズン数: {len(games_map)}")
    
    # 2-3. 2025PL基準ファイルの存在確認
    print("\n3. スキーマ基準ファイル（2025PL）の確認:")
    schema_ref_path = output_base_dir / '2025' / 'PL' / 'OPS.json'
    if not schema_ref_path.exists():
        print(f"   ⚠️  警告: スキーマ基準ファイルが見つかりません: {schema_ref_path}")
        print(f"      2025PLのランキングを先に生成することを推奨します")
    else:
        try:
            with open(schema_ref_path, 'r', encoding='utf-8') as f:
                schema_ref = json.load(f)
            if not isinstance(schema_ref, list) or len(schema_ref) == 0:
                return False, f"スキーマ基準ファイルの形式が不正です: {schema_ref_path}"
            print(f"   ✅ スキーマ基準ファイル: {schema_ref_path}")
            print(f"   ✅ スキーマ検証: OK（{len(schema_ref)}件のレコード）")
        except Exception as e:
            return False, f"スキーマ基準ファイルの読み込みエラー: {e}"
    
    print("\n" + "="*60)
    print("✅ 前提条件チェック: すべてパス")
    print("="*60)
    
    return True, None


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='全シーズンのランキングJSONを一括生成')
    parser.add_argument(
        '--input_dir',
        type=str,
        required=True,
        help='入力CSVディレクトリ（npb_battingのyearly_from_master_dedup）'
    )
    parser.add_argument(
        '--out_dir',
        type=str,
        default='public/data/rankings',
        help='出力ディレクトリ（デフォルト: public/data/rankings）'
    )
    parser.add_argument(
        '--games_map',
        type=str,
        default='config/games_per_team_by_season.json',
        help='試合数マップのパス（デフォルト: config/games_per_team_by_season.json）'
    )
    parser.add_argument(
        '--schema_ref',
        type=str,
        default=None,
        help='スキーマ基準ファイルのパス（デフォルト: {out_dir}/2025/PL/OPS.json）'
    )
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    input_dir = Path(args.input_dir)
    output_base_dir = project_root / args.out_dir
    games_map_path = project_root / args.games_map
    
    print(f"📁 プロジェクトルート: {project_root}")
    print(f"📁 入力ディレクトリ: {input_dir}")
    print(f"📁 出力ディレクトリ: {output_base_dir}")
    print(f"📁 試合数マップ: {games_map_path}")
    
    # 前提条件チェック
    is_valid, error_msg = validate_prerequisites(
        input_dir,
        games_map_path,
        output_base_dir,
        project_root
    )
    if not is_valid:
        print(f"\n❌ エラー: {error_msg}")
        return 1
    
    # 試合数マップを読み込む
    games_map = load_games_map(games_map_path)
    if not games_map:
        print(f"⚠️  警告: 試合数マップが空です。推定値を使用します")
    
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
    
    print(f"\n✅ Record.csv: {record_csv_path}")
    
    # metric_mapを読み込む
    try:
        metric_map = load_metric_map(project_root)
        print(f"✅ metric_map.json: {len(metric_map)}件")
    except Exception as e:
        print(f"⚠️  metric_map.jsonの読み込みに失敗: {e}")
        metric_map = {}
    
    # CSVファイルを列挙
    csv_files = list(input_dir.glob('batting_*_*_from_master.csv'))
    print(f"\n📋 処理対象CSVファイル: {len(csv_files)}件")
    
    if not csv_files:
        print(f"❌ エラー: CSVファイルが見つかりません")
        return 1
    
    # レポート用データ
    report_data: List[Dict[str, Any]] = []
    
    # 各CSVファイルを処理
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    for csv_path in sorted(csv_files):
        success, report_entry = process_csv_file(
            csv_path,
            output_base_dir,
            games_map,
            record_csv_path,
            metric_map,
            report_data
        )
        if success:
            if report_entry.get("status") == "SKIPPED":
                skipped_count += 1
            else:
                success_count += 1
        else:
            error_count += 1
    
    # レポートを生成
    report_dir = project_root / 'output' / 'reports'
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / 'ranking_generation_report.md'
    
    # ユニークな(seasonKey, league)の数を計算
    unique_seasons = set()
    total_files_written = 0
    total_files_expected = 0
    missing_seasons = []
    
    for entry in report_data:
        if entry.get("seasonKey") and entry.get("league"):
            unique_seasons.add((entry["seasonKey"], entry["league"]))
        total_files_written += entry.get("files_written", 0)
        total_files_expected += entry.get("files_expected", 0)
        if entry.get("status") in ["MISSING_FILES", "ERROR"]:
            missing_seasons.append(entry)
    
    # レポートを生成
    report_lines = [
        "# ランキング生成レポート",
        "",
        f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## サマリー",
        "",
        f"- CSVファイル数: {len(csv_files)}",
        f"- 処理成功: {success_count}",
        f"- 処理失敗: {error_count}",
        f"- スキップ: {skipped_count}",
        f"- 生成した(seasonKey, league)のユニーク件数: {len(unique_seasons)}",
        f"- 生成ファイル総数: {total_files_written}/{total_files_expected}",
        f"- 生成ディレクトリ: {output_base_dir}",
        "",
        "## シーズンごとの詳細",
        "",
        "| seasonKey | league | csv_filename | team_games_source | team_games | min_pa_qual | files_expected | files_written | status |",
        "|-----------|--------|--------------|-------------------|------------|-------------|----------------|---------------|--------|",
    ]
    
    # テーブル行を追加
    for entry in sorted(report_data, key=lambda x: (x.get("seasonKey") or "", x.get("league") or "")):
        season_key = entry.get("seasonKey", "N/A")
        league = entry.get("league", "N/A")
        csv_filename = entry.get("csv_filename", "N/A")
        team_games_source = entry.get("team_games_source", "N/A")
        team_games = entry.get("team_games", "N/A")
        min_pa_qual = entry.get("min_pa_qual", "N/A")
        files_expected = entry.get("files_expected", 0)
        files_written = entry.get("files_written", 0)
        status = entry.get("status", "UNKNOWN")
        
        report_lines.append(
            f"| {season_key} | {league} | {csv_filename} | {team_games_source} | "
            f"{team_games} | {min_pa_qual} | {files_expected} | {files_written} | {status} |"
        )
    
    # 欠損一覧
    if missing_seasons:
        report_lines.extend([
            "",
            "## 欠損一覧",
            "",
        ])
        
        for entry in missing_seasons:
            season_key = entry.get("seasonKey", "N/A")
            league = entry.get("league", "N/A")
            status = entry.get("status", "UNKNOWN")
            missing_files = entry.get("missing_files", [])
            failed_metrics = entry.get("failed_metrics", [])
            error = entry.get("error")
            
            report_lines.append(f"### {season_key} / {league} ({status})")
            if error:
                report_lines.append(f"- エラー: {error}")
            if failed_metrics:
                report_lines.append(f"- 失敗した指標: {', '.join(failed_metrics)}")
            if missing_files:
                report_lines.append(f"- 欠損ファイル（先頭10件）: {', '.join(missing_files)}")
            report_lines.append("")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"\n{'='*60}")
    print(f"✅ 処理完了: 成功={success_count}, 失敗={error_count}, スキップ={skipped_count}")
    print(f"📄 レポート: {report_path}")
    
    if missing_seasons:
        print(f"⚠️  警告: {len(missing_seasons)}件のシーズンで欠損があります。レポートを確認してください。")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

