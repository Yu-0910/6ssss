# ランキング内の重複選手削除計画書

## 1. 現状分析

### 1.1 重複の状況
- **重複エントリ数**: 578件
- **重複している選手数（年度・リーグ・選手名の組み合わせ）**: 289組
- **重複が発生している年度・リーグの組み合わせ**: 49組
- **対象期間**: 1950年～2025年

### 1.2 重複のパターン
CSVファイルの分析結果から、以下のパターンが確認されています：

1. **チーム名の表記ゆれによる重複**
   - 例：`千葉ロッテマリーンズ` vs `埼玉西武ライオンズ`（1973-1978年PL）
   - 例：`横浜DeNAベイスターズ` vs `横浜ベイスターズ`（1978-1980年CL）

2. **同一選手が同じ値で2回出現**
   - 同じ`value`（指標値）を持つ
   - 同じ`rank`または連続した`rank`を持つ
   - 同じ`playerId`パターン（player-5, player-6など）

3. **すべての指標ファイルで一貫して発生**
   - 1つの指標ファイルで重複が見つかると、その年度・リーグのすべての指標ファイルで同じ重複が発生している可能性が高い

### 1.3 影響範囲
- **影響を受けるファイル**: `public/data/rankings/{YEAR}/{LEAGUE}/{METRIC}.json`
- **推定ファイル数**: 49組 × 指標数（約72-176ファイル/年度・リーグ） = 約3,500-8,600ファイル
- **実際の重複ファイル数**: 各年度・リーグで1つの指標ファイルを代表としてチェックしているため、実際にはすべての指標ファイルで重複が発生している可能性が高い

## 2. 削除基準の決定

### 2.1 削除対象の選定方法

以下の優先順位で削除対象を決定する：

#### 方法A: ランクが高い方を残す（推奨）
- **基準**: `rank`が小さい方（上位）を残し、大きい方を削除
- **理由**: ランキングの整合性を保つため
- **例**: rank=5とrank=6が同じ選手名の場合、rank=5を残す

#### 方法B: チーム名の優先順位で決定
- **基準**: 特定のチーム名表記を優先（例：`横浜DeNAベイスターズ` > `横浜ベイスターズ`）
- **理由**: より正確なチーム名を保持するため
- **問題点**: チーム名の優先順位を定義する必要がある

#### 方法C: 最初に出現した方を残す
- **基準**: JSON配列内で先に出現したエントリを残す
- **理由**: シンプル
- **問題点**: ランクの整合性が崩れる可能性

### 2.2 推奨方法
**方法A（ランクが高い方を残す）を推奨**

理由：
1. ランキングの意味を保持できる
2. 実装がシンプル
3. データの整合性が保たれる

## 3. 実装方法

### 3.1 アプローチ

#### アプローチ1: JSONファイルを直接編集（推奨）
- 各ランキングJSONファイルを読み込み
- 重複選手を検出して削除
- ランクを再計算
- ファイルを上書き保存

**メリット**:
- 直接的な解決
- 既存のランキングファイルを修正できる

**デメリット**:
- 大量のファイルを処理する必要がある
- ランクの再計算が必要

#### アプローチ2: ランキングを再生成
- 元のCSVファイルから重複を除去
- ランキング生成スクリプトを再実行

**メリット**:
- 根本的な解決
- ランクが自動的に再計算される

**デメリット**:
- 元のCSVファイルの修正が必要
- すべての年度・リーグのランキングを再生成する必要がある

### 3.2 推奨アプローチ
**アプローチ1（JSONファイルを直接編集）を推奨**

理由：
1. 既存のランキングファイルを直接修正できる
2. 元のCSVファイルに影響を与えない
3. 段階的な実行が可能

### 3.3 実装手順

#### ステップ1: 削除対象リストの生成
1. `output/reports/duplicate_player_names_in_rankings.csv`を読み込む
2. 各重複について、削除対象を決定（ランクが高い方を残す）
3. 削除対象リストを作成：
   ```
   {
     (year, league, player_name): {
       'keep': {rank, playerId, ...},
       'remove': {rank, playerId, ...}
     }
   }
   ```

#### ステップ2: ランキングJSONファイルの処理
各年度・リーグのすべての指標ファイルに対して：

1. JSONファイルを読み込む
2. 削除対象リストに基づいて重複選手を削除
3. ランクを再計算（1から連番に振り直し）
4. `playerId`を更新（`player-{new_rank}`）
5. JSONファイルを保存

#### ステップ3: 検証
1. 削除後のファイルで重複が残っていないか確認
2. ランクが正しく再計算されているか確認
3. JSONファイルの構造が正しいか確認

## 4. 安全対策

### 4.1 バックアップ
- **必須**: 処理前に`public/data/rankings/`ディレクトリ全体をバックアップ
- **バックアップ先**: `output/backups/rankings_backup_{timestamp}/`
- **方法**: `shutil.copytree()`を使用

### 4.2 ドライラン機能
- 実際にファイルを変更せず、削除対象を確認できるモード
- `--dry-run`フラグで実行
- 削除対象のリストをCSVで出力

### 4.3 ログ記録
- 削除した選手の詳細をログファイルに記録
- 各ファイルの処理状況を記録
- エラーが発生した場合の詳細情報を記録

### 4.4 段階的実行
- 1つの年度・リーグずつ処理
- 問題が発生した場合にロールバック可能
- `--year`と`--league`オプションで対象を限定

### 4.5 検証スクリプト
- 削除後の重複チェック
- ランクの整合性チェック
- JSONファイルの構造チェック

## 5. 実装詳細

### 5.1 スクリプト構成

```
scripts/
└── remove_duplicate_players_from_rankings.py
    ├── load_duplicate_list()      # 重複リストの読み込み
    ├── determine_removal_targets() # 削除対象の決定
    ├── process_ranking_file()     # 1つのJSONファイルを処理
    ├── recalculate_ranks()        # ランクの再計算
    └── main()                     # メイン処理
```

### 5.2 削除対象決定ロジック

```python
def determine_removal_targets(duplicates):
    """
    重複リストから削除対象を決定
    
    基準: rankが小さい方（上位）を残す
    """
    removal_targets = {}
    
    for (year, league, player_name), entries in duplicates.items():
        # rankでソート（小さい順）
        sorted_entries = sorted(entries, key=lambda x: x['rank'])
        
        # 最初（rankが最小）を残す、残りを削除
        keep = sorted_entries[0]
        remove = sorted_entries[1:]
        
        removal_targets[(year, league, player_name)] = {
            'keep': keep,
            'remove': remove
        }
    
    return removal_targets
```

### 5.3 ランク再計算ロジック

```python
def recalculate_ranks(players):
    """
    選手リストのランクを再計算
    
    1. 削除後のリストを取得
    2. value（指標値）でソート（降順）
    3. 1から連番でrankを割り当て
    4. playerIdを更新
    """
    # valueでソート（降順）
    sorted_players = sorted(
        players, 
        key=lambda x: x.get('value', 0), 
        reverse=True
    )
    
    # ランクを再割り当て
    for new_rank, player in enumerate(sorted_players, start=1):
        player['rank'] = new_rank
        player['playerId'] = f"player-{new_rank}"
    
    return sorted_players
```

### 5.4 ファイル処理ロジック

```python
def process_ranking_file(file_path, removal_targets):
    """
    1つのランキングJSONファイルを処理
    
    1. JSONファイルを読み込む
    2. 削除対象リストに基づいて選手を削除
    3. ランクを再計算
    4. ファイルを保存
    """
    # JSON読み込み
    with open(file_path, 'r', encoding='utf-8') as f:
        players = json.load(f)
    
    # 年度・リーグ・指標を取得
    year, league, metric = extract_file_info(file_path)
    
    # 削除対象を特定
    players_to_remove = []
    for player in players:
        player_name = player.get('name', '')
        key = (year, league, player_name)
        
        if key in removal_targets:
            remove_list = removal_targets[key]['remove']
            # この選手が削除対象かチェック
            if should_remove(player, remove_list):
                players_to_remove.append(player)
    
    # 削除
    players = [p for p in players if p not in players_to_remove]
    
    # ランク再計算
    players = recalculate_ranks(players)
    
    # 保存
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(players, f, ensure_ascii=False, indent=2)
    
    return len(players_to_remove)
```

## 6. 実行手順

### 6.1 準備
1. バックアップの作成
2. 重複リストの確認
3. ドライランで削除対象を確認

### 6.2 実行
1. 小規模テスト（1つの年度・リーグで実行）
2. 結果の確認
3. 全件実行

### 6.3 検証
1. 重複が残っていないか確認
2. ランクが正しく再計算されているか確認
3. JSONファイルの構造が正しいか確認

## 7. リスクと対策

### 7.1 リスク
1. **データ損失**: 誤って重要な選手を削除する可能性
2. **ランクの不整合**: ランク再計算のロジックエラー
3. **大量ファイル処理**: 処理時間が長い、メモリ不足
4. **部分的な失敗**: 一部のファイルのみ処理が失敗

### 7.2 対策
1. **バックアップ必須**: 処理前に必ずバックアップ
2. **段階的実行**: 小規模テストから開始
3. **ログ記録**: すべての操作をログに記録
4. **検証スクリプト**: 処理後の自動検証
5. **ロールバック機能**: 問題発生時にバックアップから復元

## 8. 検証方法

### 8.1 重複チェック
処理後に`find_duplicate_player_names_in_rankings.py`を再実行し、重複が0件になることを確認

### 8.2 ランクチェック
- 各JSONファイルで`rank`が1から連番になっているか確認
- `playerId`が`player-{rank}`の形式になっているか確認

### 8.3 データ整合性チェック
- JSONファイルが正しい形式か確認
- 選手数が適切か確認（削除前後で比較）

## 9. 実行コマンド例

```bash
# ドライラン（削除対象の確認のみ）
py scripts/remove_duplicate_players_from_rankings.py --dry-run

# 1つの年度・リーグでテスト
py scripts/remove_duplicate_players_from_rankings.py --year 1973 --league PL

# 全件実行
py scripts/remove_duplicate_players_from_rankings.py

# 検証
py scripts/find_duplicate_player_names_in_rankings.py
```

## 10. 次のステップ

1. **計画書の承認**: この計画書を確認・承認
2. **スクリプト実装**: `remove_duplicate_players_from_rankings.py`を作成
3. **テスト実行**: 小規模テストで動作確認
4. **本番実行**: 全件処理
5. **検証**: 結果の確認

## 11. 補足事項

### 11.1 チーム名の表記ゆれについて
重複の多くはチーム名の表記ゆれによるものです。将来的には：
- チーム名の正規化処理を追加
- 元のCSVファイルでチーム名を統一

などの対策を検討することを推奨します。

### 11.2 パフォーマンス
- 約5,000-10,000ファイルを処理する必要がある
- 並列処理を検討（ただし、ファイルI/Oの競合に注意）
- 進捗表示を実装

### 11.3 エラーハンドリング
- ファイル読み込みエラー
- JSON形式エラー
- ディスク容量不足
- 権限エラー

など、各種エラーに対する適切な処理を実装する必要があります。
