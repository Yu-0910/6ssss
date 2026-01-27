# 2025年新規所属選手の成績取得・反映計画書

## 目的

2025年から所属となった選手（ファビアン、西川史礁ら他多数）の成績が取れていない問題を解決するため、NPB公式サイトからスクレイピングを行い、ランキングページに反映するまでの全工程を実装する。

## 現状分析

### 問題点
- 2025年から所属となった選手の成績がマスターCSVに含まれていない
- 例：ファビアン、西川史礁など
- 結果として、ランキングページにこれらの選手が表示されない

### 現在のデータフロー
1. **マスターCSV**: `_data/master_csv/batting_YYYY_LEAGUE_from_master.csv`
   - 生の打撃成績データ（スクレイピング元データ）
2. **計算済みCSV**: `_data/master_csv_calculated/batting_YYYY_LEAGUE_from_master.csv`
   - `compute_metrics_all_seasons.py` で指標を計算したデータ
   - **ランキングページはこのファイルを読み込む**
3. **ランキングページ**: `app/ranking/[year]/[league]/page.tsx`
   - `lib/ranking/loaders.ts` の `loadBattingCsv()` でCSVを読み込み
   - `lib/ranking/adapter.ts` の `buildRankingWithAllMetrics()` でランキングデータを生成

### 既存のスクレイピング関連スクリプト
- `scripts/fact_check_npb_official.mjs`: NPB公式サイトから選手リストを取得（比較用）
- URL構造: `https://npb.jp/bis/stats/${year}/${leagueLower}/batting.html`
- ただし、これは選手リストの比較のみで、実際の成績データのスクレイピングは未実装

## 実装計画

### Phase 1: NPB公式サイトからの成績データスクレイピング

#### 1.1 スクレイピングスクリプトの作成
**ファイル**: `scripts/scrape_npb_batting_stats.py`

**機能**:
- NPB公式サイトの打撃成績ページから全選手の成績を取得
- URL: `https://npb.jp/bis/stats/${year}/${leagueLower}/batting.html`
- 取得データ:
  - 選手名（日本語）
  - チーム名
  - player_id（NPB公式の選手ID）
  - 基本成績（試合、打席、打数、安打、本塁打、打点など）
  - 率系指標（打率、出塁率、長打率など）

**実装方針**:
- HTMLパーサー（BeautifulSoup）を使用
- テーブル構造を解析してデータを抽出
- エラーハンドリング（ネットワークエラー、HTML構造変更への対応）
- レート制限対応（リクエスト間隔を空ける）

**出力形式**:
- **既存ファイルを更新**: `_data/master_csv/batting_${year}_${league}_from_master.csv`
- 既存ファイルが存在する場合:
  - `player_id` をキーとして重複チェック
  - 新規選手（`player_id`が存在しない）のみ追加
  - 既存選手のデータは既存のまま保持（上書きしない）
- 既存ファイルが存在しない場合は新規作成

#### 1.2 データ検証機能
**機能**:
- スクレイピングしたデータの妥当性チェック
- 必須カラムの存在確認
- データ型の検証（数値カラムが数値であることなど）
- 欠損値のチェック

### Phase 2: 既存データとのマージ（Phase 1に統合）

**注意**: マージ機能は Phase 1 のスクレイピングスクリプトに統合します。
- スクレイピングスクリプト内で既存ファイルを読み込み
- `player_id` をキーとして重複チェック
- 新規選手のみを追加（既存選手は既存データを保持）
- 既存ファイルを直接更新（バックアップは自動的に作成）

### Phase 3: 指標計算とランキング生成

#### 3.1 指標計算の実行
**既存スクリプト**: `scripts/compute_metrics_all_seasons.py`

**実行**:
```bash
# 2025年パ・リーグ
python scripts/compute_metrics_all_seasons.py --year 2025 --league PL

# 2025年セ・リーグ
python scripts/compute_metrics_all_seasons.py --year 2025 --league CL
```

**機能**:
- `_data/master_csv/batting_2025_PL_from_master.csv` を読み込み
- Record.csvに記載された指標を計算
- `_data/master_csv_calculated/batting_2025_PL_from_master.csv` に出力（既存ファイルを上書き）
- 既存のロジックをそのまま使用

**重要**: 
- マスターCSV（`_data/master_csv/`）を更新した後、必ずこのスクリプトを実行して計算済みCSVを再生成する
- ランキングページは `_data/master_csv_calculated/` のファイルを読み込むため、この再生成が必須

#### 3.2 ランキングページへの反映確認
- ランキングページは自動的に `_data/master_csv_calculated/` の最新データを読み込む
- キャッシュをクリアして反映を確認

### Phase 4: 検証とレポート生成

#### 4.1 データ検証
**既存スクリプト**: `scripts/fact_check_npb_official.mjs`

**実行**:
```bash
node scripts/fact_check_npb_official.mjs 2025 PL
node scripts/fact_check_npb_official.mjs 2025 CL
```

**確認項目**:
- NPB公式サイトに存在する選手がすべてCSVに含まれているか
- 新規選手（ファビアン、西川史礁など）が含まれているか

#### 4.2 レポート生成
- スクレイピング結果のサマリー
- 新規追加された選手のリスト
- エラーや警告の記録

## 実装詳細

### ステップ1: スクレイピングスクリプトの実装

#### 必要なライブラリ
```python
# requirements.txt に追加（既存のものがあれば確認）
beautifulsoup4>=4.12.0
requests>=2.31.0
lxml>=4.9.0
pandas>=2.0.0  # CSV操作用
```

#### スクリプト構造
```python
#!/usr/bin/env python3
"""
scrape_npb_batting_stats.py

NPB公式サイトから打撃成績をスクレイピングしてCSV形式で保存するスクリプト
"""

import argparse
import csv
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Dict, Any, Optional

def scrape_batting_stats(year: int, league: str) -> List[Dict[str, Any]]:
    """
    NPB公式サイトから打撃成績をスクレイピング
    
    Args:
        year: 年度（例: 2025）
        league: リーグ（'PL' または 'CL'）
    
    Returns:
        選手成績のリスト（辞書形式）
    """
    # URL構築
    league_lower = league.lower()
    url = f"https://npb.jp/bis/stats/{year}/{league_lower}/batting.html"
    
    # HTML取得
    # テーブル解析
    # データ抽出
    # 返却
    
def update_existing_csv(scraped_data: List[Dict[str, Any]], existing_path: Path) -> List[Dict[str, Any]]:
    """
    既存CSVファイルを更新（新規選手のみ追加）
    
    Args:
        scraped_data: スクレイピングで取得したデータ
        existing_path: 既存CSVファイルのパス
    
    Returns:
        更新後の全データ（既存 + 新規）
    """
    # 既存ファイルを読み込む
    # player_idをキーとして既存データをマップ
    # スクレイピングデータから新規選手（player_idが既存にない）を抽出
    # 既存データ + 新規選手を結合
    # 返却

def save_to_csv(data: List[Dict[str, Any]], output_path: Path, backup: bool = True):
    """
    CSV形式で保存（既存ファイルがある場合はバックアップを作成）
    
    Args:
        data: 保存するデータ
        output_path: 出力先パス
        backup: 既存ファイルをバックアップするか
    """
    # 既存ファイルがある場合はバックアップを作成
    # CSV書き込み

def main():
    # コマンドライン引数解析
    #   --year: 年度（必須）
    #   --league: リーグ（PL/CL、必須）
    #   --update-existing: 既存ファイルを更新する（デフォルト: True）
    #   --overwrite: 既存ファイルを完全に上書きする（デフォルト: False）
    
    # 既存ファイルのパスを構築
    #   _data/master_csv/batting_{year}_{league}_from_master.csv
    
    # スクレイピング実行
    # 既存ファイルがある場合:
    #   - 既存データを読み込む
    #   - スクレイピングデータとマージ（新規選手のみ追加）
    #   - 既存ファイルを更新（バックアップ作成）
    # 既存ファイルがない場合:
    #   - 新規ファイルを作成
    
    # 検証とレポート
    #   - 追加された新規選手のリストを表示
    #   - エラーや警告を記録
```

### ステップ2: マージ機能の実装

#### マージロジック
- `player_id` をキーとして重複チェック
- 新規選手のみ追加
- 既存選手は既存データを保持（または上書きオプション）

### ステップ3: エラーハンドリング

#### 想定されるエラー
1. **ネットワークエラー**: リトライ機能を実装
2. **HTML構造変更**: エラーメッセージで構造変更を通知
3. **データ欠損**: 警告を出して続行
4. **レート制限**: リクエスト間隔を空ける

## 実行手順

### 1. バックアップ作成（推奨）
```bash
# 既存ファイルのバックアップを作成
# PowerShell
Copy-Item "_data/master_csv_calculated/batting_2025_PL_from_master.csv" "_data/master_csv_calculated/batting_2025_PL_from_master.csv.backup"
Copy-Item "_data/master_csv_calculated/batting_2025_CL_from_master.csv" "_data/master_csv_calculated/batting_2025_CL_from_master.csv.backup"
```

### 2. スクレイピング実行（既存ファイルを更新）
```bash
# 2025年パ・リーグ
# 既存の _data/master_csv/batting_2025_PL_from_master.csv を読み込み、新規選手を追加
python scripts/scrape_npb_batting_stats.py --year 2025 --league PL --update-existing

# 2025年セ・リーグ
python scripts/scrape_npb_batting_stats.py --year 2025 --league CL --update-existing
```

**動作**:
- 既存ファイル `_data/master_csv/batting_2025_PL_from_master.csv` が存在する場合:
  - 既存データを読み込む
  - NPB公式サイトからスクレイピング
  - `player_id` をキーとして重複チェック
  - 新規選手（既存にない `player_id`）のみ追加
  - 既存ファイルを更新（バックアップは自動作成）
- 既存ファイルが存在しない場合:
  - 新規ファイルを作成

### 3. 指標計算（計算済みCSVを再生成）
```bash
# 2025年パ・リーグ
python scripts/compute_metrics_all_seasons.py --year 2025 --league PL

# 2025年セ・リーグ
python scripts/compute_metrics_all_seasons.py --year 2025 --league CL
```

**重要**: 
- マスターCSVを更新した後、必ずこのスクリプトを実行
- `_data/master_csv_calculated/batting_2025_PL_from_master.csv` が再生成される
- ランキングページはこの計算済みCSVを読み込む

### 4. 検証
```bash
# NPB公式サイトと比較して不足選手を確認
node scripts/fact_check_npb_official.mjs 2025 PL
node scripts/fact_check_npb_official.mjs 2025 CL
```

### 5. ランキングページの確認
```bash
# ローカルサーバーを起動（既に起動している場合は再起動）
npm run dev

# ブラウザでアクセス
# http://localhost:3000/ranking/2025/PL
# http://localhost:3000/ranking/2025/CL
```

**確認項目**:
- 新規選手（ファビアン、西川史礁など）が表示されているか
- 既存選手のデータが正しく保持されているか
- ページ下部のデバッグ情報で `Duplicates: 0 ids / 0 rows` になっているか

## 注意事項

### スクレイピングの倫理
- NPB公式サイトの利用規約を遵守
- リクエスト間隔を適切に空ける（レート制限対策）
- robots.txtを確認

### データの整合性
- スクレイピングしたデータと既存データの整合性を確認
- 新規選手の `player_id` が正しく取得できているか確認
- チーム名の表記ゆれに注意
- 既存選手のデータは上書きしない（新規選手のみ追加）

### ファイル更新の流れ
1. **マスターCSV更新**: `_data/master_csv/batting_2025_PL_from_master.csv`
   - スクレイピングスクリプトで新規選手を追加
   - 既存選手のデータは保持
2. **計算済みCSV再生成**: `_data/master_csv_calculated/batting_2025_PL_from_master.csv`
   - `compute_metrics_all_seasons.py` で指標を再計算
   - 既存ファイルを上書き
3. **ランキングページ反映**: 自動的に最新の計算済みCSVを読み込む

### エラー時の対応
- スクレイピングが失敗した場合、既存データを保持（既存ファイルは変更しない）
- 部分的な成功でも、取得できた新規選手データは追加
- エラーログを詳細に記録
- バックアップファイルから復元可能（`_data/master_csv/batting_2025_PL_from_master.csv.backup`）

## 成功基準

1. ✅ NPB公式サイトから2025年の打撃成績を正常に取得できる
2. ✅ 新規選手（ファビアン、西川史礁など）がCSVに含まれている
3. ✅ 指標計算が正常に完了し、`_data/master_csv_calculated/` に出力されている
4. ✅ ランキングページに新規選手が表示されている
5. ✅ `fact_check_npb_official.mjs` で不足選手が0件になっている

## 次のステップ（将来の拡張）

- 定期実行の自動化（cron jobなど）
- 変更検知機能（新規選手の自動検出）
- 複数年度の一括スクレイピング
- 投手成績のスクレイピング対応
