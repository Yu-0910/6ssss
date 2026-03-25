# Phase 3（英字名充足）評価

## 1. 達成したこと

| 項目 | 評価 | 内容 |
|------|------|------|
| 既存選手の流用 | ✅ 達成 | 2024年以前の from_master から 10,223 件の英字名を収集し、2025年CSVの**空欄行のみ**に流用するロジックを実装。今回の実行では2025年側が既に埋まっていたため流用更新 0 件だったが、仕様どおり動作。 |
| 新外国人の表示 | ✅ 達成 | 24名全員に `FOREIGN_ROMAN_LOOKUP` で英字表記を設定（「モイセエフ・ニキータ」を LOOKUP に追加済み）。報告書の `player_name_en` および from_master 反映可能。 |
| 日本人新選手のひらがな→ローマ字 | ✅ 達成 | **Playwright** 導入＋手動補完（徳山一翔: とくやま・かずと / Tokuyama Kazuto）により **93名全員** が `name_kana` / `player_name_en` 充足。 |
| 報告書→from_master 連携 | ✅ 達成 | Step 3（phase3）および `apply_report_en_to_from_master_2025.py` で報告書の `player_name_en` を from_master に一括反映。 |
| オプション | ✅ 達成 | `--skip-scrape`（スクレイピング省略）、`--dry-run`（書き込みなし）で運用しやすい。 |

---

## 2. 実行結果の整理

- **Step 1（流用）**: 過去 10,223 件読み込み。2025年CL/PL は既に英字名が入っていたため **0 件更新**。
- **Step 2（報告書）**: 新外国人 24 名全員に `player_name_en` を設定。日本人新選手は Playwright スクレイピング＋手動補完（徳山一翔含む）で **93名全員** が `name_kana` / `player_name_en` 充足。
- **Step 3（from_master 反映）**: 報告書の英字名を `batting_2025_CL_from_master.csv` / `batting_2025_PL_from_master.csv` に反映（`phase3_fill_roman_names_2025.py` の Step 3 および `apply_report_en_to_from_master_2025.py` で実施済み）。

---

## 3. 課題・ギャップ

### 3.1 未充足の解消（済）

| 選手名 | 対応内容 |
|--------|----------|
| **徳山一翔** | 報告書に手動で `name_kana`: とくやま・かずと、`player_name_en`: Tokuyama Kazuto を追加済み。 |
| **モイセエフ・ニキータ** | 報告書に `player_name_en`: Nikita Moiseev を追加。`phase3_fill_roman_names_2025.py` の `FOREIGN_ROMAN_LOOKUP` に `'モイセエフ・ニキータ': 'Nikita Moiseev'` を追加済み。 |

### 3.2 流用のキーが「名前＋チーム」のみ

- 2024年以前のデータは `normalize_name(player_name_ja)::team` で検索。表記ゆれ（スペース・全角等）で一致しないと流用されない。
- 同一名前の他チーム在籍歴がある場合は、どちらか一方の英字名が使われる可能性がある（現状仕様として許容）。

### 3.3 スクレイピングの負荷と安定性

- Playwright により JS 描画後のページから取得可能になったが、1 名あたり成績ページ＋個人ページのアクセスが必要。都度保存で中断時も進捗は保持。
- NPB の HTML 構造変更やアクセス制限で取得できなくなるリスクあり。`--skip-scrape` で外国人LOOKUPと流用のみに絞る運用は有効。

---

## 4. 改善提案（優先度順）

1. **from_master 反映**: 報告書更新後は `apply_report_en_to_from_master_2025.py` を実行し、from_master CSV に英字名を反映する。
2. **手動補完の運用**: 報告書の `name_kana` / `player_name_en` を手動で入力した行は、Phase 3 再実行時に上書きしない（既に値がある場合はスキップする仕様は済み）。手動で埋めたあと Step 3 または `apply_report_en_to_from_master_2025.py` で from_master に反映する流れを運用として固定するとよい。
3. **ランキングJSONへの反映**: Phase 3 実行後、規定用CSV再生成とランキング再ビルドを行わないと、サイト表示の `romanName` は変わらない。`docs/DATA_PATHS.md` のチェックリストに「Phase 3 実行後は規定用CSV・ランキング再ビルドを行う」を追記するとよい。

---

## 5. 総合評価

| 観点 | 評価 |
|------|------|
| 計画書との整合 | ✅ 既存流用・新外国人LOOKUP（24名全員・モイセエフ含む）・報告書→from_master 反映は計画どおり。日本人新選手は Playwright＋手動補完（徳山一翔含む）で **93名全員** 充足。 |
| 運用性 | ✅ `--skip-scrape` / `--dry-run` で安全に試行可能。Playwright は都度保存で中断時も進捗保持。 |
| 品質 | ✅ 新外国人24名・日本人新選手93名とも英字名／ひらがな充足済み。未充足 0 名。 |
| 保守性 | ✅ スクリプト単体で完結し、LOOKUP の追加やキー変更がしやすい。 |

**結論**: Phase 3 の「既存選手の英字名流用」「新外国人の名前の下にスペル表示」「日本人新選手のひらがな→ローマ字」は、LOOKUP 追加（モイセエフ・ニキータ）と手動補完（徳山一翔）により**全員充足**。Phase 3 は**完了**と評価できる。報告書更新後は `apply_report_en_to_from_master_2025.py` の実行とランキング再ビルドでサイトに反映される。
