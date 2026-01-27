#!/usr/bin/env python3
"""
STEP 3: 全player_idで公式かな＋（あれば）公式英字を収集して保存（完走仕様）
"""

import csv
import re
import time
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

# プロジェクトルートを取得
script_dir = Path(__file__).parent
project_root = script_dir.parent


def fetch_html(url: str, timeout: Tuple[int, int] = (5, 15)) -> Tuple[Optional[str], int, Optional[str]]:
    """HTMLを取得（HTTP statusも返す）
    
    Returns:
        (html_text, status_code, error_type)
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
            try:
                text = raw.decode('utf-8', errors='replace')
            except Exception:
                return None, response.status_code, 'DECODE_FAIL'
        
        return text, response.status_code, None
    except requests.exceptions.Timeout:
        return None, 0, 'TIMEOUT'
    except requests.exceptions.RequestException as e:
        status_code = getattr(e.response, 'status_code', 0) if hasattr(e, 'response') else 0
        return None, status_code, 'NETWORK_ERROR'


def generate_url_candidates(player_id: str) -> List[str]:
    """player_idから複数のURL候補を生成"""
    base_url = "https://npb.jp/bis/players/"
    candidates = []
    
    # パターン1: そのまま
    candidates.append(f"{base_url}{player_id}.html")
    
    # パターン2: ゼロ埋め8桁
    try:
        id_int = int(player_id)
        candidates.append(f"{base_url}{id_int:08d}.html")
    except ValueError:
        pass
    
    # パターン3: ゼロ埋め7桁
    try:
        id_int = int(player_id)
        candidates.append(f"{base_url}{id_int:07d}.html")
    except ValueError:
        pass
    
    return candidates


def find_japanese_name(html: str) -> Optional[str]:
    """HTMLから選手名（日本語）を探す"""
    if not html:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # 優先1: id="pc_v_name" のli要素を直接探す
        pc_v_name_li = soup.find('li', id='pc_v_name')
        if pc_v_name_li:
            name_text = pc_v_name_li.get_text().strip()
            if name_text and 2 <= len(name_text) <= 50:
                return name_text
        
        # 優先2: div#pc_v_name の中のli#pc_v_nameを探す
        pc_v_name_div = soup.find('div', id='pc_v_name')
        if pc_v_name_div:
            ul = pc_v_name_div.find('ul')
            if ul:
                pc_v_name_li = ul.find('li', id='pc_v_name')
                if pc_v_name_li:
                    name_text = pc_v_name_li.get_text().strip()
                    if name_text and 2 <= len(name_text) <= 50:
                        return name_text
                
                # フォールバック: ul内の最初のli要素（id="pc_v_name"以外）を探す
                # ただし、id="pc_v_no"やid="pc_v_team"は除外
                for li in ul.find_all('li'):
                    li_id = li.get('id', '')
                    if li_id not in ['pc_v_no', 'pc_v_team', 'pc_v_kana']:
                        name_text = li.get_text().strip()
                        # 日本語が含まれているか確認（ひらがな、カタカナ、漢字）
                        if name_text and re.search(r'[あ-んア-ン一-龠]', name_text):
                            if 2 <= len(name_text) <= 50:
                                return name_text
    except Exception:
        pass
    
    return None


def find_kana_name(html: str) -> Optional[str]:
    """HTMLから読み（ひらがな・カタカナ）を探す（DOM構造を優先）"""
    if not html:
        return None
    
    try:
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
                                    return kana_part
                            # カタカナ・ひらがなが含まれている場合（英字が含まれていないことを確認）
                            elif re.search(r'[あ-んア-ン]', kana_part) and not re.search(r'[一-龠A-Za-z]', kana_part):
                                if 2 <= len(kana_part) <= 30:
                                    return kana_part
                    else:
                        # 括弧がない場合
                        # ひらがなのみ（カタカナや漢字、英字が混ざっていない）を優先
                        if re.match(r'^[あ-ん・\s]+$', kana_text) and not re.search(r'[ア-ン一-龠A-Za-z]', kana_text):
                            if 2 <= len(kana_text) <= 30:
                                return kana_text
                        # カタカナが含まれている場合も許容（漢字や英字が混ざっていないことを確認）
                        elif re.search(r'[あ-んア-ン]', kana_text) and not re.search(r'[一-龠A-Za-z]', kana_text):
                            if 2 <= len(kana_text) <= 30:
                                return kana_text
    except Exception:
        pass
    
    return None


def find_roman_name(html: str) -> Optional[str]:
    """HTMLから英字表記を探す（DOM構造を優先）"""
    if not html:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # 優先1: id="pc_v_name" の中の英字名（括弧内）- 外国人選手用
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
                        return ' '.join(word.capitalize() for word in roman_name.split())
        
        # 優先2: id="pc_v_kana" の中の英字名
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
                        return ' '.join(word.capitalize() for word in roman_name.split())
            
            # パターン2-2: 括弧なしで英字名が直接入っている場合（外国人選手用）
            # ひらがな・カタカナ・漢字が含まれていない、英字のみの場合はスペルとして扱う
            if re.match(r'^[A-Za-z\s\.\-\']+$', kana_text) and not re.search(r'[あ-んア-ン一-龠]', kana_text):
                roman_name = kana_text.strip()
                # 組織名を除外
                if not any(exclude in roman_name.upper() for exclude in ['NIPPON', 'PROFESSIONAL', 'BASEBALL', 'ORGANIZATION']):
                    if 2 <= len(roman_name) <= 50:
                        # Title Caseに変換
                        return ' '.join(word.capitalize() for word in roman_name.split())
    except Exception:
        pass
    
    return None


def load_cached_html(player_id: str, html_cache_dir: Path) -> Optional[str]:
    """キャッシュされたHTMLを読み込む"""
    html_path = html_cache_dir / f"{player_id}.html"
    if html_path.exists():
        try:
            return html_path.read_text(encoding='utf-8')
        except Exception:
            return None
    return None


def save_html_cache(player_id: str, html: str, html_cache_dir: Path) -> bool:
    """HTMLをキャッシュに保存"""
    try:
        html_cache_dir.mkdir(parents=True, exist_ok=True)
        html_path = html_cache_dir / f"{player_id}.html"
        html_path.write_text(html, encoding='utf-8')
        return True
    except Exception:
        return False


def process_player_id_with_retry(
    player_id: str,
    html_cache_dir: Optional[Path] = None,
    use_cache: bool = True,
    rate_limit: float = 1.0,
    max_retries: int = 5
) -> Dict:
    """1つのplayer_idについてページを調査（リトライ付き）"""
    url_candidates = generate_url_candidates(player_id)
    
    # キャッシュから読み込む（use_cacheがTrueの場合）
    if use_cache and html_cache_dir:
        cached_html = load_cached_html(player_id, html_cache_dir)
        if cached_html:
            try:
                name_ja = find_japanese_name(cached_html)
                name_kana = find_kana_name(cached_html)
                roman_official = find_roman_name(cached_html)
                
                # name_ja、name_kana、roman_officialのいずれかが取得できた場合は結果を返す
                if name_ja or name_kana or roman_official:
                    # outcome分類
                    if roman_official and name_kana:
                        outcome = "OK"
                    elif roman_official:
                        outcome = "OK"
                    elif name_kana:
                        outcome = "OK"
                    elif name_ja:
                        outcome = "NAME_JA_ONLY"  # name_jaのみ取得できた場合
                    else:
                        outcome = "NO_DATA"
                    
                    return {
                        'player_id': player_id,
                        'name_ja': name_ja or '',
                        'name_kana': name_kana or '',
                        'roman_official': roman_official or '',
                        'url_used': f"cache:{player_id}.html",
                        'http_status': 200,
                        'outcome': outcome,
                    }
            except Exception:
                # キャッシュが壊れている場合は再取得
                pass
    
    # ネットワークから取得（リトライ付き）
    current_rate = rate_limit
    last_error_type = None
    
    for url in url_candidates:
        for retry in range(max_retries):
            html, status_code, error_type = fetch_html(url, timeout=(5, 15))
            
            # 成功した場合
            if html and status_code == 200:
                # HTMLを保存
                if html_cache_dir:
                    save_html_cache(player_id, html, html_cache_dir)
                
                # HTMLのパース
                try:
                    name_ja = find_japanese_name(html)
                    name_kana = find_kana_name(html)
                    roman_official = find_roman_name(html)
                    
                    # name_ja、name_kana、roman_officialのいずれかが取得できた場合は結果を返す
                    if name_ja or name_kana or roman_official:
                        # outcome分類
                        if roman_official and name_kana:
                            outcome = "OK"
                        elif roman_official:
                            outcome = "OK"
                        elif name_kana:
                            outcome = "OK"
                        elif name_ja:
                            outcome = "NAME_JA_ONLY"  # name_jaのみ取得できた場合
                        else:
                            outcome = "NO_DATA"
                        
                        return {
                            'player_id': player_id,
                            'name_ja': name_ja or '',
                            'name_kana': name_kana or '',
                            'roman_official': roman_official or '',
                            'url_used': url,
                            'http_status': status_code,
                            'outcome': outcome,
                        }
                    else:
                        # 何も取得できなかった場合
                        return {
                            'player_id': player_id,
                            'name_ja': '',
                            'name_kana': '',
                            'roman_official': '',
                            'url_used': url,
                            'http_status': status_code,
                            'outcome': 'NO_DATA',
                        }
                except Exception as e:
                    return {
                        'player_id': player_id,
                        'name_ja': '',
                        'name_kana': '',
                        'roman_official': '',
                        'url_used': url,
                        'http_status': status_code,
                        'outcome': 'PARSE_FAIL',
                    }
            
            # エラーハンドリング
            if status_code == 404:
                # 404の場合は次のURL候補を試す
                break
            
            if status_code == 429:
                # レート制限エラー: backoffしてrateを上げる
                backoff = min(2 ** retry, 20)  # 1s, 2s, 4s, 8s, 16s, 最大20s
                current_rate = min(current_rate * 1.5, 2.0)  # rateを上げる
                time.sleep(backoff)
                last_error_type = 'HTTP_429'
                continue
            
            if status_code >= 500:
                # サーバーエラー: backoffしてリトライ
                backoff = min(2 ** retry, 20)
                time.sleep(backoff)
                last_error_type = f'HTTP_{status_code}'
                continue
            
            if error_type == 'TIMEOUT':
                # タイムアウト: backoffしてリトライ
                backoff = min(2 ** retry, 20)
                time.sleep(backoff)
                last_error_type = 'TIMEOUT'
                continue
            
            if error_type:
                # その他のエラー
                last_error_type = error_type
                break
        
        # レート制限
        if html and status_code == 200:
            time.sleep(current_rate)
        else:
            time.sleep(min(current_rate, 1.0))
    
    # すべてのURL候補とリトライが失敗した場合
    return {
        'player_id': player_id,
        'name_ja': '',
        'name_kana': '',
        'roman_official': '',
        'url_used': url_candidates[0] if url_candidates else '',
        'http_status': 0,
        'outcome': last_error_type or 'FAILED',
    }


def load_existing_results(output_path: Path) -> set:
    """既存の結果CSVから処理済みplayer_idを読み込む"""
    if not output_path.exists():
        return set()
    
    processed_ids = set()
    try:
        with open(output_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                player_id = row.get('player_id', '').strip()
                if player_id:
                    processed_ids.add(player_id)
    except Exception:
        pass
    
    return processed_ids


def main():
    import argparse
    parser = argparse.ArgumentParser(description='全player_idで公式かな＋（あれば）公式英字を収集（完走仕様）')
    parser.add_argument('--ids', '--input', type=str, default=None, help='入力CSVファイル（デフォルト: output/master/all_player_ids.csv）')
    parser.add_argument('--out', '--output', type=str, default=None, help='出力CSVファイル（デフォルト: output/master/player_id_name_kana_official.csv）')
    parser.add_argument('--rate', '--rate-limit', type=float, default=1.0, help='レート制限（秒、デフォルト: 1.0）')
    parser.add_argument('--resume', action='store_true', default=True, help='既存の結果を読み込んで続きから実行（デフォルト: True）')
    parser.add_argument('--no-resume', action='store_true', help='resumeを無効化')
    parser.add_argument('--use-cache', action='store_true', default=True, help='HTMLキャッシュを使用（デフォルト: True）')
    parser.add_argument('--no-cache', action='store_true', help='キャッシュを使用しない')
    parser.add_argument('--limit', type=int, default=None, help='処理件数の上限（デバッグ用）')
    args = parser.parse_args()
    
    # 入力パスを決定
    if args.ids:
        input_path = Path(args.ids)
    else:
        input_path = project_root / 'output' / 'master' / 'all_player_ids.csv'
    
    if not input_path.exists():
        print(f"❌ 入力ファイルが見つかりません: {input_path}")
        return 1
    
    # 出力パスを決定
    if args.out:
        output_path = Path(args.out)
    else:
        output_path = project_root / 'output' / 'master' / 'player_id_name_kana_official.csv'
    
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # HTMLキャッシュディレクトリ
    html_cache_dir = project_root / 'output' / 'html_cache' / 'players'
    
    # オプション処理
    use_cache = args.use_cache and not args.no_cache
    resume = args.resume and not args.no_resume
    
    # player_idを読み込む
    player_ids = []
    with open(input_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            player_id = row.get('player_id', '').strip()
            if player_id:
                player_ids.append(player_id)
    
    # limitオプション
    if args.limit:
        player_ids = player_ids[:args.limit]
    
    print(f"✅ {len(player_ids)}件のplayer_idを読み込みました")
    
    # 既存の結果を読み込む（resumeオプション）
    processed_ids = set()
    if resume:
        processed_ids = load_existing_results(output_path)
        print(f"📋 既存の結果から {len(processed_ids)}件のplayer_idをスキップします")
    
    # 未処理のplayer_idをフィルタ
    remaining_ids = [pid for pid in player_ids if pid not in processed_ids]
    print(f"🔍 処理対象: {len(remaining_ids)}件")
    
    if not remaining_ids:
        print("✅ すべてのplayer_idが処理済みです")
        return 0
    
    # 結果を追記モードで開く
    file_exists = output_path.exists()
    with open(output_path, 'a', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['player_id', 'name_ja', 'name_kana', 'roman_official', 'url_used', 'http_status', 'outcome'])
        
        if not file_exists:
            writer.writeheader()
        
        # 統計
        ok_count = 0
        fail_count = 0
        
        # 各player_idを処理
        for i, player_id in enumerate(remaining_ids, 1):
            try:
                result = process_player_id_with_retry(
                    player_id,
                    html_cache_dir,
                    use_cache=use_cache,
                    rate_limit=args.rate,
                    max_retries=5
                )
                writer.writerow(result)
                f.flush()  # 即座に書き込み
                
                # 統計更新
                if result['outcome'] == 'OK':
                    ok_count += 1
                else:
                    fail_count += 1
                
                # 進捗表示（10件ごと）
                if i % 10 == 0 or i == len(remaining_ids):
                    print(f"[{i}/{len(remaining_ids)}] processed: {i}, OK: {ok_count}, FAIL: {fail_count}")
            except KeyboardInterrupt:
                print(f"\n⚠️  中断されました。{i-1}件まで処理済み。--resume で続きから実行できます。")
                return 1
            except Exception as e:
                # 予期しないエラーも記録
                result = {
                    'player_id': player_id,
                    'name_ja': '',
                    'name_kana': '',
                    'roman_official': '',
                    'url_used': '',
                    'http_status': 0,
                    'outcome': 'UNKNOWN',
                }
                writer.writerow(result)
                f.flush()
                fail_count += 1
                print(f"⚠️  予期しないエラー ({player_id}): {e}")
    
    print(f"\n✅ 結果を出力しました: {output_path}")
    
    # 最終サマリーを表示
    with open(output_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        results = list(reader)
    
    outcome_counts = {}
    name_kana_filled = 0
    roman_official_filled = 0
    
    for result in results:
        outcome = result['outcome']
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        
        if result.get('name_kana', '').strip():
            name_kana_filled += 1
        if result.get('roman_official', '').strip():
            roman_official_filled += 1
    
    print(f"\n📊 最終サマリー:")
    print(f"   総player_id数: {len(results)}件")
    print(f"   name_kana 非空率: {name_kana_filled}件 ({name_kana_filled/len(results)*100:.1f}%)")
    print(f"   roman_official 非空率: {roman_official_filled}件 ({roman_official_filled/len(results)*100:.1f}%)")
    print(f"   outcome別件数:")
    for outcome, count in sorted(outcome_counts.items()):
        percentage = (count / len(results)) * 100
        print(f"      {outcome}: {count}件 ({percentage:.1f}%)")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
