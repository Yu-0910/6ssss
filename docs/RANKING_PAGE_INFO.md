# ランキングページのデータ埋め込みに関する情報まとめ

## 1. ランキングページの構造

### 1.1 ページファイル

#### `/ranking/OPS` ページ（複数指標を横に並べて表示）
- **ファイル**: `app/ranking/[category]/RankingPageClient.tsx`
- **URL**: `http://localhost:3001/ranking/OPS`
- **特徴**: 
  - OPS順に並んだ選手の複数指標を横に並べて表示
  - Record.csvから指標リストを読み込む（クライアント側）
  - `public/data/rankings/2025/PL/OPS.json` からデータを読み込む
  - 表示指標はRecord.csvの順番に従う

#### `/ranking/2025/PL` ページ（1指標ずつ表示、指標タブで切替）
- **ファイル**: `app/ranking/2025/PL/page.tsx` (Server Component)
- **Client Component**: `app/ranking/2025/PL/RankingPageClient.tsx`
- **URL**: `http://localhost:3001/ranking/2025/PL?metric=ops`
- **特徴**:
  - 1指標ずつ表示、指標タブで切替
  - CSVから直接読み込んでランキング生成（サーバー側）
  - Record.csvの順番で指標タブを表示
  - `?metric=` クエリパラメータで指標を切替

### 1.2 コンポーネント

#### `components/RankingUI.tsx`
- **Pure UI Component**（表示専用）
- props: `{ viewModel, onMetricChange }`
- 指標の数が1でも20でも同じ構造で描画

#### `components/RankingUILocked.tsx`
- **UI Baseline**（LOCKED）
- UIが壊れた場合の復元用

### 1.3 ライブラリ

#### `lib/ranking/types.ts`
- 型定義: `MetricDefinition`, `RankingRow`, `RankingViewModel`, `BattingCsvRow`

#### `lib/ranking/record.ts`
- Record.csvから指標リストを取得（順番を保持）
- `loadMetricsFromRecord()`: Record.csvの順番で指標定義の配列を返す

#### `lib/ranking/loaders.ts`
- CSVファイルを読み込み、利用可能な指標を抽出
- `loadBattingCsv(season, league)`: CSVを読み込み、Record.csv順でCSVに存在する指標のみを返す

#### `lib/ranking/adapter.ts`
- CSVデータをUI表示用のViewModelに変換
- `buildRanking(rows, metric, topN)`: ランキング生成、整形、ソート、ランキング付与まで完結
- BB%、K%、BB/Kは計算で補完（CSVに "nan" が入っている場合）

## 2. データソース

### 2.1 JSONファイル
- **場所**: `public/data/rankings/2025/PL/{METRIC}.json`
- **生成スクリプト**: `scripts/build_rankings_2025_PL_full.py`
- **構造例** (OPS.json):
```json
[
  {
    "rank": 1,
    "player": "F.レイエス",
    "name": "F.レイエス",
    "romanName": "Franmil Reyes",
    "team": "北海道日本ハムファイターズ",
    "value": 0.862,
    "metric": "OPS",
    "ops": 0.862,
    "avg": 0.277,
    "obp": 0.347,
    "slg": 0.515,
    "hr": 32,
    "rbi": 90,
    "hits": 132,
    "runs": 62,
    "pa": 531,
    "ab": 476,
    "games": 130,
    "singles": 68,
    "doubles": 24,
    "triples": 8,
    "bb": 48,
    "ibb": 2,
    "hbp": 7,
    "so": 142,
    "tb": 245,
    "sb": 0,
    "cs": 0,
    "sh": 0,
    "sf": 3,
    "gidp": 8,
    "isop": 0.238,
    "isod": 0.07,
    "bbPct": 9.0,
    "kPct": 26.7,
    "bbk": 0.338,
    "rc": 95,
    "xr": 98,
    "babip": 0.312,
    "seca": 0.553,
    "ta": 0.91,
    "noi": 0.85,
    "gpa": 0.287
  }
]
```

### 2.2 CSVファイル
- **場所**: `_data/master_csv_calculated/batting_2025_PL_from_master.csv`
- **探索順序**:
  1. `_data/master_csv_calculated/batting_{season}_{league}_from_master.csv`
  2. `_data/master_csv/batting_{season}_{league}_from_master.csv`
  3. `batting_{season}_{league}_from_master.csv`

### 2.3 Record.csv
- **場所**: `Record.csv` または `_data/master_csv/Record.csv`
- **内容**: 指標の順番を定義（1行目が指標名のカンマ区切り）
```
OPS,打率,安打,本塁打,打点,試合,打席,打数,単打,二塁打,三塁打,得点,出塁率,長打率,四球,敬遠,死球,三振,塁打,盗塁,盗塁死,犠打,犠飛,併殺打,IsoP,IsoD,BB%,K%,BB/K,RC,XR,BABIP,SecA,TA,NOI,GPA
```

## 3. データ生成スクリプト

### 3.1 `scripts/build_rankings_2025_PL_full.py`
- **機能**: 2025年パ・リーグの全指標ランキングTOP100を生成
- **入力**: 
  - `batting_2025_PL_from_master.csv`
  - `Record.csv`
- **出力**: `public/data/rankings/2025/PL/{METRIC}.json`
- **処理**:
  1. Record.csvから指標リストを抽出
  2. CSVを読み込み、各指標のランキングを生成
  3. 規定打席フィルタ（443 PA）を適用（率・効率系指標のみ）
  4. ソート（降順、K%のみ昇順）
  5. TOP100を抽出してJSONに出力

### 3.2 JSON生成時のデータ構造
- **キー名**: 小文字（例: `ops`, `avg`, `bbPct`, `kPct`, `bbk`）
- **値の型**: 数値（整数または小数）
- **特殊処理**:
  - BB%、K%、BB/Kは計算で補完（CSVに "nan" が入っている場合）
  - `format_value()` でフォーマット（率系は小数3桁、%系は小数1桁、整数系は整数）

## 4. 指標名のマッピング

### 4.1 Record.csv → JSONキー名のマッピング

| Record.csv | JSONキー | 備考 |
|------------|----------|------|
| OPS | ops | |
| 打率 | avg | |
| 安打 | hits | |
| 本塁打 | hr | |
| 打点 | rbi | |
| 試合 | games | |
| 打席 | pa | |
| 打数 | ab | |
| 単打 | singles | |
| 二塁打 | doubles | |
| 三塁打 | triples | |
| 得点 | runs | |
| 出塁率 | obp | |
| 長打率 | slg | |
| 四球 | bb | |
| 敬遠 | ibb | |
| 死球 | hbp | |
| 三振 | so | |
| 塁打 | tb | |
| 盗塁 | sb | |
| 盗塁死 | cs | |
| 犠打 | sh | |
| 犠飛 | sf | |
| 併殺打 | gidp | |
| IsoP | isop | |
| IsoD | isod | |
| BB% | bbPct | **注意: キー名が異なる** |
| K% | kPct | **注意: キー名が異なる** |
| BB/K | bbk | **注意: キー名が異なる** |
| RC | rc | |
| XR | xr | |
| BABIP | babip | |
| SecA | seca | |
| TA | ta | |
| NOI | noi | |
| GPA | gpa | |

### 4.2 問題点
- **BB%、K%、BB/Kのマッピングが不完全**
  - Record.csv: `BB%`, `K%`, `BB/K`
  - JSONキー: `bbPct`, `kPct`, `bbk`
  - `/ranking/OPS` ページで `normalizeMetricKey()` 関数が正しくマッピングしているが、値が取得できない場合がある

## 5. 現在の問題点

### 5.1 `/ranking/OPS` ページで3つの指標が表示されない
- **対象指標**: BB%、K%、BB/K
- **原因**:
  1. JSONデータのキー名（`bbPct`, `kPct`, `bbk`）とRecord.csvの指標名（`BB%`, `K%`, `BB/K`）のマッピングが不完全
  2. 値が "nan" 文字列の場合、数値変換でNaNになり除外される
  3. 大文字小文字の違いに対応していない場合がある

### 5.2 修正済みの内容
- `normalizeMetricKey()` 関数を拡張（BB% → bbPct, K% → kPct, BB/K → bbk）
- 値の取得ロジックを改善（大文字小文字対応、'nan' 文字列除外）
- `/ranking/2025/PL` ページでは `adapter.ts` で計算補完を実装済み

## 6. データフロー

### 6.1 `/ranking/OPS` ページ
```
1. クライアント側で Record.csv を読み込み
   → displayMetrics を生成（Record.csv順）

2. クライアント側で OPS.json を読み込み
   → players 配列に格納

3. displayMetrics をループして各指標の値を表示
   → player[metric.key] で値を取得
   → formatStat(metric.label, value) でフォーマット
```

### 6.2 `/ranking/2025/PL` ページ
```
1. サーバー側で CSV を読み込み
   → loadBattingCsv('2025', 'PL')
   → availableMetrics を生成（Record.csv順、CSVに存在する指標のみ）

2. サーバー側でランキングを生成
   → buildRanking(rows, activeMetric, 100)
   → RankingRow[] を生成（整形済み）

3. クライアント側で表示
   → RankingUI コンポーネントに ViewModel を渡す
```

## 7. 修正が必要な箇所

### 7.1 `/ranking/OPS` ページの値取得ロジック
- **現在**: `player[metric.key]` で直接取得
- **問題**: キー名の不一致（BB% → bbPct など）で値が取得できない
- **修正方針**: 
  1. キー名のマッピングを完全にする
  2. 大文字小文字の違いに対応
  3. "nan" 文字列を除外
  4. 値が取得できない場合は計算で補完（BB%、K%、BB/K）

### 7.2 JSONデータ生成時のキー名統一
- **現在**: 小文字（`bbPct`, `kPct`, `bbk`）
- **問題**: Record.csvの指標名（`BB%`, `K%`, `BB/K`）と不一致
- **修正方針**: 
  1. JSON生成時にキー名を統一する
  2. または、マッピングテーブルを完全にする

## 8. 関連ファイル一覧

### 8.1 ページファイル
- `app/ranking/[category]/page.tsx` - Server Component
- `app/ranking/[category]/RankingPageClient.tsx` - Client Component（複数指標表示）
- `app/ranking/2025/PL/page.tsx` - Server Component（1指標表示）
- `app/ranking/2025/PL/RankingPageClient.tsx` - Client Component（1指標表示）

### 8.2 コンポーネント
- `components/RankingUI.tsx` - Pure UI Component
- `components/RankingUILocked.tsx` - UI Baseline（LOCKED）
- `components/RankingTable.tsx` - テーブルコンポーネント（未使用？）

### 8.3 ライブラリ
- `lib/ranking/types.ts` - 型定義
- `lib/ranking/record.ts` - Record.csv読み込み
- `lib/ranking/loaders.ts` - CSV読み込み
- `lib/ranking/adapter.ts` - ランキング生成アダプター
- `lib/formatStat.ts` - 数値フォーマット
- `lib/csvReader.ts` - CSV読み込みユーティリティ

### 8.4 データファイル
- `Record.csv` - 指標の順番定義
- `_data/master_csv_calculated/batting_2025_PL_from_master.csv` - 元データ
- `public/data/rankings/2025/PL/{METRIC}.json` - 生成されたランキングJSON

### 8.5 スクリプト
- `scripts/build_rankings_2025_PL_full.py` - ランキングJSON生成スクリプト



















