#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2024年型の非規定（全選手用）CSVの更新版を作り、2025年新入団・新外国人を組み込み、
ランキングページまで反映する一括スクリプト。

手順:
1. 現在の2025 from_master（計算済み）をバックアップ（ファビアン・キャベッジ等の成績を保持）
2. NPBから2025年CL/PL打撃成績をスクレイプ → _data/master_csv__import_1950_2024
3. 指標計算（import → calculated）で 2025 年のみ処理
4. 2025新選手報告書に載っている選手で calculated にいない者を追加（バックアップに居ればその行で成績を反映）
5. 規定打席到達版CSV作成（create_qualifying_csv_2025）
6. ランキングJSON再生成（build_rankings_from_calculated --year 2025 --league CL/PL）

オプション:
  --skip-scrape  スクレイプをスキップし、既存の import または calculated のみで 4〜6 を実行
"""

import argparse
import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

TEAM_TO_LEAGUE: Dict[str, str] = {
    '読売ジャイアンツ': 'CL', '東京ヤクルトスワローズ': 'CL', '横浜DeNAベイスターズ': 'CL',
    '広島東洋カープ': 'CL', '中日ドラゴンズ': 'CL', '阪神タイガース': 'CL',
    '福岡ソフトバンクホークス': 'PL', '北海道日本ハムファイターズ': 'PL', '千葉ロッテマリーンズ': 'PL',
    '東北楽天ゴールデンイーグルス': 'PL', '埼玉西武ライオンズ': 'PL', 'オリックス・バファローズ': 'PL',
}


def normalize_key(name: str, team: str) -> Tuple[str, str]:
    n = (name or '').strip().replace('\u3000', ' ').replace('　', ' ')
    n = re.sub(r'\s+', ' ', n)
    t = (team or '').strip()
    return (n, t)


def load_csv_with_encoding(csv_path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    for enc in ('utf-8-sig', 'utf-8', 'shift_jis', 'cp932'):
        try:
            with open(csv_path, 'r', encoding=enc) as f:
                reader = csv.DictReader(f)
                header = list(reader.fieldnames or [])
                rows = list(reader)
                return (header, rows)
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    raise ValueError(f"Failed to read {csv_path}")


def load_report_players(report_path: Path) -> List[Dict[str, str]]:
    _header, rows = load_csv_with_encoding(report_path)
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        ja = (r.get('player_name_ja') or r.get('\ufeffplayer_name_ja') or '').strip()
        team = (r.get('team') or '').strip()
        if not ja or not team:
            continue
        out.append({
            'player_name_ja': ja,
            'team': team,
            'player_name_en': (r.get('player_name_en') or '').strip(),
        })
    return out


def existing_keys_from_batting(rows: List[Dict[str, Any]]) -> Set[Tuple[str, str]]:
    keys = set()
    for r in rows:
        name = (r.get('player_name_ja') or r.get('name') or '').strip().replace('\u3000', ' ').replace('　', ' ')
        name = re.sub(r'\s+', ' ', name)
        team = (r.get('team') or r.get('Team') or '').strip()
        if name and team:
            keys.add((name, team))
    return keys


def make_empty_row(header: List[str], year: int, league: str, team: str, player_name_ja: str, player_name_en: str) -> Dict[str, Any]:
    float_cols = {'AVG', 'OBP', 'SLG', 'OPS', 'IsoP', 'IsoD', 'BB%', 'K%', 'BB/K', 'BABIP', 'SecA', 'TA', 'NOI', 'GPA'}
    int_cols = {'G', 'PA', 'AB', 'R', 'H', '2B', '3B', 'HR', 'TB', 'RBI', 'SB', 'CS', 'SH', 'SF', 'BB', 'IBB', 'HBP', 'SO', 'GDP',
                '打率', '安打', '本塁打', '打点', '試合', '打席', '打数', '単打', '二塁打', '三塁打', '得点', '出塁率', '長打率',
                '四球', '敬遠', '死球', '三振', '塁打', '盗塁', '盗塁死', '犠打', '犠飛', '併殺打', 'RC', 'XR'}
    row: Dict[str, Any] = {}
    for col in header:
        if col == 'year':
            row[col] = year
        elif col == 'league':
            row[col] = league
        elif col == 'team':
            row[col] = team
        elif col == 'player_id':
            row[col] = ''
        elif col == 'player_name_ja':
            row[col] = player_name_ja
        elif col == 'player_name_en':
            row[col] = player_name_en
        elif col in float_cols:
            row[col] = 0.0
        elif col in int_cols:
            row[col] = 0
        else:
            row[col] = ''
    return row


def find_row_by_key(rows: List[Dict[str, Any]], key: Tuple[str, str]) -> Optional[Dict[str, Any]]:
    for r in rows:
        name = (r.get('player_name_ja') or r.get('name') or '').strip().replace('\u3000', ' ').replace('　', ' ')
        name = re.sub(r'\s+', ' ', name)
        team = (r.get('team') or r.get('Team') or '').strip()
        if (name, team) == key:
            return r
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description='2025年全選手用CSV更新＋新入団・新外国人組み込み＋ランキング反映')
    parser.add_argument('--skip-scrape', action='store_true', help='スクレイプをスキップし、既存CSVのみでマージ〜ランキングまで実行')
    args = parser.parse_args()

    data_dir = PROJECT_ROOT / '_data'
    import_dir = data_dir / 'master_csv__import_1950_2024'
    calculated_dir = data_dir / 'master_csv_calculated'
    report_path = data_dir / 'reports' / '2025_new_players_report.csv'
    backup_dir = calculated_dir / '_backup_2025_from_master'

    if not report_path.exists():
        print(f"ERROR: 報告書が見つかりません: {report_path}")
        return 1

    report_players = load_report_players(report_path)
    cl_report = [p for p in report_players if TEAM_TO_LEAGUE.get(p['team']) == 'CL']
    pl_report = [p for p in report_players if TEAM_TO_LEAGUE.get(p['team']) == 'PL']
    print(f"[0] 2025新選手リスト: CL {len(cl_report)}件, PL {len(pl_report)}件")

    # 1. 現在の 2025 from_master（計算済み）をバックアップ
    backup_dir.mkdir(parents=True, exist_ok=True)
    cl_calc = calculated_dir / 'batting_2025_CL_from_master.csv'
    pl_calc = calculated_dir / 'batting_2025_PL_from_master.csv'
    backup_cl = backup_dir / 'batting_2025_CL_from_master.csv'
    backup_pl = backup_dir / 'batting_2025_PL_from_master.csv'
    if cl_calc.exists():
        shutil.copy2(cl_calc, backup_cl)
        print(f"[1] バックアップ: {backup_cl.name}")
    if pl_calc.exists():
        shutil.copy2(pl_calc, backup_pl)
        print(f"[1] バックアップ: {backup_pl.name}")

    # 2. スクレイプ（オプション）
    if not args.skip_scrape:
        for league in ('CL', 'PL'):
            cmd = [sys.executable, str(SCRIPT_DIR / 'scrape_npb_batting_stats.py'), '--year', '2025', '--league', league, '--overwrite']
            print(f"[2] スクレイプ: 2025 {league} ...")
            r = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
            if r.returncode != 0:
                print(f"WARN: スクレイプ 2025 {league} が失敗しました (returncode={r.returncode})。既存CSVで続行します。")
    else:
        print("[2] スクレイプをスキップしました")

    # 3. 指標計算（import → calculated）、2025年のみ
    import_cl = import_dir / 'batting_2025_CL_from_master.csv'
    import_pl = import_dir / 'batting_2025_PL_from_master.csv'
    if import_cl.exists() or import_pl.exists():
        cmd = [
            sys.executable, str(SCRIPT_DIR / 'compute_metrics_all_seasons.py'),
            '--input-dir', '_data/master_csv__import_1950_2024',
            '--year', '2025',
            '--overwrite',
        ]
        print("[3] 指標計算 (2025年)...")
        r = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        if r.returncode != 0:
            print("WARN: 指標計算に失敗しました。既存の calculated を使用して続行します。")
    else:
        print("[3] import に 2025 の from_master が無いため指標計算をスキップ（既存 calculated を使用）")

    # 4. 新選手を追加（報告書に載っていて calculated にいない者。バックアップに居ればその行を使用）
    backup_header_cl, backup_rows_cl = load_csv_with_encoding(backup_cl) if backup_cl.exists() else ([], [])
    backup_header_pl, backup_rows_pl = load_csv_with_encoding(backup_pl) if backup_pl.exists() else ([], [])

    added_total = 0
    for league_key, csv_path, to_add, backup_header, backup_rows in [
        ('CL', cl_calc, cl_report, backup_header_cl, backup_rows_cl),
        ('PL', pl_calc, pl_report, backup_header_pl, backup_rows_pl),
    ]:
        if not csv_path.exists():
            print(f"   WARN: {csv_path.name} が存在しないためスキップ")
            continue
        header, rows = load_csv_with_encoding(csv_path)
        existing = existing_keys_from_batting(rows)
        for p in to_add:
            key = normalize_key(p['player_name_ja'], p['team'])
            if key in existing:
                continue
            backup_row = find_row_by_key(backup_rows, key) if backup_rows else None
            if backup_row and backup_header:
                # バックアップの行を流用（ヘッダーに合わせてキーを揃える）
                new_row = {col: backup_row.get(col, '') for col in header}
                new_row['year'] = 2025
                new_row['league'] = league_key
                rows.append(new_row)
                print(f"   追加(成績反映): {p['player_name_ja']} ({p['team']}) -> {csv_path.name}")
            else:
                new_row = make_empty_row(header, 2025, league_key, p['team'], p['player_name_ja'], p.get('player_name_en') or '')
                rows.append(new_row)
                print(f"   追加(0で埋め): {p['player_name_ja']} ({p['team']}) -> {csv_path.name}")
            existing.add(key)
            added_total += 1

        if rows:
            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=header, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(rows)
            print(f"   保存: {csv_path.name} ({len(rows)}行)")
    print(f"[4] 新選手追加: {added_total}件")

    # 5. 規定打席到達版CSV作成
    print("[5] 規定打席到達版CSV作成...")
    r = subprocess.run([sys.executable, str(SCRIPT_DIR / 'create_qualifying_csv_2025.py')], cwd=str(PROJECT_ROOT))
    if r.returncode != 0:
        print("ERROR: 規定打席到達版CSVの作成に失敗しました")
        return 1

    # 6. ランキングJSON再生成（CL / PL それぞれ）
    print("[6] ランキングJSON再生成 (2025年)...")
    for league in ('CL', 'PL'):
        cmd = [
            sys.executable, str(SCRIPT_DIR / 'build_rankings_from_calculated.py'),
            '--input_dir', '_data/master_csv_calculated',
            '--out_dir', 'public/data/rankings',
            '--year', '2025',
            '--league', league,
        ]
        r = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        if r.returncode != 0:
            print(f"ERROR: ランキングJSON生成 2025 {league} に失敗しました")
            return 1
    print("完了: ランキングページは public/data/rankings/2025/{CL|PL}/*.json を参照します")
    return 0


if __name__ == '__main__':
    sys.exit(main())
