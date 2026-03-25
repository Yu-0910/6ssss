#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aggregate_pitcher_inning_runs_simple.py

Yahoo! プロ野球 (baseball.yahoo.co.jp) のスコアページとテキスト速報ページから、
「指定試合・指定投手」について、おおまかなイニング別失点数を集計して JSON 出力する簡易スクリプト。

⚠ 制約（簡易版の割り切り）:
  - 「その投手が登板していたイニング」ごとに、そのイニングの相手チームの得点合計を
    まるごとその投手の失点として扱う。
  - 同じイニングの途中で投手交代があった場合でも、イニングトータルの失点しか見ていないため、
    実際の責任投手の割り振りとは一致しない可能性がある。
  - ただし、「降板した後の回」の失点は一切カウントしない、という意味では
    「降板後の失点を含めない」という要件は満たす。

使い方（例）:
  python scripts/aggregate_pitcher_inning_runs_simple.py --game-id 2021040084 --pitcher-id 2103788 --pitcher-side home
  python scripts/aggregate_pitcher_inning_runs_simple.py --game-id 2021040084 --pitcher-id 2103788 --pitcher-side away --out-dir _data/yahoo_games_pilot

出力:
  デフォルトでは _data/yahoo_games_pilot/inning_runs_{game_id}_{pitcher_id}.json に JSON を保存する。
  形式の例:
  {
    "game_id": "2021040084",
    "pitcher_id": "2103788",
    "pitcher_side": "home",
    "innings": [
      {"inning": 1, "runs": 0},
      {"inning": 2, "runs": 0},
      ...
    ],
    "total_runs": 0
  }
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ pip install requests beautifulsoup4 lxml")
    sys.exit(1)

# 既存の球種別集計スクリプトから、打席一覧取得ロジックを流用する
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from fetch_game_pitch_types import (  # type: ignore
    BASE_URL,
    parse_plate_appearances_from_html,
)


def fetch_html(url: str, timeout: int = 30) -> str | None:
    """単純な HTML 取得ヘルパー"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ HTML取得エラー: {url} -> {e}")
        return None


def get_innings_for_pitcher(game_id: str, pitcher_id: str) -> set[int]:
    """
    テキスト速報ページから「その投手が投げたイニング番号」の集合を取得。
    （打席一覧パーサーを流用し、該当投手の打席 inning をユニーク化する）
    """
    text_url = f"{BASE_URL}/npb/game/{game_id}/text"
    print(f"📥 テキスト速報から登板イニング取得: {text_url}")
    html = fetch_html(text_url)
    if not html:
        print("❌ テキストページの取得に失敗しました")
        return set()

    pas = parse_plate_appearances_from_html(html, game_id)
    innings: set[int] = set()
    for pa in pas:
        if str(pa.get("pitcher_id")) == pitcher_id:
            try:
                inn = int(pa.get("inning") or 0)
            except ValueError:
                continue
            if inn > 0:
                innings.add(inn)

    print(f"   👉 該当投手が登板したイニング: {sorted(innings)}")
    return innings


def parse_scoreboard_inning_runs(html: str, pitcher_side: str) -> dict[int, int]:
    """
    スコアページの HTML から、相手チームのイニング別得点を取得する。

    pitcher_side:
      - 'home' : 投手はホームチーム側 → 相手チームはビジターチーム（上段）
      - 'away' : 投手はビジターチーム側 → 相手チームはホームチーム（下段）
    """
    soup = BeautifulSoup(html, "lxml")

    # Yahoo! スコアページのイニング表は、通常「スコアボード」テーブルにある
    # 構造は変更される可能性があるので、行テキストで判断する。
    table = None
    for tbl in soup.find_all("table"):
        # ざっくり「回」や「計」などを含むヘッダーがあるテーブルを探す
        th_texts = [th.get_text(strip=True) for th in tbl.find_all("th")]
        joined = " ".join(th_texts)
        if "回" in joined and ("計" in joined or "R" in joined):
            table = tbl
            break

    if table is None:
        print("⚠️ スコアボードテーブルが見つかりませんでした")
        return {}

    rows = table.find_all("tr")
    if len(rows) < 3:
        print("⚠️ スコアボードの行数が想定より少ないです")
        return {}

    # 一般的には 1 行目: ヘッダー, 2 行目: ビジター, 3 行目: ホーム という構造になっている
    header_cells = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
    away_cells = [c.get_text(strip=True) for c in rows[1].find_all(["th", "td"])]
    home_cells = [c.get_text(strip=True) for c in rows[2].find_all(["th", "td"])]

    # ヘッダーから「1」「2」「3」... の列インデックスを推定
    inning_col_indices: list[tuple[int, int]] = []  # (inning_number, col_index)
    for idx, label in enumerate(header_cells):
        if not label:
            continue
        try:
            inn = int(label)
        except ValueError:
            continue
        inning_col_indices.append((inn, idx))

    if not inning_col_indices:
        print("⚠️ イニング列がヘッダーから検出できませんでした")
        return {}

    opponent_row = away_cells if pitcher_side == "home" else home_cells

    inning_runs: dict[int, int] = {}
    for inn, col_idx in inning_col_indices:
        if col_idx >= len(opponent_row):
            continue
        val = opponent_row[col_idx]
        # "x" や空欄は 0 点扱い
        try:
            r = int(val)
        except ValueError:
            r = 0
        inning_runs[inn] = r

    print(f"   👉 相手チームのイニング別得点 (スコアボード): {inning_runs}")
    return inning_runs


def aggregate_inning_runs_simple(game_id: str, pitcher_id: str, pitcher_side: str) -> dict:
    """
    簡易ロジックで「該当投手が登板したイニングの失点」を集計して dict を返す。
    """
    # 1) テキスト速報から、その投手が投げたイニング番号を取得
    pitch_innings = get_innings_for_pitcher(game_id, pitcher_id)
    if not pitch_innings:
        print("⚠️ 該当投手の登板イニングが見つかりませんでした（0失点 / 登板なしの可能性）")

    # 2) スコアページから相手チームのイニング別得点を取得
    score_url = f"{BASE_URL}/npb/game/{game_id}/score"
    print(f"📥 スコアページからイニング別得点取得: {score_url}")
    score_html = fetch_html(score_url)
    if not score_html:
        print("❌ スコアページの取得に失敗しました")
        inning_runs_all: dict[int, int] = {}
    else:
        inning_runs_all = parse_scoreboard_inning_runs(score_html, pitcher_side=pitcher_side)

    # 3) 「その投手が投げたイニング」に限定して失点を抽出
    innings_list: list[dict] = []
    total_runs = 0

    for inn in sorted(pitch_innings):
        runs = inning_runs_all.get(inn, 0)
        innings_list.append({"inning": inn, "runs": runs})
        total_runs += runs

    result = {
        "game_id": game_id,
        "pitcher_id": pitcher_id,
        "pitcher_side": pitcher_side,
        "innings": innings_list,
        "total_runs": total_runs,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Yahoo!スコア + テキスト速報から、指定試合・指定投手の簡易イニング別失点を集計するスクリプト"
        )
    )
    parser.add_argument("--game-id", required=True, help="試合ID (例: 2021040084)")
    parser.add_argument("--pitcher-id", required=True, help="投手のYahoo ID (例: 2103788)")
    parser.add_argument(
        "--pitcher-side",
        required=True,
        choices=["home", "away"],
        help="投手がホーム側かビジター側か（home/away）",
    )
    parser.add_argument(
        "--out-dir",
        default="_data/yahoo_games_pilot",
        help="JSON 出力ディレクトリ（デフォルト: _data/yahoo_games_pilot）",
    )

    args = parser.parse_args()

    game_id = args.game_id.strip()
    pitcher_id = args.pitcher_id.strip()
    pitcher_side = args.pitcher_side.strip().lower()

    root = Path(__file__).resolve().parent.parent
    out_dir = root / args.out_dir.strip()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== 簡易イニング別失点集計 ===")
    print(f"  試合ID      : {game_id}")
    print(f"  投手ID      : {pitcher_id}")
    print(f"  投手サイド  : {pitcher_side}")
    print(f"  出力ディレクトリ: {out_dir}")
    print("")

    data = aggregate_inning_runs_simple(game_id, pitcher_id, pitcher_side)

    out_path = out_dir / f"inning_runs_{game_id}_{pitcher_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("\n✅ 集計完了")
    print(f"  total_runs: {data.get('total_runs')}")
    print(f"  innings   : {data.get('innings')}")
    print(f"  出力ファイル: {out_path.absolute()}")


if __name__ == "__main__":
    main()

