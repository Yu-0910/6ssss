#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""debug_pitches を使って集計ロジックを検証"""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from fetch_pitcher_zone_stats import (
    aggregate_zone_by_hand,
    is_hit,
    is_settlement_result,
    load_roster_bat_hand,
)

root = SCRIPT_DIR.parent
debug_path = root / "_data/yahoo_games_pilot/debug_pitches_2021040084_2103788.json"
with open(debug_path, encoding="utf-8") as f:
    all_pitches = json.load(f)

# 決着球の結果を一覧
pa_blocks = {}
for p in all_pitches:
    if p.get("pitcher_id") != "2103788":
        continue
    key = (p.get("inning"), p.get("top_bottom"), p.get("bat_order"))
    if key not in pa_blocks:
        pa_blocks[key] = []
    pa_blocks[key].append(p)

print("=== 決着球チェック ===")
hits_found = []
for key in sorted(pa_blocks.keys(), key=lambda x: (x[0], 0 if x[1] == "表" else 1, x[2])):
    pitches = pa_blocks[key]
    last = sorted(pitches, key=lambda x: int(x.get("pitch_no") or 0))[-1]
    result = (last.get("result") or "").strip()
    zid = last.get("zone_id") or "?"
    is_settle = is_settlement_result(result)
    is_h = is_hit(result)
    status = "HIT" if is_h else ("SETTLE" if is_settle else "skip")
    print(f"  {key[0]}{key[1]} {key[2]}番: result={result[:40]!r} zone={zid} -> {status}")
    if is_h:
        hits_found.append((key, result, zid))

print(f"\n検出した安打: {len(hits_found)}件")
for k, r, z in hits_found:
    print(f"  {k[0]}{k[1]} {k[2]}番: {r} (zone {z})")

roster = load_roster_bat_hand(root)
agg = aggregate_zone_by_hand(all_pitches, "2103788", roster)

print("\n=== 集計結果（安打ありゾーン） ===")
for hand in ["vsRight", "vsLeft"]:
    for z in agg[hand]:
        if z.get("h", 0) > 0:
            print(f"  {hand} zone{z['zoneId']}: ab={z['ab']} h={z['h']} avg={z['avg']}")
