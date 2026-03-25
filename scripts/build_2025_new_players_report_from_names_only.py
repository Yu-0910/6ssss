#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docs/2025_new_players_names_only.md を解析し、
_data/reports/2025_new_players_report.csv を再生成する。

Phase 2: ドラフト選手・新外国人をすべて報告書に載せる。
"""

import csv
import re
import sys
from pathlib import Path

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# #### で始まる行のチーム名（厳密一致用）
TEAM_NAMES = [
    '読売ジャイアンツ', '東京ヤクルトスワローズ', '横浜DeNAベイスターズ',
    '広島東洋カープ', '中日ドラゴンズ', '阪神タイガース',
    '福岡ソフトバンクホークス', '北海道日本ハムファイターズ', '千葉ロッテマリーンズ',
    '東北楽天ゴールデンイーグルス', '埼玉西武ライオンズ', 'オリックス・バファローズ',
]


def extract_player_name(line: str) -> tuple[str | None, bool]:
    """
    "- 名前（...）" または "- 名前" から (player_name_ja, is_draft) を抽出する。
    is_draft: 行に「位」が含まれる＝ドラフト枠の行。
    """
    m = re.match(r'^-\s+(.+?)\s*$', line.strip())
    if not m:
        return None, False
    raw = m.group(1).strip()
    if not raw:
        return None, False
    # player_id などの子行はスキップ
    if raw.startswith('player_id:') or (':' in raw and '（' not in raw):
        return None, False
    is_draft = '位）' in raw or '位)' in raw
    # "名前（..." の形式
    if '（' in raw:
        before_paren = raw.split('（', 1)[0].strip()
        rest = raw[raw.index('（') + 1:]
        # "ファビアン）（外野手）" のような短縮名があれば採用
        short_match = re.match(r'^([^）]+)）\s*（', rest)
        if short_match:
            short = short_match.group(1).strip()
            if short and len(short) <= 10 and not re.search(r'[投手内野外野捕手／/]', short):
                return short, is_draft
        # ドラフト（○位）の行は短縮しない
        if is_draft:
            return before_paren, is_draft
        # 外国人風 "名前・姓（ポジション）" → 姓（・の後ろ）を採用
        if '・' in before_paren:
            parts = before_paren.split('・')
            last = (parts[-1] or '').strip()
            if last and re.match(r'^[\u30a0-\u30ff]+$', last) and 2 <= len(last) <= 10:
                return last, is_draft
        return before_paren, is_draft
    return raw, is_draft


def is_foreign_display_name(name_ja: str) -> bool:
    """表示名が外国人風か（カタカナのみ／英字含む）"""
    if not name_ja:
        return False
    if re.search(r'[A-Za-z]', name_ja):
        return True
    if re.match(r'^[\u30a0-\u30ff・\s]+$', name_ja) and '・' in name_ja:
        return True
    # 単一カタカナ名（ボスラー、ネビン等）
    if re.match(r'^[\u30a0-\u30ff]+$', name_ja) and len(name_ja) <= 6:
        return True
    return False


def main() -> int:
    md_path = PROJECT_ROOT / 'docs' / '2025_new_players_names_only.md'
    out_path = PROJECT_ROOT / '_data' / 'reports' / '2025_new_players_report.csv'

    if not md_path.exists():
        print(f"ERROR: 見つかりません: {md_path}")
        return 1

    text = md_path.read_text(encoding='utf-8')
    lines = text.splitlines()
    current_team: str | None = None
    rows: list[dict] = []

    for line in lines:
        stripped = line.strip()
        # セクション1・2以外が始まったら選手リストは終わり
        if stripped.startswith('## ') and not stripped.startswith('## 1.') and not stripped.startswith('## 2.'):
            current_team = None
        # #### チーム名
        if stripped.startswith('#### '):
            team_candidate = stripped[5:].strip()
            if team_candidate in TEAM_NAMES:
                current_team = team_candidate
            continue
        # "- 選手名（...）"（漢字・カタカナ・英字のみ。長い説明文は除外）
        if stripped.startswith('- ') and current_team:
            name_ja, is_draft = extract_player_name(line)
            if not name_ja or len(name_ja) > 20:
                continue
            if is_draft:
                source = 'DRAFT_2024'
                is_foreign = is_foreign_display_name(name_ja)
            else:
                source = 'FOREIGN_PLAYER'
                is_foreign = True
            rows.append({
                'player_name_ja': name_ja,
                'team': current_team,
                'name_kana': '',
                'player_name_en': '',
                'is_foreign': 'Yes' if is_foreign else 'No',
                'source': source,
                '備考': '',
            })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ['player_name_ja', 'team', 'name_kana', 'player_name_en', 'is_foreign', 'source', '備考']
    with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"報告書を出力しました: {out_path}")
    print(f"  合計 {len(rows)} 名（ドラフト＋新外国人）")
    return 0


if __name__ == '__main__':
    sys.exit(main())
