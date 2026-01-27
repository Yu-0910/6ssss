# 全選手の識別・同定プロセス レポート

## 📋 概要

本レポートでは、NPB（日本プロ野球）の全選手を「その選手たちであることを認識する」プロセスに焦点を当て、選手の識別・同定の仕組みを詳しく説明します。

**核心的な課題**: 複数のデータソース（成績CSV、HTMLページ）から選手情報を収集し、同一選手を確実に識別し、一意の選手として管理する。

---

## 🎯 選手識別の全体フロー

```
┌─────────────────────────────────────────────────────────────────┐
│ 【段階0: 成績データのスクレイピング（選手の存在認識）】            │
│ └─ NPB公式サイトから成績データをスクレイピング                    │
│ └─ player_idと成績データを取得                                   │
│ └─ 「この選手が存在する」と最初に認識した段階                    │
│ └─ 出力: batting_{YEAR}_{LEAGUE}_from_master.csv                │
└─────────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ 段階1: player_idの抽出と集約                                      │
│ └─ 全成績CSVからplayer_idをユニーク抽出                           │
│ └─ 選手の一意性の基盤を確立                                       │
│ └─ 【既存の選手情報を変換】                                      │
└─────────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ 段階2: 選手名情報の収集（HTMLスクレイピング）                      │
│ └─ 各player_idに対応するHTMLページを取得                         │
│ └─ 選手名（日本語）、かな、ローマ字を抽出                         │
│ └─ 【既存の選手情報を補完】                                      │
└─────────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ 段階3: 選手名情報の統合と正規化                                   │
│ └─ 複数ソースからの情報を統合                                     │
│ └─ 重複排除と最適な情報の選択                                     │
│ └─ 【既存の選手情報を変換】                                      │
└─────────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ 段階4: ローマ字名の生成                                           │
│ └─ 公式ローマ字の優先使用                                         │
│ └─ かなからの自動生成（ヘボン式）                                │
│ └─ イニシャル.苗字形式への変換                                    │
│ └─ 【既存の選手情報を変換】                                      │
└─────────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ 段階5: 最終辞書の作成                                             │
│ └─ player_id → 選手名（日本語、かな、ローマ字）のマッピング      │
│ └─ 成績データとの紐付け準備完了                                  │
│ └─ 【既存の選手情報を変換】                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📝 各段階の詳細

### 段階0: 成績データのスクレイピング（選手の存在認識）

**目的**: NPB公式サイトから成績データをスクレイピングし、**「この選手が存在する」と最初に認識する**。

**処理内容**:

1. **NPB公式サイトからの成績データ取得**
   - NPB公式サイト（npb.jp）から各年度・各リーグの成績データを取得
   - 年度範囲: 1950年〜2024年（および2025年）
   - リーグ: セ・リーグ（CL）、パ・リーグ（PL）

2. **取得されるデータ**
   - **player_id**: 選手の一意の識別子（NPB公式サイトで使用されるID）
   - **player_name_ja**: 選手名（日本語）
   - **player_name_en**: 選手名（英語・ローマ字、一部の選手のみ）
   - **成績データ**: 試合数（G）、打席（PA）、打数（AB）、安打（H）、本塁打（HR）、打点（RBI）など

3. **出力ファイル**
   - ファイル名: `batting_{YEAR}_{LEAGUE}_from_master.csv`
   - 保存場所: `_data/master_csv__import_1950_2024/`（過去のスクレイピングデータ）
   - 現在使用中: `_data/master_csv/` または `_data/master_csv_calculated/`

4. **CSVファイルの構造例**
   ```csv
   year,league,team,player_id,player_name_ja,player_name_en,G,PA,AB,R,H,2B,3B,HR,...
   2024,PL,福岡ソフトバンクホークス,11015138,辰己　涼介,R.Tatsumi,143,597,537,68,158,22,12,7,...
   2024,PL,東北楽天ゴールデンイーグルス,11015157,平良　竜哉,R.Taira,18,24,21,4,3,0,0,0,...
   ```

**重要なポイント**:
- **この段階で、player_idと成績データが取得され、「この選手が存在する」と最初に認識される**
- player_idはNPB公式サイトで使用される一意の識別子であり、選手の存在を保証する
- 成績データには選手名（日本語）が含まれるが、かなやローマ字は含まれない場合が多い
- この段階で取得されたデータが、以降の全プロセスの基盤となる

**データの特徴**:
- **player_id**: 必ず存在する（選手の一意性を保証）
- **player_name_ja**: ほとんどの場合存在する（一部欠損の可能性あり）
- **player_name_en**: 一部の選手のみ存在（外国人選手や一部の日本人選手）
- **成績データ**: 全選手について取得される

**この段階の意義**:
- **選手の存在認識**: この段階で、システムは「このplayer_idを持つ選手が存在し、この年度・このリーグで成績を残した」と認識する
- **データの基盤**: 以降の全プロセス（選手名の補完、ローマ字生成など）は、この段階で取得されたplayer_idと成績データを基盤とする
- **選手の一意性**: player_idにより、同じ選手を異なる年度・異なるリーグで一貫して識別可能

**注意事項**:
- 成績データのスクレイピングは、過去に実施された作業であり、現在のシステムでは既存のCSVファイルを使用
- 新しい年度のデータを追加する場合は、再度スクレイピングを実施する必要がある
- スクレイピング時に取得できなかった選手は、システムに存在しない選手として扱われる

---

### 段階1: player_idの抽出と集約

**目的**: 全成績CSVファイルからplayer_idを抽出し、システム全体で使用する一意の選手IDリストを作成する。

**スクリプト**: `scripts/build_all_player_ids.py`

**処理内容**:

1. **成績CSVファイルの探索**
   ```python
   # 探索対象ディレクトリ
   - _data/master_csv/
   - _data/master_csv_calculated/
   - _data/（その他）
   ```
   - パターン: `batting_YYYY_(PL|CL)_from_master.csv`
   - 1950年〜2025年の全年度・全リーグを対象

2. **player_id抽出**
   ```python
   # 各CSVファイルからplayer_id列を抽出
   for row in csv_reader:
       player_id = row.get('player_id', '').strip()
       if player_id and player_id not in ['', 'nan', 'None', '-']:
           player_ids.add(player_id)
   ```
   - 空文字・NaN・Noneを除外
   - 各CSVファイルから抽出したplayer_idをセットに追加

3. **ユニーク化**
   ```python
   # 重複を除去し、ソート
   sorted_player_ids = sorted(all_player_ids, key=lambda x: (len(x), x))
   ```
   - 重複するplayer_idを除去
   - ソート（長さ→文字列順）

4. **結果保存**
   - 出力ファイル: `output/master/all_player_ids.csv`
   - カラム: `player_id`
   - 形式: 1行1player_id

**実行例**:
```bash
python scripts/build_all_player_ids.py
```

**出力例**:
```csv
player_id
01001001
01001002
01001003
...
```

**統計情報**:
- 処理したCSVファイル数
- 抽出したユニークplayer_id数

**重要なポイント**:
- **この段階は、段階0で取得された既存の選手情報を変換しているだけ**
- player_idは段階0で既に取得されており、この段階ではそれらを集約している
- 複数のCSVファイルに同じplayer_idが存在する可能性があるが、これらは同一選手を表す
- この段階で、システム全体で管理すべき全選手のリストが確定する

---

### 段階2: 選手名情報の収集（HTMLスクレイピング）

**目的**: 各player_idに対応するNPB公式サイトのHTMLページから、選手名（日本語）、かな、ローマ字を抽出する。

**スクリプト**: `scripts/build_player_name_kana_and_official_roman.py`

**処理内容**:

1. **player_idリストの読み込み**
   ```python
   # 段階1で生成したall_player_ids.csvを読み込み
   player_ids = []
   with open('output/master/all_player_ids.csv', 'r') as f:
       reader = csv.DictReader(f)
       for row in reader:
           player_ids.append(row['player_id'])
   ```

2. **URL生成とHTML取得**
   ```python
   # 複数のURL候補を生成
   base_url = "https://npb.jp/bis/players/"
   candidates = [
       f"{base_url}{player_id}.html",
       f"{base_url}{int(player_id):08d}.html",  # ゼロ埋め8桁
       f"{base_url}{int(player_id):07d}.html",  # ゼロ埋め7桁
   ]
   
   # 各URL候補を試行（リトライ付き）
   for url in candidates:
       html, status_code, error = fetch_html(url)
       if html and status_code == 200:
           break
   ```

3. **HTMLキャッシュ保存**
   ```python
   # 取得したHTMLをキャッシュに保存
   html_cache_dir = Path('output/html_cache/players/')
   html_path = html_cache_dir / f"{player_id}.html"
   html_path.write_text(html, encoding='utf-8')
   ```
   - 次回実行時にキャッシュを優先使用（高速化）
   - データのバックアップとしても機能

4. **選手名（日本語）の抽出**
   ```python
   def find_japanese_name(html: str) -> Optional[str]:
       soup = BeautifulSoup(html, 'html.parser')
       
       # 優先1: id="pc_v_name" のli要素を直接探す
       pc_v_name_li = soup.find('li', id='pc_v_name')
       if pc_v_name_li:
           name_text = pc_v_name_li.get_text().strip()
           if 2 <= len(name_text) <= 50:
               return name_text
       
       # 優先2: div#pc_v_name の中のli#pc_v_nameを探す
       pc_v_name_div = soup.find('div', id='pc_v_name')
       if pc_v_name_div:
           ul = pc_v_name_div.find('ul')
           if ul:
               pc_v_name_li = ul.find('li', id='pc_v_name')
               if pc_v_name_li:
                   return pc_v_name_li.get_text().strip()
   ```
   - DOM構造を解析して選手名を抽出
   - 日本語（ひらがな、カタカナ、漢字）を含む文字列を取得

5. **かなの抽出**
   ```python
   def find_kana_name(html: str) -> Optional[str]:
       soup = BeautifulSoup(html, 'html.parser')
       
       # id="pc_v_kana"のli要素を探す
       pc_v_kana_li = soup.find('li', id='pc_v_kana')
       if pc_v_kana_li:
           kana_text = pc_v_kana_li.get_text().strip()
           
           # 括弧がある場合（カタカナ + 英字の形式）
           if '(' in kana_text or '（' in kana_text:
               # 括弧前の部分を抽出
               match = re.search(r'^([^\(（]+)', kana_text)
               if match:
                   kana_part = match.group(1).strip()
                   # ひらがなのみを優先
                   if re.match(r'^[あ-ん・\s]+$', kana_part):
                       return kana_part
   ```
   - ひらがなのみを優先（カタカナ・漢字・英字が混ざっていない）
   - 括弧内の英字名は除外

6. **ローマ字の抽出**
   ```python
   def find_roman_name(html: str) -> Optional[str]:
       soup = BeautifulSoup(html, 'html.parser')
       
       # 優先1: id="pc_v_name" の中の英字名（括弧内）- 外国人選手用
       pc_v_name = soup.find('li', id='pc_v_name')
       if pc_v_name:
           name_text = pc_v_name.get_text()
           # 全角括弧または半角括弧内の英字名を抽出
           match = re.search(r'[（(]([A-Za-z\s\.\-\']+)[）)]', name_text)
           if match:
               roman_name = match.group(1).strip()
               # 組織名を除外
               if not any(exclude in roman_name.upper() for exclude in ['NIPPON', 'PROFESSIONAL', 'BASEBALL']):
                   return ' '.join(word.capitalize() for word in roman_name.split())
   ```
   - 括弧内の英字名を抽出（外国人選手用）
   - 組織名（NIPPON、PROFESSIONAL、BASEBALLなど）を除外

7. **結果保存**
   - 出力ファイル: `output/master/player_id_name_kana_official.csv`
   - カラム:
     - `player_id`: 選手ID
     - `name_ja`: 選手名（日本語）
     - `name_kana`: かな（ひらがな優先）
     - `roman_official`: ローマ字（公式表記）
     - `url_used`: 使用したURL（またはキャッシュパス）
     - `http_status`: HTTPステータスコード
     - `outcome`: 処理結果（OK、NAME_JA_ONLY、NO_DATA、FAILEDなど）

**実行例**:
```bash
python scripts/build_player_name_kana_and_official_roman.py
```

**オプション**:
- `--ids`: 入力CSVファイル（デフォルト: `output/master/all_player_ids.csv`）
- `--out`: 出力CSVファイル（デフォルト: `output/master/player_id_name_kana_official.csv`）
- `--rate`: レート制限（秒、デフォルト: 1.0）
- `--resume`: 既存の結果を読み込んで続きから実行（デフォルト: True）
- `--use-cache`: HTMLキャッシュを使用（デフォルト: True）

**エラーハンドリング**:
- HTTP 404: 次のURL候補を試行
- HTTP 429（レート制限）: バックオフしてリトライ
- HTTP 500以上: バックオフしてリトライ
- タイムアウト: バックオフしてリトライ
- ネットワークエラー: エラーを記録して次へ

**重要なポイント**:
- **この段階は、段階0で既に認識された選手の情報を補完している**
- 各player_idに対して、選手名（日本語）、かな、ローマ字の3つの情報を収集
- 段階0で取得されたplayer_name_jaを補完・拡張する
- HTMLキャッシュにより、再実行時の高速化とデータのバックアップを実現
- エラーが発生しても処理を継続し、取得できた情報を記録

---

### 段階3: 選手名情報の統合と正規化

**目的**: 複数のソースから取得した選手名情報を統合し、重複を排除して最適な情報を選択する。

**スクリプト**: `scripts/build_player_id_to_roman_full.py`（統合処理部分）

**処理内容**:

1. **入力データの読み込み**
   ```python
   # 段階2で生成したplayer_id_name_kana_official.csvを読み込み
   all_rows = []
   with open('output/master/player_id_name_kana_official.csv', 'r') as f:
       reader = csv.DictReader(f)
       for row in reader:
           all_rows.append(row)
   ```

2. **player_idごとのグループ化**
   ```python
   # player_idごとにグループ化
   player_groups = defaultdict(list)
   for row in all_rows:
       player_id = row.get('player_id', '').strip()
       player_groups[player_id].append(row)
   ```
   - 同じplayer_idが複数回出現する可能性がある（複数のHTMLページから取得した場合など）
   - 各player_idについて、関連する全行をグループ化

3. **最適な行の選択**
   ```python
   # 各player_idについて最適な行を選択
   for player_id, rows in player_groups.items():
       if len(rows) == 1:
           # 1行のみの場合はそのまま
           player_dict[player_id] = rows[0]
       else:
           # 複数行がある場合、統合ルールを適用
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
           
           player_dict[player_id] = best_row
   ```

**統合ルール**:
1. **優先1**: `roman_official`が非空の行を最優先（公式ローマ字がある場合）
2. **優先2**: `name_kana`が非空の行を優先（かながある場合）
3. **優先3**: `name_ja`が非空の行を優先（選手名（日本語）がある場合）

**重要なポイント**:
- **この段階は、段階2で取得された既存の選手情報を変換しているだけ**
- 同じplayer_idに対して複数の情報源がある場合、最も信頼性の高い情報を選択
- `roman_official`（公式ローマ字）が最も信頼性が高い
- 統合により、各player_idに対して1行のデータが確定する

---

### 段階4: ローマ字名の生成

**目的**: 公式ローマ字が存在しない場合、かなからローマ字を自動生成し、イニシャル.苗字形式に変換する。

**スクリプト**: `scripts/build_player_id_to_roman_full.py`

**処理内容**:

1. **ローマ字生成の優先順位**
   ```python
   def process_row(row: Dict) -> Dict:
       player_id = row.get('player_id', '').strip()
       name_ja = row.get('name_ja', '').strip()
       name_kana = row.get('name_kana', '').strip()
       roman_official = row.get('roman_official', '').strip()
       
       # 優先1: roman_officialが非空ならそれを採用（外国人選手の可能性が高い）
       if roman_official:
           full_name = to_title_case(roman_official)
           roman_name = to_initial_lastname(full_name, is_japanese=False)
           source = 'NPB_OFFICIAL'
           confidence = 'HIGH'
       
       # 優先2: name_kanaをヘボン式でローマ字化（日本人選手として処理）
       elif name_kana:
           full_name = convert_kana_to_romaji(name_kana)
           roman_name = to_initial_lastname(full_name, is_japanese=True)
           source = 'KANA_CONVERTED'
           confidence = 'HIGH'
       
       # 優先3: どちらもない場合
       else:
           roman_name = ''
           source = 'MISSING'
           confidence = 'LOW'
   ```

2. **ヘボン式ローマ字変換**
   ```python
   def kana_to_romaji(kana: str) -> str:
       """ひらがなをヘボン式ローマ字に変換"""
       # カタカナをひらがなに変換
       kana = kana.translate(str.maketrans(
           'アイウエオ...',  # カタカナ
           'あいうえお...'  # ひらがな
       ))
       
       # ヘボン式ローマ字変換テーブルを使用
       HEPBURN_TABLE = {
           'あ': 'a', 'い': 'i', 'う': 'u', 'え': 'e', 'お': 'o',
           'か': 'ka', 'き': 'ki', 'く': 'ku', 'け': 'ke', 'こ': 'ko',
           ...
       }
       
       # 長音記号（ー）の処理
       # 促音（っ）の処理
       # 拗音（きゃ、きゅ、きょなど）の処理
   ```
   - ひらがなをヘボン式ローマ字に変換
   - カタカナは先にひらがなに変換
   - 長音記号（ー）、促音（っ）、拗音（きゃ、きゅ、きょなど）に対応

3. **イニシャル.苗字形式への変換**
   ```python
   def to_initial_lastname(full_name: str, is_japanese: bool = False) -> str:
       """
       完全な名前を「イニシャル.苗字」形式に変換
       
       外国人選手の場合（is_japanese=False）:
           "Roman Mejias" → "R.Mejias" （名前のイニシャル.苗字）
       
       日本人選手の場合（is_japanese=True）:
           "Sato Shigeo" → "S.Sato" （名前のイニシャル.苗字）
           ただし、入力は「苗字 名前」の順序であることを想定
       """
       parts = full_name.strip().split()
       
       if is_japanese:
           # 日本人選手: 「苗字 名前」→「名前のイニシャル.苗字」
           last_name = parts[0].strip()  # 最初の部分が苗字
           first_name = parts[-1].strip()  # 最後の部分が名前
           initial = first_name[0].upper()
           last_name_title = last_name[0].upper() + last_name[1:].lower()
           return f"{initial}.{last_name_title}"
       else:
           # 外国人選手: 「名前 苗字」→「名前のイニシャル.苗字」
           first_name = parts[0].strip()  # 最初の部分が名前
           last_name = parts[-1].strip()  # 最後の部分が苗字
           initial = first_name[0].upper()
           last_name_title = last_name[0].upper() + last_name[1:].lower()
           return f"{initial}.{last_name_title}"
   ```

**ローマ字生成の例**:
- `さとう てるあき` → `Sato Teruaki` → `T.Sato`
- `おかもと かずま` → `Okamoto Kazuma` → `K.Okamoto`
- `むらかみ むねたか` → `Murakami Munetaka` → `M.Murakami`

**重要なポイント**:
- **この段階は、段階2で取得された既存の選手情報を変換しているだけ**
- 公式ローマ字（`roman_official`）が存在する場合はそれを優先使用
- 公式ローマ字が存在しない場合、かなから自動生成（ヘボン式）
- イニシャル.苗字形式に統一することで、表示の一貫性を保つ

---

### 段階5: 最終辞書の作成

**目的**: player_idと選手名（日本語、かな、ローマ字）のマッピングを確定し、成績データとの紐付け準備を完了する。

**スクリプト**: `scripts/build_player_id_to_roman_full.py`

**処理内容**:

1. **統合データの処理**
   ```python
   # 段階3で統合したデータを処理
   results = []
   for player_id, row in sorted(player_dict.items()):
       result = process_row(row)  # 段階4でローマ字生成
       results.append(result)
   ```

2. **結果保存**
   - 出力ファイル: `output/master/player_id_to_roman_full.csv`
   - カラム:
     - `player_id`: 選手ID
     - `romanName`: ローマ字名（イニシャル.苗字形式）
     - `source`: 情報源（NPB_OFFICIAL、KANA_CONVERTED、MISSING）
     - `confidence`: 信頼度（HIGH、LOW）
     - `name_ja`: 選手名（日本語）
     - `name_kana`: かな

3. **検証**
   ```python
   # rows数とnuniqueが一致することを確認
   unique_player_ids = set(result['player_id'] for result in results)
   rows_count = len(results)
   unique_count = len(unique_player_ids)
   
   if rows_count == unique_count:
       print("✅ 検証成功: rows == nunique")
   else:
       print("❌ 検証失敗: rows != nunique")
   ```
   - 各player_idが1行のみであることを確認
   - 重複がないことを保証

**実行例**:
```bash
python scripts/build_player_id_to_roman_full.py
```

**出力例**:
```csv
player_id,romanName,source,confidence,name_ja,name_kana
01001001,T.Sato,NPB_OFFICIAL,HIGH,佐藤輝明,さとう てるあき
01001002,K.Okamoto,KANA_CONVERTED,HIGH,岡本和真,おかもと かずま
01001003,M.Murakami,KANA_CONVERTED,HIGH,村上宗隆,むらかみ むねたか
...
```

**統計情報**:
- 総player_id数
- romanNameが埋まった数と割合
- source別内訳（NPB_OFFICIAL、KANA_CONVERTED、MISSING）

**重要なポイント**:
- **この段階は、段階3と段階4で変換された既存の選手情報を最終的な形式にまとめているだけ**
- 各player_idに対して、1行のデータが確定する
- 最終辞書により、player_idから選手名（日本語、かな、ローマ字）を一意に取得可能
- 成績データとの紐付け準備が完了

---

## 🔗 成績データとの紐付け

**目的**: 最終辞書を使用して、成績CSVファイルに選手名情報を追加する。

**スクリプト**: `scripts/apply_roman_to_master_csvs.py`

**処理内容**:

1. **最終辞書の読み込み**
   ```python
   roman_dict = {}
   with open('output/master/player_id_to_roman_full.csv', 'r') as f:
       reader = csv.DictReader(f)
       for row in reader:
           player_id = row.get('player_id', '').strip()
           roman_dict[player_id] = {
               'romanName': row.get('romanName', '').strip(),
               'name_ja': row.get('name_ja', '').strip(),
               'name_kana': row.get('name_kana', '').strip(),
           }
   ```

2. **成績CSVファイルの処理**
   ```python
   # 各成績CSVファイルを処理
   for csv_file in batting_csv_files:
       data = []
       with open(csv_file, 'r', encoding='utf-8-sig') as f:
           reader = csv.DictReader(f)
           for row in reader:
               player_id = row.get('player_id', '').strip()
               
               # 最終辞書から選手名情報を取得
               if player_id in roman_dict:
                   row['RomanName'] = roman_dict[player_id]['romanName']
                   row['player_name_ja'] = roman_dict[player_id]['name_ja']
                   row['player_name_kana'] = roman_dict[player_id]['name_kana']
               
               data.append(row)
       
       # 更新したデータを保存
       with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
           writer = csv.DictWriter(f, fieldnames=fieldnames)
           writer.writeheader()
           writer.writerows(data)
   ```

**重要なポイント**:
- **player_idをキーとして、成績データと選手名情報を紐付ける**
- 成績CSVファイルに`RomanName`、`player_name_ja`、`player_name_kana`列を追加
- これにより、ランキング表示時に選手名を表示可能になる

---

## 📊 データフロー図（選手識別に特化）

```
【段階0: 成績データのスクレイピング（選手の存在認識）】
NPB公式サイト
└─ 各年度・各リーグの成績ページからデータを取得
    ├─ player_id: 01001001
    │  ├─ player_name_ja: 佐藤輝明
    │  ├─ player_name_en: （一部の選手のみ）
    │  └─ 成績データ: G, PA, AB, H, HR, RBI, ...
    ├─ player_id: 01001002
    │  ├─ player_name_ja: 岡本和真
    │  └─ 成績データ: ...
    └─ ...（全選手）

    ↓ [スクレイピング結果をCSVに保存]

成績CSVファイル群（段階0の出力）
├─ batting_2025_PL_from_master.csv
├─ batting_2025_CL_from_master.csv
├─ batting_2024_PL_from_master.csv
└─ ...（全年度・全リーグ、150ファイル以上）
    └─ 保存場所: _data/master_csv__import_1950_2024/

    ↓ [段階1: player_id抽出（既存情報の変換）]

all_player_ids.csv
└─ ユニークなplayer_idリスト（例: 6,958件）

    ↓ [段階2: HTMLスクレイピング]

player_id_name_kana_official.csv
├─ player_id: 01001001
│  ├─ name_ja: 佐藤輝明
│  ├─ name_kana: さとう てるあき
│  └─ roman_official: （空）
├─ player_id: 01001002
│  ├─ name_ja: 岡本和真
│  ├─ name_kana: おかもと かずま
│  └─ roman_official: （空）
└─ ...（全player_id）

    ↓ [段階3: 統合と正規化]

統合されたデータ
├─ player_id: 01001001 → 最適な行を選択
├─ player_id: 01001002 → 最適な行を選択
└─ ...（各player_idに対して1行）

    ↓ [段階4: ローマ字生成]

player_id_to_roman_full.csv
├─ player_id: 01001001
│  ├─ romanName: T.Sato
│  ├─ source: KANA_CONVERTED
│  ├─ confidence: HIGH
│  ├─ name_ja: 佐藤輝明
│  └─ name_kana: さとう てるあき
├─ player_id: 01001002
│  ├─ romanName: K.Okamoto
│  ├─ source: KANA_CONVERTED
│  ├─ confidence: HIGH
│  ├─ name_ja: 岡本和真
│  └─ name_kana: おかもと かずま
└─ ...（全player_id）

    ↓ [段階5: 成績データとの紐付け]

成績CSVファイル（更新後）
├─ batting_2025_PL_from_master.csv
│  ├─ player_id: 01001001
│  │  ├─ RomanName: T.Sato
│  │  ├─ player_name_ja: 佐藤輝明
│  │  └─ player_name_kana: さとう てるあき
│  └─ ...
└─ ...（全年度・全リーグ）
```

---

## 🔍 選手識別の信頼性

### 情報源の優先順位

1. **NPB_OFFICIAL（公式ローマ字）**
   - 信頼度: **HIGH**
   - ソース: NPB公式サイトのHTMLページから抽出
   - 外国人選手に多い
   - 例: `R.Mejias`、`B.Eldred`

2. **KANA_CONVERTED（かなから生成）**
   - 信頼度: **HIGH**
   - ソース: かなをヘボン式ローマ字に変換
   - 日本人選手に多い
   - 例: `T.Sato`、`K.Okamoto`

3. **MISSING（情報欠損）**
   - 信頼度: **LOW**
   - ソース: なし
   - HTMLページから情報を取得できなかった場合
   - 例: `（空）`

### 検証方法

1. **ユニーク性の確認**
   ```python
   # 各player_idが1行のみであることを確認
   unique_player_ids = set(result['player_id'] for result in results)
   assert len(results) == len(unique_player_ids)
   ```

2. **情報の完全性**
   ```python
   # romanNameが埋まった割合を確認
   filled_count = sum(1 for r in results if r['romanName'])
   fill_rate = filled_count / len(results) * 100
   print(f"romanName埋まり率: {fill_rate:.1f}%")
   ```

3. **ソース別の分布**
   ```python
   # ソース別の件数を確認
   source_counts = {}
   for result in results:
       source = result['source']
       source_counts[source] = source_counts.get(source, 0) + 1
   ```

---

## ⚠️ 注意事項・制約事項

### player_idの一意性

- **player_idは選手の一意性を保証する唯一の識別子**
- 同じplayer_idは常に同じ選手を表す
- 異なるplayer_idは異なる選手を表す（ただし、データの誤りがある可能性は否定できない）

### 選手名の表記ゆれ

- **選手名（日本語）の表記ゆれ**: 同じ選手でも、年度やデータソースによって表記が異なる可能性がある
  - 例: `佐藤輝明` vs `佐藤 輝明`（スペースの有無）
- **対応**: player_idで識別することで、表記ゆれの影響を回避

### 情報の欠損

- **HTMLページから情報を取得できなかった場合**: `name_ja`、`name_kana`、`roman_official`がすべて空になる可能性がある
- **対応**: エラーを記録し、処理を継続。後で手動で補完可能

### ローマ字生成の精度

- **かなからローマ字への変換**: ヘボン式ローマ字変換テーブルを使用しているが、特殊な読みには対応できない可能性がある
- **対応**: 公式ローマ字（`roman_official`）を優先使用することで、精度を向上

---

## 📝 まとめ

### 選手識別の核心

1. **【段階0】成績データのスクレイピングによる選手の存在認識**
   - **これが最も重要な段階**: NPB公式サイトから成績データをスクレイピングした時点で、「この選手が存在する」と最初に認識される
   - player_idと成績データが取得され、選手の存在が確定する
   - この段階で取得されたplayer_idが、以降の全プロセスの基盤となる

2. **player_idによる一意性の保証**
   - player_idは選手の一意性を保証する唯一の識別子（段階0で取得）
   - 複数のデータソースから同じplayer_idを集約することで、全選手のリストを確定（段階1）

3. **多様な情報源からの情報収集（段階2）**
   - HTMLスクレイピングにより、選手名（日本語）、かな、ローマ字を収集
   - 段階0で取得されたplayer_name_jaを補完・拡張する
   - 複数の情報源から取得した情報を統合し、最適な情報を選択（段階3）

4. **ローマ字名の自動生成（段階4）**
   - 公式ローマ字が存在しない場合、かなから自動生成（ヘボン式）
   - イニシャル.苗字形式に統一することで、表示の一貫性を保つ

5. **最終辞書の作成（段階5）**
   - player_idと選手名（日本語、かな、ローマ字）のマッピングを確定
   - 成績データとの紐付け準備を完了

### システムの信頼性

- **情報源の優先順位**: 公式ローマ字 > かなから生成 > 情報欠損
- **検証**: ユニーク性、情報の完全性、ソース別の分布を確認
- **エラーハンドリング**: エラーが発生しても処理を継続し、取得できた情報を記録

このプロセスにより、**全選手が「その選手たちであることを認識」され、システム全体で一貫して管理される**。

---

**作成日**: 2025年1月
**最終更新**: 2025年1月

