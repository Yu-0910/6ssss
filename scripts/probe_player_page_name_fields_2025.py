#!/usr/bin/env python3
"""
STEP 2: 2025年のNPB公式サイトの選手個人ページから英字名前を取得する方法を調査
2025年対応版: player_idが空の場合はplayer_name_ja + teamの組み合わせで識別
"""

import csv
import random
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup
import time

# プロジェクトルートを取得
script_dir = Path(__file__).parent
project_root = script_dir.parent

# WindowsでのUnicode出力対応
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def extract_identifiers_from_csv(csv_path: Path, limit: Optional[int] = None) -> List[Dict]:
    """CSVからidentifier、player_id、player_name_ja、teamを抽出"""
    identifiers = []
    
    encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
    
    for encoding in encodings:
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    identifier = row.get('identifier', '').strip()
                    player_id = row.get('player_id', '').strip()
                    player_name_ja = row.get('player_name_ja', '').strip()
                    team = row.get('team', '').strip()
                    
                    if identifier:
                        identifiers.append({
                            'identifier': identifier,
                            'player_id': player_id,
                            'player_name_ja': player_name_ja,
                            'team': team,
                        })
                break
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    
    if not identifiers:
        print(f"❌ CSVファイルの読み込みに失敗: {csv_path}")
        return []
    
    # ランダムに選択（limit指定時）
    if limit and len(identifiers) > limit:
        identifiers = random.sample(identifiers, limit)
    
    print(f"✅ identifierを抽出しました: {len(identifiers)}件")
    return identifiers


def generate_url_candidates(identifier: str, player_id: str = '') -> List[str]:
    """identifierから複数のURL候補を生成"""
    base_url = "https://npb.jp/bis/players/"
    candidates = []
    
    # player_idがある場合は、既存のロジックを使用
    if player_id:
        # パターン1: そのまま
        candidates.append(f"{base_url}{player_id}.html")
        
        # パターン2: ゼロ埋め7桁
        try:
            id_int = int(player_id)
            candidates.append(f"{base_url}{id_int:07d}.html")
        except ValueError:
            pass
        
        # パターン3: ゼロ埋め8桁
        try:
            id_int = int(player_id)
            candidates.append(f"{base_url}{id_int:08d}.html")
        except ValueError:
            pass
    else:
        # player_idが空の場合は、identifier（player_name_ja::team）から検索
        # 注意: 2025年のデータはplayer_idが空の場合が多いため、
        # この場合はNPB公式サイトの検索機能を使用するか、別の方法を検討する必要がある
        # 現時点では、player_idがない場合はスキップ
        pass
    
    return candidates


def fetch_html(url: str, timeout: int = 10) -> Tuple[Optional[str], int]:
    """HTMLを取得（HTTP statusも返す）"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        
        # bytesを取得
        raw = response.content
        
        # エンコーディングを自動検出（UTF-8を優先）
        encodings_to_try = ['utf-8', 'cp932', 'shift_jis', 'euc-jp']
        text = None
        
        for enc in encodings_to_try:
            try:
                test_text = raw.decode(enc, errors='strict')
                # 日本語が含まれているか確認（正しくデコードできたか）
                if re.search(r'[あ-んア-ン一-龠]', test_text):
                    text = test_text
                    break
            except (UnicodeDecodeError, LookupError):
                continue
        
        if not text:
            # すべて失敗した場合はutf-8でreplace
            text = raw.decode('utf-8', errors='replace')
        
        return text, response.status_code
    except requests.exceptions.RequestException as e:
        return None, 0


def find_roman_name(html: str) -> Tuple[bool, Optional[str], str]:
    """
    HTMLから英字表記を探す（DOM構造を優先）
    2025年対応: かっこ内スペルを優先的に抽出（外国人選手用）
    
    Returns:
        (found, roman_name, source)
    """
    if not html:
        return False, None, ''
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 優先1: id="pc_v_name" の中の英字名（括弧内）- 外国人選手用（かっこ内スペル）
    # 例: 「ブラッド・エルドレッド　(BRAD ELDRED)」
    pc_v_name = soup.find('li', id='pc_v_name')
    if pc_v_name:
        name_text = pc_v_name.get_text()
        # 全角括弧または半角括弧内の英字名を抽出
        # パターン: 全角括弧「（」または半角括弧「(」内の英字（大文字小文字、スペース、ハイフン、ピリオドを含む）
        match = re.search(r'[（(]([A-Za-z\s\.\-\']+)[）)]', name_text)
        if match:
            roman_name = match.group(1).strip()
            # 組織名を除外
            if not any(exclude in roman_name.upper() for exclude in ['NIPPON', 'PROFESSIONAL', 'BASEBALL', 'ORGANIZATION']):
                if 2 <= len(roman_name) <= 50:
                    # Title Caseに変換（大文字小文字を適切に）
                    title_case = ' '.join(word.capitalize() for word in roman_name.split())
                    return True, title_case, 'pc_v_name_brackets'
    
    # 優先2: id="pc_v_kana" の中の英字名（括弧内）- 日本人選手用
    pc_v_kana = soup.find('li', id='pc_v_kana')
    if pc_v_kana:
        kana_text = pc_v_kana.get_text().strip()
        
        # パターン2-1: 括弧内の英字名を抽出（日本人選手用）
        match = re.search(r'[（(]([A-Za-z\s\.\-\']+)[）)]', kana_text)
        if match:
            roman_name = match.group(1).strip()
            # 組織名を除外
            if not any(exclude in roman_name.upper() for exclude in ['NIPPON', 'PROFESSIONAL', 'BASEBALL', 'ORGANIZATION']):
                if 2 <= len(roman_name) <= 50:
                    # Title Caseに変換
                    title_case = ' '.join(word.capitalize() for word in roman_name.split())
                    return True, title_case, 'pc_v_kana_brackets'
        
        # パターン2-2: 括弧なしで英字名が直接入っている場合（外国人選手用）
        # ひらがな・カタカナ・漢字が含まれていない、英字のみの場合はスペルとして扱う
        if re.match(r'^[A-Za-z\s\.\-\']+$', kana_text) and not re.search(r'[あ-んア-ン一-龠]', kana_text):
            roman_name = kana_text.strip()
            # 組織名を除外
            if not any(exclude in roman_name.upper() for exclude in ['NIPPON', 'PROFESSIONAL', 'BASEBALL', 'ORGANIZATION']):
                if 2 <= len(roman_name) <= 50:
                    # Title Caseに変換
                    title_case = ' '.join(word.capitalize() for word in roman_name.split())
                    return True, title_case, 'pc_v_kana_direct'
    
    return False, None, ''


def find_kana_name(html: str) -> Tuple[bool, Optional[str]]:
    """HTMLから読み（ひらがな・カタカナ）を探す（DOM構造を優先）"""
    if not html:
        return False, None
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # id="pc_v_name" のdiv内のulを探し、li要素を順に確認
    pc_v_name_div = soup.find('div', id='pc_v_name')
    if pc_v_name_div:
        ul = pc_v_name_div.find('ul')
        if ul:
            # id="pc_v_kana"のli要素を探す
            pc_v_kana_li = ul.find('li', id='pc_v_kana')
            if pc_v_kana_li:
                kana_text = pc_v_kana_li.get_text().strip()
                
                # 括弧がある場合（カタカナ + 英字の形式、またはひらがな + 英字の形式）
                if '(' in kana_text or '（' in kana_text:
                    # 括弧前の部分を抽出
                    match = re.search(r'^([^\(（]+)', kana_text)
                    if match:
                        kana_part = match.group(1).strip()
                        # ひらがなのみの場合は優先
                        if re.match(r'^[あ-ん・\s]+$', kana_part) and not re.search(r'[ア-ン一-龠A-Za-z]', kana_part):
                            if 2 <= len(kana_part) <= 30:
                                return True, kana_part
                        # カタカナ・ひらがなが含まれている場合（英字が含まれていないことを確認）
                        elif re.search(r'[あ-んア-ン]', kana_part) and not re.search(r'[一-龠A-Za-z]', kana_part):
                            if 2 <= len(kana_part) <= 30:
                                return True, kana_part
                else:
                    # 括弧がない場合
                    # ひらがなのみ（カタカナや漢字、英字が混ざっていない）を優先
                    if re.match(r'^[あ-ん・\s]+$', kana_text) and not re.search(r'[ア-ン一-龠A-Za-z]', kana_text):
                        if 2 <= len(kana_text) <= 30:
                            return True, kana_text
                    # カタカナが含まれている場合も許容（漢字や英字が混ざっていないことを確認）
                    elif re.search(r'[あ-んア-ン]', kana_text) and not re.search(r'[一-龠A-Za-z]', kana_text):
                        if 2 <= len(kana_text) <= 30:
                            return True, kana_text
    
    return False, None


def probe_player_page(identifier: str, player_id: str = '', player_name_ja: str = '', team: str = '', save_html: bool = False, html_cache_dir: Optional[Path] = None) -> Dict:
    """1つのidentifierについてページを調査"""
    url_candidates = generate_url_candidates(identifier, player_id)
    
    if not url_candidates:
        # player_idが空の場合は、現時点では調査不可
        return {
            'identifier': identifier,
            'player_id': player_id,
            'player_name_ja': player_name_ja,
            'team': team,
            'url_used': '',
            'http_status': 0,
            'found_roman': False,
            'found_kana': False,
            'roman_sample': '',
            'kana_sample': '',
            'roman_source': '',
            'outcome': 'NO_PLAYER_ID',
        }
    
    for url in url_candidates:
        html, status_code = fetch_html(url)
        
        if status_code == 200 and html:
            try:
                found_roman, roman_sample, roman_source = find_roman_name(html)
                found_kana, kana_sample = find_kana_name(html)
                
                # HTMLを保存（オプション）
                if save_html and html_cache_dir and player_id:
                    html_cache_dir.mkdir(parents=True, exist_ok=True)
                    html_path = html_cache_dir / f"{player_id}.html"
                    try:
                        with open(html_path, 'w', encoding='utf-8', newline='') as f:
                            f.write(html)
                    except Exception:
                        pass
                
                # outcome分類
                if found_roman and found_kana:
                    outcome = "FOUND_BOTH"
                elif found_roman:
                    outcome = "FOUND_ROMAN"
                elif found_kana:
                    outcome = "FOUND_KANA"
                else:
                    outcome = "NO_ROMAN_NO_KANA"
                
                return {
                    'identifier': identifier,
                    'player_id': player_id,
                    'player_name_ja': player_name_ja,
                    'team': team,
                    'url_used': url,
                    'http_status': status_code,
                    'found_roman': found_roman,
                    'found_kana': found_kana,
                    'roman_sample': roman_sample or '',
                    'kana_sample': kana_sample or '',
                    'roman_source': roman_source,
                    'outcome': outcome,
                }
            except Exception as e:
                return {
                    'identifier': identifier,
                    'player_id': player_id,
                    'player_name_ja': player_name_ja,
                    'team': team,
                    'url_used': url,
                    'http_status': status_code,
                    'found_roman': False,
                    'found_kana': False,
                    'roman_sample': '',
                    'kana_sample': '',
                    'roman_source': '',
                    'outcome': 'PARSE_FAIL',
                }
        elif status_code == 404:
            continue
        else:
            if url == url_candidates[-1]:
                return {
                    'identifier': identifier,
                    'player_id': player_id,
                    'player_name_ja': player_name_ja,
                    'team': team,
                    'url_used': url,
                    'http_status': status_code,
                    'found_roman': False,
                    'found_kana': False,
                    'roman_sample': '',
                    'kana_sample': '',
                    'roman_source': '',
                    'outcome': f'HTTP_ERROR_{status_code}',
                }
    
    # すべてのURL候補が失敗した場合
    return {
        'identifier': identifier,
        'player_id': player_id,
        'player_name_ja': player_name_ja,
        'team': team,
        'url_used': url_candidates[0] if url_candidates else '',
        'http_status': 404,
        'found_roman': False,
        'found_kana': False,
        'roman_sample': '',
        'kana_sample': '',
        'roman_source': '',
        'outcome': 'HTTP_404',
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='2025年のNPB選手個人ページから読み仮名と英字表記の存在を検証')
    parser.add_argument('--ids', '--input', type=str, default=None, help='入力CSVファイル（デフォルト: output/master/all_player_ids_2025.csv）')
    parser.add_argument('--limit', type=int, default=20, help='テストするidentifierの数（デフォルト: 20）')
    parser.add_argument('--save-html', action='store_true', help='HTMLを保存する（output/html_cache_probe_2025/）')
    parser.add_argument('--output', type=str, default=None, help='出力CSVファイルパス（デフォルト: _data/reports/2025_player_page_structure_investigation.csv）')
    args = parser.parse_args()
    
    # 入力CSVのパスを決定
    if args.ids:
        csv_path = Path(args.ids)
    else:
        csv_path = project_root / 'output' / 'master' / 'all_player_ids_2025.csv'
    
    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return 1
    
    # identifierを抽出
    identifiers = extract_identifiers_from_csv(csv_path, limit=args.limit)
    if not identifiers:
        print("❌ identifierが抽出できませんでした")
        return 1
    
    # 出力パスを決定
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = project_root / '_data' / 'reports'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / '2025_player_page_structure_investigation.csv'
    
    # HTMLキャッシュディレクトリ
    html_cache_dir = None
    if args.save_html:
        html_cache_dir = project_root / 'output' / 'html_cache_probe_2025'
        html_cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 HTML保存先: {html_cache_dir}")
    
    print(f"\n🔍 調査を開始します...")
    print(f"   対象identifier数: {len(identifiers)}")
    print(f"   出力先: {output_path}\n")
    
    # 各identifierについて調査
    results = []
    for i, ident in enumerate(identifiers, 1):
        identifier = ident['identifier']
        player_id = ident.get('player_id', '')
        player_name_ja = ident.get('player_name_ja', '')
        team = ident.get('team', '')
        
        print(f"[{i}/{len(identifiers)}] identifier: {identifier} を調査中...", end=' ', flush=True)
        result = probe_player_page(identifier, player_id, player_name_ja, team, save_html=args.save_html, html_cache_dir=html_cache_dir)
        results.append(result)
        
        # 結果を簡潔に表示
        print(f"→ {result['outcome']} (status: {result['http_status']})")
        if result['found_roman']:
            print(f"      [英字名: {result['roman_sample']}] (source: {result['roman_source']})")
        if result['found_kana']:
            print(f"      [かな: {result['kana_sample']}]")
        
        # リクエスト間隔を空ける（サーバー負荷軽減）
        time.sleep(0.5)
    
    # CSVに出力
    fieldnames = ['identifier', 'player_id', 'player_name_ja', 'team', 'url_used', 'http_status', 
                  'found_roman', 'found_kana', 'roman_sample', 'kana_sample', 'roman_source', 'outcome']
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n✅ 結果を出力しました: {output_path}")
    
    # サマリーを表示
    print("\n📊 サマリー:")
    outcome_counts = {}
    for result in results:
        outcome = result['outcome']
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
    
    for outcome, count in sorted(outcome_counts.items()):
        percentage = (count / len(results)) * 100
        print(f"   {outcome}: {count}件 ({percentage:.1f}%)")
    
    # 詳細統計
    found_roman_count = sum(1 for r in results if r['found_roman'])
    found_kana_count = sum(1 for r in results if r['found_kana'])
    found_both_count = sum(1 for r in results if r['found_roman'] and r['found_kana'])
    http_200_count = sum(1 for r in results if r['http_status'] == 200)
    no_player_id_count = sum(1 for r in results if r['outcome'] == 'NO_PLAYER_ID')
    
    # roman_source別の集計
    roman_source_counts = {}
    for r in results:
        if r['found_roman'] and r['roman_source']:
            source = r['roman_source']
            roman_source_counts[source] = roman_source_counts.get(source, 0) + 1
    
    print(f"\n📈 詳細統計:")
    print(f"   HTTP 200: {http_200_count}件 ({http_200_count/len(results)*100:.1f}%)")
    print(f"   player_idなし: {no_player_id_count}件 ({no_player_id_count/len(results)*100:.1f}%)")
    print(f"   英字表記あり: {found_roman_count}件 ({found_roman_count/len(results)*100:.1f}%)")
    print(f"   ふりがな/かなあり: {found_kana_count}件 ({found_kana_count/len(results)*100:.1f}%)")
    print(f"   両方あり: {found_both_count}件 ({found_both_count/len(results)*100:.1f}%)")
    
    if roman_source_counts:
        print(f"\n📋 英字表記の取得元（roman_source）:")
        for source, count in sorted(roman_source_counts.items()):
            percentage = (count / found_roman_count) * 100 if found_roman_count > 0 else 0
            print(f"   {source}: {count}件 ({percentage:.1f}%)")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
