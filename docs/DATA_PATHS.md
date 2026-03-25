# ランキング用データのパス一覧（正のパス）

規定用・全員用CSV分割およびランキングJSON生成で参照する「正」のディレクトリと、各スクリプトの入出力をまとめる。  
詳細な実行順序・Phase は `docs/ranking_qualifying_csv_all_years_plan.md` を参照。

---

## ディレクトリ役割

| パス | 役割 | 備考 |
|------|------|------|
| `_data/master_csv__import_1950_2024/` | スクレイピング／インポート済みの**生CSV**（年度・リーグ別） | 1950年〜2025年を格納。スクレイパの出力先。 |
| `_data/master_csv/` | 生CSVの別置き場（従来運用） | 必要に応じて import フォルダからコピーする運用も可。 |
| `_data/master_csv_calculated/` | 指標計算済みの**全員用CSV**および**規定到達版CSV**の格納先 | 入力: 生CSV。出力: `*_from_master.csv`（全員用）、`*_qualifying.csv`（Phase 1 で生成）。 |
| `public/data/rankings/` | ランキング用**JSON**の出力先 | 年度／リーグ／指標別。サイト頁が読みにいく。 |
| `config/games_per_team_by_season.json` | 試合数マップ（規定打席算出用） | 未作成時は CSV の G 列から推定。 |

---

## スクリプト別 入力・出力

| スクリプト | 入力 | 出力 |
|------------|------|------|
| `scripts/scrape_npb_batting_stats.py` | NPB 公式（HTTP） | `_data/master_csv__import_1950_2024/batting_{year}_{league}_from_master.csv` |
| `scripts/compute_metrics_all_seasons.py` | `_data/master_csv/` または `--input-dir` で指定（例: `_data/master_csv__import_1950_2024`） | `_data/master_csv_calculated/batting_*_from_master.csv` |
| `scripts/create_qualifying_csv_all_years.py` | `_data/master_csv_calculated/batting_*_from_master.csv` | `_data/master_csv_calculated/batting_*_qualifying.csv` |
| `scripts/build_rankings_from_calculated.py` | `_data/master_csv_calculated/`（from_master + qualifying） | `public/data/rankings/{YEAR}/{LEAGUE}/*.json` |
| `scripts/build_rankings_2025_PL_full.py` | `_data/master_csv_calculated/`（2025年セ・パ） | `public/data/rankings/2025/{CL\|PL}/*.json` |

---

## 推奨実行順序（ランキング用データ更新）

1. スクレイピング／インポート → 生CSVを `_data/master_csv__import_1950_2024/` に配置
2. 指標計算: `python scripts/compute_metrics_all_seasons.py`（必要なら `--input-dir _data/master_csv__import_1950_2024`）
3. 規定到達版CSV生成: `python scripts/create_qualifying_csv_all_years.py`
4. ランキングJSON生成:  
   - 2024年以前: `python scripts/build_rankings_from_calculated.py`  
   - 2025年: `python scripts/build_rankings_2025_PL_full.py --year 2025 --league CL` および `--league PL`（規定/全員の切り替え・romanName 出力に対応。両方: `--league CL` のあとに `--league PL` を実行）。
5. **2025年新入団選手の追加（報告書ベース・運用ルール）**  
   シーズン中・オフに新入団が判明したら、**報告書に1行追加**し、以下を実行する。  
   - **詳細な手順・バックアップ・コマンド例**: **`docs/2025_ranking_update_operations.md`**（Phase 5 運用手順書）を参照。  
   - **手順（2025年ランキング更新チェックリスト）**  
     1. `_data/reports/2025_new_players_report.csv` を編集し、新入団選手の行を追加（player_name_ja, team, player_name_en 必須。備考は任意）。  
     2. `python scripts/merge_2025_new_players_from_report.py` で全員版CSVに不足分を追加（バックアップに成績があれば流用、無ければ最小行で追加）。  
     3. `python scripts/apply_report_en_to_from_master_2025.py` で報告書の英字名を from_master に反映。  
     4. `python scripts/create_qualifying_csv_2025.py` で規定打席到達版CSVを再生成。  
     5. `python scripts/build_rankings_2025_PL_full.py --year 2025 --league CL` および `--league PL` でランキングJSONを再生成（2025年はこのスクリプト推奨。romanName 出力対応）。  
   - 一括実行（マージ＋ビルドのみ）: `python scripts/merge_2025_new_players_and_build_rankings.py`。英字名反映・規定用CSV再生成は含まれないため、確実に反映する場合は上記 1〜5 を順に実行すること。

6. **2025年「全選手用」CSVの更新版を作り、新入団・新外国人を組み込んでランキング反映（一括）**:  
   2024年型の非規定（全選手用）CSVの更新版を作成し、2025年新入団・新外国人を組み込み、規定用CSV作成〜ランキングJSON再生成まで一括で行う場合:  
   `python scripts/build_2025_full_from_master_and_rankings.py`  
   - スクレイプをスキップして既存CSVのみでマージ〜ランキングまで行う: `--skip-scrape`  
   - 手順: 現在の2025 from_masterをバックアップ → （オプション）NPBスクレイプ → 指標計算 → 報告書の選手で不足分を追加（バックアップに居れば成績を反映） → 規定打席到達版CSV作成 → ランキングJSON再生成（CL/PL）

---

## 分割実行の例（Phase 5）

- **規定用CSVを decade 単位で生成**: `--year` は単年度指定のため、複数回実行する。例: 1950年代のみ → `python scripts/create_qualifying_csv_all_years.py --year 1950` から `--year 1959` まで順に実行（または一括で `create_qualifying_csv_all_years.py` を引数なしで実行）。
- **ランキングビルドを年度・リーグで絞る**: `python scripts/build_rankings_from_calculated.py --year 2024 --league CL`（2024年CLのみ）。`--year 1975 --league PL` で1975年PLのみ。
- **規定ルールや games_map を変更した場合**: 規定打席の算出ロジック（`qualifying_rules.py` / `games_per_team_by_season.json`）を変更したら、規定用CSVの再生成とランキングの再ビルドを行う。対象ファイル確認: `create_qualifying_csv_all_years.py --dry-run`。

---

## 検証（Phase 3）

- **サンプル年度での確認**: `--year 2024 --league CL` や `--year 1975 --league PL` で Phase 1 → Phase 2 を実行し、規定必須指標の JSON が規定用CSV由来で行数・上位が期待どおりか確認する。
- **規定用CSVなし時のフォールバック**: 規定用CSVを一時的にリネームまたは削除した状態でビルドし、従来どおり全員用CSV＋minPA で JSON が生成されることを確認する。
