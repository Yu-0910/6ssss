#!/usr/bin/env python3
"""
菊池涼介（batter_id=1100082）の 2026-03-04 のYahooパイロットデータから
個人ページブロック B,D,E,F,G,H,I,J 相当の項目を収集・集計するスクリプト。

出力: _data/yahoo_games_pilot/kikuchi_20260304_blocks.json
"""

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

# 設定
BATTER_ID = "1100082"
TARGET_DATE = "2026-03-04"
DATA_DIR = Path(__file__).resolve().parent.parent / "_data" / "yahoo_games_pilot"
OUTPUT_PATH = DATA_DIR / "kikuchi_20260304_blocks.json"


def load_pa_rows() -> list[dict]:
    """plate_appearances_normalized.csv から菊池・当該日付の打席を取得"""
    pa_path = DATA_DIR / "plate_appearances_normalized.csv"
    if not pa_path.exists():
        return []
    rows = []
    with open(pa_path, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if row.get("batter_id") == BATTER_ID and row.get("date") == TARGET_DATE:
                rows.append(row)
    return rows


def load_batting_stats() -> list[dict]:
    """batting_stats.csv から菊池の該当成績を取得（ブロックD用）"""
    stats_path = DATA_DIR / "batting_stats.csv"
    if not stats_path.exists():
        return []
    rows = []
    with open(stats_path, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if row.get("player_id") == BATTER_ID:
                rows.append(row)
    return rows


def load_pitcher_ids() -> set[str]:
    """pitching_stats.csv から投手ID一覧を取得（投手の利き腕判定に使用）"""
    stats_path = DATA_DIR / "pitching_stats.csv"
    if not stats_path.exists():
        return set()
    ids = set()
    with open(stats_path, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if pid := row.get("player_id"):
                ids.add(pid)
    return ids


def parse_pitcher_throws_from_html(game_id: str, pitcher_ids: set[str]) -> dict[str, str]:
    """
    game の _top.html から投手の利き腕を取得。
    スタメン投手テーブルのみを対象（打順テーブルの打列と混同しない）。
    投手テーブルは th scope="col">投</th を含み、直前に「投手」ラベルがある。
    """
    html_path = DATA_DIR / f"{game_id}_top.html"
    if not html_path.exists():
        return {}
    text = html_path.read_text(encoding="utf-8")
    result: dict[str, str] = {}
    # 投手テーブルブロックを抽出（先発/中継ぎ/抑え を含む行のみ。打順の 1,2,3 と区別）
    # 投手テーブル: <td>先発</td> or <td>中継ぎ</td> などの後に player link と 投(左/右)
    for m in re.finditer(
        r'<td[^>]*>(?:先発|中継ぎ|抑え|リリーフ)</td>.*?'
        r'href="/npb/player/(\d+)/top"[^>]*>[^<]+</a>\s*</td>\s*<td[^>]*>([左右])</td>',
        text,
        re.DOTALL,
    ):
        pid, hand = m.group(1), m.group(2)
        if pid in pitcher_ids:
            result[pid] = "R" if hand == "右" else "L"
    return result


def detect_hit_direction(result_raw: str) -> str | None:
    """result_raw から打球方向（左/中/右）を判定。レフト/ライト/センター系の語を優先"""
    if not result_raw:
        return None
    r = result_raw
    if "レフト" in r or "左翼" in r or "左飛" in r:
        return "L"
    if "ライト" in r or "右翼" in r or "右飛" in r:
        return "R"
    if "センター" in r or "センターフライ" in r or "中飛" in r:
        return "C"
    # サード/ショート/セカンド/ファースト/ピッチャー は方向としては扱わない（ゴロの守備位置）
    return None


def detect_ground_fly(result_raw: str) -> str | None:
    """result_raw からゴロ/フライを判定"""
    if not result_raw:
        return None
    r = result_raw
    if "ゴロ" in r:
        return "ground"
    if "フライ" in r or "ライナー" in r:
        return "fly"
    return None


def _int(val) -> int:
    try:
        return int(val or 0)
    except (TypeError, ValueError):
        return 0


def _aggregate_batting_by_risp(pa_rows: list[dict]) -> dict[str, dict]:
    """PA行を得点圏(risp=1)・非得点圏(risp=0)で分けて打撃成績を集計"""
    risp_rows = [r for r in pa_rows if r.get("is_pa") == "1" and r.get("risp") == "1"]
    no_risp_rows = [r for r in pa_rows if r.get("is_pa") == "1" and r.get("risp") != "1"]

    def agg(rows: list[dict]) -> dict:
        if not rows:
            return {"pa": 0, "ab": 0, "r": 0, "h": 0, "h2": 0, "h3": 0, "hr": 0, "tb": 0, "rbi": 0,
                    "so": 0, "bb": 0, "ibb": 0, "hbp": 0, "sh": 0, "sf": 0, "sb": 0, "cs": 0, "g": 0,
                    "avg": "", "obp": "", "slg": "", "ops": ""}
        pa = len(rows)
        ab = sum(_int(r.get("ab")) for r in rows)
        r = sum(_int(r.get("r")) for r in rows)
        h = sum(_int(r.get("h")) for r in rows) + sum(_int(r.get("h2")) for r in rows) + sum(
            _int(r.get("h3")) for r in rows
        ) + sum(_int(r.get("hr")) for r in rows)
        h1 = sum(_int(r.get("h")) for r in rows)
        h2 = sum(_int(r.get("h2")) for r in rows)
        h3 = sum(_int(r.get("h3")) for r in rows)
        hr = sum(_int(r.get("hr")) for r in rows)
        tb = h1 + h2 * 2 + h3 * 3 + hr * 4
        rbi = sum(_int(r.get("rbi")) for r in rows)
        so = sum(_int(r.get("so")) for r in rows)
        bb = sum(_int(r.get("bb")) for r in rows)
        ibb = sum(_int(r.get("ibb")) for r in rows)
        hbp = sum(_int(r.get("hbp")) for r in rows)
        sh = sum(_int(r.get("sh")) for r in rows)
        sf = sum(_int(r.get("sf")) for r in rows)
        sb = sum(_int(r.get("sb")) for r in rows)
        cs = sum(_int(r.get("cs")) for r in rows)
        g = len(set(r.get("game_id", "") for r in rows))
        avg = f"{h / ab:.3f}" if ab > 0 else ""
        obp_num = h + bb + hbp
        obp_den = ab + bb + hbp + sf
        obp = f"{obp_num / obp_den:.3f}" if obp_den > 0 else ""
        slg = f"{tb / ab:.3f}" if ab > 0 else ""
        obp_f = float(obp) if obp else 0
        slg_f = float(slg) if slg else 0
        ops = f"{obp_f + slg_f:.3f}" if (obp and slg) else ""
        return {
            "pa": pa,
            "ab": ab,
            "r": r,
            "h": h,
            "h2": h2,
            "h3": h3,
            "hr": hr,
            "tb": tb,
            "rbi": rbi,
            "so": so,
            "bb": bb,
            "ibb": ibb,
            "hbp": hbp,
            "sh": sh,
            "sf": sf,
            "sb": sb,
            "cs": cs,
            "g": g,
            "avg": avg,
            "obp": obp,
            "slg": slg,
            "ops": ops,
        }

    return {"risp": agg(risp_rows), "no_risp": agg(no_risp_rows)}


def collect_blocks(pa_rows: list[dict], batting_stats: list[dict], pitcher_throws: dict[str, str]) -> dict:
    """各ブロックの集計を実行"""
    blocks: dict = {}

    # === ブロックD: batting_stats から（既存）===
    d_rows = []
    for row in batting_stats:
        d_rows.append({
            "split_type": row.get("split_type", ""),
            "split_value": row.get("split_value", ""),
            "g": int(row.get("g") or 0),
            "pa": int(row.get("pa") or 0),
            "ab": int(row.get("ab") or 0),
            "h": int(row.get("h") or 0),
            "hr": int(row.get("hr") or 0),
            "rbi": int(row.get("rbi") or 0),
            "bb": int(row.get("bb") or 0),
            "so": int(row.get("so") or 0),
            "sb": int(row.get("sb") or 0),
            "cs": int(row.get("cs") or 0),
            "avg": row.get("avg", ""),
            "obp": row.get("obp", ""),
            "slg": row.get("slg", ""),
            "ops": row.get("ops", ""),
        })
    blocks["D"] = {"source": "batting_stats", "rows": d_rows}

    # === ブロックF: スプリット（月別・曜日・球場・走者状況）===
    f_by_month: dict[str, int] = defaultdict(int)
    f_by_day_night: dict[str, int] = defaultdict(int)
    f_by_stadium: dict[str, int] = defaultdict(int)
    f_by_base_state: dict[str, int] = defaultdict(int)
    f_by_risp: dict[str, int] = defaultdict(int)

    for row in pa_rows:
        if row.get("is_pa") != "1":
            continue
        # 月
        date = row.get("date", "")
        if len(date) >= 7:
            month = date[:7]
            f_by_month[month] += 1
        # 曜日: date からは取れない、day_night で代替
        dn = row.get("day_night", "")
        if dn:
            f_by_day_night[dn] += 1
        # 球場
        stad = row.get("stadium", "")
        if stad:
            f_by_stadium[stad] += 1
        # 走者状況
        base = row.get("base_state", "")
        if base:
            f_by_base_state[base] += 1
        # RISP
        risp = row.get("risp", "0")
        key = "risp" if risp == "1" else "no_risp"
        f_by_risp[key] += 1

    # 得点圏・非得点圏の詳細打撃成績
    f_by_risp_stats = _aggregate_batting_by_risp(pa_rows)

    blocks["F"] = {
        "source": "plate_appearances",
        "by_month": dict(f_by_month),
        "by_day_night": dict(f_by_day_night),
        "by_stadium": dict(f_by_stadium),
        "by_base_state": dict(f_by_base_state),
        "by_risp": dict(f_by_risp),
        "by_risp_stats": f_by_risp_stats,
    }

    # === ブロックG: 打球方向・コース・球種 ===
    g_direction: dict[str, int] = defaultdict(int)
    g_course: dict[str, int] = defaultdict(int)
    g_pitch_type: dict[str, int] = defaultdict(int)

    for row in pa_rows:
        if row.get("is_pa") != "1":
            continue
        d = detect_hit_direction(row.get("result_raw", ""))
        if d:
            g_direction[d] += 1
        c = row.get("course", "").strip()
        if c:
            g_course[c] += 1
        pt = row.get("pitch_type", "").strip()
        if pt:
            g_pitch_type[pt] += 1

    blocks["G"] = {
        "source": "plate_appearances",
        "hit_direction": dict(g_direction),
        "course": dict(g_course),
        "pitch_type": dict(g_pitch_type),
    }

    # === ブロックH: ゴロ/フライ、対左右 ===
    h_ground_fly: dict[str, int] = defaultdict(int)
    h_vs_l: int = 0
    h_vs_r: int = 0
    h_vs_unknown: int = 0

    for row in pa_rows:
        if row.get("is_pa") != "1":
            continue
        gf = detect_ground_fly(row.get("result_raw", ""))
        if gf:
            h_ground_fly[gf] += 1
        pid = row.get("pitcher_id", "")
        hand = pitcher_throws.get(pid, "?")
        if hand == "L":
            h_vs_l += 1
        elif hand == "R":
            h_vs_r += 1
        else:
            h_vs_unknown += 1

    blocks["H"] = {
        "source": "plate_appearances",
        "ground_fly": dict(h_ground_fly),
        "vs_left": h_vs_l,
        "vs_right": h_vs_r,
        "vs_unknown": h_vs_unknown,
        "pitcher_throws_lookup": pitcher_throws,
    }

    # === ブロックI: イニング別・状況別 ===
    i_by_inning: dict[str, int] = defaultdict(int)
    i_by_outs: dict[str, int] = defaultdict(int)
    i_by_base_state: dict[str, int] = defaultdict(int)

    for row in pa_rows:
        if row.get("is_pa") != "1":
            continue
        inn = row.get("inning", "")
        if inn:
            i_by_inning[str(inn)] += 1
        outs = row.get("outs", "")
        if outs:
            i_by_outs[str(outs)] += 1
        base = row.get("base_state_code", "") or row.get("base_state", "")
        if base:
            i_by_base_state[base] += 1

    blocks["I"] = {
        "source": "plate_appearances",
        "by_inning": dict(i_by_inning),
        "by_outs": dict(i_by_outs),
        "by_base_state": dict(i_by_base_state),
    }

    # === ブロックE: 選球眼（一球速報の投球データが必要、現状は不可）===
    blocks["E"] = {
        "source": "plate_appearances",
        "note": "一球速報の投球データが必要。plate_appearances には最終球の pitch_type/course のみ。",
        "available": False,
    }

    # === ブロックJ: 盗塁(Aに含む)、クラッチ(HR時)、直近(当該日のみ) ===
    total_sb = sum(int(r.get("sb") or 0) for r in pa_rows)
    total_cs = sum(int(r.get("cs") or 0) for r in pa_rows)
    total_hr = sum(int(r.get("hr") or 0) for r in pa_rows)
    clutch_hr = sum(1 for r in pa_rows if int(r.get("hr") or 0) > 0 and r.get("risp") == "1")

    blocks["J"] = {
        "source": "plate_appearances",
        "sb": total_sb,
        "cs": total_cs,
        "hr": total_hr,
        "clutch_hr_risp": clutch_hr,
        "recent_date": TARGET_DATE,
        "note": "直近は当該日のみを対象",
    }

    return blocks


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    pa_rows = load_pa_rows()
    batting_stats = load_batting_stats()
    pitcher_ids = load_pitcher_ids()
    game_ids = {r.get("game_id") for r in pa_rows if r.get("game_id")}
    pitcher_throws: dict[str, str] = {}
    for gid in game_ids:
        pitcher_throws.update(parse_pitcher_throws_from_html(gid, pitcher_ids))

    # 既知の投手を補完（HTMLに載っていない場合）
    pitcher_throws.setdefault("2000096", "R")  # 山下舜平大（先発）
    pitcher_throws.setdefault("2108148", "R")  # ジェリー（リリーフ）

    blocks = collect_blocks(pa_rows, batting_stats, pitcher_throws)

    out = {
        "meta": {
            "batter_id": BATTER_ID,
            "batter_name": "菊池涼介",
            "date": TARGET_DATE,
            "pa_count": len([r for r in pa_rows if r.get("is_pa") == "1"]),
            "game_ids": list(game_ids),
        },
        "blocks": blocks,
    }

    OUTPUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    print(f"  PA count: {out['meta']['pa_count']}")
    print(f"  Games: {out['meta']['game_ids']}")


if __name__ == "__main__":
    main()
