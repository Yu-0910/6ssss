# ディレクトリの関係分析

## 質問

`_data/master_csv__import_1950_2024/` と `_data/master_csv_calculated/` は：
1. 計算前と計算後というだけの違い？
2. それとも全く別の機会にスクレイピングしたもの？

## 調査結果

### 結論

**`master_csv__import_1950_2024` と `master_csv_calculated` は、計算前と計算後の関係です。**

ただし、`master_csv_calculated` は `master_csv` から生成されるため、`master_csv__import_1950_2024` と `master_csv` が同じデータソースなら、結果的に同じデータが含まれることになります。

### スクリプトの処理フロー

#### 1. `compute_metrics_all_seasons.py`

**入力**: `_data/master_csv/`  
**出力**: `_data/master_csv_calculated/`  
**処理**: 生データから計算済み指標（RC、XR、日本語列名など）を追加

```python
data_master_csv_dir = project_root / '_data' / 'master_csv'
output_dir = project_root / '_data' / 'master_csv_calculated'
```

#### 2. `fact_check_compare_scraped.py`

**参照1**: `_data/master_csv__import_1950_2024/` (スクレイピングデータ)  
**参照2**: `_data/master_csv_calculated/` (現在のデータ)

```python
scraped_path = Path(f'_data/master_csv__import_1950_2024/batting_{year}_{league}_from_master.csv')
current_path = Path(f'_data/master_csv_calculated/batting_{year}_{league}_from_master.csv')
```

### データの比較

#### 列数の違い

| ディレクトリ | 列数 | 内容 |
|------------|------|------|
| `master_csv__import_1950_2024` | 41列 | 基本指標のみ（G, PA, AB, R, H, 2B, 3B, HR, TB, RBI, SB, CS, SH, SF, BB, IBB, HBP, SO, GDP, AVG, OBP, SLG, OPS, 1B, IsoP, IsoD, IOPS, BB%, K%, BB/K, BABIP, GPA, NOI, SecA, TA） |
| `master_csv_calculated` | 66列 | 基本指標 + 計算済み指標（RC、XR、日本語列名など） |

#### 基本データの比較（若松勉 1971年）

| 指標 | master_csv__import_1950_2024 | master_csv_calculated | 一致 |
|------|------------------------------|----------------------|------|
| G (試合) | 112.0 | 112.0 | ✅ |
| PA (打席) | 305.0 | 305.0 | ✅ |
| H (安打) | 83.0 | 83.0 | ✅ |
| HR (本塁打) | 3.0 | 3.0 | ✅ |

**基本データは同じです。**

### ディレクトリの役割

1. **`_data/master_csv__import_1950_2024/`**
   - **役割**: 過去にスクレイピングした生データ（1950-2024年の範囲）
   - **列数**: 41列
   - **用途**: ファクトチェックの参照データ、計算処理の入力データ

2. **`_data/master_csv/`**
   - **役割**: 現在使用中の生データ
   - **列数**: 41列（`master_csv__import_1950_2024` と同じ構造）
   - **用途**: 計算処理の入力データ

3. **`_data/master_csv_calculated/`**
   - **役割**: 計算処理を経て生成された計算済みデータ
   - **列数**: 66列
   - **用途**: ランキング生成やUI表示に使用

### データの流れ

```
master_csv__import_1950_2024 (スクレイピング生データ)
    ↓
master_csv (現在使用中の生データ)
    ↓
compute_metrics_all_seasons.py (計算処理)
    ↓
master_csv_calculated (計算済みデータ)
```

### 結論

**`master_csv__import_1950_2024` と `master_csv_calculated` は、計算前と計算後の関係です。**

- `master_csv__import_1950_2024`: 過去にスクレイピングした生データ（41列）
- `master_csv_calculated`: 計算処理を経て生成された計算済みデータ（66列）

ただし、`master_csv_calculated` は `master_csv` から生成されるため、`master_csv__import_1950_2024` と `master_csv` が同じデータソース（同じスクレイピング結果）なら、結果的に同じ基本データが含まれることになります。

### 注意事項

- `master_csv__import_1950_2024` は「過去にスクレイピングしたデータ」として保存されている
- `master_csv` は「現在使用中のデータ」として管理されている
- 両者が同じデータソースなら、基本データは同じになる
- `master_csv_calculated` は `master_csv` から計算処理を経て生成される



