# ランキングページのデータ表示フロー

## 概要

このドキュメントでは、ランキングページ（`/ranking/[year]/[league]`）に成績が表示されるまでの全体的なデータフローと、関連するファイルの関係性を説明します。

## データフロー全体図

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. データソース（CSVファイル）                                   │
│    _data/master_csv_calculated/batting_{year}_{league}_from_master.csv │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Record.csv（指標の順番定義）                                  │
│    Record.csv または _data/master_csv/Record.csv                  │
│    → 表示する指標のリストと順番を定義                            │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. サーバー側処理（Next.js Server Component）                    │
│    app/ranking/[year]/[league]/page.tsx                          │
│    → loadBattingCsv() でCSVを読み込み                           │
│    → buildRankingWithAllMetrics() でランキングデータを生成       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. クライアント側処理（React Client Component）                  │
│    app/ranking/[year]/[league]/RankingPageClient.tsx             │
│    → ソート処理、規定打席フィルタ、URLクエリパラメータ管理       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. UI表示（Pure UI Component）                                  │
│    components/RankingUI.tsx                                      │
│    → テーブル形式でランキングを表示                               │
└─────────────────────────────────────────────────────────────────┘
```

## 詳細な処理フロー

### ステップ1: CSVファイルの読み込み

**ファイル**: `lib/ranking/loaders.ts`

**関数**: `loadBattingCsv(year: string, league: string)`

**処理内容**:

1. **CSVファイルの探索**（優先順位順）
   ```typescript
   1. _data/master_csv_calculated/batting_{year}_{league}_from_master.csv
   2. _data/master_csv/batting_{year}_{league}_from_master.csv
   3. プロジェクトルート直下の batting_{year}_{league}_from_master.csv
   ```

2. **CSVファイルの読み込み**
   - 複数エンコーディング対応（`utf-8-sig`, `utf-8`, `shift_jis`, `cp932`）
   - CSVをパースして `BattingCsvRow[]` に変換

3. **Record.csvから指標リストを取得**
   - `loadMetricsFromRecord()` を呼び出し
   - Record.csvの順番で指標定義の配列を取得

4. **利用可能な指標のフィルタリング**
   - CSVに存在する指標のみを抽出
   - Record.csvの順番を保持

**出力**:
```typescript
{
  rows: BattingCsvRow[],        // CSVから読み込んだ全選手データ
  availableMetrics: MetricDefinition[]  // Record.csv順の利用可能な指標
}
```

### ステップ2: Record.csvの読み込み

**ファイル**: `lib/ranking/record.ts`

**関数**: `loadMetricsFromRecord()`

**処理内容**:

1. **Record.csvの探索**（優先順位順）
   ```typescript
   1. プロジェクトルート直下の Record.csv
   2. _data/master_csv/Record.csv
   3. data/Record.csv
   ```

2. **指標リストの抽出**
   - 1行目を読み込み（カンマ区切りまたはタブ区切り）
   - 除外列（`id`, `name`, `label`, `desc`など）を除外
   - 各指標名を正規化して `MetricDefinition` に変換

3. **指標名のマッピング**
   - `config/metric_map.json` を使用してJSONキー名を取得
   - 例: `BB%` → `bbPct`, `K%` → `kpct`, `BB/K` → `bbk`

**出力**:
```typescript
MetricDefinition[] = [
  { key: 'ops', label: 'OPS', csvKey: 'OPS' },
  { key: 'avg', label: '打率', csvKey: '打率' },
  // ... Record.csvの順番で並ぶ
]
```

### ステップ3: ランキングデータの生成

**ファイル**: `lib/ranking/adapter.ts`

**関数**: `buildRankingWithAllMetrics(rows, availableMetrics)`

**処理内容**:

1. **規定打席フィルタ**
   ```typescript
   const filteredRows = rows.filter(row => {
     const pa = getNumericValue(row, ['PA', 'pa', '打席'])
     return pa !== null && pa > 0
   })
   ```

2. **全指標の値を含むランキング行を生成**
   - 各選手の行に対して、全指標の値を取得
   - `getMetricValue(row, metric)` で指標の値を取得
   - 計算で補完される指標（BB%、K%、BB/K）も処理

3. **選手情報の抽出**
   - `getPlayerNames(row)` で選手名、ローマ字名、playerIdを取得
   - `getTeamName(row)` でチーム名を取得

**出力**:
```typescript
RankingRow[] = [
  {
    rank: 1,  // 仮のランク（Client側でソート後に再計算）
    playerId: "1003820",
    name: "加藤 英司",
    romanName: "A.Hishikawa",
    team: "オリックス・バファローズ",
    ops: 0.959,
    avg: 0.337,
    hr: 20,
    // ... 全指標の値
  },
  // ...
]
```

### ステップ4: サーバーコンポーネントでの統合

**ファイル**: `app/ranking/[year]/[league]/page.tsx`

**処理内容**:

1. **URLパラメータの取得**
   ```typescript
   const { year, league } = await params
   ```

2. **CSVデータの読み込み**
   ```typescript
   const { rows, availableMetrics } = loadBattingCsv(year, league.toUpperCase())
   ```

3. **ランキングデータの生成**
   ```typescript
   const rankingRows = buildRankingWithAllMetrics(rows, availableMetrics)
   ```

4. **ViewModelの構築**
   ```typescript
   const viewModel: RankingViewModel = {
     title: `${leagueName}　打撃成績ランキング (${year}年)`,
     season: year,
     league: league.toUpperCase(),
     metrics: availableMetrics,
     activeMetric: 'ops',
     rows: rankingRows,
   }
   ```

5. **Client Componentに渡す**
   ```typescript
   <RankingPageClient initialViewModel={viewModel} />
   ```

### ステップ5: クライアント側でのソートとフィルタ

**ファイル**: `app/ranking/[year]/[league]/RankingPageClient.tsx`

**処理内容**:

1. **URLクエリパラメータからソート情報を取得**
   ```typescript
   const sortKey = searchParams.get('sort') || 'ops'
   const order = searchParams.get('order') || 'desc'
   ```

2. **規定打席フィルタの適用**
   - 指標ごとに規定打席が必要か判定（`shouldRequireQualifyingPA()`）
   - 年度・リーグごとの規定打席を計算（`calculateMinPA()`）
   - 1950-1958年の特別ルール（規定打数を使用）も考慮

3. **ソート処理**
   ```typescript
   const sortedRows = useMemo(() => {
     // 規定打席フィルタを適用
     let filteredRows = rows.filter(row => {
       const pa = row.pa || row.PA
       return pa >= minPA
     })
     
     // ソート（降順がデフォルト、K%のみ昇順）
     filteredRows.sort((a, b) => {
       const aValue = a[sortKey] ?? 0
       const bValue = b[sortKey] ?? 0
       return order === 'asc' ? aValue - bValue : bValue - aValue
     })
     
     // ランクを再計算
     return filteredRows.map((row, index) => ({
       ...row,
       rank: index + 1
     }))
   }, [rows, sortKey, order, minPA])
   ```

4. **指標変更ハンドラ**
   ```typescript
   const handleSortChange = (metricKey: string) => {
     const newOrder = getDefaultSortOrder(metricKey)
     router.push(`/ranking/${year}/${league}?sort=${metricKey}&order=${newOrder}`)
   }
   ```

### ステップ6: UI表示

**ファイル**: `components/RankingUI.tsx`

**処理内容**:

1. **テーブルヘッダーの生成**
   - Record.csv順で指標タブを表示
   - 現在選択中の指標をハイライト

2. **ランキングテーブルの表示**
   - 順位、選手名、チーム名、指標値を表示
   - ソート可能な列はクリックでソート

3. **値のフォーマット**
   ```typescript
   formatStat(metric.label, row[metric.key])
   ```
   - 率系（打率、出塁率など）: 小数3桁
   - %系（BB%、K%など）: 小数1桁
   - 整数系（本塁打、打点など）: 整数

## ファイルの関係性

### データファイル

```
_data/
├── master_csv/
│   ├── Record.csv                    # 指標の順番定義
│   └── batting_{year}_{league}_from_master.csv  # 元データ（オプション）
└── master_csv_calculated/
    └── batting_{year}_{league}_from_master.csv  # 計算済みデータ（優先）
```

### ライブラリファイル

```
lib/ranking/
├── types.ts              # 型定義
│   ├── MetricDefinition
│   ├── RankingRow
│   ├── RankingViewModel
│   └── BattingCsvRow
├── record.ts            # Record.csv読み込み
│   └── loadMetricsFromRecord()
├── loaders.ts           # CSV読み込み
│   └── loadBattingCsv()
├── adapter.ts           # ランキング生成
│   ├── buildRanking()
│   └── buildRankingWithAllMetrics()
├── metricMap.ts         # 指標名マッピング
│   └── getJsonKey()
└── qualifyingPA.ts      # 規定打席計算
    ├── shouldRequireQualifyingPA()
    └── calculateMinPA()
```

### ページファイル

```
app/ranking/[year]/[league]/
├── page.tsx                    # Server Component
│   └── loadBattingCsv()
│   └── buildRankingWithAllMetrics()
│   └── RankingPageClient に渡す
└── RankingPageClient.tsx       # Client Component
    └── ソート処理
    └── 規定打席フィルタ
    └── RankingUI に渡す
```

### UIコンポーネント

```
components/
└── RankingUI.tsx               # Pure UI Component
    └── テーブル表示
    └── 指標タブ表示
    └── ソート機能
```

## 指標の値取得ロジック

### CSV列名のマッピング

`lib/ranking/adapter.ts` の `getMetricValue()` 関数では、以下の順序で値を取得します：

1. **直接マッチ**
   - CSV列名が指標名と完全一致する場合

2. **マッピングテーブル**
   ```typescript
   const mapping: Record<string, string[]> = {
     'OPS': ['OPS', 'ops'],
     '打率': ['打率', 'AVG', 'avg'],
     '安打': ['安打', 'H', 'h', 'Hits', 'hits'],
     // ...
   }
   ```

3. **計算で補完**
   - BB%: `(BB / PA) * 100`
   - K%: `(SO / PA) * 100`
   - BB/K: `BB / SO`

### 指標名の正規化

`config/metric_map.json` を使用して、Record.csvの指標名をJSONキー名に変換：

```json
{
  "OPS": "ops",
  "打率": "avg",
  "BB%": "bbPct",
  "K%": "kpct",
  "BB/K": "bbk"
}
```

## 規定打席フィルタのロジック

### 規定打席が必要な指標

- 率系指標（打率、出塁率、長打率、OPS、BABIPなど）
- 効率系指標（BB%、K%、BB/Kなど）

### 規定打席が不要な指標

- 累計系指標（本塁打、打点、安打、得点など）

### 年度・リーグごとの規定打席

`lib/ranking/qualifyingPA.ts` で計算：

- **通常**: チーム試合数 × 3.1
- **1950-1958年（一部）**: 規定打数（AB）を使用
- **1966-1967年パ・リーグ**: チーム別規定打席

## データの流れのまとめ

1. **CSVファイル** → `loadBattingCsv()` → `BattingCsvRow[]`
2. **Record.csv** → `loadMetricsFromRecord()` → `MetricDefinition[]`
3. **BattingCsvRow[] + MetricDefinition[]** → `buildRankingWithAllMetrics()` → `RankingRow[]`
4. **RankingRow[]** → Server Component → Client Component
5. **Client Component** → ソート・フィルタ → `sortedRows`
6. **sortedRows** → `RankingUI` → ブラウザに表示

## 重要なポイント

1. **CSVファイルが唯一のデータソース**
   - JSONファイル（`public/data/rankings/`）は使用されない
   - ランキングページは常にCSVから直接読み込む

2. **Record.csvが指標の順番を決定**
   - Record.csvの順番がそのままUIの指標タブの順番になる
   - CSVに存在しない指標は自動的に除外される

3. **サーバー側でデータを準備**
   - 全選手の全指標の値を含む `RankingRow[]` を生成
   - クライアント側ではソートとフィルタのみを行う

4. **動的なソートとフィルタ**
   - URLクエリパラメータ（`?sort=ops&order=desc`）でソート
   - 指標ごとに規定打席フィルタを適用
   - ソート順は指標ごとに最適化（K%のみ昇順）

## 重複問題の発生と対処

### 問題の発生箇所

重複選手がランキングページに表示される問題は、以下のステップで発生しています：

#### ステップ1: CSVファイルの読み込み（問題発生箇所）

**ファイル**: `lib/ranking/loaders.ts` の `loadBattingCsv()`

**問題**:
- CSVファイルに同じ`player_id`で異なるチーム名の行が存在する場合、重複がそのまま読み込まれる
- 例: `player_id: 11913826` で「竹之内 雅史」が「千葉ロッテマリーンズ」と「埼玉西武ライオンズ」の2行で存在

**コード**:
```typescript
// 重複排除の処理がない
const rows = parseCsv(csvContent)  // 重複がそのまま含まれる
```

#### ステップ3: ランキングデータの生成（問題継続）

**ファイル**: `lib/ranking/adapter.ts` の `buildRankingWithAllMetrics()`

**問題**:
- CSVから読み込んだ重複行がそのまま`RankingRow[]`に変換される
- 重複排除の処理がない

**コード**:
```typescript
// 重複排除の処理がない
const rankingRows: RankingRow[] = filteredRows.map((row, index) => {
  // 重複がそのまま含まれる
})
```

#### ステップ5: クライアント側でのソートとフィルタ（問題継続）

**ファイル**: `app/ranking/[year]/[league]/RankingPageClient.tsx`

**問題**:
- ソート処理や規定打席フィルタには重複排除の処理がない
- 重複選手がそのまま表示される

### これまでの対処方法と結果

#### 対処方法1: JSONファイルから重複を削除（❌ 解決しなかった）

**実施内容**:
- `scripts/remove_duplicate_players_from_rankings.py` を作成
- `public/data/rankings/{year}/{league}/{metric}.json` から重複選手を削除
- 578件の重複エントリを削除

**結果**:
- ❌ ランキングページに変化がなかった

**なぜ解決しなかったか**:
1. **ランキングページはJSONファイルを使用していない**
   - ランキングページ（`/ranking/[year]/[league]`）はCSVファイルから直接読み込む
   - JSONファイル（`public/data/rankings/`）は別の用途で使用されている可能性がある
   - `lib/ranking/loaders.ts` の `loadBattingCsv()` はCSVファイルのみを読み込む

2. **データソースの誤認識**
   - 当初、JSONファイルがランキングページのデータソースだと思われていた
   - 実際にはCSVファイルが唯一のデータソースだった

#### 対処方法2: CSVファイルから重複を削除（✅ 正しい対処）

**実施内容**:
- `scripts/remove_duplicate_players_from_csv.py` を作成
- `_data/master_csv_calculated/batting_{year}_{league}_from_master.csv` から重複選手を削除
- 71ファイルから2,392行の重複を削除

**削除基準**:
- 同じ`player_id`で異なるチーム名の行がある場合
- 最初に出現した行を残し、残りを削除
- **重要**: 両方とも削除することは絶対に禁止

**結果**:
- ✅ CSVファイルから重複は削除された（確認済み）
- ⚠️ しかし、ローカルサーバー上では変化がないと報告された

**なぜ解決しなかったか（可能性）**:
1. **Next.jsのキャッシュ**
   - `.next`ディレクトリにキャッシュが残っている
   - サーバーを再起動していない
   - ブラウザのキャッシュが残っている

2. **別のCSVファイルが優先的に読み込まれている可能性**
   - `lib/ranking/loaders.ts` の `findBattingCsv()` は以下の優先順位で探索：
     ```typescript
     1. _data/master_csv_calculated/batting_{year}_{league}_from_master.csv  ← こちらを更新
     2. _data/master_csv/batting_{year}_{league}_from_master.csv              ← こちらが存在する場合、優先される可能性
     3. プロジェクトルート直下の batting_{year}_{league}_from_master.csv
     ```
   - `_data/master_csv/` に同じファイルがある場合、そちらが優先される可能性がある

3. **サーバーが再起動されていない**
   - CSVファイルを更新しても、サーバーを再起動しないと反映されない可能性がある

### 重複問題の根本原因

1. **データソースの重複**
   - CSVファイルに同じ`player_id`で異なるチーム名の行が存在
   - チーム名の表記ゆれ（例: 「千葉ロッテマリーンズ」と「埼玉西武ライオンズ」）による重複

2. **重複排除処理の欠如**
   - `loadBattingCsv()` に重複排除の処理がない
   - `buildRankingWithAllMetrics()` に重複排除の処理がない
   - クライアント側のソート処理にも重複排除の処理がない

### 推奨される解決方法

#### 方法1: CSVファイルから重複を削除（実施済み）

1. **CSVファイルから重複を削除**
   ```bash
   py scripts\remove_duplicate_players_from_csv.py
   ```

2. **Next.jsのキャッシュをクリア**
   ```powershell
   Remove-Item -Recurse -Force .next
   ```

3. **開発サーバーを再起動**
   ```powershell
   npm run dev
   ```

4. **ブラウザのキャッシュをクリア**
   - ハードリロード: `Ctrl + Shift + R`
   - またはシークレットモードで確認

#### 方法2: ランタイムで重複排除（将来の改善案）

`lib/ranking/adapter.ts` の `buildRankingWithAllMetrics()` に重複排除処理を追加：

```typescript
export function buildRankingWithAllMetrics(
  rows: BattingCsvRow[],
  availableMetrics: MetricDefinition[]
): RankingRow[] {
  // 重複排除: 同じplayer_idで最初の行のみを残す
  const seenPlayerIds = new Set<string>()
  const uniqueRows = rows.filter(row => {
    const playerId = (row['player_id'] || row['playerId'] || '').toString().trim()
    if (!playerId || seenPlayerIds.has(playerId)) {
      return false
    }
    seenPlayerIds.add(playerId)
    return true
  })

  // 以降の処理は uniqueRows を使用
  const filteredRows = uniqueRows.filter(row => {
    const pa = getNumericValue(row, ['PA', 'pa', '打席'])
    return pa !== null && pa > 0
  })
  
  // ...
}
```

### 重複問題の確認方法

```powershell
# CSVファイルの重複を確認
$csv = Import-Csv "_data/master_csv_calculated/batting_1973_PL_from_master.csv" -Encoding UTF8
$duplicates = $csv | Group-Object player_id | Where-Object { $_.Count -gt 1 }
Write-Host "重複player_id数: $($duplicates.Count)"
```

### 関連ドキュメント

- `docs/RANKING_PAGE_INFO.md` - ランキングページの詳細情報
- `docs/csv_duplicate_removal_guide.md` - CSV重複削除ガイド
- `docs/fix_csv_duplicate_not_reflected.md` - CSV重複削除が反映されない問題の解決方法
- `docs/duplicate_player_removal_plan.md` - 重複選手削除計画書（JSONファイル用）
- `README.md` - プロジェクト全体の説明
