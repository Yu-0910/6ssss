# CSV重複削除が反映されない問題の解決方法

## 確認済み

✅ CSVファイルから重複は削除されています
- `player_id`での重複: 0件
- `player_name_ja`での重複: 0件

## 原因

Next.jsのキャッシュが原因の可能性が高いです。

## 解決手順

### 1. 開発サーバーを停止

ターミナルで `Ctrl + C` を押してサーバーを停止してください。

### 2. Next.jsのキャッシュをクリア

```powershell
Remove-Item -Recurse -Force .next
```

### 3. 開発サーバーを再起動

```powershell
npm run dev
```

### 4. ブラウザのキャッシュをクリア

以下のいずれかを実行してください：

**方法1: ハードリロード**
- `Ctrl + Shift + R` (Windows/Linux)
- `Cmd + Shift + R` (Mac)

**方法2: 開発者ツールを使用**
1. `F12` で開発者ツールを開く
2. `Network` タブを開く
3. `Disable cache` にチェックを入れる
4. ページをリロード

**方法3: シークレットモードで確認**
- 新しいシークレットウィンドウで `http://localhost:3001/ranking/1973/PL` にアクセス

### 5. 確認

以下のURLにアクセスして、重複選手が表示されないことを確認してください：
- `http://localhost:3001/ranking/1973/PL`
- 以前重複していた選手（例: 竹之内 雅史、基 満男）が1回だけ表示されることを確認

## それでも反映されない場合

### サーバーのログを確認

開発サーバーのターミナルに以下のようなログが表示されているか確認してください：

```
[loadBattingCsv] Searching for CSV: batting_1973_PL_from_master.csv
[loadBattingCsv] Found path: C:\Users\...\TopPage\_data\master_csv_calculated\batting_1973_PL_from_master.csv
[loadBattingCsv] Parsed XXX rows
```

### 実際に読み込まれているCSVファイルを確認

サーバーのログに表示されているパスが、実際に更新したCSVファイルと同じか確認してください。

### 別のCSVファイルが読み込まれている可能性

`lib/ranking/loaders.ts`の`findBattingCsv`関数は、以下の優先順位でCSVファイルを探します：

1. `_data/master_csv/batting_{year}_{league}_from_master.csv`
2. `_data/master_csv_calculated/batting_{year}_{league}_from_master.csv` ← こちらを更新しました
3. プロジェクトルート直下の `batting_{year}_{league}_from_master.csv`

もし `_data/master_csv/` に同じファイルがある場合、そちらが優先的に読み込まれます。

### 確認方法

```powershell
# どのCSVファイルが存在するか確認
Get-ChildItem -Recurse -Filter "batting_1973_PL_from_master.csv" | Select-Object FullName
```
