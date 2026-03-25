#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
報告書（2025_new_players_report.csv）に載っている日本人新選手の
ひらがなスクレイピングを再試行する。

- 名前はCSVの「，」（カンマ）の前に存在する。先頭列に「佐々木泰，広島東洋カープ」
  のように全角カンマで名前とチームが繋がっている行は、名前＝「，」の前、チーム＝「，」の後として解釈する。
- NPB公式サイト内で検索して選手を特定し、個人ページ（id=pc_v_kana）からひらがなを取得する。
  検索順: (1) 選手検索 search/result?search_keyword= (2) 現役球団別一覧 rst_*.html (3) 2025年打撃成績 bat_*.html。
  注意: NPBの一覧がJavaScriptで描画されている場合、requests ではリンクが取れず0件になることがある。
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

# 名前比較用: 空白（半角・全角）を除去
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
    """報告書を読み、先頭列に「，」が含まれる場合は名前＝「，」の前・チーム＝「，」の後として正規化する。"""
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
        # 全角カンマ「，」で名前とチームが繋がっている場合
        if '，' in raw_first:
            parts = [p.strip() for p in raw_first.split('，', 1)]
            row[name_col] = parts[0] if parts else ''
            if len(parts) > 1 and parts[1] and not (row.get(team_col) or '').strip():
                row[team_col] = parts[1]
        # チーム欠損の既知補正（坂口翔颯＝横浜DeNA）
        if (row.get(name_col) or '').strip() == '坂口翔颯' and not (row.get(team_col) or '').strip():
            row[team_col] = '横浜DeNAベイスターズ'

    return (header, rows)


def fetch_html(url: str, timeout: Tuple[int, int] = (5, 15)) -> Tuple[Optional[str], int, Optional[str]]:
    try:
        import requests
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=timeout)
        raw = r.content
        for enc in ('utf-8', 'cp932', 'shift_jis', 'euc-jp'):
            try:
                t = raw.decode(enc, errors='strict')
                if re.search(r'[あ-んア-ン一-龠]', t):
                    return t, r.status_code, None
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode('utf-8', errors='replace'), r.status_code, None
    except Exception:
        return None, 0, None


def fetch_kana_from_player_page(player_id: str) -> Optional[str]:
    url = f"https://npb.jp/bis/players/{player_id}.html"
    html, status, _ = fetch_html(url)
    if not html or status != 200:
        return None
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        pc = soup.find('li', id='pc_v_kana')
        if not pc:
            return None
        text = pc.get_text(strip=True)
        if '(' in text or '（' in text:
            m = re.search(r'^([^\(（]+)', text)
            if m:
                text = m.group(1).strip()
        if re.match(r'^[あ-ん・\s]+$', text) and 2 <= len(text) <= 30:
            return text
        if re.search(r'[あ-んア-ン]', text) and not re.search(r'[一-龠A-Za-z]', text) and 2 <= len(text) <= 30:
            return text
    except Exception:
        pass
    return None


# チーム名 → NPB球団別一覧のファイル名（現役選手から探す）
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


def _find_player_id_in_html(html: str, player_name_ja: str) -> Optional[str]:
    """HTML内の選手個人ページリンクのうち、リンクテキストが名前と一致する player_id を返す。"""
    key_norm = normalize_for_match(player_name_ja)
    if not key_norm:
        return None
    # まず正規表現で <a href=".../bis/players/12345.html">選手名</a> を一括抽出（JSで動的生成されていなくても静的にある場合に対応）
    link_pattern = re.compile(
        r'<a[^>]*href=["\']([^"\']*?/bis/players/(\d+)(?:\.html)?)["\'][^>]*>([^<]+)</a>',
        re.IGNORECASE | re.DOTALL
    )
    for m in link_pattern.finditer(html):
        pid, link_text = m.group(2), m.group(3).strip()
        link_text = re.sub(r'\([^)]*\)', '', link_text).strip()  # (巨) 等を除去
        link_norm = normalize_for_match(link_text)
        if not link_norm:
            continue
        if key_norm in link_norm or link_norm in key_norm:
            return pid
        if player_name_ja in link_text or link_text in player_name_ja:
            return pid
    # BeautifulSoupでフォールバック（href が 12345.html のみの相対パスなど）
    id_re = re.compile(r'(?:/bis/players/)?(\d+)(?:\.html)?')
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        for a in soup.find_all('a', href=re.compile(r'\d+')):
            href = a.get('href', '')
            m = id_re.search(href)
            if not m:
                continue
            link_text = a.get_text(strip=True)
            link_text = re.sub(r'\([^)]*\)', '', link_text).strip()
            link_norm = normalize_for_match(link_text)
            if not link_norm:
                continue
            if key_norm in link_norm or link_norm in key_norm:
                return m.group(1)
            if player_name_ja in link_text or link_text in player_name_ja:
                return m.group(1)
    except Exception:
        pass
    return None


def search_player_id_by_npb_search(player_name_ja: str) -> Optional[str]:
    """NPB公式「選手検索」で名前を検索し、ヒットした選手の player_id を返す。"""
    if not player_name_ja or not player_name_ja.strip():
        return None
    keyword = player_name_ja.strip()
    # 現役＋全ての対象で検索（active_flg=Y 現役 / なしで全て）
    for active in ('Y', ''):
        if active:
            url = f"https://npb.jp/bis/players/search/result?search_keyword={quote(keyword, encoding='utf-8')}&active_flg={active}"
        else:
            url = f"https://npb.jp/bis/players/search/result?search_keyword={quote(keyword, encoding='utf-8')}"
        html, status, _ = fetch_html(url)
        if not html or status != 200:
            continue
        pid = _find_player_id_in_html(html, player_name_ja)
        if pid:
            return pid
    return None


def search_player_id_by_team_roster(player_name_ja: str, team: str) -> Optional[str]:
    """NPB「現役選手から探す」球団別一覧ページで名前を探す。"""
    rst = TEAM_TO_RST.get(team)
    if not rst:
        return None
    url = f"https://npb.jp/bis/players/active/{rst}.html"
    html, status, _ = fetch_html(url)
    if not html or status != 200:
        return None
    return _find_player_id_in_html(html, player_name_ja)


# 2025年打撃成績ページから抽出した name -> player_id キャッシュ（2ページだけ取得して再利用）
_2025_batting_name_to_id: Optional[Dict[str, str]] = None


def _get_2025_batting_player_ids() -> Dict[str, str]:
    """2025年 bat_c / bat_p のHTMLから全選手リンクを抽出し、名前（正規化）-> player_id の辞書を返す。"""
    global _2025_batting_name_to_id
    if _2025_batting_name_to_id is not None:
        return _2025_batting_name_to_id
    result: Dict[str, str] = {}
    link_pattern = re.compile(
        r'<a[^>]*href=["\']([^"\']*?/bis/players/(\d+)(?:\.html)?)["\'][^>]*>([^<]+)</a>',
        re.IGNORECASE | re.DOTALL
    )
    for league_code in ('c', 'p'):
        url = f"https://npb.jp/bis/2025/stats/bat_{league_code}.html"
        html, status, _ = fetch_html(url)
        if not html or status != 200:
            continue
        for m in link_pattern.finditer(html):
            pid, link_text = m.group(2), m.group(3).strip()
            link_text = re.sub(r'\([^)]*\)', '', link_text).strip()
            link_norm = normalize_for_match(link_text)
            if link_norm and link_norm not in result:
                result[link_norm] = pid
    _2025_batting_name_to_id = result
    return result


def search_player_id_from_2025_batting(player_name_ja: str) -> Optional[str]:
    """2025年打撃成績ページに登場する選手なら、名前で player_id を返す。"""
    key_norm = normalize_for_match(player_name_ja)
    if not key_norm:
        return None
    mapping = _get_2025_batting_player_ids()
    return mapping.get(key_norm)


def search_player_id_and_fetch_kana(player_name_ja: str, team: str) -> Optional[str]:
    """NPB公式内で検索して選手を特定し、個人ページからひらがなを取得する。
    1) NPB選手検索 2) 球団別一覧 3) 2025年打撃成績ページのリンク一覧。"""
    pid = search_player_id_by_npb_search(player_name_ja)
    if not pid:
        pid = search_player_id_by_team_roster(player_name_ja, team)
    if not pid:
        pid = search_player_id_from_2025_batting(player_name_ja)
    if not pid:
        return None
    return fetch_kana_from_player_page(pid)


# ヘボン式ローマ字変換（phase3 と同様の最小実装）
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


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description='報告書の日本人新選手のひらがなスクレイピング再試行')
    p.add_argument('--rate', type=float, default=1.5)
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    report_path = PROJECT_ROOT / '_data' / 'reports' / '2025_new_players_report.csv'
    calculated_dir = PROJECT_ROOT / '_data' / 'master_csv_calculated'

    if not report_path.exists():
        print(f"ERROR: {report_path} が見つかりません")
        return 1

    header, rows = load_report(report_path)
    for col in ('name_kana', 'player_name_en'):
        if col not in header:
            header.append(col)

    # 2025年打撃成績ページから選手リンクを事前に取得（検索のフォールバック用）
    if not args.dry_run:
        print("  2025年打撃成績ページから選手一覧を取得中...")
        n = len(_get_2025_batting_player_ids())
        print(f"    {n} 件の選手リンクを取得しました")

    updated = 0
    for i, row in enumerate(rows):
        name_ja = (row.get('player_name_ja') or '').strip()
        team = (row.get('team') or '').strip()
        if not name_ja:
            continue
        if is_foreign_row(row):
            continue
        if not team:
            print(f"  スキップ（チームなし）: {name_ja}")
            continue
        current_kana = (row.get('name_kana') or '').strip()
        current_en = (row.get('player_name_en') or '').strip()
        if current_kana and current_en:
            continue
        print(f"  取得試行: {name_ja} ({team}) ...", end=' ', flush=True)
        if args.dry_run:
            print("[DRY-RUN]")
            continue
        kana = search_player_id_and_fetch_kana(name_ja, team)
        if kana:
            row['name_kana'] = kana
            roman = convert_kana_to_romaji(kana)
            if roman:
                row['player_name_en'] = roman
            updated += 1
            print(f"→ {kana} → {roman or '-'}")
        else:
            print("→ 取得できず")
        time.sleep(args.rate)

    if updated > 0:
        with open(report_path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=header, extrasaction='ignore')
            w.writeheader()
            w.writerows(rows)
        print(f"報告書を更新しました: {updated} 件")

        # from_master に報告書の player_name_en を反映
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
            n = 0
            for row in data:
                name_ja = normalize_for_match((row.get('player_name_ja') or '').strip())
                team = (row.get('team') or row.get('Team') or '').strip()
                if (name_ja, team) in report_en:
                    row['player_name_en'] = report_en[(name_ja, team)]
                    n += 1
            if n > 0:
                with open(path, 'w', encoding='utf-8-sig', newline='') as f:
                    w = csv.DictWriter(f, fieldnames=h, extrasaction='ignore')
                    w.writeheader()
                    w.writerows(data)
                print(f"  {path.name}: {n} 行を英字名で更新")

    print("再試行完了.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
