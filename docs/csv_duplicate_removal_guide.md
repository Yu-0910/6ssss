# CSV重複削除ガイド

## 問題の原因

ランキングページ（`/ranking/[year]/[league]`）は**CSVファイル**（`_data/master_csv_calculated/`）からデータを読み込んでいます。JSONファイル（`public/data/rankings/`）は使用されていません。

そのため、JSONファイルから重複を削除しても、ランキングページには反映されませんでした。

## 解決方法

### 1. CSVファイルから重複を削除

```bash
# ドライラン（削除しない）
py scripts\remove_duplicate_players_from_csv.py --dry-run

# 特定年度・リーグのみ
py scripts\remove_duplicate_players_from_csv.py --year 1973 --league PL

# 全年度・全リーグ
py scripts\remove_duplicate_players_from_csv.py
```

### 2. Next.jsのキャッシュをクリア

```bash
# .nextディレクトリを削除
Remove-Item -Recurse -Force .next
```

### 3. 開発サーバーを再起動

```bash
# サーバーを停止（Ctrl+C）
# サーバーを再起動
npm run dev
```

### 4. ブラウザのキャッシュをクリア

- **ハードリロード**: `Ctrl + Shift + R` (Windows/Linux) または `Cmd + Shift + R` (Mac)
- **開発者ツール**: F12 → Networkタブ → "Disable cache" にチェック

## 重複削除の基準

- **基準**: 同じ`player_id`で異なるチーム名の行がある場合
- **削除方法**: 最初に出現した行を残し、残りを削除
- **重要**: 両方とも削除することは絶対に禁止

## 確認方法

```powershell
# CSVファイルの重複を確認
$csv = Import-Csv "_data/master_csv_calculated/batting_1973_PL_from_master.csv" -Encoding UTF8
$duplicates = $csv | Group-Object player_id | Where-Object { $_.Count -gt 1 }
Write-Host "重複player_id数: $($duplicates.Count)"
```

## バックアップ

重複削除スクリプトは、削除前にバックアップを作成します：
- 場所: `output/backups/csv_backup_{timestamp}/`
