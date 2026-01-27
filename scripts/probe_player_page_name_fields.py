#!/usr/bin/env python3
"""
NPB公式選手個人ページから「読み仮名（ふりがな/かな）」と「英字表記（romanName）」の存在を検証するスクリプト
"""

import csv
import random
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import time

# プロジェクトルートを取得
script_dir = Path(__file__).parent
project_root = script_dir.parent


def extract_player_ids(csv_path: Path, limit: Optional[int] = None) -> List[str]:
    """CSVからplayer_idを抽出（ユニーク、ランダム選択）"""
    player_ids = set()
    
    encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
    csv_data = None
    
    for encoding in encodings:
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    player_id = row.get('player_id', '').strip()
                    if player_id:
                        player_ids.add(player_id)
                csv_data = list(player_ids)
                break
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    
    if not csv_data:
        print(f"❌ CSVファイルの読み込みに失敗: {csv_path}")
        return []
    
    # ランダムに選択
    if limit and len(csv_data) > limit:
        csv_data = random.sample(csv_data, limit)
    
    print(f"✅ player_idを抽出しました: {len(csv_data)}件")
    return csv_data


def generate_url_candidates(player_id: str) -> List[str]:
    """player_idから複数のURL候補を生成"""
    base_url = "https://npb.jp/bis/players/"
    candidates = []
    
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
    
    # パターン4: ゼロ埋め6桁
    try:
        id_int = int(player_id)
        candidates.append(f"{base_url}{id_int:06d}.html")
    except ValueError:
        pass
    
    return candidates


def fetch_html(url: str, timeout: int = 10) -> Tuple[Optional[str], int]:
    """HTMLを取得（HTTP statusも返す）
    
    NPBサイトのHTMLはUTF-8でエンコードされているが、
    response.encodingが誤判定されることがあるため、
    response.content（bytes）を直接デコードする。
    """
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
        print(f"⚠️  URL取得エラー ({url}): {e}")
        return None, 0


def find_roman_name(html: str) -> Tuple[bool, Optional[str]]:
    """HTMLから英字表記を探す（DOM構造を優先）"""
    if not html:
        return False, None
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 優先1: id="pc_v_kana" の中の英字名（括弧内）
    # 例: <li id="pc_v_kana">リバン・モイネロ (LIVAN MOINELO)</li>
    pc_v_kana = soup.find('li', id='pc_v_kana')
    if pc_v_kana:
        kana_text = pc_v_kana.get_text()
        # 括弧内の英字名を抽出
        match = re.search(r'\(([A-Z\s\.\-]+)\)', kana_text)
        if match:
            roman_name = match.group(1).strip()
            # 組織名を除外（"Nippon Professional Baseball"など）
            if not any(exclude in roman_name.upper() for exclude in ['NIPPON', 'PROFESSIONAL', 'BASEBALL', 'ORGANIZATION']):
                if 2 <= len(roman_name) <= 50:
                    return True, roman_name
    
    # 優先2: titleタグから抽出（選手名が含まれている場合）
    if soup.title:
        title_text = soup.title.get_text()
        # タイトル形式: "ロイモイネロ（福岡ソフトバンクホークス） | 個人年度別成績"
        # 英字名が含まれている場合を探す
        roman_match = re.search(r'\(([A-Z][A-Z\s\.\-]+)\)', title_text)
        if roman_match:
            roman_name = roman_match.group(1).strip()
            if not any(exclude in roman_name.upper() for exclude in ['NIPPON', 'PROFESSIONAL', 'BASEBALL', 'ORGANIZATION']):
                if 2 <= len(roman_name) <= 50:
                    return True, roman_name
    
    # 優先3: og:titleから抽出
    og_title = soup.find('meta', property='og:title')
    if og_title:
        og_content = og_title.get('content', '')
        roman_match = re.search(r'\(([A-Z][A-Z\s\.\-]+)\)', og_content)
        if roman_match:
            roman_name = roman_match.group(1).strip()
            if not any(exclude in roman_name.upper() for exclude in ['NIPPON', 'PROFESSIONAL', 'BASEBALL', 'ORGANIZATION']):
                if 2 <= len(roman_name) <= 50:
                    return True, roman_name
    
    # フォールバック: 一般的なパターンマッチング（mainコンテンツ内）
    contents = soup.find('div', class_='contents') or soup.find('main') or soup
    if contents:
        # 英字表記のパターン
        roman_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b',  # "John Smith" 形式
            r'\b([A-Z]\.\s*[A-Z][a-z]+)\b',  # "T. Yamada" 形式
            r'\b([A-Z][a-z]+-[A-Z][a-z]+)\b',  # "Kenji-Murakami" 形式
        ]
        
        content_text = contents.get_text()
        for pattern in roman_patterns:
            matches = re.findall(pattern, content_text)
            for match in matches:
                if not any(exclude in match.upper() for exclude in ['NIPPON', 'PROFESSIONAL', 'BASEBALL', 'ORGANIZATION']):
                    if 3 <= len(match) <= 50:
                        return True, match.strip()
    
    return False, None


def find_kana_name(html: str) -> Tuple[bool, Optional[str]]:
    """HTMLから読み（ひらがな）を探す（DOM構造を優先）"""
    if not html:
        return False, None
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 優先1: id="pc_v_name" のdiv内のulを探し、li要素を順に確認
    # 構造例1: <div id="pc_v_name"><ul><li id="pc_v_name">漢字名</li><li id="pc_v_kana">ひらがな読み</li></ul></div>
    # 構造例2: <div id="pc_v_name"><ul><li id="pc_v_name">漢字名</li><li id="pc_v_kana">カタカナ (英字)</li></ul></div>
    pc_v_name_div = soup.find('div', id='pc_v_name')
    if pc_v_name_div:
        ul = pc_v_name_div.find('ul')
        if ul:
            # id="pc_v_kana"のli要素を探す
            pc_v_kana_li = ul.find('li', id='pc_v_kana')
            if pc_v_kana_li:
                kana_text = pc_v_kana_li.get_text().strip()
                
                # 括弧がある場合（カタカナ + 英字の形式）
                if '(' in kana_text:
                    # 括弧前の部分を抽出（カタカナの可能性）
                    match = re.search(r'^([^\(]+)', kana_text)
                    if match:
                        kana_part = match.group(1).strip()
                        # ひらがなのみの場合は優先
                        if re.match(r'^[あ-ん・\s]+$', kana_part) and not re.search(r'[ア-ン一-龠]', kana_part):
                            if 2 <= len(kana_part) <= 30:
                                return True, kana_part
                        # カタカナ・ひらがなが含まれている場合
                        elif re.search(r'[あ-んア-ン]', kana_part):
                            if 2 <= len(kana_part) <= 30:
                                return True, kana_part
                else:
                    # 括弧がない場合（ひらがなの読みの可能性が高い）
                    # ひらがなのみ（カタカナや漢字が混ざっていない）を優先
                    if re.match(r'^[あ-ん・\s]+$', kana_text) and not re.search(r'[ア-ン一-龠]', kana_text):
                        if 2 <= len(kana_text) <= 30:
                            return True, kana_text
                    # カタカナが含まれている場合も許容
                    elif re.search(r'[あ-んア-ン]', kana_text) and not re.search(r'[一-龠]', kana_text):
                        if 2 <= len(kana_text) <= 30:
                            return True, kana_text
            
            # id="pc_v_kana"がない場合、ul内のli要素を順に確認
            li_elements = ul.find_all('li', recursive=False)
            for li in li_elements:
                li_text = li.get_text().strip()
                li_id = li.get('id', '')
                
                # id="pc_v_name"以外のli要素で、ひらがなのみを探す
                if li_id != 'pc_v_name' and li_id != 'pc_v_no' and li_id != 'pc_v_team':
                    if re.match(r'^[あ-ん・\s]+$', li_text) and not re.search(r'[ア-ン一-龠]', li_text):
                        if 2 <= len(li_text) <= 30:
                            return True, li_text
    
    # 優先2: id="pc_v_name" のli要素の次の兄弟要素を確認
    pc_v_name_li = soup.find('li', id='pc_v_name')
    if pc_v_name_li:
        # 次の兄弟要素を確認
        next_sibling = pc_v_name_li.find_next_sibling('li')
        if next_sibling:
            next_text = next_sibling.get_text().strip()
            # ひらがなのみを探す
            if re.match(r'^[あ-ん・\s]+$', next_text) and not re.search(r'[ア-ン一-龠]', next_text):
                if 2 <= len(next_text) <= 30:
                    return True, next_text
    
    return False, None


def probe_player_page(player_id: str, save_html: bool = False, html_cache_dir: Optional[Path] = None) -> Dict:
    """1つのplayer_idについてページを調査"""
    url_candidates = generate_url_candidates(player_id)
    
    for url in url_candidates:
        html, status_code = fetch_html(url)
        
        if status_code == 200 and html:
            # HTMLのパースを試す（fetch_htmlが返した正しくデコード済みのtextを使用）
            try:
                found_roman, roman_sample = find_roman_name(html)
                found_kana, kana_sample = find_kana_name(html)
                
                # デバッグ用：kana_sampleのreprを出力（1件のみ）
                if kana_sample:
                    print(f"      [DEBUG kana_sample: {repr(kana_sample[:50])}]", end=' ', flush=True)
                
                # HTMLを保存（オプション）- デコード済みtextをUTF-8で保存
                if save_html and html_cache_dir:
                    html_cache_dir.mkdir(parents=True, exist_ok=True)
                    html_path = html_cache_dir / f"{player_id}.html"
                    try:
                        with open(html_path, 'w', encoding='utf-8', newline='') as f:
                            f.write(html)
                        print(f"      [HTML保存: {html_path}]", end=' ', flush=True)
                    except Exception as e:
                        print(f"      [HTML保存失敗: {e}]", end=' ', flush=True)
                
                # outcome分類
                if found_roman and found_kana:
                    outcome = "FOUND_BOTH"
                elif found_roman:
                    outcome = "FOUND_ROMAN"
                elif found_kana:
                    outcome = "FOUND_KANA"
                elif not found_roman and not found_kana:
                    outcome = "NO_ROMAN_NO_KANA"
                else:
                    outcome = "UNKNOWN"
                
                return {
                    'player_id': player_id,
                    'url_used': url,
                    'http_status': status_code,
                    'found_roman': found_roman,
                    'found_kana': found_kana,
                    'roman_sample': roman_sample or '',
                    'kana_sample': kana_sample or '',
                    'outcome': outcome,
                }
            except Exception as e:
                print(f"⚠️  HTMLパースエラー ({url}): {e}")
                return {
                    'player_id': player_id,
                    'url_used': url,
                    'http_status': status_code,
                    'found_roman': False,
                    'found_kana': False,
                    'roman_sample': '',
                    'kana_sample': '',
                    'outcome': 'PARSE_FAIL',
                }
        elif status_code == 404:
            # 404の場合は次の候補を試す
            continue
        else:
            # その他のエラー
            if url == url_candidates[-1]:  # 最後の候補の場合
                return {
                    'player_id': player_id,
                    'url_used': url,
                    'http_status': status_code,
                    'found_roman': False,
                    'found_kana': False,
                    'roman_sample': '',
                    'kana_sample': '',
                    'outcome': f'HTTP_ERROR_{status_code}',
                }
    
    # すべてのURL候補が失敗した場合
    return {
        'player_id': player_id,
        'url_used': url_candidates[0] if url_candidates else '',
        'http_status': 404,
        'found_roman': False,
        'found_kana': False,
        'roman_sample': '',
        'kana_sample': '',
        'outcome': 'HTTP_404',
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='NPB選手個人ページから読み仮名と英字表記の存在を検証')
    parser.add_argument('--limit', type=int, default=100, help='テストするplayer_idの数（デフォルト: 100）')
    parser.add_argument('--csv', type=str, default=None, help='入力CSVファイルのパス（デフォルト: _data/master_csv_calculated/batting_2025_PL_from_master.csv）')
    parser.add_argument('--save-html', action='store_true', help='HTMLを保存する（output/html_cache_probe/）')
    args = parser.parse_args()
    
    # 入力CSVのパスを決定
    if args.csv:
        csv_path = Path(args.csv)
    else:
        csv_path = project_root / '_data' / 'master_csv_calculated' / 'batting_2025_PL_from_master.csv'
    
    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return 1
    
    # player_idを抽出
    player_ids = extract_player_ids(csv_path, limit=args.limit)
    if not player_ids:
        print("❌ player_idが抽出できませんでした")
        return 1
    
    # 出力ディレクトリを作成
    output_dir = project_root / 'output' / 'reports'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f'player_page_probe_{len(player_ids)}.csv'
    
    # HTMLキャッシュディレクトリ
    html_cache_dir = None
    if args.save_html:
        html_cache_dir = project_root / 'output' / 'html_cache_probe'
        html_cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 HTML保存先: {html_cache_dir}")
    
    print(f"\n🔍 調査を開始します...")
    print(f"   対象player_id数: {len(player_ids)}")
    print(f"   出力先: {output_path}\n")
    
    # 各player_idについて調査
    results = []
    for i, player_id in enumerate(player_ids, 1):
        print(f"[{i}/{len(player_ids)}] player_id: {player_id} を調査中...", end=' ', flush=True)
        result = probe_player_page(player_id, save_html=args.save_html, html_cache_dir=html_cache_dir)
        results.append(result)
        
        # 結果を簡潔に表示
        print(f"→ {result['outcome']} (status: {result['http_status']})")
        
        # リクエスト間隔を空ける（サーバー負荷軽減）
        time.sleep(0.5)
    
    # CSVに出力
    fieldnames = ['player_id', 'url_used', 'http_status', 'found_roman', 'found_kana', 'roman_sample', 'kana_sample', 'outcome']
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
    
    # roman_sampleが空でない件数（人名っぽい、組織名を除外）
    roman_non_empty = sum(1 for r in results if r['found_roman'] and r['roman_sample'] and 
                         not any(exclude in r['roman_sample'].upper() for exclude in ['NIPPON', 'PROFESSIONAL', 'BASEBALL', 'ORGANIZATION']))
    
    print(f"\n📈 詳細統計:")
    print(f"   HTTP 200: {http_200_count}件 ({http_200_count/len(results)*100:.1f}%)")
    print(f"   英字表記あり: {found_roman_count}件 ({found_roman_count/len(results)*100:.1f}%)")
    print(f"   英字表記（人名っぽい）: {roman_non_empty}件 ({roman_non_empty/len(results)*100:.1f}%)")
    print(f"   ふりがな/かなあり: {found_kana_count}件 ({found_kana_count/len(results)*100:.1f}%)")
    print(f"   両方あり: {found_both_count}件 ({found_both_count/len(results)*100:.1f}%)")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

