#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
報告書（2025_new_players_report.csv）の日本人新選手について、
Playwright で NPB 公式サイトを開きひらがなを取得する。

NPB の選手検索・球団別一覧が JavaScript で描画されているため、
requests ではリンクが取れない場合にこのスクリプトを使用する。

使い方:
  pip install playwright
  playwright install chromium
  python scripts/retry_kana_scrape_2025_playwright.py [--dry-run] [--rate 2.0]
"""

import csv
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


def normalize_for_match(s: str) -> str:
    if not s:
        return ''
    return re.sub(r'[\s　\u3000]+', '', (s or '').strip())


def detect_encoding(path: Path) -> str:
    for enc in ('utf-8-sig', 'utf-8', 'shift_jis', 'cp932'):
        try:
            with open(path, 'r', encoding=enc) as f:
                f.read(1024)
            return enc
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return 'utf-8'


def load_report(path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    enc = detect_encoding(path)
    with open(path, 'r', encoding=enc) as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or [])
        rows = list(reader)

    name_col = 'player_name_ja'
    team_col = 'team'
    for row in rows:
        raw_first = (row.get(name_col) or '').strip()
        if not raw_first:
            continue
        if '，' in raw_first:
            parts = [p.strip() for p in raw_first.split('，', 1)]
            row[name_col] = parts[0] if parts else ''
            if len(parts) > 1 and parts[1] and not (row.get(team_col) or '').strip():
                row[team_col] = parts[1]
        if (row.get(name_col) or '').strip() == '坂口翔颯' and not (row.get(team_col) or '').strip():
            row[team_col] = '横浜DeNAベイスターズ'

    return (header, rows)


# チーム名 → NPB 球団別一覧のファイル名
TEAM_TO_RST: Dict[str, str] = {
    '読売ジャイアンツ': 'rst_g',
    '阪神タイガース': 'rst_t',
    '横浜DeNAベイスターズ': 'rst_db',
    '広島東洋カープ': 'rst_c',
    '東京ヤクルトスワローズ': 'rst_s',
    '中日ドラゴンズ': 'rst_d',
    '福岡ソフトバンクホークス': 'rst_h',
    '北海道日本ハムファイターズ': 'rst_f',
    '千葉ロッテマリーンズ': 'rst_m',
    '東北楽天ゴールデンイーグルス': 'rst_e',
    'オリックス・バファローズ': 'rst_b',
    '埼玉西武ライオンズ': 'rst_l',
}

# ヘボン式ローマ字
HEPBURN = {
    'あ': 'a', 'い': 'i', 'う': 'u', 'え': 'e', 'お': 'o',
    'か': 'ka', 'き': 'ki', 'く': 'ku', 'け': 'ke', 'こ': 'ko',
    'が': 'ga', 'ぎ': 'gi', 'ぐ': 'gu', 'げ': 'ge', 'ご': 'go',
    'さ': 'sa', 'し': 'shi', 'す': 'su', 'せ': 'se', 'そ': 'so',
    'ざ': 'za', 'じ': 'ji', 'ず': 'zu', 'ぜ': 'ze', 'ぞ': 'zo',
    'た': 'ta', 'ち': 'chi', 'つ': 'tsu', 'て': 'te', 'と': 'to',
    'だ': 'da', 'ぢ': 'ji', 'づ': 'zu', 'で': 'de', 'ど': 'do',
    'な': 'na', 'に': 'ni', 'ぬ': 'nu', 'ね': 'ne', 'の': 'no',
    'は': 'ha', 'ひ': 'hi', 'ふ': 'fu', 'へ': 'he', 'ほ': 'ho',
    'ば': 'ba', 'び': 'bi', 'ぶ': 'bu', 'べ': 'be', 'ぼ': 'bo',
    'ぱ': 'pa', 'ぴ': 'pi', 'ぷ': 'pu', 'ぺ': 'pe', 'ぽ': 'po',
    'ま': 'ma', 'み': 'mi', 'む': 'mu', 'め': 'me', 'も': 'mo',
    'や': 'ya', 'ゆ': 'yu', 'よ': 'yo',
    'ら': 'ra', 'り': 'ri', 'る': 'ru', 'れ': 're', 'ろ': 'ro',
    'わ': 'wa', 'を': 'wo', 'ん': 'n',
    'きゃ': 'kya', 'きゅ': 'kyu', 'きょ': 'kyo', 'しゃ': 'sha', 'しゅ': 'shu', 'しょ': 'sho',
    'ちゃ': 'cha', 'ちゅ': 'chu', 'ちょ': 'cho', 'にゃ': 'nya', 'にゅ': 'nyu', 'にょ': 'nyo',
    'ひゃ': 'hya', 'ひゅ': 'hyu', 'ひょ': 'hyo', 'みゃ': 'mya', 'みゅ': 'myu', 'みょ': 'myo',
    'りゃ': 'rya', 'りゅ': 'ryu', 'りょ': 'ryo', 'ぎゃ': 'gya', 'ぎゅ': 'gyu', 'ぎょ': 'gyo',
    'じゃ': 'ja', 'じゅ': 'ju', 'じょ': 'jo', 'びゃ': 'bya', 'びゅ': 'byu', 'びょ': 'byo',
    'ぴゃ': 'pya', 'ぴゅ': 'pyu', 'ぴょ': 'pyo', 'っ': '',
}
K2H = str.maketrans(
    'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポキャキュキョギャギュギョシャシュショジャジュジョチャチュチョニャニュニョヒャヒュヒョビャビュビョピャピュピョミャミュミョリャリュリョッー・',
    'あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽきゃきゅきょぎゃぎゅぎょしゃしゅしょじゃじゅじょちゃちゅちょにゃにゅにょひゃひゅひょびゃびゅびょぴゃぴゅぴょみゃみゅみょりゃりゅりょっー・'
)


def kana_to_romaji(kana: str) -> str:
    if not kana:
        return ''
    kana = kana.translate(K2H)
    out = []
    i = 0
    while i < len(kana):
        c = kana[i]
        if c in ' ・　':
            out.append(' ')
            i += 1
            continue
        if c == 'ー' and out:
            last = out[-1]
            if last in ['a', 'i', 'u', 'e', 'o']:
                out.append(last)
            i += 1
            continue
        if c == 'っ' and i + 1 < len(kana):
            nc = kana[i + 1]
            if nc in HEPBURN and HEPBURN[nc] and HEPBURN[nc][0] in 'kstp':
                out.append(HEPBURN[nc][0])
            i += 1
            continue
        if i + 1 < len(kana) and kana[i:i+2] in HEPBURN:
            out.append(HEPBURN[kana[i:i+2]])
            i += 2
            continue
        if c in HEPBURN:
            out.append(HEPBURN[c])
        i += 1
    r = ''.join(out)
    r = re.sub(r'\s+', ' ', re.sub(r'・+', ' ', r)).strip()
    return r


def convert_kana_to_romaji(name_kana: str) -> str:
    if not name_kana:
        return ''
    parts = [p.strip() for p in name_kana.split('・') if p.strip()]
    out = []
    for p in parts:
        r = kana_to_romaji(p)
        if r:
            out.append(r[0].upper() + r[1:].lower() if len(r) > 1 else r.upper())
    return ' '.join(out)


def _save_report_and_from_master(
    header: List[str],
    rows: List[Dict[str, Any]],
    report_path: Path,
    calculated_dir: Path,
) -> None:
    """報告書 CSV と from_master の player_name_en を保存する。"""
    with open(report_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    report_en = {}
    for row in rows:
        n = (row.get('player_name_ja') or '').strip()
        t = (row.get('team') or '').strip()
        e = (row.get('player_name_en') or '').strip()
        if n and t and e:
            report_en[(normalize_for_match(n), t)] = e
    for league in ('CL', 'PL'):
        path = calculated_dir / f'batting_2025_{league}_from_master.csv'
        if not path.exists():
            continue
        enc = detect_encoding(path)
        with open(path, 'r', encoding=enc) as f:
            r = csv.DictReader(f)
            h = list(r.fieldnames or [])
            data = list(r)
        if 'player_name_en' not in h:
            h.append('player_name_en')
        for row in data:
            name_ja = normalize_for_match((row.get('player_name_ja') or '').strip())
            team = (row.get('team') or row.get('Team') or '').strip()
            if (name_ja, team) in report_en:
                row['player_name_en'] = report_en[(name_ja, team)]
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=h, extrasaction='ignore')
            w.writeheader()
            w.writerows(data)


def is_foreign_row(row: Dict[str, Any]) -> bool:
    v = (row.get('is_foreign') or '').strip().upper()
    if v == 'YES' or v == '1':
        return True
    name = (row.get('player_name_ja') or '').strip()
    if re.match(r'^[ァ-ヶ・\s]+$', name) and not re.search(r'[あ-ん一-龠]', name):
        return True
    if re.search(r'[A-Za-z]', name):
        return True
    return False


def _match_player_name(link_text: str, player_name_ja: str) -> bool:
    link_clean = re.sub(r'\([^)]*\)', '', link_text).strip()
    key_norm = normalize_for_match(player_name_ja)
    link_norm = normalize_for_match(link_clean)
    if not key_norm or not link_norm:
        return False
    if key_norm in link_norm or link_norm in key_norm:
        return True
    if player_name_ja in link_text or link_text in player_name_ja:
        return True
    return False


def _extract_player_id_from_href(href: str) -> Optional[str]:
    m = re.search(r'/bis/players/(\d+)(?:\.html)?', href)
    return m.group(1) if m else None


def search_player_id_playwright(page, player_name_ja: str, team: str) -> Optional[str]:
    """
    Playwright の page で (1) 選手検索 (2) 球団別一覧 の順に開き、
    名前と一致する選手リンクから player_id を返す。
    """
    keyword = (player_name_ja or '').strip()
    if not keyword:
        return None

    # (1) 選手検索
    for active in ('Y', ''):
        url = (
            f"https://npb.jp/bis/players/search/result?search_keyword={quote(keyword, encoding='utf-8')}&active_flg={active}"
            if active
            else f"https://npb.jp/bis/players/search/result?search_keyword={quote(keyword, encoding='utf-8')}"
        )
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=15000)
            page.wait_for_timeout(2000)
            links = page.query_selector_all('a[href*="/bis/players/"]')
            for a in links:
                href = a.get_attribute('href') or ''
                pid = _extract_player_id_from_href(href)
                if not pid:
                    continue
                text = (a.inner_text() or '').strip()
                if _match_player_name(text, player_name_ja):
                    return pid
        except Exception:
            continue

    # (2) 球団別一覧
    rst = TEAM_TO_RST.get(team)
    if rst:
        url = f"https://npb.jp/bis/players/active/{rst}.html"
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=15000)
            page.wait_for_timeout(2000)
            links = page.query_selector_all('a[href*="/bis/players/"]')
            for a in links:
                href = a.get_attribute('href') or ''
                pid = _extract_player_id_from_href(href)
                if not pid:
                    continue
                text = (a.inner_text() or '').strip()
                if _match_player_name(text, player_name_ja):
                    return pid
        except Exception:
            pass

    return None


def fetch_kana_from_player_page_playwright(page, player_id: str) -> Optional[str]:
    url = f"https://npb.jp/bis/players/{player_id}.html"
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        page.wait_for_timeout(1000)
        el = page.query_selector('li#pc_v_kana')
        if not el:
            return None
        text = (el.inner_text() or '').strip()
        if '(' in text or '（' in text:
            m = re.search(r'^([^\(（]+)', text)
            if m:
                text = m.group(1).strip()
        if re.match(r'^[あ-ん・\s]+$', text) and 2 <= len(text) <= 30:
            return text
        if re.search(r'[あ-んア-ン]', text) and not re.search(r'[一-龠A-Za-z]', text) and 2 <= len(text) <= 30:
            return text
        return text if (2 <= len(text) <= 30) else None
    except Exception:
        return None


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description='Playwright で報告書の日本人新選手のひらがなを取得')
    p.add_argument('--rate', type=float, default=2.0, help='リクエスト間の待機秒数')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright がインストールされていません。")
        print("  pip install playwright")
        print("  playwright install chromium")
        return 1

    report_path = PROJECT_ROOT / '_data' / 'reports' / '2025_new_players_report.csv'
    calculated_dir = PROJECT_ROOT / '_data' / 'master_csv_calculated'

    if not report_path.exists():
        print(f"ERROR: {report_path} が見つかりません")
        return 1

    header, rows = load_report(report_path)
    for col in ('name_kana', 'player_name_en'):
        if col not in header:
            header.append(col)

    to_process = [
        (i, row)
        for i, row in enumerate(rows)
        if (row.get('player_name_ja') or '').strip()
        and not is_foreign_row(row)
        and (row.get('team') or '').strip()
        and (not (row.get('name_kana') or '').strip() or not (row.get('player_name_en') or '').strip())
    ]

    if not to_process:
        print("ひらがな／英字名を取得する対象がありません。")
        return 0

    print(f"対象: 日本人新選手 {len(to_process)} 名（Playwright 使用）")
    if args.dry_run:
        for i, row in to_process[:5]:
            print(f"  DRY-RUN: {(row.get('player_name_ja') or '').strip()} ({(row.get('team') or '').strip()})")
        if len(to_process) > 5:
            print(f"  ... 他 {len(to_process) - 5} 名")
        return 0

    updated = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            for i, row in to_process:
                name_ja = (row.get('player_name_ja') or '').strip()
                team = (row.get('team') or '').strip()
                print(f"  取得試行: {name_ja} ({team}) ...", end=' ', flush=True)
                pid = search_player_id_playwright(page, name_ja, team)
                if not pid:
                    print("→ 選手ID取得できず")
                    time.sleep(args.rate)
                    continue
                kana = fetch_kana_from_player_page_playwright(page, pid)
                if kana:
                    row['name_kana'] = kana
                    roman = convert_kana_to_romaji(kana)
                    if roman:
                        row['player_name_en'] = roman
                    updated += 1
                    print(f"→ {kana} → {roman or '-'}")
                    # 進捗を都度保存（タイムアウト時も取得分を残す）
                    _save_report_and_from_master(header, rows, report_path, calculated_dir)
                else:
                    print("→ ひらがな取得できず")
                time.sleep(args.rate)
        finally:
            browser.close()

    if updated > 0:
        print(f"報告書を更新しました: 合計 {updated} 件")

    print("Playwright による再試行完了.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
