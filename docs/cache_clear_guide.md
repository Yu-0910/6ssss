# ローカルサーバーで変化が反映されない場合の対処法

## 原因

ランキングJSONファイル（`public/data/rankings/`）を更新しても、トップページのリーダー表示には影響しません。

**理由**:
- トップページのリーダー表示は**CSVファイル**（`_data/master_csv/` または `_data/master_csv_calculated/`）から読み込まれています
- ランキングJSONファイルは別の用途（ランキングページ表示用）で使用されています

## 解決方法

### 1. Next.jsのキャッシュをクリア

```powershell
# .nextディレクトリを削除
Remove-Item -Recurse -Force .next
```

### 2. 開発サーバーを再起動

```powershell
# サーバーを停止（Ctrl+C）
# その後、再起動
npm run dev
```

### 3. ブラウザのキャッシュをクリア

- **Chrome/Edge**: `Ctrl + Shift + Delete` → キャッシュされた画像とファイルを削除
- **Firefox**: `Ctrl + Shift + Delete` → キャッシュを削除
- または、ハードリロード: `Ctrl + Shift + R` (Windows) / `Cmd + Shift + R` (Mac)

### 4. CSVファイルからも重複を削除する必要がある場合

トップページのリーダー表示に重複選手が表示されている場合は、CSVファイルからも重複を削除する必要があります。
