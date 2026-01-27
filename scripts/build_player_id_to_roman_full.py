#!/usr/bin/env python3
"""
STEP 4: かな→ローマ字生成 & 最終辞書作成
"""

import csv
import re
import sys
from pathlib import Path
from typing import Dict, Optional

# プロジェクトルートを取得
script_dir = Path(__file__).parent
project_root = script_dir.parent

# ヘボン式ローマ字変換テーブル（ひらがな→ローマ字）
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
    'っ': '',  # 促音は次の子音を重ねる（後で処理）
}

# 長音記号の処理
LONG_VOWEL_MAP = {
    'aa': 'ā', 'ii': 'ī', 'uu': 'ū', 'ee': 'ē', 'oo': 'ō',
}


def kana_to_romaji(kana: str) -> str:
    """ひらがなをヘボン式ローマ字に変換"""
    if not kana:
        return ''
    
    # カタカナをひらがなに変換
    kana = kana.translate(str.maketrans(
        'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポキャキュキョギャギュギョシャシュショジャジュジョチャチュチョニャニュニョヒャヒュヒョビャビュビョピャピュピョミャミュミョリャリュリョッー・',
        'あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽきゃきゅきょぎゃぎゅぎょしゃしゅしょじゃじゅじょちゃちゅちょにゃにゅにょひゃひゅひょびゃびゅびょぴゃぴゅぴょみゃみゅみょりゃりゅりょっー・'
    ))
    
    result = []
    i = 0
    while i < len(kana):
        char = kana[i]
        
        # 空白や・はそのまま保持
        if char in [' ', '・', '　']:
            result.append(char)
            i += 1
            continue
        
        # 長音記号（ー）の処理
        if char == 'ー' and result:
            # 前の文字の母音を長音化
            last_char = result[-1] if result else ''
            if last_char in ['a', 'i', 'u', 'e', 'o']:
                # 長音記号は母音を重ねる（例: aー → aa）
                result.append(last_char)
            else:
                result.append('')
            i += 1
            continue
        
        # 促音（っ）の処理
        if char == 'っ' and i + 1 < len(kana):
            next_char = kana[i + 1]
            # 次の文字が子音で始まる場合、その子音を重ねる
            if next_char in HEPBURN_TABLE:
                next_romaji = HEPBURN_TABLE[next_char]
                if next_romaji and next_romaji[0] in 'kstp':
                    result.append(next_romaji[0])
                else:
                    result.append('')
            else:
                result.append('')
            i += 1
            continue
        
        # 2文字の組み合わせ（拗音）を優先的にチェック
        if i + 1 < len(kana):
            two_char = kana[i:i+2]
            if two_char in HEPBURN_TABLE:
                result.append(HEPBURN_TABLE[two_char])
                i += 2
                continue
        
        # 1文字の変換
        if char in HEPBURN_TABLE:
            result.append(HEPBURN_TABLE[char])
        else:
            # 変換できない文字はそのまま
            result.append(char)
        
        i += 1
    
    # 結果を結合
    romaji = ''.join(result)
    
    # 空白と・を正規化
    romaji = re.sub(r'\s+', ' ', romaji)  # 連続する空白を1つに
    romaji = re.sub(r'・+', ' ', romaji)  # ・を空白に変換
    romaji = romaji.strip()
    
    return romaji


def to_title_case(text: str) -> str:
    """文字列をTitle Caseに変換（各単語の先頭を大文字、他を小文字）"""
    if not text:
        return ''
    
    words = text.split()
    title_words = []
    for word in words:
        if word:
            title_words.append(word[0].upper() + word[1:].lower() if len(word) > 1 else word.upper())
        else:
            title_words.append('')
    
    return ' '.join(title_words)


def to_initial_lastname(full_name: str, is_japanese: bool = False) -> str:
    """
    完全な名前を「イニシャル.苗字」形式に変換
    
    外国人選手の場合（is_japanese=False）:
        "Roman Mejias" → "R.Mejias" （名前のイニシャル.苗字）
    
    日本人選手の場合（is_japanese=True）:
        "Sato Shigeo" → "S.Sato" （名前のイニシャル.苗字）
        ただし、入力は「苗字 名前」の順序であることを想定
    """
    if not full_name:
        return ''
    
    # 空白で分割
    parts = full_name.strip().split()
    
    if len(parts) == 0:
        return ''
    
    if len(parts) == 1:
        # 1単語のみの場合（苗字のみ、または名前のみ）
        # 最初の文字をイニシャルとして扱う
        name = parts[0].strip()
        if len(name) > 0:
            initial = name[0].upper()
            return f"{initial}.{name}"
        return ''
    
    # 複数の単語がある場合
    if is_japanese:
        # 日本人選手の場合: 「苗字 名前」→「名前のイニシャル.苗字」
        # 例: "Sato Shigeo" → "S.Sato"
        last_name = parts[0].strip()  # 最初の部分が苗字
        first_name = parts[-1].strip()  # 最後の部分が名前
        
        if not first_name or not last_name:
            return full_name
        
        # 名前の最初の文字をイニシャルとして取得
        initial = first_name[0].upper()
        
        # 苗字をTitle Caseに変換（先頭大文字、他小文字）
        last_name_title = last_name[0].upper() + last_name[1:].lower() if len(last_name) > 1 else last_name.upper()
        
        return f"{initial}.{last_name_title}"
    else:
        # 外国人選手の場合: 「名前 苗字」→「名前のイニシャル.苗字」
        # 例: "Roman Mejias" → "R.Mejias"
        first_name = parts[0].strip()  # 最初の部分が名前
        last_name = parts[-1].strip()  # 最後の部分が苗字
        
        if not first_name or not last_name:
            return full_name
        
        # 名前の最初の文字をイニシャルとして取得
        initial = first_name[0].upper()
        
        # 苗字をTitle Caseに変換（先頭大文字、他小文字）
        last_name_title = last_name[0].upper() + last_name[1:].lower() if len(last_name) > 1 else last_name.upper()
        
        return f"{initial}.{last_name_title}"


def convert_kana_to_romaji(name_kana: str) -> str:
    """name_kana（'・'区切り）をローマ字に変換してTitle Caseで返す"""
    if not name_kana:
        return ''
    
    # '・'で分割（姓と名）
    parts = name_kana.split('・')
    
    romaji_parts = []
    for part in parts:
        part = part.strip()
        if part:
            romaji = kana_to_romaji(part)
            if romaji:
                romaji_parts.append(romaji)
    
    # 半角スペースで結合してTitle Caseに変換
    result = ' '.join(romaji_parts)
    return to_title_case(result)


def process_row(row: Dict) -> Dict:
    """1行を処理して最終辞書の形式に変換"""
    player_id = row.get('player_id', '').strip()
    name_ja = row.get('name_ja', '').strip()
    name_kana = row.get('name_kana', '').strip()
    roman_official = row.get('roman_official', '').strip()
    
    # roman_officialが非空ならそれを採用（外国人選手の可能性が高い）
    if roman_official:
        # Title Caseに変換してから、イニシャル.苗字形式に変換（外国人選手として処理）
        full_name = to_title_case(roman_official)
        roman_name = to_initial_lastname(full_name, is_japanese=False)
        source = 'NPB_OFFICIAL'
        confidence = 'HIGH'
    elif name_kana:
        # name_kanaをヘボン式でローマ字化してから、イニシャル.苗字形式に変換（日本人選手として処理）
        # convert_kana_to_romajiは「苗字 名前」の順序で出力する
        full_name = convert_kana_to_romaji(name_kana)
        roman_name = to_initial_lastname(full_name, is_japanese=True)
        source = 'KANA_CONVERTED'
        confidence = 'HIGH'
    else:
        # どちらもない場合
        roman_name = ''
        source = 'MISSING'
        confidence = 'LOW'
    
    return {
        'player_id': player_id,
        'romanName': roman_name,
        'source': source,
        'confidence': confidence,
        'name_ja': name_ja,
        'name_kana': name_kana,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='かな→ローマ字生成 & 最終辞書作成')
    parser.add_argument('--input', type=str, default=None, help='入力CSVファイル（デフォルト: output/master/player_id_name_kana_official.csv）')
    parser.add_argument('--output', type=str, default=None, help='出力CSVファイル（デフォルト: output/master/player_id_to_roman_full.csv）')
    args = parser.parse_args()
    
    # 入力パスを決定
    if args.input:
        input_path = Path(args.input)
    else:
        input_path = project_root / 'output' / 'master' / 'player_id_name_kana_official.csv'
    
    if not input_path.exists():
        print(f"❌ 入力ファイルが見つかりません: {input_path}")
        return 1
    
    # 出力パスを決定
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = project_root / 'output' / 'master' / 'player_id_to_roman_full.csv'
    
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 入力CSVを読み込む（同一player_idを統合）
    from collections import defaultdict
    
    # まず全行を読み込む
    all_rows = []
    with open(input_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            player_id = row.get('player_id', '').strip()
            if player_id:
                all_rows.append(row)
    
    # player_idごとにグループ化
    player_groups = defaultdict(list)
    for row in all_rows:
        player_id = row.get('player_id', '').strip()
        player_groups[player_id].append(row)
    
    # 各player_idについて最適な行を選択
    player_dict = {}  # player_id -> 最適な行データ
    
    for player_id, rows in player_groups.items():
        if len(rows) == 1:
            # 1行のみの場合はそのまま
            player_dict[player_id] = rows[0]
        else:
            # 複数行がある場合、統合ルールを適用
            # 統合ルール:
            # 1) roman_officialが非空の行を最優先
            # 2) それ以外はname_kanaが非空の行を優先
            # 3) name_ja/name_kanaは空より非空を優先
            
            best_row = None
            best_score = -1
            
            for row in rows:
                roman = row.get('roman_official', '').strip()
                kana = row.get('name_kana', '').strip()
                ja = row.get('name_ja', '').strip()
                
                # スコア計算: roman_official > name_kana > name_ja
                score = 0
                if roman:
                    score += 100  # roman_officialが最優先
                if kana:
                    score += 10   # name_kanaが次に優先
                if ja:
                    score += 1    # name_jaは最小優先
                
                if score > best_score:
                    best_score = score
                    best_row = row
            
            if best_row:
                player_dict[player_id] = best_row
            else:
                # すべて空の場合は最初の行
                player_dict[player_id] = rows[0]
    
    # 統合されたデータを処理
    results = []
    for player_id, row in sorted(player_dict.items()):
        result = process_row(row)
        results.append(result)
    
    print(f"✅ {len(player_dict)}件のユニークplayer_idを処理しました（入力: {len(all_rows)}行）")
    
    # 出力CSVに書き込む
    fieldnames = ['player_id', 'romanName', 'source', 'confidence', 'name_ja', 'name_kana']
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"✅ 結果を出力しました: {output_path}")
    
    # 検証: rows数とnuniqueが一致することを確認
    unique_player_ids = set(result['player_id'] for result in results)
    rows_count = len(results)
    unique_count = len(unique_player_ids)
    
    print(f"\n🔍 検証:")
    print(f"   総行数: {rows_count}件")
    print(f"   ユニークplayer_id数: {unique_count}件")
    if rows_count == unique_count:
        print(f"   ✅ 検証成功: rows == nunique")
    else:
        print(f"   ❌ 検証失敗: rows ({rows_count}) != nunique ({unique_count})")
        return 1
    
    # サマリーを表示
    source_counts = {}
    filled_count = 0
    
    for result in results:
        source = result['source']
        source_counts[source] = source_counts.get(source, 0) + 1
        if result['romanName']:
            filled_count += 1
    
    print(f"\n📊 サマリー:")
    print(f"   総player_id数: {rows_count}件")
    print(f"   romanNameが埋まった数: {filled_count}件 ({filled_count/rows_count*100:.1f}%)")
    print(f"   source別内訳:")
    for source, count in sorted(source_counts.items()):
        percentage = (count / rows_count) * 100
        print(f"      {source}: {count}件 ({percentage:.1f}%)")
    
    # サンプルを表示
    print(f"\n📝 サンプル（最初の10件）:")
    for i, result in enumerate(results[:10], 1):
        print(f"   {i}. {result['player_id']}: {result['name_ja']} ({result['name_kana']}) → {result['romanName']} [{result['source']}]")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())


