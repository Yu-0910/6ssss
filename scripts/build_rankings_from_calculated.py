#!/usr/bin/env python3
"""
build_rankings_from_calculated.py

計算済みCSV（_data/master_csv_calculated/）からランキングJSONを一括生成するスクリプト

入力: _data/master_csv_calculated/batting_YYYY_LEAGUE_from_master.csv
出力: public/data/rankings/{YEAR}/{LEAGUE}/{METRIC}.json

2025PLは除外（既に生成済みのため）
"""

import argparse
import json
import math
import re
import sys
import io
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime


def safe_str(x: Any) -> str:
    """
    pandas由来のNaNを空扱いにする安全な文字列変換
    
    Args:
        x: 変換対象の値
        
    Returns:
        空文字列（None/NaNの場合）または文字列化した値
    """
    if x is None:
        return ""
    if isinstance(x, float) and math.isnan(x):
        return ""
    return str(x).strip()

# WindowsでのUnicode出力対応
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 既存のbuild_rankings_2025_PL_full.pyから関数をインポート
sys.path.insert(0, str(Path(__file__).parent))
try:
    from build_rankings_2025_PL_full import (
        load_csv_with_encoding,
        sanitize_filename,
        generate_ranking_for_metric,
        load_metric_map,
        extract_metrics_from_record_csv,
        normalize_metric_json_for_ui,
        validate_metric_json_mapping,
        normalize_name,
        METRICS_REQUIRE_QUALIFYING_PA_BY_NAME,
    )
except ImportError as e:
    print(f"❌ エラー: build_rankings_2025_PL_full.py から関数をインポートできません: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# チーム名正規化関数をインポート
try:
    from add_qualifying_pa_flags import normalize_team_name
except ImportError as e:
    print(f"⚠️  警告: add_qualifying_pa_flags.py から normalize_team_name をインポートできません: {e}")
    # フォールバック: 簡易版の正規化関数
    def normalize_team_name(team: str) -> str:
        return team.strip() if team else ""

# 規定ルールモジュールをインポート
try:
    from qualifying.qualifying_rules import (
        get_qualifying_rule,
        calc_qual_threshold,
        is_player_qualified,
        QualifyingBasis
    )
except ImportError as e:
    print(f"❌ エラー: qualifying_rules.py から関数をインポートできません: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 共通パーサーをインポート
try:
    from lib.filename_parser import parse_batting_filename, build_rankings_output_path
except ImportError:
    # フォールバック: scripts/lib/filename_parser.py
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from lib.filename_parser import parse_batting_filename, build_rankings_output_path


def parse_year_and_league_from_filename(filename: str) -> Optional[Tuple[int, str]]:
    """
    ファイル名から年度とリーグキーをパース（後方互換性のため残す）
    
    @deprecated: parse_batting_filename() を直接使用してください
    """
    parsed = parse_batting_filename(filename)
    if parsed:
        return (parsed["year"], parsed["league_key"])
    return None


def should_skip_by_max_year(year: int, max_year: Optional[int]) -> bool:
    """max_yearフィルタでスキップすべきか判定"""
    if max_year is None:
        return False
    return year > max_year


def parse_exclude_pattern(exclude_str: str) -> List[Tuple[int, str]]:
    """除外パターンをパース（例: "2025:PL" → [(2025, "PL")]）"""
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
                print(f"⚠️  無効な除外パターン: {part}（スキップ）")
    return patterns


def generate_qualified_ranking_for_metric(
    batting_data: List[Dict[str, Any]],
    metric: str,
    output_path: str,
    qualifying_rule: Dict[str, Any],
    year: int,
    league: str,
    team_games: int,
    top_n: int = 100,
    metric_map: Optional[Dict[str, str]] = None,
    normalized_columns: Optional[Dict[str, str]] = None,
    csv_columns: Optional[List[str]] = None
) -> bool:
    """
    規定到達者版ランキングを生成
    
    Args:
        batting_data: バッティングデータ
        metric: 指標の表示名
        output_path: 出力パス
        qualifying_rule: 規定ルール辞書
        year: 年度
        league: リーグ
        team_games: チーム試合数
        top_n: 上位N件
        metric_map: 指標マップ
        normalized_columns: 正規化列名マッピング
        csv_columns: CSV列名一覧
    
    Returns:
        成功した場合True
    """
    from build_rankings_2025_PL_full import (
        calculate_missing_values,
        get_metric_value,
        format_value,
        get_player_name,
        get_team_name,
        get_pa_value,
        normalize_string,
        safe_int,
        safe_float
    )
    
    # チーム名→チーム試合数のマッピングを作成
    team_games_map = {}
    for row in batting_data:
        team = row.get("Team") or row.get("team") or row.get("チーム") or ""
        if team and team not in team_games_map:
            # チーム試合数は games_map から取得するか、デフォルト値を使用
            team_games_map[team] = team_games
    
    # チームごとのthresholdを計算（ログは process_calculated_csv で既に出力済み）
    team_threshold_map = {}
    basis = qualifying_rule["basis"]
    rounding_mode = qualifying_rule.get("rounding_mode", "round_half_up")
    
    # team_games_mapのキー（チーム名）を使って、各チームのthresholdを計算
    # チーム名は正規化してから使用
    for raw_team_name in team_games_map.keys():
        if not raw_team_name:
            continue
        
        # チーム名を正規化
        team_name_normalized = normalize_team_name(raw_team_name)
        team_games_for_team = team_games_map[raw_team_name]
        
        # 規定到達しきい値を計算（正規化後のチーム名を使用）
        try:
            threshold = calc_qual_threshold(qualifying_rule, team_games_for_team, team_name=team_name_normalized)
            # 元のチーム名と正規化後のチーム名の両方でマッピングを保持
            team_threshold_map[raw_team_name] = threshold
            team_threshold_map[team_name_normalized] = threshold
        except Exception as e:
            team_threshold_map[raw_team_name] = None
            team_threshold_map[team_name_normalized] = None
    
    # デバッグログ: 判定基準を確認
    basis_str = basis.value if isinstance(basis, QualifyingBasis) else str(basis)
    using = "AB" if basis in [QualifyingBasis.AB_FIXED, QualifyingBasis.AB_TEAMGAMES_MULT, QualifyingBasis.AB_TEAM_GROUP] else "PA"
    # 代表的なthresholdを取得（最初の非None値）
    sample_threshold = next((t for t in team_threshold_map.values() if t is not None), None)
    if sample_threshold is not None:
        print(f"   [QUALCHECK] metric={metric} basis={basis_str} threshold={sample_threshold} using={using}")
    
    # 規定到達者をフィルタリング
    qualified_data = []
    for row in batting_data:
        # データを補完
        enriched_row = calculate_missing_values(row.copy())
        
        # チーム名を取得して正規化
        raw_team_name = enriched_row.get("Team") or enriched_row.get("team") or enriched_row.get("チーム") or ""
        team_name_normalized = normalize_team_name(raw_team_name)
        
        # thresholdを取得（正規化後のチーム名で検索）
        threshold = team_threshold_map.get(team_name_normalized) or team_threshold_map.get(raw_team_name)
        
        # threshold が None の場合はスキップ
        if threshold is None:
            continue
        
        # 規定到達者かどうかを判定
        min_player_games = qualifying_rule.get("min_player_games")
        
        if is_player_qualified(enriched_row, threshold, basis, min_player_games):
            qualified_data.append(enriched_row)
    
    if not qualified_data:
        return False
    
    # 指標値を取得してソート
    metric_values = []
    for row in qualified_data:
        value, col_name, status = get_metric_value(row, metric, normalized_columns)
        if value is not None and not math.isnan(value) and not math.isinf(value):
            metric_values.append((value, row))
    
    # 降順でソート
    metric_values.sort(key=lambda x: x[0], reverse=True)
    
    # 上位N件を取得
    top_players = metric_values[:top_n]
    
    # JSON形式に整形（generate_ranking_for_metric と同じ形式）
    players = []
    for rank, (value, row) in enumerate(top_players, start=1):
        # 選手名の取得（優先順位: player_name_ja > player_name）
        display_name_ja = safe_str(row.get("player_name_ja"))
        display_name_en = safe_str(row.get("player_name_en"))
        fallback_name = safe_str(row.get("player_name"))
        
        # player_name_jaを優先、なければfallback_nameを使用
        player_name = display_name_ja if display_name_ja else fallback_name
        if not player_name:
            # 最終フォールバック: get_player_nameを使用
            player_name = get_player_name(row)
        
        team_name = get_team_name(row)
        pa, _ = get_pa_value(row)
        ab = safe_int(row.get('AB') or row.get('ab') or row.get('AB'), 0)
        
        # チーム名を正規化してthresholdを取得
        raw_team_name = row.get("Team") or row.get("team") or row.get("チーム") or team_name
        team_name_normalized = normalize_team_name(raw_team_name)
        player_threshold = team_threshold_map.get(team_name_normalized) or team_threshold_map.get(raw_team_name)
        
        formatted_value = format_value(value, metric)
        
        player_data = {
            'rank': rank,
            'player': player_name,
            'team': team_name,
            'PA': pa,
            'value': formatted_value,
            'metric': metric,
        }
        
        # 規定到達条件を設定（basisに応じてmin_abまたはmin_paを設定）
        if basis in [QualifyingBasis.AB_FIXED, QualifyingBasis.AB_TEAMGAMES_MULT, QualifyingBasis.AB_TEAM_GROUP]:
            if player_threshold is not None:
                player_data['min_ab'] = player_threshold
        elif basis in [QualifyingBasis.PA_FIXED, QualifyingBasis.PA_TEAMGAMES_MULT]:
            if player_threshold is not None:
                player_data['min_pa'] = player_threshold
        
        # 既存UIの形式に合わせて追加フィールドを設定
        player_data['playerId'] = f"player-{rank}"
        player_data['name'] = normalize_string(player_name)
        
        # 英字名の取得（player_name_enがあればそこへ、無ければ空）
        roman_name = normalize_string(display_name_en) if display_name_en else ''
        player_data['romanName'] = roman_name
        player_data['team'] = normalize_string(team_name)
        
        # その他のフィールドも可能な限り設定
        player_data['age'] = safe_int(row.get('Age') or row.get('age'), 0)
        player_data['ops'] = format_value(safe_float(row.get('OPS') or row.get('ops')), 'OPS')
        player_data['avg'] = format_value(safe_float(row.get('AVG') or row.get('avg')), 'AVG')
        player_data['hits'] = safe_int(row.get('H') or row.get('hits') or row.get('Hits'), 0)
        player_data['hr'] = safe_int(row.get('HR') or row.get('hr') or row.get('HR'), 0)
        player_data['rbi'] = safe_int(row.get('RBI') or row.get('rbi') or row.get('RBI'), 0)
        player_data['games'] = safe_int(row.get('G') or row.get('games') or row.get('G'), 0)
        player_data['pa'] = safe_int(row.get('PA') or row.get('pa') or row.get('PA'), 0)
        player_data['ab'] = safe_int(row.get('AB') or row.get('ab') or row.get('AB'), 0)
        
        players.append(player_data)
    
    # 出力ディレクトリを作成
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # JSONファイルに出力
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(players, f, ensure_ascii=False, indent=2)
    
    return True


def calculate_min_pa_from_games_map(
    year: int,
    league: str,
    games_map: Dict[str, Dict[str, int]],
    batting_data: List[Dict[str, Any]]
) -> Tuple[int, int, str]:
    """
    規定打席を計算（games_map優先、フォールバックあり）
    
    @returns: (min_pa, team_games, source)
    """
    season_key = str(year)
    
    # games_mapから取得を試みる
    if season_key in games_map and league in games_map[season_key]:
        team_games = games_map[season_key][league]
        if team_games is not None and team_games > 0:
            min_pa = round(team_games * 3.1)
            return min_pa, team_games, "games_map"
    
    # フォールバック: CSVのgames列のmaxから推定
    team_games_est = 0
    for row in batting_data:
        games_val = None
        for col in ['G', 'games', 'Games', '試合']:
            if col in row and row[col]:
                try:
                    games_val = int(float(row[col]))
                    if games_val > team_games_est:
                        team_games_est = games_val
                    break
                except (ValueError, TypeError):
                    continue
    
    if team_games_est > 0:
        min_pa = round(team_games_est * 3.1)
        return min_pa, team_games_est, "fallback_max_games"
    
    # デフォルト値
    team_games_default = 143
    min_pa_default = round(team_games_default * 3.1)
    return min_pa_default, team_games_default, "default"


def process_calculated_csv(
    csv_path: Path,
    output_base_dir: Path,
    games_map: Dict[str, Dict[str, int]],
    record_csv_path: Path,
    metric_map: Dict[str, str],
    report_data: List[Dict[str, Any]],
    max_year: Optional[int] = None,
    filter_year: Optional[int] = None,
    filter_league: Optional[str] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    1つの計算済みCSVを処理してランキングJSONを生成
    
    @param max_year: 最大年度（この年度以下のみ処理、Noneの場合は制限なし）
    @returns: (成功した場合True, レポートエントリ)
    """
    filename = csv_path.name
    parsed_info = parse_batting_filename(filename)
    
    if not parsed_info:
        print(f"⚠️  ファイル名からyear/league_keyを抽出できません: {filename}")
        report_data.append({
            "year": None,
            "league": None,
            "csv_filename": filename,
            "status": "ERROR",
            "error": "year/league_key抽出失敗"
        })
        return False, {}
    
    year = parsed_info["year"]
    league_key = parsed_info["league_key"]
    
    # league_keyからleagueを抽出（PRE_spring -> PRE）
    if league_key.startswith("PRE_"):
        league = "PRE"
        season_info = league_key.replace("PRE_", "")  # "spring" or "fall"
    else:
        league = league_key
        season_info = None
    
    # season_codeを生成（PRE春秋の場合のみ）
    season_code = None
    if league == "PRE" and season_info:
        if season_info == "spring":
            season_code = f"{year}s"
        elif season_info == "fall":
            season_code = f"{year}f"
    
    # 規定ルールを取得
    qualifying_rule = get_qualifying_rule(year, league, season_code)
    if qualifying_rule:
        basis_str = qualifying_rule["basis"].value if isinstance(qualifying_rule["basis"], QualifyingBasis) else str(qualifying_rule["basis"])
        print(f"   📋 規定ルール: basis={basis_str}, rounding={qualifying_rule['rounding_mode']}, "
              f"min_games={qualifying_rule.get('min_player_games')}, special={qualifying_rule.get('special_measures', False)}")
    else:
        print(f"   ⚠️  規定ルールが見つかりません（1945年など）")
    
    # max-yearフィルタチェック
    if should_skip_by_max_year(year, max_year):
        print(f"🚫 SKIP by max-year: {year} > {max_year}")
        report_data.append({
            "year": year,
            "league": league,
            "csv_filename": filename,
            "status": "SKIPPED",
            "error": f"SKIP by max-year: {year} > {max_year}"
        })
        return False, {}
    
    # 2025年の場合は絶対に処理しない（安全チェック）
    # ただし、--year / --league でスポット検証時はスキップ
    if year >= 2025 and (filter_year is None and filter_league is None):
        print(f"🚫 SKIP: 2025年以降は処理しません（year={year}）")
        report_data.append({
            "year": year,
            "league": league,
            "csv_filename": filename,
            "status": "SKIPPED",
            "error": f"SKIP: 2025年以降は処理しません（year={year}）"
        })
        return False, {}
    
    print(f"\n{'='*60}")
    print(f"📄 処理中: {filename}")
    season_info_str = ""
    if season_info:
        season_info_str = f", シーズン: {season_info}"
    print(f"   年度: {year}, リーグ: {league}, リーグキー: {league_key}{season_info_str}")
    
    # CSVを読み込む
    try:
        batting_data = load_csv_with_encoding(str(csv_path))
        print(f"   ✅ CSV読み込み完了: {len(batting_data)}件")
        
        # 列名の正規化マッピングを作成
        if batting_data:
            sample_row = batting_data[0]
            csv_columns = list(sample_row.keys())
            normalized_columns = {}
            for orig_col in csv_columns:
                norm_col = normalize_name(orig_col)
                if norm_col not in normalized_columns:
                    normalized_columns[norm_col] = orig_col
            print(f"   ✅ 列名正規化マッピング作成: {len(normalized_columns)}件")
            
            # CSV列名の代表30件を表示
            print(f"   📋 CSV列名（代表30件）: {', '.join(csv_columns[:30])}{'...' if len(csv_columns) > 30 else ''}")
        else:
            csv_columns = []
            normalized_columns = {}
    except Exception as e:
        print(f"   ❌ CSV読み込みエラー: {e}")
        report_data.append({
            "year": year,
            "league": league,
            "csv_filename": filename,
            "status": "ERROR",
            "error": f"CSV読み込みエラー: {e}"
        })
        return False, {}
    
    # season_codeを生成（PRE春秋の場合のみ）
    season_code = None
    if league == "PRE" and season_info:
        if season_info == "spring":
            season_code = f"{year}s"
        elif season_info == "fall":
            season_code = f"{year}f"
    
    # 規定ルールを取得
    qualifying_rule = get_qualifying_rule(year, league, season_code)
    if qualifying_rule:
        basis_str = qualifying_rule["basis"].value if isinstance(qualifying_rule["basis"], QualifyingBasis) else str(qualifying_rule["basis"])
        print(f"   📋 規定ルール: basis={basis_str}, rounding={qualifying_rule['rounding_mode']}, "
              f"min_games={qualifying_rule.get('min_player_games')}, special={qualifying_rule.get('special_measures', False)}")
    else:
        print(f"   ⚠️  規定ルールが見つかりません（1945年など）")
    
    # 規定打席を計算
    min_pa, team_games, source = calculate_min_pa_from_games_map(year, league, games_map, batting_data)
    
    # AB_TEAM_GROUP の場合のみ、チームごとのログを出力（規定ルール取得直後、各チーム1回のみ）
    if qualifying_rule and qualifying_rule["basis"] == QualifyingBasis.AB_TEAM_GROUP:
        # チーム一覧を取得（CSVから）し、正規化する
        teams_in_data = set()
        team_normalized_map = {}  # raw_team -> normalized_team のマッピング
        for row in batting_data:
            raw_team = row.get("Team") or row.get("team") or row.get("チーム") or ""
            if raw_team:
                normalized_team = normalize_team_name(raw_team)
                teams_in_data.add(normalized_team)
                team_normalized_map[normalized_team] = raw_team  # ログ用に元の名前も保持
        
        # 各チームのthresholdを計算してログ出力（正規化後のチーム名を使用）
        rounding_mode = qualifying_rule.get("rounding_mode", "round_half_up")
        for team_name_normalized in sorted(teams_in_data):
            try:
                threshold = calc_qual_threshold(qualifying_rule, team_games, team_name=team_name_normalized)
                if threshold is None:
                    print(f"   [QUAL][SKIP] year={year} league={league} team={team_name_normalized} reason=threshold is None (team_name missing)")
                else:
                    print(f"   [QUAL] year={year} league={league} team={team_name_normalized} team_games={team_games} basis={basis_str} threshold={threshold} rounding={rounding_mode} rule={basis_str}")
            except Exception as e:
                print(f"   [QUAL][SKIP] year={year} league={league} team={team_name_normalized} reason=exception: {e}")
    source_label = {
        "games_map": "games_map",
        "fallback_max_games": "fallback_max_games",
        "default": "default"
    }.get(source, source)
    print(f"   📊 試合数: {team_games}, 規定打席: {min_pa} (source: {source_label})")
    
    # 出力ディレクトリ（2025年以降は絶対に書き込まない）
    # ただし、--year / --league でスポット検証時はスキップ
    if year >= 2025 and (filter_year is None and filter_league is None):
        print(f"   🚫 エラー: 2025年以降のランキングJSONは生成しません（year={year}）")
        report_data.append({
            "year": year,
            "league": league,
            "csv_filename": filename,
            "status": "ERROR",
            "error": f"2025年以降のランキングJSONは生成しません（year={year}）"
        })
        return False, {}
    
    # league_keyを使用して出力パスを生成: {year}/{league_key}/
    output_dir = output_base_dir / str(year) / league_key
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 指標リストを取得
    try:
        metrics = extract_metrics_from_record_csv(str(record_csv_path))

        # ★ ADD: BB/K を必ず含める（CSV列名が BB/K のため）
        if "BB/K" not in metrics:
            metrics.append("BB/K")

        print(f"   ✅ 指標リスト取得: {len(metrics)}件")

    except Exception as e:
        print(f"   ❌ 指標リスト取得エラー: {e}")
        report_data.append({
            "year": year,
            "league": league,
            "csv_filename": filename,
            "status": "ERROR",
            "error": f"指標リスト取得エラー: {e}"
        })
        return False, {}
    
    # 各指標のランキングを生成（規定あり版、規定なし版、規定到達者版の3種類）
    success_count = 0
    failed_metrics = []
    
    # qualified生成状況のカウンタ
    qualified_written = 0
    qualified_skipped_no_rule = 0
    qualified_failed = 0
    
    for metric in metrics:
        file_metric = sanitize_filename(metric)
        
        # 規定あり版（既存）
        output_path = output_dir / f"{file_metric}.json"
        try:
            success, error_reason = generate_ranking_for_metric(
                batting_data,
                metric,
                str(output_path),
                top_n=100,
                min_pa=min_pa,
                metric_map=metric_map,
                normalized_columns=normalized_columns,
                csv_columns=csv_columns
            )
            if success:
                success_count += 1
            else:
                print(f"   ⚠️  {metric} → 生成失敗: {error_reason}")
                failed_metrics.append(f"{metric}({error_reason})")
        except Exception as e:
            print(f"   ❌ {metric} → 例外: {e}")
            import traceback
            traceback.print_exc()
            failed_metrics.append(f"{metric}(例外:{str(e)[:50]})")
        
        # 規定なし版（既存）
        output_path_all = output_dir / f"{file_metric}_all.json"
        try:
            success_all, error_reason_all = generate_ranking_for_metric(
                batting_data,
                metric,
                str(output_path_all),
                top_n=100,
                min_pa=0,
                metric_map=metric_map,
                normalized_columns=normalized_columns,
                csv_columns=csv_columns
            )
            if not success_all:
                print(f"   ⚠️  {metric}_all → 生成失敗: {error_reason_all}")
        except Exception as e:
            print(f"   ❌ {metric}_all → 例外: {e}")
            import traceback
            traceback.print_exc()
        
        # 規定到達者版（新規追加）
        # 率系指標のみ対象
        if metric in METRICS_REQUIRE_QUALIFYING_PA_BY_NAME:
            if qualifying_rule is None:
                print(f"   ⚠️  {metric}__qualified → スキップ（規定ルールなし）")
                qualified_skipped_no_rule += 1
            else:
                output_path_qualified = output_dir / f"{file_metric}__qualified.json"
                try:
                    success_qualified = generate_qualified_ranking_for_metric(
                        batting_data,
                        metric,
                        str(output_path_qualified),
                        qualifying_rule,
                        year,
                        league,
                        team_games,
                        top_n=100,
                        metric_map=metric_map,
                        normalized_columns=normalized_columns,
                        csv_columns=csv_columns
                    )
                    if success_qualified:
                        print(f"   ✅ {metric}__qualified → 生成成功")
                        qualified_written += 1
                    else:
                        print(f"   ⚠️  {metric}__qualified → 生成失敗（規定到達者なし）")
                        qualified_failed += 1
                except Exception as e:
                    print(f"   ❌ {metric}__qualified → 例外: {e}")
                    import traceback
                    traceback.print_exc()
                    qualified_failed += 1
    
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
        "year": year,
        "league": league,
        "csv_filename": filename,
        "team_games_source": source_label,
        "team_games": team_games,
        "min_pa_qual": min_pa,
        "files_expected": expected_files,
        "files_written": actual_files,
        "status": status,
        "failed_metrics": failed_metrics,
        "missing_files": missing_files[:10] if len(missing_files) > 10 else missing_files,
        "qualified_written": qualified_written,
        "qualified_skipped_no_rule": qualified_skipped_no_rule,
        "qualified_failed": qualified_failed
    }
    report_data.append(report_entry)
    
    if failed_metrics:
        print(f"   ⚠️  失敗した指標: {', '.join(failed_metrics[:5])}{'...' if len(failed_metrics) > 5 else ''}")
    if missing_files:
        print(f"   ⚠️  欠損ファイル: {len(missing_files)}件")
    
    return True, report_entry


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='計算済みCSVからランキングJSONを一括生成')
    parser.add_argument(
        '--input_dir',
        type=str,
        default='_data/master_csv_calculated',
        help='入力ディレクトリ（デフォルト: _data/master_csv_calculated）'
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
        '--exclude',
        type=str,
        default='',
        help='除外パターン（デフォルト: 空（除外なし））'
    )
    parser.add_argument(
        '--max-year',
        type=int,
        help='最大年度（この年度以下のみ処理、例: --max-year 2024）'
    )
    parser.add_argument(
        '--year',
        type=int,
        help='単年指定（この年のみ処理、例: --year 1952）'
    )
    parser.add_argument(
        '--league',
        type=str,
        choices=['PRE', 'CL', 'PL'],
        help='リーグ指定（このリーグのみ処理、例: --league PL）'
    )
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    input_dir = project_root / args.input_dir
    output_base_dir = project_root / args.out_dir
    games_map_path = project_root / args.games_map
    
    print(f"📁 プロジェクトルート: {project_root}")
    print(f"📁 入力ディレクトリ: {input_dir}")
    print(f"📁 出力ディレクトリ: {output_base_dir}")
    print(f"📁 試合数マップ: {games_map_path}")
    
    # 除外パターンをパース
    exclude_patterns = parse_exclude_pattern(args.exclude)
    if exclude_patterns:
        print(f"🚫 除外パターン: {exclude_patterns}")
    
    # max-yearの表示
    if args.max_year:
        print(f"📅 最大年度フィルタ: {args.max_year}年以下のみ処理")
        # 2025年以降を除外パターンに追加（安全のため）
        if 2025 not in [p[0] for p in exclude_patterns]:
            exclude_patterns.append((2025, 'PL'))
            exclude_patterns.append((2025, 'CL'))
            print(f"🚫 2025年以降を自動除外: {[(2025, 'PL'), (2025, 'CL')]}")
    
    # 入力ディレクトリの確認
    if not input_dir.exists():
        print(f"❌ エラー: 入力ディレクトリが存在しません: {input_dir}")
        return 1
    
    # 試合数マップを読み込む（オプション）
    games_map = {}
    if games_map_path.exists():
        try:
            with open(games_map_path, 'r', encoding='utf-8') as f:
                games_map = json.load(f)
            print(f"✅ 試合数マップ読み込み: {len(games_map)}件")
        except Exception as e:
            print(f"⚠️  試合数マップの読み込みに失敗: {e}（フォールバックを使用）")
    else:
        print(f"⚠️  試合数マップが見つかりません: {games_map_path}（フォールバックを使用）")
    
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
    
    # metric_mapを読み込む
    try:
        metric_map = load_metric_map(project_root)
        print(f"✅ metric_map.json: {len(metric_map)}件")
    except Exception as e:
        print(f"⚠️  metric_map.jsonの読み込みに失敗: {e}")
        metric_map = {}
    
    # CSVファイルを列挙
    csv_files = []
    skipped_by_filter = []
    
    # フィルタリング情報をログ出力
    filter_year = args.year
    filter_league = args.league
    if filter_year is not None or filter_league is not None:
        print(f"🔍 FILTER year={filter_year}, league={filter_league}")
    
    for csv_path in input_dir.glob('batting_*_*_from_master.csv'):
        parsed = parse_year_and_league_from_filename(csv_path.name)
        if parsed:
            year, league = parsed
            
            # --year フィルタ
            if filter_year is not None:
                if year != filter_year:
                    skipped_by_filter.append((csv_path, year, league, f"SKIP by --year filter: {year} != {filter_year}"))
                    continue
            
            # --league フィルタ
            if filter_league is not None:
                parsed_info = parse_batting_filename(csv_path.name)
                if parsed_info:
                    file_league_key = parsed_info["league_key"]
                    if file_league_key.startswith("PRE_"):
                        file_league = "PRE"
                    else:
                        file_league = file_league_key
                    
                    if file_league != filter_league:
                        skipped_by_filter.append((csv_path, year, league, f"SKIP by --league filter: {file_league} != {filter_league}"))
                        continue
            
            # 除外パターンチェック
            if (year, league) in exclude_patterns:
                skipped_by_filter.append((csv_path, year, league, "除外パターン"))
                continue
            # max-yearフィルタチェック
            if should_skip_by_max_year(year, args.max_year):
                skipped_by_filter.append((csv_path, year, league, f"SKIP by max-year: {year} > {args.max_year}"))
                continue
            # 2025年以降は絶対に処理しない（安全チェック）
            # ただし、--year / --league でスポット検証時はスキップ
            if year >= 2025 and (filter_year is None and filter_league is None):
                skipped_by_filter.append((csv_path, year, league, f"SKIP: 2025年以降は処理しません（year={year}）"))
                continue
            csv_files.append(csv_path)
    
    if skipped_by_filter:
        print(f"\n🚫 フィルタで除外されたCSVファイル: {len(skipped_by_filter)}件")
        for csv_path, year, league, reason in skipped_by_filter[:10]:
            print(f"   - {csv_path.name} (年度: {year}, リーグ: {league}): {reason}")
        if len(skipped_by_filter) > 10:
            print(f"   ... 他 {len(skipped_by_filter) - 10}件")
    
    print(f"\n📋 処理対象CSVファイル: {len(csv_files)}件")
    
    if not csv_files:
        print(f"❌ エラー: CSVファイルが見つかりません")
        return 1
    
    # レポート用データ
    report_data: List[Dict[str, Any]] = []
    
    # 各CSVファイルを処理
    success_count = 0
    error_count = 0
    
    for csv_path in sorted(csv_files):
        success, report_entry = process_calculated_csv(
            csv_path,
            output_base_dir,
            games_map,
            record_csv_path,
            metric_map,
            report_data,
            args.max_year,
            filter_year,
            filter_league
        )
        if success:
            success_count += 1
        else:
            error_count += 1
    
    # レポートを生成
    report_dir = project_root / 'output' / 'reports'
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / 'ranking_generation_from_calculated_report.md'
    
    # ユニークな(year, league)の数を計算
    unique_seasons = set()
    total_files_written = 0
    total_files_expected = 0
    missing_seasons = []
    
    # qualified生成状況の集計
    total_qualified_written = 0
    total_qualified_skipped_no_rule = 0
    total_qualified_failed = 0
    
    for entry in report_data:
        if entry.get("year") and entry.get("league"):
            unique_seasons.add((entry["year"], entry["league"]))
        total_files_written += entry.get("files_written", 0)
        total_files_expected += entry.get("files_expected", 0)
        total_qualified_written += entry.get("qualified_written", 0)
        total_qualified_skipped_no_rule += entry.get("qualified_skipped_no_rule", 0)
        total_qualified_failed += entry.get("qualified_failed", 0)
        if entry.get("status") in ["MISSING_FILES", "ERROR"]:
            missing_seasons.append(entry)
    
    # レポートを生成
    report_lines = [
        "# ランキング生成レポート（計算済みCSVから）",
        "",
        f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## サマリー",
        "",
        f"- CSVファイル数: {len(csv_files)}",
        f"- 処理成功: {success_count}",
        f"- 処理失敗: {error_count}",
        f"- 生成した(year, league)のユニーク件数: {len(unique_seasons)}",
        f"- 生成ファイル総数: {total_files_written}/{total_files_expected}",
        f"- 生成ディレクトリ: {output_base_dir}",
        f"- qualified生成ファイル数: {total_qualified_written}",
        f"- qualifiedスキップ件数(規定ルールなし): {total_qualified_skipped_no_rule}",
        f"- qualified生成失敗件数(規定到達者なし/例外): {total_qualified_failed}",
        "",
        "## シーズンごとの詳細",
        "",
        "| year | league | csv_filename | team_games_source | team_games | min_pa_qual | files_expected | files_written | status |",
        "|------|--------|--------------|-------------------|------------|-------------|----------------|---------------|--------|",
    ]
    
    # テーブル行を追加
    for entry in sorted(report_data, key=lambda x: (x.get("year") or 0, x.get("league") or "")):
        year = entry.get("year", "N/A")
        league = entry.get("league", "N/A")
        csv_filename = entry.get("csv_filename", "N/A")
        team_games_source = entry.get("team_games_source", "N/A")
        team_games = entry.get("team_games", "N/A")
        min_pa_qual = entry.get("min_pa_qual", "N/A")
        files_expected = entry.get("files_expected", 0)
        files_written = entry.get("files_written", 0)
        status = entry.get("status", "UNKNOWN")
        
        report_lines.append(
            f"| {year} | {league} | {csv_filename} | {team_games_source} | "
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
            year = entry.get("year", "N/A")
            league = entry.get("league", "N/A")
            status = entry.get("status", "UNKNOWN")
            missing_files = entry.get("missing_files", [])
            failed_metrics = entry.get("failed_metrics", [])
            error = entry.get("error")
            
            report_lines.append(f"### {year} / {league} ({status})")
            if error:
                report_lines.append(f"- エラー: {error}")
            if failed_metrics:
                report_lines.append(f"- 失敗した指標: {', '.join(failed_metrics)}")
            if missing_files:
                report_lines.append(f"- 欠損ファイル（先頭10件）: {', '.join(missing_files)}")
            report_lines.append("")
    
    # 完了判定: qualifiedファイルの件数と空ファイル数を計算
    try:
        qualified_files = 0
        zero_files = 0
        
        # 出力ディレクトリ配下を再帰走査
        for qualified_path in output_base_dir.rglob("*__qualified.json"):
            qualified_files += 1
            try:
                # ファイル内容を読み込んで空かどうか判定
                with open(qualified_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    # 空、空配列、空オブジェクトを判定
                    if content == "" or content == "[]" or content == "{}":
                        zero_files += 1
            except Exception as e:
                # ファイル読み込みエラーは無視（カウントには含めない）
                pass
        
        report_lines.append(f"COMPLETION_CHECK qualified_files={qualified_files} zero_files={zero_files}")
    except Exception as e:
        report_lines.append(f"COMPLETION_CHECK failed: {str(e)}")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"\n{'='*60}")
    print(f"✅ 処理完了: 成功={success_count}, 失敗={error_count}")
    print(f"📄 レポート: {report_path}")
    print(f"")
    print(f"qualified生成ファイル数: {total_qualified_written}")
    print(f"qualifiedスキップ件数(規定ルールなし): {total_qualified_skipped_no_rule}")
    print(f"qualified生成失敗件数(規定到達者なし/例外): {total_qualified_failed}")
    
    if missing_seasons:
        print(f"⚠️  警告: {len(missing_seasons)}件のシーズンで欠損があります。レポートを確認してください。")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())


