# 1936/1937年 春秋分割 監査レポート

生成日時: 1766683522.9159272

## 1. 発見した関連ファイル

### dedupファイル
- C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting\data\batting\yearly_from_master_dedup\batting_1937_PRE_from_master.csv
- C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting\data\batting\yearly_from_master_dedup\batting_1936_PRE_from_master.csv

### yearly_from_masterファイル（dedup前）

### masterファイル

## 2. 各ファイルの監査結果

### batting_1936_PRE_from_master.csv

- **パス**: `C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting\data\batting\yearly_from_master_dedup\batting_1936_PRE_from_master.csv`
- **存在**: ✅
- **行数**: 77行
- **対象年度フィルタ後行数**: 77行
- **列数**: 65列

- **season列**: なし ❌
- **URL列**: なし ❌
- **year列**: year
  - ユニーク値数: 1
  - **春秋情報が含まれている可能性**: ❌
- **重複チェック (player_id + year)**:
  - 重複キー数: 0
  - 総キー数: 77
  - **重複なし**: ❌ (dedup済みの可能性)

### batting_1937_PRE_from_master.csv

- **パス**: `C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting\data\batting\yearly_from_master_dedup\batting_1937_PRE_from_master.csv`
- **存在**: ✅
- **行数**: 137行
- **対象年度フィルタ後行数**: 137行
- **列数**: 65列

- **season列**: なし ❌
- **URL列**: なし ❌
- **year列**: year
  - ユニーク値数: 1
  - **春秋情報が含まれている可能性**: ❌
- **重複チェック (player_id + year)**:
  - 重複キー数: 6
  - 総キー数: 131
  - **重複あり**: ✅ (春秋分割の可能性あり)

## 3. 結論

### ✅ 分割可能

**理由**: dedup前のファイル (batting_1937_PRE_from_master.csv) に player_id+year の重複が存在

次のステップ: `scripts/split_1936_1937.py` を実行して分割を実行してください。
