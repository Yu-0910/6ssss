# CSV重複問題の修正と反映確認手順

## 実装内容

### (A) ランキングページを強制的に動的にする（キャッシュ無効化）

**ファイル**: `app/ranking/[year]/[league]/page.tsx`

```typescript
export const dynamic = 'force-dynamic'
export const revalidate = 0
```

これにより、Next.jsの静的化、ISR、route cacheが無効化され、常に最新のCSVデータが読み込まれます。

### (B) loadBattingCsvが読んだCSVパスを返す

**ファイル**: `lib/ranking/loaders.ts`

- `loadBattingCsv()` の返り値に `csvPath` を追加
- 開発時のみログ出力: `[loadBattingCsv] using: {csvPath}, rows: {rows.length}`

### (C) 画面に読んだCSVパスと重複数を表示（開発時のみ）

**ファイル**: 
- `app/ranking/[year]/[league]/page.tsx` - 重複統計の計算
- `components/RankingUI.tsx` - デバッグ情報の表示

ページ下部に表示:
```
DataSource: {csvPath}
Duplicates: {duplicatePlayerIdCount} ids / {duplicateRowCount} rows
```

### (D) ランタイムでplayer_id重複排除（安全装置）

**ファイル**: `lib/ranking/adapter.ts` の `buildRankingWithAllMetrics()`

- 同じ`player_id`で複数行がある場合、PAが最大の行を優先（次点AB最大）
- `player_id`が空の行は除外
- これにより、CSVが再度汚れてもUIには重複が表示されない

### (E) findBattingCsvの優先順位確認

**ファイル**: `lib/ranking/loaders.ts`

優先順位（正しく設定済み）:
1. `_data/master_csv_calculated/batting_{year}_{league}_from_master.csv` ← 計算済みCSV優先
2. `_data/master_csv/batting_{year}_{league}_from_master.csv`
3. プロジェクトルート直下の `batting_{year}_{league}_from_master.csv`

## 反映確認手順

### 1. 開発サーバーを停止

ターミナルで `Ctrl + C` を押してサーバーを停止してください。

### 2. .nextディレクトリを削除

```powershell
Remove-Item -Recurse -Force .next
```

### 3. 開発サーバーを起動

```powershell
npm run dev
```

### 4. ランキングページを開く

ブラウザで以下のURLにアクセス:
- `http://localhost:3000/ranking/1973/PL` または
- `http://localhost:3001/ranking/1973/PL`

### 5. デバッグ情報を確認

ページ下部に以下の情報が表示されていることを確認:

```
DataSource: C:\Users\short\OneDrive\ドキュメント\デスクトップ\TopPage\_data\master_csv_calculated\batting_1973_PL_from_master.csv
Duplicates: 0 ids / 0 rows
```

**確認ポイント**:
- ✅ `DataSource` が `_data/master_csv_calculated/...` になっているか
- ✅ `Duplicates` が `0 ids / 0 rows` になっているか

### 6. ターミナルのログを確認

開発サーバーのターミナルに以下のようなログが表示されていることを確認:

```
[loadBattingCsv] Searching for CSV: batting_1973_PL_from_master.csv
[loadBattingCsv] Found path: C:\Users\...\TopPage\_data\master_csv_calculated\batting_1973_PL_from_master.csv
[loadBattingCsv] Successfully read CSV with encoding: utf-8-sig
[loadBattingCsv] Parsed 243 rows
[loadBattingCsv] using: C:\Users\...\TopPage\_data\master_csv_calculated\batting_1973_PL_from_master.csv, rows: 243
```

## トラブルシューティング

### DataSourceが想定と異なる場合

1. **`_data/master_csv/` に同じファイルがある場合**
   - `_data/master_csv_calculated/` のファイルを確認
   - `_data/master_csv/` のファイルを削除または移動

2. **パスが正しく探索されていない場合**
   - `lib/ranking/loaders.ts` の `findBattingCsv()` を確認
   - ファイルが実際に存在するか確認

### Duplicatesが0にならない場合

1. **CSVファイルに重複が残っている**
   - `scripts/remove_duplicate_players_from_csv.py` を再実行
   - CSVファイルを直接確認

2. **重複排除ロジックが動作していない**
   - `lib/ranking/adapter.ts` の `buildRankingWithAllMetrics()` を確認
   - ターミナルのログを確認

### キャッシュが残っている場合

1. **ブラウザのキャッシュをクリア**
   - ハードリロード: `Ctrl + Shift + R`
   - シークレットモードで確認

2. **Next.jsのキャッシュを再確認**
   - `.next` ディレクトリが完全に削除されているか確認
   - サーバーを再起動

## 期待される動作

1. **常に最新のCSVデータが読み込まれる**
   - `export const dynamic = 'force-dynamic'` により、キャッシュが無効化される

2. **重複選手が表示されない**
   - ランタイムで重複排除が行われる
   - 画面下部の `Duplicates` が `0 ids / 0 rows` になる

3. **正しいCSVファイルが読み込まれる**
   - `_data/master_csv_calculated/` のファイルが優先的に読み込まれる
   - 画面下部の `DataSource` で確認できる
