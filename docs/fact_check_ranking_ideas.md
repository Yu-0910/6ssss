# ランキングページ成績のファクトチェック：解決策アイデア

## 問題の本質

外部ソース（NPB公式サイトなど）からスクレイピングしても、**同じ条件でスクレイピングした場合、取得できない選手は同じ選手が取得できない**という問題があります。

これは、外部ソース自体に問題がある（データが存在しない、URLが間違っている、アクセス制限があるなど）場合、何度スクレイピングしても同じ結果になるという懸念です。

## 解決策アイデア

### ✅ 実装可能な解決策

#### 1. **内部整合性チェック（推奨）**

外部ソースに依存せず、**内部の複数のデータソース間で整合性をチェック**する方法です。

**アプローチ：**
- `_data/master_csv__import_1950_2024/`（インポート済み生データ）
- `_data/master_csv_calculated/`（計算済みデータ）
- `_data/master_csv/`（マスターデータ）
- `public/data/rankings/`（ランキングJSON）

これらの間で、同じ年度・リーグの選手リストを比較し、欠けている選手を特定します。

**メリット：**
- 外部ソースに依存しない
- 既存のデータを活用できる
- スクレイピングの失敗に影響されない

**実装方法：**
```python
# 例: scripts/fact_check_internal_consistency.py
# 1. 各CSVディレクトリから同じ年度・リーグの選手リストを抽出
# 2. player_idで比較
# 3. 欠けている選手を特定
# 4. 統計的な異常（特定の年度だけ欠けている、特定のチームだけ欠けている）を検出
```

#### 2. **統計的な異常検出**

特定のパターン（年度間の不整合、チーム間の不整合など）を検出する方法です。

**検出パターン：**
- 特定の選手が特定の年度だけ欠けている
- 特定のチームの選手がまとめて欠けている
- 特定の年度・リーグで選手数が異常に少ない
- 連続する年度で選手が突然消える/現れる

**実装方法：**
```python
# 例: scripts/detect_statistical_anomalies.py
# 1. 各年度・リーグの選手数を集計
# 2. 前年比で異常な減少がないかチェック
# 3. チーム別の選手数をチェック
# 4. 特定のplayer_idが特定の年度だけ欠けているパターンを検出
```

#### 3. **複数年度間の整合性チェック**

同じ選手が複数年度にわたって存在する場合、その選手が特定の年度だけ欠けているかをチェックします。

**実装方法：**
```python
# 例: scripts/fact_check_cross_year_consistency.py
# 1. 各player_idについて、どの年度に存在するかを集計
# 2. 連続する年度で突然消える/現れるパターンを検出
# 3. デビュー年・引退年と整合性があるかチェック
```

#### 4. **ランキングJSONとCSVの整合性チェック**

ランキングJSONに表示されている選手が、元のCSVに存在するかをチェックします。

**実装方法：**
```python
# 例: scripts/fact_check_ranking_vs_csv.py
# 1. public/data/rankings/ のJSONから選手リストを抽出
# 2. 対応するCSVから選手リストを抽出
# 3. JSONにあるがCSVにない選手、CSVにあるがJSONにない選手を特定
```

#### 5. **履歴データとの比較**

過去に取得できたデータ（HTMLキャッシュ、過去のCSVなど）と現在のデータを比較します。

**実装方法：**
```python
# 例: scripts/fact_check_historical_comparison.py
# 1. output/html_cache/players/ のHTMLキャッシュから選手情報を抽出
# 2. 現在のCSVと比較
# 3. 過去には存在したが現在は欠けている選手を特定
```

### ⚠️ 部分的に実装可能な解決策

#### 6. **複数の外部ソースを使用**

NPB公式サイトだけでなく、他の信頼できるソース（例：Baseball-Reference、Wikipedia、その他の野球統計サイト）と比較します。

**制約：**
- 他のソースがNPBの全年度・全リーグのデータを持っているとは限らない
- 各ソースのデータ構造が異なるため、パースロジックが必要
- API制限やスクレイピング規約に注意が必要

**実装方法：**
```python
# 例: scripts/fact_check_multi_source.py
# 1. NPB公式サイトから取得
# 2. 他のソース（Baseball-Reference、Wikipediaなど）から取得
# 3. 複数のソースで一致する選手を「確実に存在する」と判定
# 4. 1つのソースにしか存在しない選手を「要確認」としてマーク
```

### ❌ 解決不可能な問題

#### 7. **外部ソース自体にデータが存在しない場合**

外部ソース（NPB公式サイトなど）自体にデータが存在しない場合、スクレイピングでは取得できません。これは**技術的には解決不可能**です。

**対処方法：**
- 手動で確認する
- 別のソース（書籍、公式記録など）を参照する
- データが本当に存在しない可能性を考慮する

## 推奨アプローチ

### フェーズ1: 内部整合性チェック（最優先）

1. **複数CSVディレクトリ間の比較**
   - `master_csv__import_1950_2024/` vs `master_csv_calculated/`
   - 欠けている選手を特定

2. **統計的な異常検出**
   - 年度間の選手数の異常な変化を検出
   - 特定のチームの選手がまとめて欠けているパターンを検出

3. **ランキングJSONとCSVの整合性**
   - JSONに表示されている選手がCSVに存在するか
   - CSVにあるがJSONに表示されていない選手を特定

### フェーズ2: 外部ソースとの比較（補完的）

1. **複数の外部ソースを使用**
   - NPB公式サイト + 他のソース
   - 複数のソースで一致する選手を「確実」と判定

2. **履歴データとの比較**
   - HTMLキャッシュから過去のデータを抽出
   - 過去には存在したが現在は欠けている選手を特定

## 実装例

### スクリプト: `scripts/fact_check_internal_consistency.py`

```python
#!/usr/bin/env python3
"""
内部整合性チェックスクリプト

複数のCSVディレクトリ間で選手リストを比較し、欠けている選手を特定します。
外部ソースに依存せず、既存のデータのみを使用します。
"""

import csv
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict

def load_players_from_csv(csv_path: Path, year: int, league: str) -> Set[str]:
    """CSVからplayer_idのセットを読み込む"""
    players = set()
    if not csv_path.exists():
        return players
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_year = int(row.get('year', year))
            row_league = row.get('league', '').upper()
            if row_year == year and row_league == league:
                player_id = row.get('player_id', '').strip()
                if player_id and player_id != 'nan':
                    players.add(player_id)
    
    return players

def check_internal_consistency(year: int, league: str, project_root: Path):
    """内部整合性をチェック"""
    
    # 各CSVディレクトリから選手リストを読み込む
    sources = {
        'imported': project_root / '_data' / 'master_csv__import_1950_2024' / f'batting_{year}_{league}_from_master.csv',
        'calculated': project_root / '_data' / 'master_csv_calculated' / f'batting_{year}_{league}_from_master.csv',
        'master': project_root / '_data' / 'master_csv' / f'batting_{year}_{league}_from_master.csv',
    }
    
    players_by_source = {}
    for source_name, csv_path in sources.items():
        players_by_source[source_name] = load_players_from_csv(csv_path, year, league)
        print(f"  {source_name}: {len(players_by_source[source_name])}人")
    
    # 全ソースの和集合（全選手）
    all_players = set()
    for players in players_by_source.values():
        all_players.update(players)
    
    # 各ソースで欠けている選手を特定
    missing_by_source = {}
    for source_name, players in players_by_source.items():
        missing = all_players - players
        if missing:
            missing_by_source[source_name] = missing
    
    return {
        'all_players': all_players,
        'players_by_source': players_by_source,
        'missing_by_source': missing_by_source,
    }

# 使用例
if __name__ == '__main__':
    project_root = Path(__file__).parent.parent
    year = 1972
    league = 'CL'
    
    result = check_internal_consistency(year, league, project_root)
    
    print(f"\n=== {year}年 {league}リーグ 内部整合性チェック結果 ===")
    print(f"全選手数: {len(result['all_players'])}人")
    
    for source_name, missing in result['missing_by_source'].items():
        print(f"\n{source_name}で欠けている選手: {len(missing)}人")
        for player_id in sorted(missing)[:10]:
            print(f"  - {player_id}")
```

## まとめ

**解決不可能な問題：**
- 外部ソース自体にデータが存在しない場合

**実装可能な解決策（推奨順）：**
1. ✅ **内部整合性チェック**（最優先・推奨）
2. ✅ **統計的な異常検出**
3. ✅ **複数年度間の整合性チェック**
4. ✅ **ランキングJSONとCSVの整合性チェック**
5. ✅ **履歴データとの比較**
6. ⚠️ **複数の外部ソースを使用**（部分的に可能）

**推奨アプローチ：**
外部ソースに依存せず、**既存の内部データ間で整合性をチェック**する方法が最も確実です。これにより、スクレイピングの失敗に影響されず、データの整合性を保証できます。
