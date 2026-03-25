#!/usr/bin/env python3
"""
2025年新選手リスト（_data/reports/2025_new_players_report.csv）に名前が載っている選手だけ、
2025年成績CSVから取り出してランキング用CSVに組み込み、ランキングJSONを再生成する。

手順:
1. 2025_new_players_report.csv を読み、選手名・チームのリストを取得
2. batting_2025_CL_from_master.csv / batting_2025_PL_from_master.csv を読み、
   リストに載っている選手の行が無ければ追加（報告書の名前・チーム・英字名で最小限の行を追加）
3. 更新したCSVを保存
4. build_rankings_from_calculated.py --year 2025 を実行してランキングJSONを再生成

ランキングページは public/data/rankings/2025/{CL|PL}/*.json を参照するため、
再生成後にランキングページに反映される。
"""

import csv
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# プロジェクトルート
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# WindowsでのUnicode出力対応
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# チーム名 → リーグ（CL/PL）
TEAM_TO_LEAGUE: Dict[str, str] = {
    '読売ジャイアンツ': 'CL',
    '東京ヤクルトスワローズ': 'CL',
    '横浜DeNAベイスターズ': 'CL',
    '広島東洋カープ': 'CL',
    '中日ドラゴンズ': 'CL',
    '阪神タイガース': 'CL',
    '福岡ソフトバンクホークス': 'PL',
    '北海道日本ハムファイターズ': 'PL',
    '千葉ロッテマリーンズ': 'PL',
    '東北楽天ゴールデンイーグルス': 'PL',
    '埼玉西武ライオンズ': 'PL',
    'オリックス・バファローズ': 'PL',
}


def normalize_key(name: str, team: str) -> Tuple[str, str]:
    """比較用に選手名・チームを正規化（全角スペース→半角、trim）"""
    n = (name or '').strip().replace('\u3000', ' ').replace('　', ' ')
    n = re.sub(r'\s+', ' ', n)
    t = (team or '').strip()
    return (n, t)


def load_csv_with_encoding(csv_path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    """CSVを読み込み（複数エンコーディング試行）。(ヘッダーリスト, 行のリスト) を返す"""
    for enc in ('utf-8-sig', 'utf-8', 'shift_jis', 'cp932'):
        try:
            with open(csv_path, 'r', encoding=enc) as f:
                reader = csv.DictReader(f)
                header = reader.fieldnames or []
                rows = list(reader)
                return (header, rows)
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    raise ValueError(f"Failed to read {csv_path}")


def load_report_players(report_path: Path) -> List[Dict[str, str]]:
    """2025_new_players_report.csv を読み、選手リストを返す"""
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
    """成績CSVの行から (正規化名前, チーム) のセットを返す"""
    keys = set()
    for r in rows:
        name = (r.get('player_name_ja') or r.get('name') or '').strip().replace('\u3000', ' ').replace('　', ' ')
        name = re.sub(r'\s+', ' ', name)
        team = (r.get('team') or r.get('Team') or '').strip()
        if name and team:
            keys.add((name, team))
    return keys


def make_empty_row(header: List[str], year: int, league: str, team: str, player_name_ja: str, player_name_en: str) -> Dict[str, Any]:
    """報告書の選手用の最小限の行（数値は0）を作成"""
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


def main() -> int:
    data_dir = PROJECT_ROOT / '_data'
    report_path = data_dir / 'reports' / '2025_new_players_report.csv'
    calculated_dir = PROJECT_ROOT / '_data' / 'master_csv_calculated'
    cl_csv = calculated_dir / 'batting_2025_CL_from_master.csv'
    pl_csv = calculated_dir / 'batting_2025_PL_from_master.csv'

    if not report_path.exists():
        print(f"ERROR: 報告書が見つかりません: {report_path}")
        return 1
    if not calculated_dir.exists():
        print(f"ERROR: 計算済みCSVディレクトリが見つかりません: {calculated_dir}")
        return 1

    # 1. 報告書の選手リストを読み込み
    report_players = load_report_players(report_path)
    print(f"[1] 2025新選手リスト: {len(report_players)}件")

    # 2. チーム→リーグでCL/PLに振り分け
    cl_add: List[Dict[str, str]] = []
    pl_add: List[Dict[str, str]] = []
    for p in report_players:
        team = p['team']
        league = TEAM_TO_LEAGUE.get(team)
        if league == 'CL':
            cl_add.append(p)
        elif league == 'PL':
            pl_add.append(p)
        else:
            print(f"   WARN: チーム未対応のためスキップ: {p['player_name_ja']} ({team})")

    # 3. 成績CSVを読み、不足している選手だけ追加
    added_total = 0
    for league_key, csv_path, to_add in [
        ('CL', cl_csv, cl_add),
        ('PL', pl_csv, pl_add),
    ]:
        if not csv_path.exists():
            print(f"   WARN: {csv_path.name} が存在しないためスキップ")
            continue
        header, rows = load_csv_with_encoding(csv_path)
        existing = existing_keys_from_batting(rows)
        year = 2025
        for p in to_add:
            key = normalize_key(p['player_name_ja'], p['team'])
            if key in existing:
                continue
            new_row = make_empty_row(
                header, year, league_key,
                p['team'], p['player_name_ja'], p['player_name_en']
            )
            rows.append(new_row)
            existing.add(key)
            added_total += 1
            print(f"   追加: {p['player_name_ja']} ({p['team']}) -> {csv_path.name}")

        if not rows:
            continue
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=header, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
        print(f"   保存: {csv_path.name} ({len(rows)}行)")

    print(f"[2] 成績CSVに追加した行数: {added_total}")

    # 4. ランキングJSONを再生成（--year 2025 で2025年のみ処理）
    print("[3] ランキングJSONを再生成 (2025年)...")
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / 'build_rankings_from_calculated.py'),
        '--input_dir', str(calculated_dir.relative_to(PROJECT_ROOT)),
        '--out_dir', 'public/data/rankings',
        '--year', '2025',
    ]
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print("ERROR: ランキングJSONの生成に失敗しました")
        return 1
    print("完了: ランキングページは public/data/rankings/2025/{CL|PL}/*.json を参照します")
    return 0


if __name__ == '__main__':
    sys.exit(main())
