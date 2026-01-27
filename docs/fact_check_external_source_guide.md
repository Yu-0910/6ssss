# 外部データソースとのファクトチェック ガイド

## 概要

パソコン外のデータソース（NPB公式サイトなど）を基に、自分の打撃CSVのファクトチェックを行う方法です。

## 手順

### ステップ1: 外部データソースから選手リストを取得

NPB公式サイトなどから、対象年度・リーグの選手リストを取得します。

#### 方法A: NPB公式サイトから手動で取得

1. NPB公式サイト（https://npb.jp）にアクセス
2. 対象年度・リーグの打撃成績ページを開く
3. 選手リストをCSV形式で保存
   - カラム: `player_id`, `name`, `team` のいずれかを含む
   - または `player_id` のみでも可

#### 方法B: 既存のスクレイピングデータを使用

過去にスクレイピングしたデータがある場合：
- `_data/master_csv__import_1950_2024/batting_{YEAR}_{LEAGUE}_from_master.csv`

### ステップ2: ファクトチェックを実行

#### 方法1: 外部CSVファイルと比較

```bash
node scripts/fact_check_external_csv.mjs <YEAR> <LEAGUE> <EXTERNAL_CSV_PATH>
```

例:
```bash
node scripts/fact_check_external_csv.mjs 2025 PL external_players_2025_PL.csv
```

#### 方法2: スクレイピングデータと比較（既存スクリプト）

```bash
python scripts/fact_check_compare_scraped.py <YEAR> <LEAGUE>
```

例:
```bash
python scripts/fact_check_compare_scraped.py 2025 PL
```

#### 方法3: 年度・リーグ別の簡易チェック

```bash
node scripts/fact_check_by_year_league.mjs <YEAR> <LEAGUE>
```

例:
```bash
node scripts/fact_check_by_year_league.mjs 2025 PL
```

## 外部CSVファイルの形式

外部CSVファイルは以下の形式である必要があります：

```csv
player_id,name,team
1005137,東浜　巨,福岡ソフトバンクホークス
1005153,佐々木　健,埼玉西武ライオンズ
...
```

または、`player_id`のみでも可：

```csv
player_id
1005137
1005153
...
```

## 出力結果

ファクトチェックの結果は以下の場所に保存されます：

- **JSON形式**: `output/reports/fact_check/fact_check_{YEAR}_{LEAGUE}_external.json`
- **CSV形式（不足している選手のみ）**: `output/reports/fact_check/missing_players_{YEAR}_{LEAGUE}_external.csv`

## 注意事項

1. **2025年のデータ**: 2025年のデータはまだNPB公式サイトに公開されていない可能性があります
2. **URL構造**: NPB公式サイトのURL構造が変更されている可能性があります
3. **手動取得**: NPB公式サイトから手動で選手リストを取得する場合は、正確なデータを取得してください

## トラブルシューティング

### 外部CSVファイルが見つからない

- ファイルパスが正しいか確認
- ファイルが存在するか確認
- ファイルのエンコーディングがUTF-8（BOM付き可）か確認

### 比較結果が正しくない

- CSVファイルのカラム名を確認
- `player_id`または`name`カラムが存在するか確認
- データの形式が正しいか確認




