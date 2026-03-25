#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 3: 英字名（romanName）の充足

- 2024年以前に名前がある選手: 既存CSVから英字名を流用（copy_roman と同様）
- docs/2025_new_players_names_only.md に名前がある新選手のみ:
  - 日本人: ひらがなをNPB公式からスクレイピング → ヘボン式ローマ字に変換して player_name_en に反映
  - 外国人: 表示用スペル（名前の下に表示）を前回例に倣い設定（3例: キャベッジ→Tyler Cabbage, ファビアン→Sandro Fabian, ボスラー→Bosler）
"""

import csv
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# 2025年新外国人選手の「名前の下に表示するスペル」（前回例を踏襲）
# 表示例1: キャベッジ → Tyler Cabbage（名前の下に T. Cabbage）
# 表示例2: ファビアン → Sandro Fabian（名前の下に S. Fabian）
# 表示例3: ボスラー → Bosler（単一表記はそのまま）
FOREIGN_ROMAN_LOOKUP: Dict[str, str] = {
    'キャベッジ': 'Tyler Cabbage',
    'ファビアン': 'Sandro Fabian',
    'モイセエフ・ニキータ': 'Nikita Moiseev',
    'ボスラー': 'Bosler',
    'ドミンゲス': 'Dominguez',
    'モンテロ': 'Montero',
    'ネルソン': 'Nick Nelson',
    'デュプランティエ': 'John Duplantier',
    'ランバート': 'Peter Lambert',
    'ウィンゲンター': 'Trey Wingenter',
    'ハワード': 'Spencer Howard',
    'ヘルナンデス': 'Hernandez',
    'ボーマン': 'Bowman',
    'アビラ': 'Avila',
    'マラー': 'Malla',
    'ウォルターズ': 'Walters',
    'マルテ': 'Marte',
    'サモンズ': 'Summons',
    'ゲレーロ': 'Guerrero',
    'ヤフーレ': 'Yahoore',
    'ディアス': 'Diaz',
    'オリバレス': 'Olivares',
    'ラミレス': 'Ramirez',
    'セデーニョ': 'Cedeno',
    'ネビン': 'Tyler Nevin',
}

# ヘボン式ローマ字変換（ひらがな→ローマ字）- build_player_id_to_roman_full と同様
HEPBURN_TABLE = {
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
    'きゃ': 'kya', 'きゅ': 'kyu', 'きょ': 'kyo',
    'ぎゃ': 'gya', 'ぎゅ': 'gyu', 'ぎょ': 'gyo',
    'しゃ': 'sha', 'しゅ': 'shu', 'しょ': 'sho',
    'じゃ': 'ja', 'じゅ': 'ju', 'じょ': 'jo',
    'ちゃ': 'cha', 'ちゅ': 'chu', 'ちょ': 'cho',
    'にゃ': 'nya', 'にゅ': 'nyu', 'にょ': 'nyo',
    'ひゃ': 'hya', 'ひゅ': 'hyu', 'ひょ': 'hyo',
    'びゃ': 'bya', 'びゅ': 'byu', 'びょ': 'byo',
    'ぴゃ': 'pya', 'ぴゅ': 'pyu', 'ぴょ': 'pyo',
    'みゃ': 'mya', 'みゅ': 'myu', 'みょ': 'myo',
    'りゃ': 'rya', 'りゅ': 'ryu', 'りょ': 'ryo',
    'っ': '',
}
KATAKANA_TO_HIRAGANA = str.maketrans(
    'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポキャキュキョギャギュギョシャシュショジャジュジョチャチュチョニャニュニョヒャヒュヒョビャビュビョピャピュピョミャミュミョリャリュリョッー・',
    'あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽきゃきゅきょぎゃぎゅぎょしゃしゅしょじゃじゅじょちゃちゅちょにゃにゅにょひゃひゅひょびゃびゅびょぴゃぴゅぴょみゃみゅみょりゃりゅりょっー・'
)


def kana_to_romaji(kana: str) -> str:
    """ひらがなをヘボン式ローマ字に変換"""
    if not kana:
        return ''
    kana = kana.translate(KATAKANA_TO_HIRAGANA)
    result = []
    i = 0
    while i < len(kana):
        char = kana[i]
        if char in [' ', '・', '　']:
            result.append(char)
            i += 1
            continue
        if char == 'ー' and result:
            last = result[-1] if result else ''
            if last in ['a', 'i', 'u', 'e', 'o']:
                result.append(last)
            else:
                result.append('')
            i += 1
            continue
        if char == 'っ' and i + 1 < len(kana):
            next_c = kana[i + 1]
            if next_c in HEPBURN_TABLE:
                nr = HEPBURN_TABLE[next_c]
                if nr and nr[0] in 'kstp':
                    result.append(nr[0])
                else:
                    result.append('')
            else:
                result.append('')
            i += 1
            continue
        if i + 1 < len(kana):
            two = kana[i:i+2]
            if two in HEPBURN_TABLE:
                result.append(HEPBURN_TABLE[two])
                i += 2
                continue
        if char in HEPBURN_TABLE:
            result.append(HEPBURN_TABLE[char])
        else:
            result.append(char)
        i += 1
    romaji = ''.join(result)
    romaji = re.sub(r'\s+', ' ', romaji)
    romaji = re.sub(r'・+', ' ', romaji)
    return romaji.strip()


def convert_kana_to_romaji(name_kana: str) -> str:
    """name_kana（'・'区切り）をローマ字に変換して Title Case で返す"""
    if not name_kana:
        return ''
    parts = [p.strip() for p in name_kana.split('・') if p.strip()]
    romaji_parts = []
    for part in parts:
        r = kana_to_romaji(part)
        if r:
            romaji_parts.append(r[0].upper() + r[1:].lower() if len(r) > 1 else r.upper())
    return ' '.join(romaji_parts)


def normalize_name(name: str) -> str:
    if not name:
        return ''
    n = (name or '').strip().replace('\u3000', ' ').replace('　', ' ')
    return re.sub(r'\s+', ' ', n)


def detect_encoding(path: Path) -> str:
    for enc in ('utf-8-sig', 'utf-8', 'shift_jis', 'cp932'):
        try:
            with open(path, 'r', encoding=enc) as f:
                f.read(1024)
            return enc
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return 'utf-8'


def load_csv(path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    enc = detect_encoding(path)
    with open(path, 'r', encoding=enc) as f:
        r = csv.DictReader(f)
        header = list(r.fieldnames or [])
        rows = list(r)
    return (header, rows)


# --- 2024年以前からの英字名流用（copy_roman と同様のロジック）---
def load_roman_from_previous_years(data_dir: Path, years: range) -> Dict[str, str]:
    roman_map: Dict[str, str] = {}
    search_dirs = [
        data_dir / 'master_csv_calculated',
        data_dir / 'master_csv',
        data_dir / 'master_csv__import_1950_2024',
    ]
    pattern = re.compile(r'batting_(\d{4})_(PL|CL)_from_master\.csv$', re.IGNORECASE)
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for csv_file in search_dir.rglob('*.csv'):
            if 'node_modules' in str(csv_file) or '.next' in str(csv_file):
                continue
            m = pattern.search(csv_file.name)
            if not m or int(m.group(1)) not in years:
                continue
            enc = detect_encoding(csv_file)
            try:
                with open(csv_file, 'r', encoding=enc) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        name_ja = (row.get('player_name_ja') or '').strip()
                        team = (row.get('team') or row.get('Team') or '').strip()
                        name_en = (row.get('player_name_en') or row.get('romanName') or row.get('roman_name') or '').strip()
                        if not name_en or (not name_ja and not team):
                            continue
                        key = f"{normalize_name(name_ja)}::{team}"
                        if key not in roman_map or len(name_en) > len(roman_map[key]):
                            roman_map[key] = name_en
            except Exception:
                continue
    return roman_map


def apply_roman_from_previous_to_2025(csv_path: Path, roman_map: Dict[str, str]) -> int:
    """2025の from_master のうち、player_name_en が空の行にのみ流用して適用。更新件数を返す。"""
    header, rows = load_csv(csv_path)
    en_key = 'player_name_en'
    if en_key not in header:
        header.append(en_key)
    updated = 0
    for row in rows:
        if (row.get(en_key) or '').strip():
            continue
        name_ja = (row.get('player_name_ja') or '').strip()
        team = (row.get('team') or row.get('Team') or '').strip()
        if not name_ja or not team:
            continue
        key = f"{normalize_name(name_ja)}::{team}"
        if key in roman_map:
            row[en_key] = roman_map[key]
            updated += 1
    if updated > 0:
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=header, extrasaction='ignore')
            w.writeheader()
            w.writerows(rows)
    return updated


# --- NPB ひらがなスクレイピング（generate_2025_new_players_report と同様）---
def fetch_html(url: str, timeout: Tuple[int, int] = (5, 15)) -> Tuple[Optional[str], int, Optional[str]]:
    try:
        import requests
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(url, headers=headers, timeout=timeout)
        raw = r.content
        for enc in ('utf-8', 'cp932', 'shift_jis', 'euc-jp'):
            try:
                t = raw.decode(enc, errors='strict')
                if re.search(r'[あ-んア-ン一-龠]', t):
                    return t, r.status_code, None
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode('utf-8', errors='replace'), r.status_code, None
    except Exception as e:
        return None, 0, str(e)


def fetch_kana_from_player_page(player_id: str) -> Optional[str]:
    """選手個人ページからひらがな（id=pc_v_kana）を取得"""
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


def search_player_id_and_fetch_kana(player_name_ja: str, team: str) -> Optional[str]:
    """NPB 2025成績ページから選手リンクを探し、個人ページでひらがなを取得"""
    league = 'CL' if any(t in team for t in ['巨人', '阪神', 'DeNA', '横浜', '広島', '中日', 'ヤクルト']) else 'PL'
    lc = 'c' if league == 'CL' else 'p'
    url = f"https://npb.jp/bis/2025/stats/bat_{lc}.html"
    html, status, _ = fetch_html(url)
    if not html or status != 200:
        return None
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        for a in soup.find_all('a', href=re.compile(r'/bis/players/(\d+)\.html')):
            if player_name_ja in a.get_text(strip=True) or a.get_text(strip=True) in player_name_ja:
                m = re.search(r'/bis/players/(\d+)\.html', a.get('href', ''))
                if m:
                    return fetch_kana_from_player_page(m.group(1))
    except Exception:
        pass
    return None


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
    parser = argparse.ArgumentParser(description='Phase 3: 2025年英字名充足（既存流用＋新選手のみひらがな取得→ローマ字）')
    parser.add_argument('--data-dir', type=str, default=None)
    parser.add_argument('--rate', type=float, default=1.5, help='スクレイピング間隔（秒）')
    parser.add_argument('--skip-scrape', action='store_true', help='スクレイピングをスキップ（既存流用と外国人LOOKUPのみ）')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    data_dir = Path(args.data_dir) if args.data_dir else PROJECT_ROOT / '_data'
    report_path = PROJECT_ROOT / '_data' / 'reports' / '2025_new_players_report.csv'
    calculated_dir = data_dir / 'master_csv_calculated'

    if not report_path.exists():
        print(f"ERROR: 報告書が見つかりません: {report_path}")
        return 1

    # Step 1: 2024年以前の英字名を流用
    print("Phase 3: 英字名（romanName）充足")
    print("  Step 1: 2024年以前に名前がある選手の英字名を流用...")
    roman_map = load_roman_from_previous_years(data_dir, range(1950, 2025))
    print(f"    過去データから {len(roman_map)} 件の英字名を読み込みました")
    for league in ('CL', 'PL'):
        path = calculated_dir / f'batting_2025_{league}_from_master.csv'
        if path.exists():
            n = apply_roman_from_previous_to_2025(path, roman_map)
            print(f"    {path.name}: {n} 件を流用で更新")
    if args.dry_run:
        print("  [DRY-RUN] ここまでで終了")
        return 0

    # Step 2: 報告書の「新選手」のみ処理（日本人＝ひらがな取得→ローマ字、外国人＝LOOKUP）
    header, report_rows = load_csv(report_path)
    for col in ('name_kana', 'player_name_en'):
        if col not in header:
            header.append(col)

    updated_report = 0
    for row in report_rows:
        name_ja = (row.get('player_name_ja') or '').strip()
        team = (row.get('team') or '').strip()
        if not name_ja or not team:
            continue
        current_en = (row.get('player_name_en') or '').strip()
        is_foreign = is_foreign_row(row)

        if is_foreign:
            # 外国人: 表示用スペル（名前の下に表示）をLOOKUPで設定
            roman = FOREIGN_ROMAN_LOOKUP.get(name_ja) or current_en
            if roman and roman != current_en:
                row['player_name_en'] = roman
                updated_report += 1
            continue

        # 日本人: 既に英字名があればスキップ（2024年以前で流用済みの可能性）
        if current_en:
            continue
        # ひらがな取得 → ローマ字変換
        current_kana = (row.get('name_kana') or '').strip()
        if not args.skip_scrape and not current_kana:
            kana = search_player_id_and_fetch_kana(name_ja, team)
            if kana:
                row['name_kana'] = kana
                current_kana = kana
            time.sleep(args.rate)
        if current_kana:
            roman = convert_kana_to_romaji(current_kana)
            if roman and roman != current_en:
                row['player_name_en'] = roman
                updated_report += 1

    if updated_report > 0:
        with open(report_path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=header, extrasaction='ignore')
            w.writeheader()
            w.writerows(report_rows)
        print(f"  報告書を更新しました: {updated_report} 件")

    # Step 3: 報告書の player_name_en を 2025 from_master に反映（該当行のみ上書き）
    print("  Step 3: 報告書の英字名を from_master に反映...")
    report_en_map: Dict[Tuple[str, str], str] = {}
    for row in report_rows:
        name_ja = (row.get('player_name_ja') or '').strip()
        team = (row.get('team') or '').strip()
        en = (row.get('player_name_en') or '').strip()
        if name_ja and team and en:
            report_en_map[(normalize_name(name_ja), team)] = en

    for league in ('CL', 'PL'):
        path = calculated_dir / f'batting_2025_{league}_from_master.csv'
        if not path.exists():
            continue
        h, rows = load_csv(path)
        if 'player_name_en' not in h:
            h.append('player_name_en')
        count = 0
        for row in rows:
            name_ja = normalize_name((row.get('player_name_ja') or '').strip())
            team = (row.get('team') or row.get('Team') or '').strip()
            key = (name_ja, team)
            if key in report_en_map:
                row['player_name_en'] = report_en_map[key]
                count += 1
        if count > 0:
            with open(path, 'w', encoding='utf-8-sig', newline='') as f:
                w = csv.DictWriter(f, fieldnames=h, extrasaction='ignore')
                w.writeheader()
                w.writerows(rows)
            print(f"    {path.name}: {count} 行を報告書の英字名で更新")

    print("Phase 3 完了.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
