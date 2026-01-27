# 規定打席フィルタの効率的な実装戦略

## 現状の問題点

### 1. フィルタ適用タイミングが分散している
- **JSON生成段階** (`scripts/build_rankings_2025_PL_full.py`): 規定あり版と規定なし版を両方生成しているが、指標ごとの判定がない
- **ページ表示段階** (`app/ranking/2025/PL/RankingPageClient.tsx`): クライアント側で毎回フィルタを適用（非効率）
- **CSV段階**: 全データを保持（変更不要）

### 2. 指標ごとの「規定打席が必要かどうか」の判定が分散
- 判定ロジックが複数箇所に散在している
- 指標定義（`Record.csv`）に `needsQualification` フラグがない

## 推奨アプローチ：JSON生成段階で判定（最優先）

### 理由
1. **パフォーマンス**: ページ表示時に毎回フィルタする必要がなくなる
2. **データ量削減**: 不要なデータを転送しない
3. **ロジックの一元化**: 判定ロジックを1箇所に集約
4. **キャッシュ効率**: フィルタ済みデータをキャッシュできる

### 実装方針

#### STEP 1: 指標定義に `needsQualification` フラグを追加

**方法A: `config/metric_map.json` を拡張（推奨）**
```json
{
  "OPS": {
    "key": "ops",
    "needsQualification": true
  },
  "打率": {
    "key": "avg",
    "needsQualification": true
  },
  "HR": {
    "key": "hr",
    "needsQualification": false
  },
  "打点": {
    "key": "rbi",
    "needsQualification": false
  }
}
```

**方法B: `Record.csv` に列を追加**
```csv
OPS,打率,HR,打点,...
needsQualification:true,true,false,false,...
```

**方法C: ハードコード（最小変更）**
```python
# scripts/build_rankings_2025_PL_full.py
QUALIFICATION_METRICS = {
    'OPS', '打率', 'AVG', '出塁率', 'OBP', '長打率', 'SLG',
    'IsoP', 'IsoD', 'BB%', 'K%', 'BB/K', 'BABIP', 'SecA', 'TA', 'NOI', 'GPA'
}
```

#### STEP 2: JSON生成時に指標ごとに判定

```python
def generate_ranking_for_metric(
    batting_data: List[Dict[str, Any]],
    metric_label: str,
    output_path: str,
    top_n: int = 100,
    min_pa: int = 443,
    metric_map: Dict[str, str] = None,
    needs_qualification: bool = True  # 追加
) -> bool:
    # needs_qualification が True の場合のみ min_pa を適用
    effective_min_pa = min_pa if needs_qualification else 0
    
    # フィルタ適用
    filtered_data = [
        row for row in batting_data
        if get_pa_value(row)[0] is not None and get_pa_value(row)[0] >= effective_min_pa
    ]
    
    # ソート・ランキング生成
    # ...
```

#### STEP 3: JSONファイル名またはメタデータで区別

**方法A: ファイル名で区別（現状維持）**
```
public/data/rankings/2025/PL/ops.json        # 規定あり
public/data/rankings/2025/PL/ops_all.json    # 規定なし
```

**方法B: JSONにメタデータを含める（推奨）**
```json
{
  "meta": {
    "metric": "ops",
    "needsQualification": true,
    "minPa": 443,
    "year": 2025,
    "league": "PL"
  },
  "data": [
    { "rank": 1, "name": "...", "ops": 0.862, ... }
  ]
}
```

#### STEP 4: ページ表示時にメタデータを確認

```typescript
// app/ranking/[category]/RankingPageClient.tsx
const response = await fetch(jsonPath)
const jsonData = await response.json()

// メタデータから needsQualification を取得
const needsQualification = jsonData.meta?.needsQualification ?? true
const data = jsonData.data ?? jsonData  // 後方互換性

// フィルタは不要（既にJSON生成時に適用済み）
setPlayers(data)
```

## 実装の優先順位

### 最優先（最小変更で最大効果）
1. **方法C（ハードコード）**: `scripts/build_rankings_2025_PL_full.py` に `QUALIFICATION_METRICS` を追加
2. JSON生成時に指標ごとに `needsQualification` を判定
3. 規定あり版のみ生成（規定なし版は削除または別用途に）

### 次優先（長期的な改善）
1. **方法A（metric_map.json拡張）**: 指標定義を一元管理
2. JSONにメタデータを含める
3. ページ表示時のフィルタ処理を削除

## 各段階での役割分担

### CSV段階
- **役割**: 全データを保持（変更不要）
- **理由**: 元データは保持し、用途に応じてフィルタする

### JSON生成段階（推奨）
- **役割**: 指標ごとに `needsQualification` を判定してフィルタ適用
- **理由**: 
  - パフォーマンス向上（ページ表示時の処理削減）
  - データ量削減（不要なデータを転送しない）
  - ロジックの一元化

### ページ表示段階
- **役割**: JSONから読み込んで表示（フィルタ不要）
- **理由**: 既にフィルタ済みデータを使用

## 実装例（最小変更版）

### 1. `scripts/build_rankings_2025_PL_full.py` に追加

```python
# 規定打席が必要な指標のセット
QUALIFICATION_METRICS = {
    'OPS', '打率', 'AVG', '出塁率', 'OBP', '長打率', 'SLG',
    'IsoP', 'IsoD', 'BB%', 'K%', 'BB/K', 'BABIP', 'SecA', 'TA', 'NOI', 'GPA'
}

def needs_qualification(metric_label: str) -> bool:
    """指標が規定打席を必要とするかどうかを判定"""
    return metric_label in QUALIFICATION_METRICS

# generate_ranking_for_metric の呼び出しを変更
for metric_label in metrics:
    needs_qual = needs_qualification(metric_label)
    effective_min_pa = MIN_PA_2025 if needs_qual else 0
    
    generate_ranking_for_metric(
        batting_data,
        metric_label,
        output_path,
        top_n=100,
        min_pa=effective_min_pa,  # 指標ごとに適用
        metric_map=metric_map
    )
```

### 2. ページ表示時のフィルタ処理を削除

```typescript
// app/ranking/2025/PL/RankingPageClient.tsx
// 以下のフィルタ処理を削除（JSON生成時に既に適用済み）
// const filteredRows = rows.filter(row => {
//   const pa = row['PA'] || row['pa']
//   if (metric.needsQualification) {
//     return pa !== undefined && pa !== null && Number(pa) >= 443
//   }
//   return true
// })
```

## まとめ

**最優先**: JSON生成段階で指標ごとに判定してフィルタ適用
- パフォーマンス向上
- データ量削減
- ロジックの一元化

**実装方法**: 最小変更版（方法C）から開始し、長期的に方法A（metric_map.json拡張）に移行



















