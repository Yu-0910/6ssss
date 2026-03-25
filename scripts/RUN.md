# スクリプト実行ガイド

## PowerShellでの実行時の注意事項

### コメント行の扱い

PowerShellでは、`#` で始まるコメント行をコピペすると、コマンドに渡ってしまう可能性があります。

**❌ 避けるべき例:**
```powershell
# これはコメント
py scripts/validate_outputs.py --max-year 1937
```

**✅ 推奨:**
```powershell
py scripts/validate_outputs.py --max-year 1937
```

コメントは別行に書くか、実行コマンドのみをコピペしてください。

### レポート閲覧

Markdownレポートを閲覧する際は、`type` コマンドと `more` を使用してください：

```powershell
type output\reports\audit_rankings_structure.md | more
```

`morepy` のような連結事故を防ぐため、`type` と `more` を組み合わせて使用します。

## ランキング用データの更新

- **2025年のみ（新入団追加・英字名反映・再ビルド）**: **`docs/2025_ranking_update_operations.md`**（Phase 5 運用手順書）に手順・コマンド例を記載。
- **全般**: ランキングJSON更新の推奨順序は 1) 指標計算（`compute_metrics_all_seasons.py`）→ 2) 規定到達版CSV生成（`create_qualifying_csv_all_years.py` または 2025年は `create_qualifying_csv_2025.py`）→ 3) ランキングビルド。詳細・パス一覧は **`docs/DATA_PATHS.md`** および **`docs/ranking_qualifying_csv_all_years_plan.md`** を参照。

## 実行コマンド

### 投手成績スクレイピング（1950〜2002年）

2002年を成功として、1950年まで遡って投手成績を取得する。

```powershell
py scripts/run_pitching_scrape_1950_2002.py
```

オプション:
- `--from-year 1960` … 開始年度
- `--to-year 1990` … 終了年度
- `--year 1975` … 単年度のみ
- `--dry-run` … 対象年度を表示するだけで実行しない

出力先: `_data/master_csv__import_1950_2024/pitching_{年}_{CL|PL}_from_master.csv`

注意: 1年度あたり数分〜十数分かかる場合あり。`time.sleep` によりサーバー負荷に配慮している。

### ランキング構造監査

```powershell
py scripts/audit_rankings_structure.py --from-year 1950 --to-year 2024
```

### バリデーション

```powershell
py scripts/validate_outputs.py --max-year 1937
```

### 2026年NPB選手名簿作成

NPB公示ページを基に2026年支配下選手名簿を作成し、打席・投球の利き手を記録する。

```powershell
py scripts/build_npb_roster_2026.py
```

オプション:
- `--delay 1.0` … リクエスト間隔（秒）。サーバー負荷軽減のため推奨
- `--skip-handedness` … 投打取得をスキップ（名簿のみ取得、高速）
- `--resume` … 既存CSVから再開（未取得の投打のみ取得）。中断した場合に使用
- `--output _data/npb_roster_2026.csv` … 出力パス

出力: `_data/npb_roster_2026.csv`  
列: npb_player_id, name_ja, name_en, team, team_code, position, uniform_no, throw_hand, bat_hand, is_new_2026  
- throw_hand: R=右投, L=左投  
- bat_hand: R=右打, L=左打, B=両打  

注意: 785名の利き手取得のため、約10〜15分かかる場合あり。

新規選手のローマ字名をアプリに反映する場合:

```powershell
py scripts/generate_new_players_roman_for_app.py
```

出力されたエントリを `app/players/[playerId]/page.tsx` の `playerRomanNames` に追加してください。

### 菊池涼介ブロック集計（パイロット日別）

菊池涼介（batter_id=1100082）の 2026-03-04 のYahooパイロットデータから、個人ページブロック B,D,E,F,G,H,I,J 相当を収集・集計する。

```powershell
py scripts/collect_kikuchi_blocks.py
```

出力: `_data/yahoo_games_pilot/kikuchi_20260304_blocks.json`




### 投手コース別成績（対右/対左）

森翔平 3/15 試合のコース別投球成績を取得し、青柳ページの「対右打者/対左打者 コース別の投球成績」に表示する。

```powershell
py scripts/fetch_pitcher_zone_stats.py --game-id 2021040084 --pitcher-id 2103788
```

森翔平 3/15 コース別成績（被OPS・被打率・被本塁打）のレポート表示:
```powershell
py scripts/report_mori_zone_stats.py --fetch
```

出力: `_data/yahoo_games_pilot/zone_stats_2021040084_2103788.json`

## ✅ 監査ルール（ファイル名）
- 表示名 BB/K はファイル名で BB_K に正規化（sanitize_filename準拠）
- 監査/生成ともに sanitize_filename の出力を正とする（手作業のBB-Kは禁止）
















