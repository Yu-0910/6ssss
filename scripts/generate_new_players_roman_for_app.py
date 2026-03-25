#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_new_players_roman_for_app.py

npb_roster_2026.csv から2026年新規登録選手の playerRomanNames エントリを生成する。
出力を app/players/[playerId]/page.tsx の playerRomanNames にマージ可能。
"""

import csv
import sys
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def main():
    root = Path(__file__).resolve().parent.parent
    roster_path = root / "_data" / "npb_roster_2026.csv"
    if not roster_path.exists():
        print("❌ _data/npb_roster_2026.csv がありません。先に build_npb_roster_2026.py を実行してください。")
        sys.exit(1)

    new_players = []
    with open(roster_path, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if row.get("is_new_2026") != "1":
                continue
            name_ja = (row.get("name_ja") or "").strip()
            name_en = (row.get("name_en") or "").strip()
            if not name_ja:
                continue
            new_players.append({"name_ja": name_ja, "name_en": name_en})

    print(f"2026年新規登録選手: {len(new_players)}名\n")
    print("--- playerRomanNames に追加するエントリ（コピペ用）---\n")
    for p in new_players:
        en = p["name_en"] or "?"  # name_enが空の場合は ? として出力（後で手動修正）
        ja = p["name_ja"].replace('"', '\\"')
        print(f'  "{ja}": "{en}",')
    print("\n--- 以上を playerRomanNames オブジェクトに追加してください ---")

if __name__ == "__main__":
    main()
