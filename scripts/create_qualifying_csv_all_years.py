#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_qualifying_csv_all_years.py

全年度・全リーグの計算済みCSVから、規定打席（または規定打数）到達者のみを抽出した
「規定打席到達版CSV」を生成する（Phase 1）。

入力: _data/master_csv_calculated/batting_YYYY_LEAGUE_from_master.csv 等
出力: _data/master_csv_calculated/batting_YYYY_LEAGUE_qualifying.csv 等

規定ルール: scripts/qualifying/qualifying_rules.py および games_map を使用。
1951/1952年PLはチーム別しきい値をスクリプト内のマッピングで対応。
"""

import csv
import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# プロジェクトルート・スクリプトパス
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR.parent))

try:
    from qualifying.qualifying_rules import (
        get_qualifying_rule,
        calc_qual_threshold,
        is_player_qualified,
        QualifyingBasis,
    )
except ImportError:
    get_qualifying_rule = None
    calc_qual_threshold = None
    is_player_qualified = None
    QualifyingBasis = None

try:
    from lib.filename_parser import parse_batting_filename
except ImportError:
    parse_batting_filename = None

# 1951年PL: 現在のチーム名 -> 規定打数（AB）。qualifyingPA.ts に準拠。
PL_1951_TEAM_AB: Dict[str, int] = {
    "福岡ソフトバンクホークス": 260,
    "埼玉西武ライオンズ": 262,
    "千葉ロッテマリーンズ": 275,
    "オリックス・バファローズ": 240,
    "北海道日本ハムファイターズ": 255,
    "近鉄バファローズ": 245,
}
PL_1951_DEFAULT_AB = 252

# 1952年PL: 現在のチーム名 -> 規定打数（AB）。上位4球団300、下位3球団270。
PL_1952_TEAM_AB: Dict[str, int] = {
    "福岡ソフトバンクホークス": 300,
    "千葉ロッテマリーンズ": 300,
    "埼玉西武ライオンズ": 300,
    "オリックス・バファローズ": 270,
    "北海道日本ハムファイターズ": 270,
    "近鉄バファローズ": 270,
}
PL_1952_DEFAULT_AB = 300


def load_csv_with_encoding(csv_path: Path) -> List[Dict[str, Any]]:
    """CSVを読み込む（文字コード自動判定）"""
    encodings = ["utf-8-sig", "utf-8", "shift_jis", "cp932"]
    for enc in encodings:
        try:
            with open(csv_path, "r", encoding=enc) as f:
                return list(csv.DictReader(f))
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    raise ValueError(f"Failed to read {csv_path}")


def get_pa_value(row: Dict[str, Any]) -> Optional[int]:
    """行からPA（打席）を取得"""
    for col in ("PA", "pa", "打席"):
        if col in row and row[col] not in (None, ""):
            try:
                return int(float(str(row[col]).strip()))
            except (ValueError, TypeError):
                pass
    return None


def get_ab_value(row: Dict[str, Any]) -> Optional[int]:
    """行からAB（打数）を取得"""
    for col in ("AB", "ab", "打数"):
        if col in row and row[col] not in (None, ""):
            try:
                return int(float(str(row[col]).strip()))
            except (ValueError, TypeError):
                pass
    return None


def get_games_value(row: Dict[str, Any]) -> Optional[int]:
    """行からG（試合）を取得"""
    for col in ("G", "games", "試合"):
        if col in row and row[col] not in (None, ""):
            try:
                return int(float(str(row[col]).strip()))
            except (ValueError, TypeError):
                pass
    return None


def get_team_value(row: Dict[str, Any]) -> str:
    """行からチーム名を取得"""
    return (
        (row.get("Team") or row.get("team") or row.get("チーム")) or ""
    ).strip()


def row_for_qualified_check(row: Dict[str, Any]) -> Dict[str, Any]:
    """is_player_qualified 用に AB, PA, G を揃えた辞書を返す"""
    pa = get_pa_value(row)
    ab = get_ab_value(row)
    g = get_games_value(row)
    r = dict(row)
    if pa is not None:
        r["PA"] = r["pa"] = pa
    if ab is not None:
        r["AB"] = r["ab"] = ab
    if g is not None:
        r["G"] = r["games"] = g
    return r


def load_games_map(project_root: Path) -> Dict[str, Dict[str, int]]:
    """config/games_per_team_by_season.json を読み込む"""
    path = project_root / "config" / "games_per_team_by_season.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_team_games_from_csv(rows: List[Dict[str, Any]]) -> int:
    """CSVのG列の最大値からリーグ試合数を推定"""
    best = 0
    for row in rows:
        g = get_games_value(row)
        if g is not None and g > best:
            best = g
    return best if best > 0 else 143


def get_threshold_for_row(
    year: int,
    league: str,
    team: str,
    qualifying_rule: Dict[str, Any],
    team_games: int,
    season_code: Optional[str],
) -> Optional[int]:
    """行（チーム）ごとの規定しきい値を返す。チーム別ルールはここで処理。"""
    basis = qualifying_rule.get("basis")
    if basis is None:
        return None

    # 1952年PL: チーム別AB（現在のチーム名マッピング）
    if year == 1952 and league == "PL":
        return PL_1952_TEAM_AB.get(team, PL_1952_DEFAULT_AB)

    # 1951年PL: チーム別AB
    if year == 1951 and league == "PL":
        return PL_1951_TEAM_AB.get(team, PL_1951_DEFAULT_AB)

    # その他: calc_qual_threshold を使用（チーム名はAB_TEAM_GROUP時のみ必要・旧名なので渡さず league 単位で計算）
    try:
        th = calc_qual_threshold(
            qualifying_rule,
            team_games,
            team_name=None,
            rounding=qualifying_rule.get("rounding_mode"),
        )
        return th
    except Exception:
        return None


def filter_qualifying_rows(
    rows: List[Dict[str, Any]],
    year: int,
    league: str,
    season_code: Optional[str],
    qualifying_rule: Dict[str, Any],
    games_map: Dict[str, Dict[str, int]],
) -> List[Dict[str, Any]]:
    """規定到達者の行のみに絞る"""
    team_games = (
        games_map.get(str(year), {}).get(league)
        or get_team_games_from_csv(rows)
    )
    basis = qualifying_rule.get("basis")
    min_player_games = qualifying_rule.get("min_player_games")

    # チーム別しきい値が必要な年度は行ごとにしきい値を求める
    result = []
    for row in rows:
        team = get_team_value(row)
        th = get_threshold_for_row(
            year, league, team, qualifying_rule, team_games, season_code
        )
        if th is None:
            continue
        row_check = row_for_qualified_check(row)
        if is_player_qualified(row_check, th, basis, min_player_games):
            result.append(row)
    return result


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: Optional[List[str]] = None) -> None:
    """CSVを書き出す"""
    if not rows:
        return
    fn = fieldnames or list(rows[0].keys())
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fn, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def process_one_file(
    input_path: Path,
    output_path: Path,
    games_map: Dict[str, Dict[str, int]],
    dry_run: bool,
    verbose_threshold: bool = False,
) -> Tuple[int, int]:
    """1ファイル処理。戻り値: (元行数, 規定到達者数)。"""
    parsed = parse_batting_filename(input_path.name) if parse_batting_filename else None
    if not parsed:
        return -1, -1

    year = parsed["year"]
    league = parsed["league"]
    league_key = parsed.get("league_key", league)
    season_tag = parsed.get("season_tag")
    season_code = None
    if league == "PRE" and season_tag:
        season_code = f"{year}s" if season_tag == "spring" else f"{year}f"

    if get_qualifying_rule is None:
        return -1, -1

    rule = get_qualifying_rule(year, league, season_code)
    if rule is None:
        return -1, -1

    rows = load_csv_with_encoding(input_path)
    if not rows:
        return 0, 0

    qualified = filter_qualifying_rows(
        rows, year, league, season_code, rule, games_map
    )
    if verbose_threshold:
        team_games = (
            games_map.get(str(year), {}).get(league)
            or get_team_games_from_csv(rows)
        )
        th = get_threshold_for_row(
            year, league, "", rule, team_games, season_code
        )
        basis_str = rule.get("basis")
        if hasattr(basis_str, "value"):
            basis_str = basis_str.value
        print(f"   [threshold] year={year} league={league_key or league} team_games={team_games} threshold={th} basis={basis_str} qualifying={len(qualified)}")
    if not dry_run and qualified:
        write_csv(output_path, qualified, fieldnames=list(rows[0].keys()))
    return len(rows), len(qualified)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="全年度・規定打席到達版CSV生成（Phase 1）")
    parser.add_argument("--input-dir", type=str, default=None,
                        help="入力ディレクトリ（デフォルト: _data/master_csv_calculated）")
    parser.add_argument("--year", type=int, default=None, help="対象年度（省略時は全年度）")
    parser.add_argument("--league", type=str, default=None, help="対象リーグ（省略時は全リーグ）")
    parser.add_argument("--dry-run", action="store_true", help="書き込まず対象と件数のみ表示")
    parser.add_argument("--verbose-threshold", action="store_true",
                        help="規定しきい値（minPA等）と規定到達者数をログに出力（検証用）")
    args = parser.parse_args()

    input_dir = Path(args.input_dir) if args.input_dir else PROJECT_ROOT / "_data" / "master_csv_calculated"
    if not input_dir.is_absolute():
        input_dir = PROJECT_ROOT / input_dir

    if not input_dir.exists():
        print(f"[ERROR] 入力ディレクトリがありません: {input_dir}")
        return 1

    games_map = load_games_map(PROJECT_ROOT)
    if games_map:
        print(f"[OK] 試合数マップ読み込み: {len(games_map)}シーズン")
    else:
        print("[WARN] 試合数マップなし（CSVのG列から推定）")

    # batting_*_from_master.csv のみ（qualifying は除外）
    pattern = re.compile(r"^batting_\d{4}_(PL|CL|PRE)(?:_(?:spring|fall))?_from_master\.csv$", re.I)
    files = sorted(f for f in input_dir.iterdir() if f.is_file() and pattern.match(f.name))

    if args.year is not None:
        files = [f for f in files if parse_batting_filename and parse_batting_filename(f.name) and parse_batting_filename(f.name)["year"] == args.year]
    if args.league:
        league_upper = args.league.upper()
        files = [f for f in files if parse_batting_filename and parse_batting_filename(f.name) and parse_batting_filename(f.name)["league"] == league_upper]

    if not files:
        print("対象CSVがありません")
        return 0

    print(f"対象ファイル数: {len(files)}")
    if args.dry_run:
        print("（dry-run: 書き込みしません）")

    total_before = 0
    total_after = 0
    for f in files:
        # 出力名: batting_YYYY_LEAGUE_qualifying.csv 等
        out_name = f.name.replace("_from_master.csv", "_qualifying.csv")
        if out_name == f.name:
            continue
        out_path = input_dir / out_name
        n_before, n_after = process_one_file(
            f, out_path, games_map, args.dry_run,
            verbose_threshold=getattr(args, "verbose_threshold", False),
        )
        if n_before < 0:
            print(f"  スキップ: {f.name}（パースまたは規定ルールなし）")
            continue
        total_before += n_before
        total_after += n_after
        print(f"  {f.name}: {n_before}件 → {n_after}件（規定到達） → {out_path.name}")
        if args.dry_run:
            pass  # 書き込み済みはしない

    print(f"\n合計: {total_before}件 → {total_after}件（規定打席到達者のみ）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
