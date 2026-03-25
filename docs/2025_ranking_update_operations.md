# 2025年ランキング更新 運用手順書（Phase 5）

Phase 1〜4 を実行するための**実行順序**と、**新入団選手を追加する手順**をまとめたドキュメント。  
計画書: `docs/2025_ranking_page_improvement_plan.md`

---

## 1. どこを更新すればよいか（担当者向け）

| 目的 | 更新するもの | 参照 |
|------|--------------|------|
| 新入団選手をランキングに追加する | `_data/reports/2025_new_players_report.csv` に1行追加し、本手順の「新入団追加フロー」を実行 | 本文 3. |
| 既存選手の英字名を直す | 報告書の `player_name_en` を修正し、「報告書→from_master 反映」以降を実行 | 本文 3.2 |
| 成績データを差し替えた（生CSVを更新した） | 指標計算 → 規定用CSV → ランキング再ビルド | 本文 2. |
| 規定打席や試合数を変えた | 規定用CSV再生成 → ランキング再ビルド | 本文 2. の 2-2〜2-4 |

---

## 2. 2025年ランキングを一から作り直す場合（Phase 1〜4 の実行順序）

報告書や全員版CSVを触らず、**既存の from_master と報告書がある状態でランキングJSONだけ再ビルドする**場合も、本節の「2-1 は省略可能」として 2-2 以降を実行する。

### 2-1. 全員版CSVの準備（必要時のみ）

- 生CSVが `_data/master_csv__import_1950_2024/` にある前提で指標計算を行う。
- 2025年新入団選手は報告書 `_data/reports/2025_new_players_report.csv` に載せ、マージで全員版に追加する。

```powershell
# 指標計算（2025年を含む全員版CSVを再計算する場合）
python scripts/compute_metrics_all_seasons.py

# 報告書に載っている選手で全員版に不足があれば追加
python scripts/merge_2025_new_players_from_report.py
```

### 2-2. 報告書の英字名を from_master に反映

報告書の `player_name_en` を、2025年セ・パの全員版CSV（from_master）に反映する。  
**報告書を編集したあと・Phase 3 を実行したあとは必ず実行する。**

```powershell
python scripts/apply_report_en_to_from_master_2025.py
```

- 出力例: `batting_2025_CL_from_master.csv: 48 行を報告書の英字名で更新`（CL/PL 各1回）

### 2-3. 規定打席到達版CSVの生成（2025年のみ）

```powershell
python scripts/create_qualifying_csv_2025.py
```

- 出力: `_data/master_csv_calculated/batting_2025_CL_qualifying.csv`（18名）、`batting_2025_PL_qualifying.csv`（22名）など。

### 2-4. ランキングJSONの再ビルド（2025年セ・パ）

**2025年は `build_rankings_2025_PL_full.py` を使用する**（規定用/全員用の切り替えと `romanName` 出力に対応）。

```powershell
# セ・リーグ
python scripts/build_rankings_2025_PL_full.py --year 2025 --league CL

# パ・リーグ
python scripts/build_rankings_2025_PL_full.py --year 2025 --league PL
```

**PowerShell で両方まとめて実行する例:**

```powershell
python scripts/build_rankings_2025_PL_full.py --year 2025 --league CL; python scripts/build_rankings_2025_PL_full.py --year 2025 --league PL
```

- 出力先: `public/data/rankings/2025/CL/*.json`、`public/data/rankings/2025/PL/*.json`
- コンソールで絵文字が文字化けする場合: `$env:PYTHONIOENCODING='utf-8'` を事前に設定してから実行する。

---

## 3. 新入団選手を追加する手順（報告書更新フロー）

### 3.1 報告書の更新ルール

- **ファイル**: `_data/reports/2025_new_players_report.csv`
- **必須列**: `player_name_ja`（日本語名）、`team`（球団名）、`player_name_en`（英字名）。  
  `name_kana`（ひらがな）は任意だが、英字名を自動変換する場合は揃えておくとよい。
- **タイミング**: シーズン中・オフを問わず、新入団が判明したら1行追加する。
- **備考**: 「備考」列に出典・メモを書いておくと後から追いやすい。

### 3.2 新入団追加後の実行順序（番号付きチェックリスト）

1. **報告書を編集する**  
   `_data/reports/2025_new_players_report.csv` に、新入団選手の行を追加（`player_name_ja`, `team`, `player_name_en` を入力）。

2. **全員版CSVにマージする**  
   ```powershell
   python scripts/merge_2025_new_players_from_report.py
   ```  
   報告書に載っているが全員版にいない選手が、最小行（またはバックアップの成績）で追加される。

3. **報告書の英字名を from_master に反映する**  
   ```powershell
   python scripts/apply_report_en_to_from_master_2025.py
   ```

4. **規定打席到達版CSVを再生成する**  
   ```powershell
   python scripts/create_qualifying_csv_2025.py
   ```

5. **ランキングJSONを再ビルドする（CL・PL 両方）**  
   ```powershell
   python scripts/build_rankings_2025_PL_full.py --year 2025 --league CL
   python scripts/build_rankings_2025_PL_full.py --year 2025 --league PL
   ```

- 一括で「マージ → ランキング再ビルド」まで行うスクリプト `merge_2025_new_players_and_build_rankings.py` もあるが、**英字名反映（手順 3）と規定用CSV再生成（手順 4）は含まれていない**。英字名と規定用CSVを確実に反映する場合は、上記 1〜5 を順に実行すること。

---

## 4. バックアップの取り方

- **報告書を大きく変える前**: `_data/reports/2025_new_players_report.csv` を別名コピー（例: `2025_new_players_report.csv.bak.YYYYMMDD`）。
- **全員版CSVを上書きする前**: `_data/master_csv_calculated/batting_2025_CL_from_master.csv` と `batting_2025_PL_from_master.csv` を同じディレクトリに `.bak.YYYYMMDD` などでコピー。
- **ランキングJSON**: 必要に応じて `public/data/rankings/2025/` を丸ごとコピー。

```powershell
# 例: 報告書のバックアップ（日付は任意）
Copy-Item _data/reports/2025_new_players_report.csv _data/reports/2025_new_players_report.csv.bak.20250129
```

---

## 5. 再ビルドのコマンド例（クイック参照）

| 作業内容 | コマンド例（PowerShell） |
|----------|---------------------------|
| 報告書の英字名だけ from_master に反映 | `python scripts/apply_report_en_to_from_master_2025.py` |
| 規定用CSVだけ再生成（2025年） | `python scripts/create_qualifying_csv_2025.py` |
| 2025年セのみランキング再ビルド | `python scripts/build_rankings_2025_PL_full.py --year 2025 --league CL` |
| 2025年パのみランキング再ビルド | `python scripts/build_rankings_2025_PL_full.py --year 2025 --league PL` |
| 2025年セ・パ両方ランキング再ビルド | `python scripts/build_rankings_2025_PL_full.py --year 2025 --league CL; python scripts/build_rankings_2025_PL_full.py --year 2025 --league PL` |
| 新入団マージのみ | `python scripts/merge_2025_new_players_from_report.py` |

---

## 6. 注意事項（ネガティブポイントと対処）

| 事象 | 対処 |
|------|------|
| 担当者が「どこを更新すればよいか」分からない | 本ドキュメントの「1. どこを更新すればよいか」と「3.2 チェックリスト」を参照する。 |
| `--year` / `--league` を間違える | 上記コマンド例をコピーして使う。2025年は必ず `--year 2025`。CL/PL は両方実行する場合は2行とも実行する。 |
| 報告書を更新したのにサイトに英字名が出ない | 手順 3（`apply_report_en_to_from_master_2025.py`）と手順 4〜5（規定用CSV・ランキング再ビルド）を実行したか確認する。 |
| 再ビルド後にブラウザで古いJSONが見える | ハードリロード（Ctrl+Shift+R など）。本番では CDN/キャッシュの無効化を検討する。 |

---

## 7. 参照

- 計画書: `docs/2025_ranking_page_improvement_plan.md`
- データパス・スクリプト一覧: `docs/DATA_PATHS.md`
- Phase 1〜4 評価: `docs/phase1_to_4_evaluation.md`
- 規定用・全員用のサイト側整理: `docs/ranking_qualifying_filter_phase4.md`
