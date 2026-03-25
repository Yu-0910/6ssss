#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_npb_roster_2026.py

NPB公示ページ (https://npb.jp/announcement/2026/) を基に
2026年NPB選手名簿を作成するスクリプト。

- 12球団の支配下選手一覧を取得
- 各選手の投打（利き手）をNPB BIS選手ページから取得
- 新規支配下登録選手を特定
- 出力: _data/npb_roster_2026.csv (打・投の利き手を記録)
"""

import argparse
import csv
import io
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ エラー: pip install requests beautifulsoup4 lxml を実行してください")
    sys.exit(1)

# NPB公示ページのチームコード -> (球団名, app用チームコード)
TEAMS: Dict[str, Tuple[str, str]] = {
    "t": ("阪神タイガース", "H"),
    "g": ("読売ジャイアンツ", "G"),
    "s": ("東京ヤクルトスワローズ", "S"),
    "d": ("中日ドラゴンズ", "D"),
    "c": ("広島東洋カープ", "C"),
    "db": ("横浜DeNAベイスターズ", "DB"),
    "f": ("北海道日本ハムファイターズ", "F"),
    "m": ("千葉ロッテマリーンズ", "M"),
    "e": ("東北楽天ゴールデンイーグルス", "E"),
    "l": ("埼玉西武ライオンズ", "L"),
    "b": ("オリックス・バファローズ", "Bs"),
    "h": ("福岡ソフトバンクホークス", "Hs"),
}

BASE = "https://npb.jp"
ROSTER_URL = f"{BASE}/announcement/2026/registered_{{team}}.html"
BIS_PLAYER_URL = f"{BASE}/bis/players/{{player_id}}.html"
NEW_REGISTERED_URL = f"{BASE}/announcement/2026/pn_registered.html"


def extract_player_id(url: str) -> Optional[str]:
    """URLからplayer_idを抽出"""
    if not url:
        return None
    m = re.search(r"/bis/players/(\d+)", url)
    return m.group(1) if m else None


def parse_touchi(touchi_str: str) -> Tuple[str, str]:
    """
    投打文字列を解析して (投, 打) を返す。
    投: R=右, L=左
    打: R=右, L=左, B=両打(スイッチ)
    """
    if not touchi_str or not isinstance(touchi_str, str):
        return ("", "")
    s = touchi_str.strip()
    throw = ""
    bat = ""
    if "右投" in s:
        throw = "R"
    elif "左投" in s:
        throw = "L"
    if "右打" in s:
        bat = "R"
    elif "左打" in s:
        bat = "L"
    elif "両打" in s:
        bat = "B"
    return (throw, bat)


def fetch_html(url: str, retry: int = 3) -> Optional[str]:
    """HTMLを取得"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for attempt in range(retry):
        try:
            if attempt > 0:
                time.sleep(2**attempt)
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except Exception as e:
            print(f"  ⚠ 取得失敗 (試行 {attempt + 1}/{retry}): {url} - {e}")
    return None


def scrape_roster(team_code: str) -> List[Dict[str, Any]]:
    """1球団の支配下選手一覧を取得（選手リンクから逆引きで確実に取得）"""
    team_name, app_code = TEAMS[team_code]
    url = ROSTER_URL.format(team=team_code)
    html = fetch_html(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")  # lxmlが使えない環境にも対応
    rows: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()

    all_links = soup.find_all("a", href=re.compile(r"/bis/players/\d+"))
    for link in all_links:
        player_id = extract_player_id(link.get("href", ""))
        name_ja = (link.get_text() or "").strip()
        if not player_id or not name_ja or player_id in seen_ids:
            continue
        tr = link.find_parent("tr")
        if not tr:
            continue
        cells = tr.find_all("td")
        if len(cells) < 3:
            continue
        first_cell = (cells[0].get_text() or "").strip()
        if first_cell == "▼":
            continue
        pos_text = ""
        uniform = ""
        if first_cell == "△":
            if len(cells) >= 3:
                pos_text = (cells[2].get_text() or "").strip().replace(" ", "")
        else:
            for c in cells[1:4]:
                t = (c.get_text() or "").strip().replace(" ", "")
                if re.search(r"[投捕内外]", t):
                    pos_text = t
                    break
            for c in cells[1:4]:
                t = (c.get_text() or "").strip()
                if re.match(r"^[\d\-→]+$", t) and len(t) <= 5:
                    uniform = t
                    break
        if not pos_text:
            continue
        rows.append({
            "npb_player_id": player_id,
            "name_ja": name_ja,
            "team": team_name,
            "team_code": app_code,
            "position": pos_text,
            "uniform_no": uniform,
        })
    if len(rows) < 30 and len(all_links) > 30:
        print(f"      ⚠ 表パースで{len(rows)}名のみ。リンクから名簿を補完...")
        for link in all_links:
            pid = extract_player_id(link.get("href", ""))
            name = (link.get_text() or "").strip()
            if not pid or not name or pid in seen_ids:
                continue
            seen_ids.add(pid)
            rows.append({
                "npb_player_id": pid,
                "name_ja": name,
                "team": team_name,
                "team_code": app_code,
                "position": "",
                "uniform_no": "",
            })
    return rows


def scrape_new_registered() -> Set[str]:
    """新規支配下選手登録リストからplayer_idのセットを取得"""
    ids: Set[str] = set()
    html = fetch_html(NEW_REGISTERED_URL)
    if not html:
        return ids
    for m in re.finditer(r'/bis/players/(\d+)', html):
        ids.add(m.group(1))
    return ids


def find_roman_name(soup: BeautifulSoup) -> str:
    """BIS選手ページのHTMLから英字表記を探す"""
    try:
        pc_v_name = soup.find("li", id="pc_v_name")
        if pc_v_name:
            name_text = pc_v_name.get_text()
            m = re.search(r"[（(]([A-Za-z\s\.\-\']+)[）)]", name_text)
            if m:
                roman = m.group(1).strip()
                if not any(x in roman.upper() for x in ["NIPPON", "PROFESSIONAL", "BASEBALL", "ORGANIZATION"]):
                    if 2 <= len(roman) <= 50:
                        return " ".join(w.capitalize() for w in roman.split())
        pc_v_kana = soup.find("li", id="pc_v_kana")
        if pc_v_kana:
            kana_text = pc_v_kana.get_text().strip()
            m = re.search(r"[（(]([A-Za-z\s\.\-\']+)[）)]", kana_text)
            if m:
                roman = m.group(1).strip()
                if not any(x in roman.upper() for x in ["NIPPON", "PROFESSIONAL", "BASEBALL", "ORGANIZATION"]):
                    if 2 <= len(roman) <= 50:
                        return " ".join(w.capitalize() for w in roman.split())
            if re.match(r"^[A-Za-z\s\.\-\']+$", kana_text) and not re.search(r"[あ-んア-ン一-龠]", kana_text):
                if 2 <= len(kana_text) <= 50:
                    return " ".join(w.capitalize() for w in kana_text.split())
    except Exception:
        pass
    return ""


def fetch_player_details(player_id: str) -> Tuple[str, str, str]:
    """BIS選手ページから投打と英字名を取得。戻り値: (throw_hand, bat_hand, name_en)"""
    url = BIS_PLAYER_URL.format(player_id=player_id)
    html = fetch_html(url)
    if not html:
        return ("", "", "")
    soup = BeautifulSoup(html, "lxml")
    throw, bat = "", ""
    for tr in soup.find_all("tr"):
        th = tr.find("th")
        td = tr.find("td")
        if th and td and "投打" in (th.get_text() or ""):
            throw, bat = parse_touchi((td.get_text() or "").strip())
            break
    name_en = find_roman_name(soup)
    return (throw, bat, name_en)


FIELDNAMES = [
    "npb_player_id",
    "name_ja",
    "name_en",
    "team",
    "team_code",
    "position",
    "uniform_no",
    "throw_hand",
    "bat_hand",
    "is_new_2026",
]


def save_roster_csv(roster: List[Dict[str, Any]], out_path: Path) -> None:
    """ロスターをCSVに保存"""
    for p in roster:
        p.setdefault("name_en", "")
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        w.writeheader()
        w.writerows(roster)


def load_roster_csv(path: Path) -> List[Dict[str, Any]]:
    """既存CSVからロスターを読み込み"""
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_roster(
    delay: float = 1.0,
    skip_handedness: bool = False,
    resume_from: Optional[Path] = None,
    save_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """名簿を構築"""
    all_players: List[Dict[str, Any]] = []

    if resume_from and resume_from.exists():
        existing = load_roster_csv(resume_from)
        missing = [p for p in existing if not (p.get("throw_hand") and p.get("bat_hand"))]
        if len(existing) >= 100 and missing:
            print("=" * 50)
            print("【再開】既存CSVから投打取得を継続")
            print("=" * 50)
            print(f"   既存: {len(existing)}名 / 未取得: {len(missing)}名\n")
            all_players = existing
            if skip_handedness:
                return all_players
            # Phase 2 のみ実行（未取得分）
            to_fetch = [(i, p) for i, p in enumerate(all_players) if not (p.get("throw_hand") and p.get("bat_hand"))]
            n = len(to_fetch)
            start_time = time.time()
            for idx, (i, p) in enumerate(to_fetch):
                pid = p["npb_player_id"]
                throw, bat, name_en = fetch_player_details(pid)
                p["throw_hand"] = throw or p.get("throw_hand", "")
                p["bat_hand"] = bat or p.get("bat_hand", "")
                if name_en:
                    p["name_en"] = name_en
                done = idx + 1
                if done % 10 == 0 or done == n:
                    elapsed = time.time() - start_time
                    rate = done / elapsed if elapsed > 0 else 0
                    remain = (n - done) / rate if rate > 0 else 0
                    print(f"   {done:4d}/{n} 完了 | 経過 {elapsed:.0f}秒 | 残り約 {remain:.0f}秒")
                if save_path and (done % 50 == 0 or done == n):
                    save_roster_csv(all_players, save_path)
                    if done < n:
                        print(f"   → 進捗を保存 ({done}/{n})")
                time.sleep(delay)
            return all_players

    print("=" * 50)
    print("【Phase 1/2】名簿取得")
    print("=" * 50)
    print("📥 新規支配下登録選手一覧を取得中...")
    new_ids = scrape_new_registered()
    print(f"   → 新規登録: {len(new_ids)}名\n")

    seen_ids: Set[str] = set()
    total_teams = len(TEAMS)

    for idx, (team_code, (team_name, _)) in enumerate(TEAMS.items(), 1):
        print(f"[{idx}/{total_teams}] {team_name} の名簿を取得中...", end=" ", flush=True)
        rows = scrape_roster(team_code)
        added = 0
        for r in rows:
            pid = r["npb_player_id"]
            if pid in seen_ids:
                continue
            seen_ids.add(pid)
            r["is_new_2026"] = "1" if pid in new_ids else "0"
            r["throw_hand"] = ""
            r["bat_hand"] = ""
            all_players.append(r)
            added += 1
        print(f"{len(rows)}名取得 → 累計 {len(all_players)}名")
        time.sleep(delay)

    print(f"\n✅ 名簿取得完了: 合計 {len(all_players)}名\n")

    if skip_handedness:
        print("⏭ 投打取得をスキップ")
        return all_players

    print("=" * 50)
    print("【Phase 2/2】投打（利き手）・英字名の取得")
    print("=" * 50)
    n = len(all_players)
    start_time = time.time()
    for i, p in enumerate(all_players):
        pid = p["npb_player_id"]
        throw, bat, name_en = fetch_player_details(pid)
        p["throw_hand"] = throw
        p["bat_hand"] = bat
        if name_en:
            p["name_en"] = name_en
        done = i + 1
        if done % 10 == 0 or done == n:
            elapsed = time.time() - start_time
            rate = done / elapsed if elapsed > 0 else 0
            remain = (n - done) / rate if rate > 0 else 0
            print(f"   {done:4d}/{n} 完了 | 経過 {elapsed:.0f}秒 | 残り約 {remain:.0f}秒")
        if save_path and (done % 50 == 0 or done == n):
            save_roster_csv(all_players, save_path)
            if done < n:
                print(f"   → 進捗を保存 ({done}/{n})")
        time.sleep(delay)

    return all_players


def load_existing_player_ids(data_dir: Path) -> Set[str]:
    """既存マスターCSVに存在するplayer_idを取得（新規選手判定用）"""
    ids: Set[str] = set()
    for pattern in ["batting_*.csv", "pitching_*.csv"]:
        for f in data_dir.glob(pattern):
            try:
                with open(f, encoding="utf-8") as fp:
                    reader = csv.DictReader(fp)
                    for row in reader:
                        pid = (row.get("player_id") or "").strip()
                        if pid:
                            ids.add(pid)
            except Exception:
                pass
    return ids


def main() -> None:
    parser = argparse.ArgumentParser(description="2026年NPB選手名簿を作成")
    parser.add_argument(
        "--delay",
        type=float,
        default=0.8,
        help="リクエスト間隔（秒）",
    )
    parser.add_argument(
        "--skip-handedness",
        action="store_true",
        help="投打取得をスキップ（名簿のみ）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="_data/npb_roster_2026.csv",
        help="出力CSVパス",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="既存CSVから再開（未取得の投打のみ取得）",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    out_path = root / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)

    resume_from = out_path if args.resume else None
    roster = build_roster(
        delay=args.delay,
        skip_handedness=args.skip_handedness,
        resume_from=resume_from,
        save_path=out_path,
    )

    save_roster_csv(roster, out_path)

    new_count = sum(1 for p in roster if p.get("is_new_2026") == "1")
    print(f"\n✅ 完了: {out_path}")
    print(f"   総数: {len(roster)}名 / 新規登録: {new_count}名")


if __name__ == "__main__":
    main()
