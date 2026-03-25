#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2025年新入団選手を報告書（2025_new_players_report.csv）に基づき
全員版 from_master CSV（非規定＝全選手用）に組み込む。

- 報告書の全選手について、現在の batting_2025_{CL|PL}_from_master.csv にいない者を
  バックアップから取得して追加。バックアップにいない場合は最小限の行を追加し、
  非規定（全員版）ランキングに名前が載るようにする。
"""

import csv
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# チーム名 → リーグ（CL=セ, PL=パ）
TEAM_TO_LEAGUE: Dict[str, str] = {}
for t in (
    '広島東洋カープ', '読売ジャイアンツ', '中日ドラゴンズ', '東京ヤクルトスワローズ',
    '横浜DeNAベイスターズ', '阪神タイガース',
):
    TEAM_TO_LEAGUE[t] = 'CL'
for t in (
    '千葉ロッテマリーンズ', '北海道日本ハムファイターズ', '埼玉西武ライオンズ',
    '東北楽天ゴールデンイーグルス', '福岡ソフトバンクホークス', 'オリックス・バファローズ',
):
    TEAM_TO_LEAGUE[t] = 'PL'

# バックアップ列名 → 現在CL列名（CLはnpb_batting形式のため変換が必要）
BACKUP_TO_CL = {
    '単打': '1B',
    '打率': 'AVG',
    '出塁率': 'OBP',
    '長打率': 'SLG',
}


def load_csv(path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    for enc in ('utf-8-sig', 'utf-8', 'shift_jis', 'cp932'):
        try:
            with open(path, 'r', encoding=enc) as f:
                r = csv.DictReader(f)
                header = list(r.fieldnames or [])
                rows = list(r)
                return (header, rows)
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    raise ValueError(f"Cannot read {path}")


def normalize_name(name: str) -> str:
    if not name:
        return ''
    n = (name or '').strip().replace('\u3000', ' ').replace('　', ' ')
    return re.sub(r'\s+', ' ', n)


def find_row(rows: List[Dict], name: str, team: str) -> Optional[Dict[str, Any]]:
    key_name = normalize_name(name)
    for r in rows:
        r_name = normalize_name(r.get('player_name_ja') or r.get('name') or '')
        r_team = (r.get('team') or r.get('Team') or '').strip()
        if r_name == key_name and r_team == team:
            return r
    # オスナ: バックアップは「オスナ」、報告書は「J.オスナ」
    if key_name == 'J.オスナ':
        for r in rows:
            r_name = normalize_name(r.get('player_name_ja') or '')
            if r_name == 'オスナ' and (r.get('team') or '').strip() == team:
                return r
    return None


def map_backup_to_cl_row(backup_row: Dict, current_header: List[str]) -> Dict[str, Any]:
    """バックアップ1行を現在のCL CSV形式に変換（CLはnpb_batting形式）。"""
    row = {}
    for col in current_header:
        if col in backup_row and backup_row[col] != '':
            row[col] = backup_row[col]
            continue
        src = BACKUP_TO_CL.get(col)
        if src and src in backup_row and backup_row[src] != '':
            row[col] = backup_row[src]
            continue
        if col == 'year':
            row[col] = 2025
        elif col == 'league':
            row[col] = 'CL'
        elif col == 'team':
            row[col] = backup_row.get('team', '')
        elif col == 'player_name_ja':
            row[col] = backup_row.get('player_name_ja', '')
        elif col == 'player_name_en':
            row[col] = backup_row.get('player_name_en', '')
        elif col == '1B':
            try:
                h = float(backup_row.get('H') or backup_row.get('安打') or 0)
                d2 = float(backup_row.get('2B') or backup_row.get('二塁打') or 0)
                d3 = float(backup_row.get('3B') or backup_row.get('三塁打') or 0)
                hr = float(backup_row.get('HR') or backup_row.get('本塁打') or 0)
                row[col] = int(h - d2 - d3 - hr) if h else ''
            except (TypeError, ValueError):
                row[col] = backup_row.get('単打', '')
        elif col == 'IOPS':
            try:
                iso = float(backup_row.get('IsoP') or 0)
                isod = float(backup_row.get('IsoD') or 0)
                row[col] = round(iso + isod, 4) if (iso or isod) else ''
            except (TypeError, ValueError):
                row[col] = ''
        else:
            row[col] = backup_row.get(col, '')
    return row


def make_minimal_row_cl(header: List[str], name_ja: str, name_en: str, team: str) -> Dict[str, Any]:
    """バックアップにいないCL選手用の最小行（非規定ランキングに名前を出すため）。"""
    row = {col: '' for col in header}
    row['year'] = 2025
    row['league'] = 'CL'
    row['team'] = team
    row['player_name_ja'] = name_ja
    row['player_name_en'] = name_en or ''
    for col in ('G', 'PA', 'AB', 'R', 'H', '2B', '3B', 'HR', 'TB', 'RBI', 'SB', 'CS', 'SH', 'SF', 'BB', 'IBB', 'HBP', 'SO', 'GDP'):
        if col in header:
            row[col] = 0
    for col in ('AVG', 'OBP', 'SLG', 'OPS', '1B', 'IsoP', 'IsoD', 'IOPS', 'BB%', 'K%', 'BB/K', 'BABIP', 'GPA', 'NOI', 'SecA', 'TA'):
        if col in header:
            row[col] = 0 if col in ('1B',) else 0.0
    return row


def make_minimal_row_pl(header: List[str], name_ja: str, name_en: str, team: str) -> Dict[str, Any]:
    """バックアップにいないPL選手用の最小行。"""
    row = {col: '' for col in header}
    row['year'] = 2025
    row['league'] = 'PL'
    row['team'] = team
    row['player_name_ja'] = name_ja
    row['player_name_en'] = name_en or ''
    for col in header:
        if col in row:
            continue
        if col in ('G', 'PA', 'AB', 'R', 'H', '2B', '3B', 'HR', 'TB', 'RBI', 'SB', 'CS', 'SH', 'SF', 'BB', 'IBB', 'HBP', 'SO', 'GDP'):
            row[col] = 0
        elif col in ('AVG', 'OBP', 'SLG', 'OPS', '打率', '出塁率', '長打率', 'IsoP', 'IsoD', 'BB%', 'K%', 'BB/K', 'RC', 'XR', 'BABIP', 'SecA', 'TA', 'NOI', 'GPA'):
            row[col] = 0.0
        elif col in ('安打', '本塁打', '打点', '試合', '打席', '打数', '単打', '二塁打', '三塁打', '得点', '四球', '敬遠', '死球', '三振', '塁打', '盗塁', '盗塁死', '犠打', '犠飛', '併殺打'):
            row[col] = 0
    return row


def process_league(
    league: str,
    report_players: List[Tuple[str, str, str]],
    calculated_dir: Path,
) -> int:
    """指定リーグの from_master に報告書で不足している選手を追加。戻り値は追加人数。"""
    backup_path = calculated_dir / '_backup_2025_from_master' / f'batting_2025_{league}_from_master.csv'
    current_path = calculated_dir / f'batting_2025_{league}_from_master.csv'

    if not current_path.exists():
        print(f"  WARN: 現在の{league} CSVがありません: {current_path.name}")
        return 0
    current_header, current_rows = load_csv(current_path)
    backup_header, backup_rows = [], []
    if backup_path.exists():
        backup_header, backup_rows = load_csv(backup_path)

    existing = set()
    for r in current_rows:
        name = normalize_name(r.get('player_name_ja') or r.get('name') or '')
        team = (r.get('team') or r.get('Team') or '').strip()
        if name and team:
            existing.add((name, team))
    # J.オスナ と オスナ を同一視
    for r in current_rows:
        name = (r.get('player_name_ja') or '').strip()
        if name == 'オスナ':
            team = (r.get('team') or '').strip()
            if team:
                existing.add(('J.オスナ', team))
                existing.add(('オスナ', team))

    added = 0
    for name_ja, team, name_en in report_players:
        key = (normalize_name(name_ja), team)
        if key in existing:
            continue
        backup_row = find_row(backup_rows, name_ja, team) if backup_rows else None
        if league == 'CL':
            if backup_row:
                new_row = map_backup_to_cl_row(backup_row, current_header)
            else:
                new_row = make_minimal_row_cl(current_header, name_ja, name_en, team)
                print(f"  [最小行] {name_ja} ({team}) — バックアップに成績なし")
        else:
            if backup_row:
                new_row = {c: backup_row.get(c, '') for c in current_header}
                new_row['year'] = 2025
                new_row['league'] = 'PL'
            else:
                new_row = make_minimal_row_pl(current_header, name_ja, name_en, team)
                print(f"  [最小行] {name_ja} ({team}) — バックアップに成績なし")
        current_rows.append(new_row)
        existing.add(key)
        added += 1
        print(f"  追加: {name_ja} ({team})")

    if added > 0:
        with open(current_path, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=current_header, extrasaction='ignore')
            w.writeheader()
            w.writerows(current_rows)
        print(f"  保存: {current_path.name} ({len(current_rows)}行, +{added}件)")
    return added


def main() -> int:
    report_path = PROJECT_ROOT / '_data' / 'reports' / '2025_new_players_report.csv'
    calculated_dir = PROJECT_ROOT / '_data' / 'master_csv_calculated'

    if not report_path.exists():
        print(f"ERROR: 報告書が見つかりません: {report_path}")
        return 1

    _, report_rows = load_csv(report_path)
    # (player_name_ja, team, player_name_en)
    report_players: List[Tuple[str, str, str]] = []
    for r in report_rows:
        name = (r.get('player_name_ja') or '').strip()
        team = (r.get('team') or r.get('Team') or '').strip()
        if not name or not team:
            continue
        league = TEAM_TO_LEAGUE.get(team)
        if not league:
            print(f"  WARN: 未対応のチーム: {team} ({name})")
            continue
        report_players.append((name, team, (r.get('player_name_en') or '').strip()))

    # リーグ別に振り分け
    cl_list = [(n, t, e) for n, t, e in report_players if TEAM_TO_LEAGUE.get(t) == 'CL']
    pl_list = [(n, t, e) for n, t, e in report_players if TEAM_TO_LEAGUE.get(t) == 'PL']

    print("2025年新入団選手を全員版 from_master に反映（報告書ベース）")
    print(f"  報告書: CL {len(cl_list)}名, PL {len(pl_list)}名")
    total = 0
    if cl_list:
        print("\n[CL]")
        total += process_league('CL', cl_list, calculated_dir)
    if pl_list:
        print("\n[PL]")
        total += process_league('PL', pl_list, calculated_dir)

    if total == 0:
        print("追加する新選手はいませんでした。")
    else:
        print(f"\n合計 +{total} 件を全員版CSVに追加しました。")
    return 0


if __name__ == '__main__':
    sys.exit(main())
