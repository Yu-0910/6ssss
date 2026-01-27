# 規定打席フィルタ実装完了レポート

## 実装概要

UIを変更せずに、ランキング生成スクリプト（`scripts/build_rankings_2025_PL_full.py`）に規定打席フィルタを実装しました。

## 実装内容

### 1. A/B分類の追加

`scripts/build_rankings_2025_PL_full.py` に以下を追加：

- `METRICS_REQUIRE_QUALIFYING_PA`: 規定打席が必要な指標（16指標）
- `METRICS_NO_QUALIFYING_PA`: 規定打席が不要な指標（20指標）
- `should_require_qualifying_pa()`: 指標キーから規定打席の要否を判定

### 2. フィルタリングロジックの修正

`generate_ranking_for_metric()` 関数を修正：

- **Aグループ（規定打席必要）**: `PA >= min_pa` でフィルタリング
- **Bグループ（規定打席不要）**: フィルタリングしない（全選手対象）

### 3. バリデーション追加

`validate_qualifying_pa_filter()` 関数を追加：

- Aグループ指標のランキングJSONを検証
- `pa < min_pa` の選手が1人でも入っていたら例外で終了
- エラーメッセージに「どの指標で、どの選手が、paいくつで混入したか」を出力

### 4. ログ出力追加

開発時のみ以下のログを出力：

- `[QUALIFY] year=2025 league=PL minPA=443`
- `[QUALIFY] metric=OPS key=ops require=true min_pa=443`
- `[QUALIFY] metric=OPS before=500 after=120 filtered_out=380`
- `[QUALIFY] metric=安打 key=hits require=false min_pa=0`
- `[QUALIFY][FAIL] metric=OPS key=ops player=XXX pa=312` (バリデーションエラー時)

## 変更ファイル

### 変更OK（実装済み）

- ✅ `scripts/build_rankings_2025_PL_full.py` - ランキング生成スクリプト

### 変更禁止（未変更）

- ❌ `components/RankingUI.tsx` - UIコンポーネント（変更なし）
- ❌ `app/ranking/[category]/RankingPageClient.tsx` - クライアントコンポーネント（変更なし）
- ❌ その他UI関連ファイル（変更なし）

## 動作確認方法

### 1. ランキング生成

```bash
python scripts/build_rankings_2025_PL_full.py --year 2025 --league PL
```

### 2. 期待される挙動

- **OPSランキング**: 全員 `pa >= 443`
- **安打ランキング**: `pa < 443` も混ざってOK（フィルタリングなし）

### 3. バリデーション

生成後、自動的にバリデーションが実行されます：

- Aグループ指標に `pa < 443` が混入していたらビルド失敗
- Bグループは `pa < 443` が存在しても成功

## 実装詳細

### 指標分類（内部キーで統一）

#### Aグループ（規定打席必要）

```python
METRICS_REQUIRE_QUALIFYING_PA = {
    "ops", "avg", "obp", "slg", "isop", "isod",
    "bbpct", "kpct", "bbk", "rc", "xr", "babip",
    "seca", "ta", "noi", "gpa"
}
```

#### Bグループ（規定打席不要）

```python
METRICS_NO_QUALIFYING_PA = {
    "hits", "hr", "rbi", "games", "pa", "ab",
    "singles", "doubles", "triples", "runs",
    "bb", "ibb", "hbp", "so", "tb", "sb", "cs",
    "sh", "sf", "gidp"
}
```

### フィルタリングロジック

```python
# 指標の内部キーを取得（metric_mapから）
metric_key = metric_map[metric] if metric in metric_map else metric.lower()

# 規定打席が必要かどうかを判定
requires_qualifying_pa = should_require_qualifying_pa(metric_key)

# 実際に使用するmin_paを決定
effective_min_pa = min_pa if requires_qualifying_pa else 0

# フィルタリング
if requires_qualifying_pa:
    # Aグループ: PA >= min_pa でフィルタリング
    if pa_val >= effective_min_pa:
        filtered_data.append(row)
else:
    # Bグループ: 全選手対象
    filtered_data.append(row)
```

## 受け入れ条件

- ✅ UIファイル差分：0（変更なし）
- ✅ 2025年PL/CL の Aグループ全指標で `pa < 443` がランキングJSONに存在しない
- ✅ Bグループは `pa < 443` が存在しても生成が成功する
- ✅ 生成後バリデーションが常に動作する

## 注意事項

1. **内部キーの統一**: `config/metric_map.json` の内部キー（小文字）を唯一のソースとして使用
2. **未知の指標キー**: エラーを投げてサイレント無視を防ぐ
3. **PA列の取得**: `PA` または `pa` 列から取得（`get_pa_value()` 関数）

## 関連ファイル

- `scripts/build_rankings_2025_PL_full.py` - ランキング生成スクリプト（実装済み）
- `config/metric_map.json` - 指標マップ（表示名 → 内部キー）
- `lib/ranking/qualifyingPA.ts` - TypeScript側の定義（参考用）


















