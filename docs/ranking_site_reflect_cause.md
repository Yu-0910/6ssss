# サイト頁に規定用CSVの結果が反映されない原因

## 原因

**ランキングページ（`/ranking/[year]/[league]`）が、ビルド済みのJSONではなくCSVを直接読み込んでいるため、Phase 2 で生成した「規定用CSV由来のJSON」が使われていません。**

| 項目 | 現状 | 期待（Phase 2 の意図） |
|------|------|------------------------|
| データソース | **CSV**（`loadBattingCsv`） | **JSON**（`loadRankingJson`） |
| 参照ファイル | `_data/master_csv_calculated/batting_{year}_{league}_from_master.csv`（全員用） | `public/data/rankings/{year}/{league}/{metric}.json`（規定必須指標は規定用CSVからビルド済み） |
| 規定の適用 | Client側で「PA >= minPA」フィルタを毎回実行 | 規定必須指標はJSON時点で規定到達者のみ（軽量・高速） |

## 該当コード

1. **`app/ranking/[year]/[league]/page.tsx`**
   - `loadBattingCsv(year, upperLeague)` で **CSV** を取得
   - `buildRankingWithAllMetrics(rows, availableMetrics)` で全指標のランキングを **CSVの行** から構築
   - `loadRankingJson` / `public/data/rankings/` は **一切参照していない**

2. **`lib/ranking/loaders.ts`**
   - `findBattingCsv()` が参照するのは `batting_{year}_{league}_from_master.csv` のみ
   - `*_qualifying.csv` は参照していない

3. **`lib/ranking/jsonLoader.ts`**
   - `loadRankingJson(year, league, metric)` は存在するが、**ランキングページからは呼ばれていない**

## 結論

Phase 2 で「規定必須指標は規定用CSVからビルドしたJSONを出力する」ようにしたが、**ランキングページはそのJSONを読まず、従来どおり全員用CSVだけを読んでいる**ため、サイト頁には規定用CSVの結果が反映されていません。

## 対応方針（案）

ランキングページで **JSON** をデータソースにする必要があります。

- **案A: 表示指標ごとにJSONを読む**  
  選択中の指標について `loadRankingJson(year, league, metric)` で取得し、そのJSONの行だけを表示する。指標切り替え時にその指標用JSONを取得。規定必須指標は規定用CSV由来（軽量）、カウント系は全員用CSV由来のJSONが既にビルドされているので、そのまま利用できる。
- **案B: 初回に全指標分のJSONを取得してマージ**  
  全指標のJSONを `loadRankingJsons` で取得し、player 単位でマージして「全指標×行」の表を作る。現在の「1CSVで全指標」に近い形を維持できるが、リクエスト数・データ量は増える。

実装コストと表示の仕様（指標ごとに1リストでよいか、全指標を1表にしたいか）に応じて案Aか案Bを選ぶ形になります。
