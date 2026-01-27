# 1936/1937年 春秋分割 実行手順

## 概要

1936年・1937年は「春／秋」の2期制（合計4シーズン）ですが、現状のデータは年単位のCSV（例：1936_PRE）しかありません。

このディレクトリには、春秋分割を実行するための3つのスクリプトがあります：

1. **audit_1936_1937_split.py** - データの監査（分割可能か判定）
2. **split_1936_1937.py** - 春秋への分割実行
3. **rebuild_1936_1937_with_season.py** - season列付きデータの再生成（分割不可の場合）

## 実行手順

### STEP 1: 監査（必須）

まず、データが分割可能かを監査します。

```powershell
python scripts/audit_1936_1937_split.py
```

#### 出力

- `output/reports/audit_1936_1937_split.md` - 詳細な監査レポート
- `output/reports/audit_1936_1937_columns.csv` - 各ファイルの列名一覧
- `output/reports/audit_1936_1937_duplicates.csv` - 重複がある場合の一覧

#### 監査内容

1. **ファイル存在チェック**: 1936/1937のCSVファイルが存在するか
2. **関連ファイル探索**: dedup前のファイル、masterファイルを探索
3. **列分析**: season列、URL列、year列の有無と内容
4. **重複チェック**: player_id + year の重複の有無（春秋分割の可能性）

### STEP 2-A: 分割可能な場合

監査レポートで「分割可能」と判定された場合、分割を実行します。

```powershell
python scripts/split_1936_1937.py
```

#### 出力先

`C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting\data\batting\yearly_prewar_split\`

- `batting_1936_spring_PRE.csv`
- `batting_1936_fall_PRE.csv`
- `batting_1937_spring_PRE.csv`
- `batting_1937_fall_PRE.csv`

#### 分割方法

スクリプトは以下の優先順位で春秋を判定します：

1. **season列**が存在する場合: 列の値から判定（spring/fall、春/秋など）
2. **URL列**が存在する場合: URLに含まれるキーワードから判定
3. **year列の値**: "1936春"、"1936秋"などの形式を判定
4. **重複行**: dedup前のファイルで player_id+year の重複がある場合、2行を春秋として分割

### STEP 2-B: 分割不可な場合

監査レポートで「分割不可」と判定された場合、season列を保持したデータを再生成します。

```powershell
python scripts/rebuild_1936_1937_with_season.py
```

#### 出力先

`C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting\data\batting\yearly_prewar_split\`

- `batting_1936_PRE_with_season.csv`
- `batting_1937_PRE_with_season.csv`

#### 再生成後の処理

1. 生成されたCSVを確認し、season列が正しく設定されているか確認
2. 必要に応じて手動で修正
3. `split_1936_1937.py` を再実行して分割

## 重要な注意事項

### dedupの影響

ファイル名に "dedup" が含まれている場合、以下の可能性があります：

- **player_id + year で重複排除**されている可能性
- 春秋が1つに潰れている可能性（分割不能）

この場合、**dedup前のデータ**（master や yearly_from_master）を確認する必要があります。

### 今後のdedupロジックの修正

分割不可だった場合、今後のdedup処理では：

- **dedupキーを (player_id, year, season) に変更**する必要があります
- yearだけでなく、seasonも考慮して重複排除するように修正してください

### データの確認

分割後は、必ず以下を確認してください：

1. 4ファイル（1936春/秋、1937春/秋）が生成されているか
2. 各ファイルの行数が妥当か
3. 各ファイル内で春秋が混ざっていないか（season列や識別情報で検証）
4. 合計行数が元データと一致するか

## トラブルシューティング

### ファイルが見つからない

パスが環境によって異なる場合は、スクリプト内のパスを修正してください：

```python
base_dedup_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting\data\batting\yearly_from_master_dedup")
```

### 春秋が判定できない

以下の場合、手動での確認・修正が必要です：

- season列が存在しない
- URL列から春秋が判定できない
- 重複行がない（dedupで潰れている）

この場合、`rebuild_1936_1937_with_season.py` を使用して、元のソース（masterデータやスクレイピング元）から season情報を復元する必要があります。

### 文字コードエラー

CSVファイルの文字コードが異なる場合、`load_csv_with_encoding` 関数が自動的に判定しますが、うまく動作しない場合は、スクリプトの `encodings` リストに適切な文字コードを追加してください。





















