# Cursor向けプロンプト：ランキングヘッダークリックでソート切替

## 目的
`/ranking/2025/PL` ページのテーブルヘッダーをクリック可能にし、クリックでソート切替が動くようにする。

## 現状の問題（原因切り分け結果）

### 1) ヘッダーがクリック要素になっていない
- `components/RankingUI.tsx` の133-140行目: ヘッダーは単純な `<th>` 要素のみ
- button/Link が存在しない
- クリックハンドラが無い

### 2) 全指標を横に並べる実装になっていない
- 現在は1指標（activeMetric）のみ表示
- 全指標を横に並べる列構造になっていない

### 3) ソート処理が実装されていない
- URLクエリパラメータ（sort, order）の読み取りが無い
- ソート処理が無い

## 修正方針

### 1) 全指標を横に並べるテーブル構造に変更
- `components/RankingUI.tsx` のテーブルヘッダーを全指標分の列を生成
- 各行に全指標の値を表示（`row[metric.key]` で取得）
- 値が無い場合は `"-"` を表示

### 2) ヘッダーにクリック可能なbuttonを追加
- 各指標のヘッダーに `<button type="button">` を配置
- `cursor-pointer`, `hover:underline` を追加
- アクティブなソート指標は背景色を変更（例: `bg-[#ffff44]`）

### 3) ソート処理をClient Componentで実装
- `app/ranking/2025/PL/RankingPageClient.tsx` で `useSearchParams` から `sort`, `order` を取得
- デフォルト: `sort=ops`, `order=desc`
- ソート処理は `useMemo` で実装（依存配列: `[rows, sortKey, order]`）
- ソートは in-place を禁止: `const sorted = [...rows].sort(...)`

### 4) URLクエリパラメータでソート状態を管理
- ヘッダークリックで `router.replace()` により `/ranking/2025/PL?sort=xxx&order=yyy` を更新
- 同じ指標を押したら `order` をトグル（`desc` ↔ `asc`）
- 違う指標なら `order` をデフォルト（`desc`）に戻す

### 5) データ取得の変更
- Server Component (`app/ranking/2025/PL/page.tsx`) で全指標のデータを含む `rows` を生成
- `buildRanking` ではなく、全指標の値を含む `rows` を返す関数を作成
- 各 `row` に全指標の値（`row[metric.key]`）を含める

## 実装タスク

### タスク1: データ取得関数の修正
- `lib/ranking/adapter.ts` に `buildRankingWithAllMetrics` 関数を追加
- 入力: `rows: BattingCsvRow[]`, `availableMetrics: MetricDefinition[]`
- 出力: 全指標の値を含む `RankedPlayer[]`（ソートは行わない、生データ）
- 各 `row` に全指標の値を設定: `player[metric.key] = getMetricValue(row, metric)`
- `RankingRow` 型を拡張して、`[key: string]: any` で全指標の値を許可

### タスク2: Server Componentの修正
- `app/ranking/2025/PL/pag2025年e.tsx` で `buildRankingWithAllMetrics` を使用
- `activeMetric` は使用しない（ソートはClient側で行う）
- `viewModel.rows` に全指標の値を含む配列を設定

### タスク3: Client Componentの修正
- `app/ranking/2025/PL/RankingPageClient.tsx` で `useSearchParams` から `sort`, `order` を取得
- デフォルト: `sort=ops`, `order=desc`
- ソート処理を `useMemo` で実装
  - `getSortOrder(metric)` でデフォルトソート順を取得（K%のみ昇順）
  - ソートは in-place を禁止: `const sorted = [...rows].sort(...)`
  - 依存配列: `[rows, sortKey, order]`
- `RankingUI` に `sortedRows`, `sortKey`, `order`, `onSortChange` を渡す

### タスク4: RankingUIの修正
- テーブルヘッダーを全指標分の列を生成（`metrics.map`）
- 各ヘッダーに `<button type="button">` を配置
- クリックで `onSortChange(metric.key)` を呼ぶ
- アクティブなソート指標は背景色を変更（`sortKey === metric.key` の時）
- ソート順の表示（`order === 'asc'` なら `↑`, `desc` なら `↓`）
- テーブルボディで全指標の値を表示（`row[metric.key]`）
- 値が無い場合は `"-"` を表示
- `formatStat(metric.label, value)` でフォーマット

## 制約
- UIデザインは維持（色、フォント、レイアウト）
- 列を消さない（全指標を表示）
- `/ranking/2025/PL/[metric]` のようなページは作らない
- 1つの表のまま

## 完了条件
- `/ranking/2025/PL` を開く
- ヘッダーの OPS / 打率 / HR を押すと
  - URLの `sort` が変わる
  - 表の順位が変わる
  - 列は消えない（他指標も表示されたまま）
- リロードしても同じ並びになる
- console error なし
