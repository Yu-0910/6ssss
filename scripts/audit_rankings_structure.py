#!/usr/bin/env python3
"""
audit_rankings_structure.py

public/data/rankings/{YEAR}/{LEAGUE}/ に対して、
metric_map.json の 36指標 × (通常 + _all) の JSON が揃っているか監査する。

重要:
- 期待するファイル名は必ず sanitize_filename(metric_display) を通す
  例: "BB/K" -> "BB-K.json"（Windows/パス仕様対策）
- 1936-1949 は PRE 系のみ（PRE_spring / PRE_fall など "PRE" で始まるフォルダを監査対象）
- 1950-2024 は CL / PL を監査対象（存在する場合に監査）
- スキーマ参照: 2025/PL/OPS.json（存在すれば keys を表示）

出力:
- output/reports/audit_rankings_structure.md
- output/reports/audit_rankings_missing_metrics.csv
"""

import argparse
import csv
import json
import sys
import io
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any

# WindowsでのUnicode出力対応
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def _fallback_sanitize_filename(metric: str) -> str:
    """
    最低限のファイル名サニタイズ（Import失敗時のフォールバック）
    ※本来は build_rankings_2025_PL_full.sanitize_filename を使う
    """
    if metric is None:
        return ""
    s = str(metric).strip()
    # Windows/パスに不適: / \ : * ? " < > |
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        s = s.replace(ch, "-")
    # 連続ハイフン整理
    while "--" in s:
        s = s.replace("--", "-")
    return s


# sanitize_filename を生成側と同じものに合わせる（あればそれを使う）
sanitize_filename = _fallback_sanitize_filename
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from build_rankings_2025_PL_full import sanitize_filename as _sanitize  # type: ignore
    sanitize_filename = _sanitize
except Exception:
    # フォールバックのまま
    pass


def load_metric_map(metric_map_path: Path) -> Dict[str, str]:
    with open(metric_map_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("metric_map.json is not a dict")
    # display -> internal_key
    return {str(k): str(v) for k, v in data.items()}


def read_json_keys(json_path: Path) -> List[str]:
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if isinstance(obj, list) and obj and isinstance(obj[0], dict):
            return sorted(list(obj[0].keys()))
        if isinstance(obj, dict):
            return sorted(list(obj.keys()))
        return []
    except Exception:
        return []


def list_year_dirs(rankings_dir: Path) -> List[Path]:
    years = []
    for p in rankings_dir.iterdir():
        if p.is_dir() and p.name.isdigit():
            years.append(p)
    return sorted(years, key=lambda x: int(x.name))


def expected_league_dirs_for_year(year: int, year_dir: Path) -> List[Path]:
    """
    1936-1949: PRE 系（PRE, PRE_spring, PRE_fall 等）
    1950-2024: CL, PL（存在するものを監査）
    """
    if year <= 1949:
        return sorted([p for p in year_dir.iterdir() if p.is_dir() and p.name.upper().startswith("PRE")])
    else:
        leagues = []
        for name in ["CL", "PL"]:
            p = year_dir / name
            if p.exists() and p.is_dir():
                leagues.append(p)
        return leagues


def audit_one_league_dir(
    league_dir: Path,
    metric_display_names: List[str],
) -> Tuple[List[str], List[str]]:
    """
    returns:
      missing_display_metrics: 例 ["BB/K", "OPS"]
      missing_display_metrics_all: 例 ["BB/K_all", "OPS_all"]
    """
    missing_normal: List[str] = []
    missing_all: List[str] = []

    for metric_display in metric_display_names:
        file_metric = sanitize_filename(metric_display)

        p_json = league_dir / f"{file_metric}.json"
        p_all = league_dir / f"{file_metric}_all.json"

        if not p_json.exists():
            missing_normal.append(metric_display)
        if not p_all.exists():
            missing_all.append(f"{metric_display}_all")

    return missing_normal, missing_all


def write_missing_csv(out_csv: Path, rows: List[Dict[str, str]]) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["year", "league", "missing_metrics", "path"])
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_md_report(
    out_md: Path,
    metric_count: int,
    expected_files_per_league: int,
    schema_ref: Path,
    schema_keys: List[str],
    missing_rows: List[Dict[str, str]],
) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    lines.append("# Rankings Structure Audit")
    lines.append("")
    lines.append(f"- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- Metrics: {metric_count} (expected files per league-dir: {expected_files_per_league})")
    lines.append("")
    lines.append("## Schema Reference")
    lines.append("")
    lines.append(f"- Ref JSON: `{schema_ref}`")
    lines.append(f"- Keys: {schema_keys}")
    lines.append("")
    lines.append("## Missing Summary")
    lines.append("")
    if not missing_rows:
        lines.append("✅ No missing metrics files. (CSV is header-only)")
    else:
        lines.append(f"⚠️ Missing rows: {len(missing_rows)}")
        lines.append("")
        lines.append("| year | league | missing_metrics | path |")
        lines.append("|---:|:---:|:---|:---|")
        for r in missing_rows[:200]:  # 上限（md肥大防止）
            lines.append(f"| {r['year']} | {r['league']} | {r['missing_metrics']} | `{r['path']}` |")
        if len(missing_rows) > 200:
            lines.append("")
            lines.append(f"... truncated. Total rows: {len(missing_rows)}")

    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit rankings JSON structure under public/data/rankings")
    parser.add_argument("--rankings_dir", type=str, default="public/data/rankings", help="rankings root dir")
    parser.add_argument("--metric_map", type=str, default="config/metric_map.json", help="metric_map.json path")
    parser.add_argument(
        "--schema_ref",
        type=str,
        default="public/data/rankings/2025/PL/OPS.json",
        help="schema reference json for displaying keys (optional)",
    )
    parser.add_argument("--out_md", type=str, default="output/reports/audit_rankings_structure.md", help="md report")
    parser.add_argument(
        "--out_csv",
        type=str,
        default="output/reports/audit_rankings_missing_metrics.csv",
        help="missing csv report",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    rankings_dir = project_root / args.rankings_dir
    metric_map_path = project_root / args.metric_map
    schema_ref = project_root / args.schema_ref
    out_md = project_root / args.out_md
    out_csv = project_root / args.out_csv

    print(f"📁 rankings_dir: {rankings_dir}")
    print(f"📁 metric_map:   {metric_map_path}")
    print("🔍 監査開始...")

    if not rankings_dir.exists():
        print(f"❌ rankings_dir not found: {rankings_dir}")
        return 1
    if not metric_map_path.exists():
        print(f"❌ metric_map.json not found: {metric_map_path}")
        return 1

    metric_map = load_metric_map(metric_map_path)
    metric_display_names = list(metric_map.keys())

    print(f"✅ metric_map.json: {len(metric_map)}件")
    print(f"✅ 指標リスト: {len(metric_display_names)}件（期待ファイル数: {len(metric_display_names) * 2}件）")

    schema_keys = read_json_keys(schema_ref) if schema_ref.exists() else []
    if schema_keys:
        print(f"✅ 参照スキーマ（{schema_ref.relative_to(project_root)}）: {schema_keys}")
    else:
        print(f"⚠️ 参照スキーマが読めません（未存在 or 読み込み失敗）: {schema_ref}")

    missing_rows: List[Dict[str, str]] = []

    for year_dir in list_year_dirs(rankings_dir):
        year = int(year_dir.name)
        league_dirs = expected_league_dirs_for_year(year, year_dir)

        # PRE年なのにPREフォルダが無い場合はスキップ（監査対象なし）
        if year <= 1949 and not league_dirs:
            continue

        for league_dir in league_dirs:
            league_key = league_dir.name  # CL / PL / PRE_spring etc.
            missing_normal, missing_all = audit_one_league_dir(league_dir, metric_display_names)
            missing = missing_normal + missing_all
            if missing:
                missing_rows.append(
                    {
                        "year": str(year),
                        "league": league_key,
                        "missing_metrics": ", ".join(missing),
                        "path": str(league_dir),
                    }
                )

    print("📊 レポート生成中...")
    write_missing_csv(out_csv, missing_rows)
    write_md_report(
        out_md=out_md,
        metric_count=len(metric_display_names),
        expected_files_per_league=len(metric_display_names) * 2,
        schema_ref=schema_ref,
        schema_keys=schema_keys,
        missing_rows=missing_rows,
    )

    print(f"✅ メインレポート: {out_md}")
    print(f"✅ 不足指標CSV: {out_csv}")
    print("=" * 60)
    print("✅ 監査完了")
    print("=" * 60)

    # missing があれば終了コード 1（CI/自動化用）
    return 1 if missing_rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
