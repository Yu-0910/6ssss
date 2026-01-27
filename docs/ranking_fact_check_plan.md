# ランキングページ ファクトチェック計画書

## 📋 目的

各年度のランキングページにおいて、**抜けている選手がいないか**を確認するためのファクトチェック計画書です。

---

## 🔍 データフロー概要

```
1. スクレイピング元データ（参照用）
   └─ _data/master_csv__import_1950_2024/batting_{YEAR}_{LEAGUE}_from_master.csv
   └─ 過去にスクレイピングした全成績データ（150ファイル以上）
   
2. マスターCSV（現在使用中）
   └─ _data/master_csv_calculated/batting_{YEAR}_{LEAGUE}_from_master.csv
   └─ 計算済み指標を含むマスターデータ
   
3. ランキング生成スクリプト
   └─ scripts/build_rankings_from_calculated.py
   └─ scripts/build_rankings_2025_PL_full.py
   
4. ランキングJSON
   └─ public/data/rankings/{YEAR}/{LEAGUE}/{METRIC}.json
   
5. ランキングページ
   └─ app/ranking/[year]/[league]/RankingPageClient.tsx
   └─ ブラウザで表示: /ranking/{YEAR}/{LEAGUE}
```

### 📦 スクレイピングデータの活用

**スクレイピングデータの場所**:
- `_data/master_csv__import_1950_2024/` に150ファイル以上のCSVが保存されています
- 1950年から2024年までの全年度・全リーグのデータが含まれています

**活用方法**:
1. **参照データとして使用**: スクレイピングデータを「正しいデータ」として使用し、現在のランキングデータと比較
2. **選手数の比較**: スクレイピングデータの選手数と現在のデータの選手数を比較
3. **抜けている選手の特定**: スクレイピングデータに存在するが、現在のランキングに含まれていない選手を特定

---

## 🎯 チェックポイント（精査段階）

### 段階0: スクレイピングデータとの比較（推奨）

**目的**: 過去にスクレイピングしたデータと現在のデータを比較し、抜けている選手を特定

**対象ファイル**:
- **参照データ**: `_data/master_csv__import_1950_2024/batting_{YEAR}_{LEAGUE}_from_master.csv`
- **現在のデータ**: `_data/master_csv_calculated/batting_{YEAR}_{LEAGUE}_from_master.csv`

**チェック項目**:

1. **選手数の比較**
   - [ ] スクレイピングデータの総選手数を記録
   - [ ] 現在のデータの総選手数を記録
   - [ ] 選手数の差分を確認

2. **選手名の比較**
   - [ ] スクレイピングデータに存在する選手が現在のデータに含まれているか
   - [ ] 現在のデータに存在しない選手をリストアップ
   - [ ] 除外された選手が適切か確認（PA=0、データ欠損など）

3. **チーム別選手数の比較**
   - [ ] 各チームの選手数を比較
   - [ ] 特定のチームで選手が抜けていないか確認

**チェック方法**:
```python
# サンプルスクリプト: scripts/fact_check_compare_scraped.py
import pandas as pd
import sys
from pathlib import Path

def compare_scraped_vs_current(year, league):
    # スクレイピングデータ（参照用）
    scraped_path = Path(f'_data/master_csv__import_1950_2024/batting_{year}_{league}_from_master.csv')
    
    # 現在のデータ
    current_path = Path(f'_data/master_csv_calculated/batting_{year}_{league}_from_master.csv')
    
    if not scraped_path.exists():
        print(f"⚠️ スクレイピングデータが見つかりません: {scraped_path}")
        return
    
    if not current_path.exists():
        print(f"⚠️ 現在のデータが見つかりません: {current_path}")
        return
    
    # データを読み込む
    df_scraped = pd.read_csv(scraped_path, encoding='utf-8-sig')
    df_current = pd.read_csv(current_path, encoding='utf-8-sig')
    
    print(f"\n=== {year}年{league}リーグ データ比較 ===\n")
    
    # 選手数の比較
    print(f"スクレイピングデータ: {len(df_scraped)}件")
    print(f"現在のデータ: {len(df_current)}件")
    print(f"差分: {len(df_scraped) - len(df_current)}件\n")
    
    # 選手名の比較（選手名カラムを特定）
    name_col_scraped = None
    name_col_current = None
    
    for col in df_scraped.columns:
        if 'name' in col.lower() or '選手' in col:
            name_col_scraped = col
            break
    
    for col in df_current.columns:
        if 'name' in col.lower() or '選手' in col:
            name_col_current = col
            break
    
    if name_col_scraped and name_col_current:
        # スクレイピングデータに存在するが、現在のデータに存在しない選手
        scraped_names = set(df_scraped[name_col_scraped].dropna().astype(str))
        current_names = set(df_current[name_col_current].dropna().astype(str))
        
        missing_names = scraped_names - current_names
        
        if missing_names:
            print(f"⚠️ 現在のデータに存在しない選手: {len(missing_names)}件")
            print("\n抜けている選手（上位10件）:")
            for i, name in enumerate(list(missing_names)[:10], 1):
                # 該当選手の情報を表示
                player_row = df_scraped[df_scraped[name_col_scraped].astype(str) == name].iloc[0]
                team = player_row.get('team', player_row.get('Team', player_row.get('チーム', 'N/A')))
                pa = player_row.get('PA', player_row.get('pa', player_row.get('打席', 'N/A')))
                print(f"  {i}. {name} ({team}, PA={pa})")
        else:
            print("✅ すべての選手が現在のデータに含まれています")
    
    # チーム別選手数の比較
    team_col_scraped = None
    team_col_current = None
    
    for col in df_scraped.columns:
        if 'team' in col.lower() or 'チーム' in col:
            team_col_scraped = col
            break
    
    for col in df_current.columns:
        if 'team' in col.lower() or 'チーム' in col:
            team_col_current = col
            break
    
    if team_col_scraped and team_col_current:
        print("\n=== チーム別選手数比較 ===")
        scraped_teams = df_scraped[team_col_scraped].value_counts().sort_index()
        current_teams = df_current[team_col_current].value_counts().sort_index()
        
        print("\nスクレイピングデータ:")
        print(scraped_teams)
        print("\n現在のデータ:")
        print(current_teams)
        
        # 差分を確認
        print("\nチーム別差分:")
        for team in scraped_teams.index:
            scraped_count = scraped_teams.get(team, 0)
            current_count = current_teams.get(team, 0)
            diff = scraped_count - current_count
            if diff != 0:
                print(f"  {team}: {scraped_count} → {current_count} (差分: {diff})")

if __name__ == '__main__':
    year = int(sys.argv[1])
    league = sys.argv[2]
    compare_scraped_vs_current(year, league)
```

**期待される結果**:
- スクレイピングデータと現在のデータの選手数が一致（または適切な差分）
- 抜けている選手が適切に除外されている（PA=0、データ欠損など）
- チーム別選手数に大きな差がない

---

### 段階1: CSVファイルの精査

**目的**: 元データに欠損や不整合がないか確認

**対象ファイル**:
- `_data/master_csv_calculated/batting_{YEAR}_{LEAGUE}_from_master.csv`

**チェック項目**:

1. **選手数の確認**
   - [ ] CSVファイルの総行数（ヘッダー除く）を記録
   - [ ] 各チームの選手数を確認
   - [ ] 期待される選手数と一致するか確認

2. **必須カラムの確認**
   - [ ] `player_name_ja`（選手名）が全行に存在するか
   - [ ] `team`（チーム名）が全行に存在するか
   - [ ] `PA`（打席数）が全行に存在するか
   - [ ] 指標計算に必要なカラムが存在するか

3. **データ欠損の確認**
   - [ ] `PA = 0` の選手がいるか（フィルタリング対象）
   - [ ] 指標値が `NaN` や空の選手がいるか
   - [ ] チーム名が空の選手がいるか

4. **データ整合性の確認**
   - [ ] `PA = AB + BB + HBP + SH + SF` が成立するか（主要選手のみサンプルチェック）
   - [ ] `H = 1B + 2B + 3B + HR` が成立するか（主要選手のみサンプルチェック）

**チェック方法**:
```python
# サンプルスクリプト: scripts/fact_check_csv.py
import pandas as pd
import sys

def check_csv(filename):
    df = pd.read_csv(filename, encoding='utf-8-sig')
    
    print(f"総行数: {len(df)}")
    print(f"チーム別選手数:")
    print(df['team'].value_counts())
    
    print(f"\nPA=0の選手数: {len(df[df['PA'] == 0])}")
    print(f"選手名が空の行数: {len(df[df['player_name_ja'].isna()])}")
    print(f"チーム名が空の行数: {len(df[df['team'].isna()])}")
    
    # 主要指標の欠損確認
    metrics = ['OPS', 'AVG', 'HR', 'H', 'RBI']
    for metric in metrics:
        missing = df[metric].isna().sum()
        if missing > 0:
            print(f"{metric}が欠損している行数: {missing}")

if __name__ == '__main__':
    check_csv(sys.argv[1])
```

**期待される結果**:
- 全選手がCSVに含まれている
- 必須カラムに欠損がない
- データ整合性が保たれている

---

### 段階2: ランキングJSONの精査

**目的**: ランキング生成スクリプトが正しく動作し、適切な選手がランキングに含まれているか確認

**対象ファイル**:
- `public/data/rankings/{YEAR}/{LEAGUE}/{METRIC}.json`

**チェック項目**:

1. **ランキング件数の確認**
   - [ ] 各指標のランキングが100件（または適切な件数）になっているか
   - [ ] 指標によって件数が異なる場合、その理由を確認

2. **フィルタリング条件の確認**
   - [ ] `PA > 0` の選手のみが含まれているか
   - [ ] 規定打席到達が必要な指標（OPS、打率など）で、規定打席未満の選手が除外されているか
   - [ ] 規定打席到達が不要な指標（HR、安打など）で、PA>0の選手が含まれているか

3. **選手の重複確認**
   - [ ] 同じ選手が複数回出現していないか
   - [ ] 選手名の表記ゆれがないか

4. **上位選手の確認**
   - [ ] 期待される上位選手が含まれているか
   - [ ] 順位が正しいか（降順/昇順）

5. **データ欠損の確認**
   - [ ] 指標値が `null` や `NaN` の選手が含まれていないか
   - [ ] 選手名やチーム名が空の選手が含まれていないか

**チェック方法**:
```python
# サンプルスクリプト: scripts/fact_check_json.py
import json
import sys
from pathlib import Path

def check_ranking_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"ランキング件数: {len(data)}")
    
    # 選手名の重複確認
    names = [player.get('name', '') for player in data]
    duplicates = [name for name in names if names.count(name) > 1]
    if duplicates:
        print(f"⚠️ 重複する選手名: {set(duplicates)}")
    
    # データ欠損確認
    for i, player in enumerate(data[:10]):  # 上位10件をチェック
        if not player.get('name'):
            print(f"⚠️ {i+1}位: 選手名が空")
        if player.get('value') is None:
            print(f"⚠️ {i+1}位: 指標値がnull")
    
    # 順位の確認
    values = [player.get('value') for player in data if player.get('value') is not None]
    if len(values) > 1:
        is_desc = values[0] >= values[1]  # 降順か昇順か
        print(f"ソート順: {'降順' if is_desc else '昇順'}")
        
        # 順位が正しいか確認
        for i in range(len(values) - 1):
            if is_desc and values[i] < values[i+1]:
                print(f"⚠️ 順位エラー: {i+1}位 < {i+2}位")
            elif not is_desc and values[i] > values[i+1]:
                print(f"⚠️ 順位エラー: {i+1}位 > {i+2}位")

if __name__ == '__main__':
    check_ranking_json(sys.argv[1])
```

**期待される結果**:
- ランキングが適切な件数になっている
- フィルタリング条件が正しく適用されている
- 選手の重複がない
- 順位が正しい

---

### 段階3: ランキングページの精査

**目的**: ブラウザで表示されるランキングページが正しく動作し、全選手が表示されているか確認

**対象ページ**:
- `/ranking/{YEAR}/{LEAGUE}?sort={METRIC}`

**チェック項目**:

1. **表示件数の確認**
   - [ ] ページに表示される選手数が期待通りか
   - [ ] スクロールで全選手が表示されるか
   - [ ] ページネーションがある場合、全ページが表示されるか

2. **フィルタリングの確認**
   - [ ] 規定打席フィルタが正しく動作しているか
   - [ ] 指標切り替え時にフィルタが正しく適用されるか

3. **ソート機能の確認**
   - [ ] 各指標でソートが正しく動作するか
   - [ ] 昇順/降順の切り替えが正しく動作するか

4. **データ表示の確認**
   - [ ] 選手名、チーム名、指標値が正しく表示されるか
   - [ ] データ欠損が適切に処理されているか（`-` や `N/A` など）

5. **抜けている選手の確認**
   - [ ] 期待される選手が表示されているか
   - [ ] 特定のチームの選手が抜けていないか
   - [ ] 特定の指標で選手が抜けていないか

**チェック方法**:

1. **手動チェック**:
   - ブラウザで各年度・各リーグ・各指標のランキングページを開く
   - 期待される選手が表示されているか確認
   - 開発者ツールのコンソールでエラーがないか確認

2. **自動チェックスクリプト**:
```python
# サンプルスクリプト: scripts/fact_check_page.py
import requests
import json
from pathlib import Path

def check_ranking_page(year, league, metric='OPS'):
    # ランキングJSONを直接読み込んで確認
    json_path = Path(f'public/data/rankings/{year}/{league}/{metric}.json')
    
    if not json_path.exists():
        print(f"❌ JSONファイルが見つかりません: {json_path}")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✅ {year}年{league}リーグ {metric}ランキング: {len(data)}件")
    
    # 上位10件を表示
    print("\n上位10件:")
    for i, player in enumerate(data[:10], 1):
        print(f"{i:2d}. {player.get('name', 'N/A'):20s} {player.get('team', 'N/A'):15s} {player.get('value', 'N/A')}")

if __name__ == '__main__':
    import sys
    year = int(sys.argv[1])
    league = sys.argv[2]
    metric = sys.argv[3] if len(sys.argv) > 3 else 'OPS'
    check_ranking_page(year, league, metric)
```

**期待される結果**:
- 全選手が正しく表示されている
- フィルタリングとソートが正しく動作している
- データ欠損が適切に処理されている

---

## 🔎 抜けている選手の原因候補

### 1. フィルタリング条件による除外

**原因**:
- `PA = 0` の選手が除外されている
- 規定打席未到達の選手が除外されている（指標によって異なる）

**確認方法**:
```python
# CSVでPA=0の選手を確認
df = pd.read_csv('batting_2025_PL_from_master.csv')
pa_zero = df[df['PA'] == 0]
print(f"PA=0の選手数: {len(pa_zero)}")
print(pa_zero[['player_name_ja', 'team', 'PA']])
```

**対処方法**:
- フィルタリング条件が正しいか確認
- 除外される選手が意図通りか確認

---

### 2. データ欠損による除外

**原因**:
- 指標値が `NaN` や `null` の選手が除外されている
- 必須カラム（選手名、チーム名など）が欠損している

**確認方法**:
```python
# CSVでデータ欠損を確認
df = pd.read_csv('batting_2025_PL_from_master.csv')
print(f"OPSが欠損している行数: {df['OPS'].isna().sum()}")
print(f"選手名が欠損している行数: {df['player_name_ja'].isna().sum()}")
```

**対処方法**:
- データ欠損の原因を特定
- 必要に応じてデータを補完

---

### 3. ランキング件数制限による除外

**原因**:
- ランキングが上位100件に制限されている
- 100位以下の選手が表示されない

**確認方法**:
```python
# JSONでランキング件数を確認
with open('public/data/rankings/2025/PL/OPS.json', 'r') as f:
    data = json.load(f)
print(f"ランキング件数: {len(data)}")
```

**対処方法**:
- ランキング件数制限が適切か確認
- 必要に応じて制限を緩和

---

### 4. 計算エラーによる除外

**原因**:
- 指標計算時にエラーが発生し、選手が除外されている
- 数値変換エラー（文字列を数値に変換できないなど）

**確認方法**:
```python
# ランキング生成スクリプトのログを確認
# エラーメッセージや警告を確認
```

**対処方法**:
- 計算エラーの原因を特定
- エラーハンドリングを改善

---

### 5. チーム名の表記ゆれによる除外

**原因**:
- チーム名の表記が異なる（例: "広島" vs "広島東洋カープ"）
- チーム名の正規化が正しく動作していない

**確認方法**:
```python
# CSVでチーム名の一意な値を確認
df = pd.read_csv('batting_2025_PL_from_master.csv')
print("チーム名の一意な値:")
print(df['team'].unique())
```

**対処方法**:
- チーム名の正規化ロジックを確認
- 必要に応じて正規化を改善

---

## 📊 ファクトチェック手順

### ステップ0: スクレイピングデータとの比較（推奨）

1. **スクレイピングデータの確認**
   ```bash
   python scripts/fact_check_compare_scraped.py 2025 PL
   ```

2. **比較結果の確認**
   - [ ] 選手数の差分を確認
   - [ ] 抜けている選手をリストアップ
   - [ ] 除外された選手が適切か確認

3. **結果を記録**
   - [ ] 比較結果を記録
   - [ ] 問題があれば原因を特定

**注意**: スクレイピングデータが存在しない年度・リーグの場合は、このステップをスキップしてステップ1に進みます。

---

### ステップ1: 準備

1. **対象年度・リーグの決定**
   - [ ] チェック対象の年度・リーグを決定
   - [ ] チェック対象の指標を決定

2. **期待値の設定**
   - [ ] 期待される選手リストを作成
   - [ ] 期待されるランキング順位を記録

3. **チェックツールの準備**
   - [ ] CSVチェックスクリプトを準備
   - [ ] JSONチェックスクリプトを準備
   - [ ] ページチェックスクリプトを準備

---

### ステップ2: CSVファイルの精査

1. **CSVファイルを読み込む**
   ```bash
   python scripts/fact_check_csv.py _data/master_csv_calculated/batting_2025_PL_from_master.csv
   ```

2. **チェック項目を確認**
   - [ ] 選手数の確認
   - [ ] 必須カラムの確認
   - [ ] データ欠損の確認
   - [ ] データ整合性の確認

3. **結果を記録**
   - [ ] チェック結果を記録
   - [ ] 問題があれば原因を特定

---

### ステップ3: ランキングJSONの精査

1. **ランキングJSONを読み込む**
   ```bash
   python scripts/fact_check_json.py public/data/rankings/2025/PL/OPS.json
   ```

2. **チェック項目を確認**
   - [ ] ランキング件数の確認
   - [ ] フィルタリング条件の確認
   - [ ] 選手の重複確認
   - [ ] 上位選手の確認
   - [ ] データ欠損の確認

3. **CSVとJSONを比較**
   - [ ] CSVに含まれる選手がJSONに含まれているか
   - [ ] 除外された選手が適切か

4. **結果を記録**
   - [ ] チェック結果を記録
   - [ ] 問題があれば原因を特定

---

### ステップ4: ランキングページの精査

1. **ランキングページを開く**
   - [ ] ブラウザで `/ranking/2025/PL?sort=OPS` を開く

2. **チェック項目を確認**
   - [ ] 表示件数の確認
   - [ ] フィルタリングの確認
   - [ ] ソート機能の確認
   - [ ] データ表示の確認
   - [ ] 抜けている選手の確認

3. **JSONとページを比較**
   - [ ] JSONに含まれる選手がページに表示されているか
   - [ ] 表示されない選手がいるか

4. **結果を記録**
   - [ ] チェック結果を記録
   - [ ] 問題があれば原因を特定

---

### ステップ5: 問題の特定と修正

1. **問題の特定**
   - [ ] どの段階で問題が発生しているか特定
   - [ ] 問題の原因を特定

2. **修正の実施**
   - [ ] 問題を修正
   - [ ] 修正後の再チェック

3. **結果の記録**
   - [ ] 修正内容を記録
   - [ ] 再チェック結果を記録

---

## 📝 チェックリスト

### CSVファイルの精査

- [ ] 総行数が期待通りか
- [ ] 各チームの選手数が期待通りか
- [ ] 必須カラムに欠損がないか
- [ ] `PA = 0` の選手が適切に除外されているか
- [ ] データ整合性が保たれているか

### ランキングJSONの精査

- [ ] ランキング件数が適切か
- [ ] フィルタリング条件が正しく適用されているか
- [ ] 選手の重複がないか
- [ ] 上位選手が含まれているか
- [ ] 順位が正しいか

### ランキングページの精査

- [ ] 全選手が表示されているか
- [ ] フィルタリングが正しく動作しているか
- [ ] ソート機能が正しく動作しているか
- [ ] データ欠損が適切に処理されているか

---

## 🛠️ チェックツール

### 0. スクレイピングデータ比較スクリプト（推奨）

**ファイル**: `scripts/fact_check_compare_scraped.py`

**使用方法**:
```bash
python scripts/fact_check_compare_scraped.py 2025 PL
```

**出力**:
- スクレイピングデータと現在のデータの選手数比較
- 抜けている選手のリスト
- チーム別選手数の比較

---

### 1. CSVチェックスクリプト

**ファイル**: `scripts/fact_check_csv.py`

**使用方法**:
```bash
python scripts/fact_check_csv.py _data/master_csv_calculated/batting_2025_PL_from_master.csv
```

**出力**:
- 総行数
- チーム別選手数
- データ欠損の確認
- データ整合性の確認

---

### 2. JSONチェックスクリプト

**ファイル**: `scripts/fact_check_json.py`

**使用方法**:
```bash
python scripts/fact_check_json.py public/data/rankings/2025/PL/OPS.json
```

**出力**:
- ランキング件数
- 選手の重複確認
- 順位の確認
- データ欠損の確認

---

### 3. ページチェックスクリプト

**ファイル**: `scripts/fact_check_page.py`

**使用方法**:
```bash
python scripts/fact_check_page.py 2025 PL OPS
```

**出力**:
- ランキング件数
- 上位10件の表示

---

### 4. 一括チェックスクリプト

**ファイル**: `scripts/fact_check_all.py`

**使用方法**:
```bash
python scripts/fact_check_all.py 2025 PL
```

**出力**:
- 全指標のランキングを一括チェック
- チェック結果をレポート形式で出力

---

### 5. スクレイピングデータ一括比較スクリプト

**ファイル**: `scripts/fact_check_compare_all_scraped.py`

**使用方法**:
```bash
# 特定年度・リーグを比較
python scripts/fact_check_compare_all_scraped.py 2025 PL

# 全年度・全リーグを一括比較
python scripts/fact_check_compare_all_scraped.py --all
```

**出力**:
- 全年度・全リーグのスクレイピングデータと現在のデータを比較
- 抜けている選手の一覧
- チーム別選手数の比較結果

---

## 📋 レポート形式

### チェック結果レポート

```
=== ランキングファクトチェック結果 ===

年度: 2025
リーグ: PL
チェック日時: 2026-01-19 12:00:00

【CSVファイルの精査】
✅ 総行数: 150件
✅ チーム別選手数: 正常
✅ 必須カラム: 正常
⚠️  PA=0の選手: 5件（意図通り除外）

【ランキングJSONの精査】
✅ OPSランキング: 100件
✅ フィルタリング: 正常
✅ 選手の重複: なし
✅ 上位選手: 正常

【ランキングページの精査】
✅ 表示件数: 正常
✅ フィルタリング: 正常
✅ ソート機能: 正常

【問題点】
なし

【推奨事項】
- 定期的なファクトチェックの実施
```

---

## 🎯 優先度

### 高優先度

1. **CSVファイルの精査**
   - 元データの品質を確保
   - データ欠損や不整合を早期に発見

2. **ランキングJSONの精査**
   - ランキング生成ロジックの正確性を確保
   - フィルタリング条件の適用を確認

### 中優先度

3. **ランキングページの精査**
   - ユーザーが実際に見る画面の正確性を確保
   - UI/UXの問題を発見

### 低優先度

4. **一括チェックの自動化**
   - 効率的なチェックの実施
   - 定期的なチェックの実施

---

## 📚 参考資料

- `scripts/build_rankings_from_calculated.py`: ランキング生成スクリプト
- `scripts/build_rankings_2025_PL_full.py`: ランキング生成ロジック
- `app/_lib/ranking.ts`: ランキング表示ロジック
- `lib/ranking/qualifyingPA.ts`: 規定打席フィルタリングロジック

---

## ✅ まとめ

### チェック段階

0. **スクレイピングデータとの比較**（段階0、推奨）
   - 過去にスクレイピングしたデータを参照データとして使用
   - 現在のデータと比較して抜けている選手を特定
   - **最も効率的な方法**（スクレイピングデータが存在する場合）

1. **CSVファイルの精査**（段階1）
   - 元データの品質を確保
   - データ欠損や不整合を早期に発見

2. **ランキングJSONの精査**（段階2）
   - ランキング生成ロジックの正確性を確保
   - フィルタリング条件の適用を確認

3. **ランキングページの精査**（段階3）
   - ユーザーが実際に見る画面の正確性を確保
   - UI/UXの問題を発見

### 推奨されるチェック順序

**スクレイピングデータが存在する場合**:
1. **スクレイピングデータとの比較**（段階0） → 2. **CSVファイルの精査**（段階1） → 3. **ランキングJSONの精査**（段階2） → 4. **ランキングページの精査**（段階3）

**スクレイピングデータが存在しない場合**:
1. **CSVファイルの精査**（段階1） → 2. **ランキングJSONの精査**（段階2） → 3. **ランキングページの精査**（段階3）

### スクレイピングデータの活用メリット

1. **効率的なチェック**: スクレイピングデータを参照データとして使用することで、抜けている選手を迅速に特定できます
2. **正確な比較**: 過去にスクレイピングした全成績データと比較することで、データの完全性を確認できます
3. **早期発見**: データ処理の各段階で問題を発見する前に、元データの段階で問題を特定できます

この順序でチェックすることで、問題を段階的に特定し、効率的に修正できます。

