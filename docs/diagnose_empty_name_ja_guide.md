# player_name_jaが空の原因診断ガイド

## 目的

「同年度・同球団の中で、一部選手だけ player_name_ja が空になる」原因を、最短で A/B/C のどれかに切り分ける。

## 原因候補

- **A**: 段階5（apply_roman_to_master_csvs.py）が「辞書の空 name_ja」で元CSVの player_name_ja を無条件上書きして消している
- **B**: 段階2（build_player_name_kana_and_official_roman.py）で選手ページHTML取得に失敗 or パース失敗して、辞書側 name_ja が空
- **C**: 段階3（build_player_id_to_roman_full.py）の最適行選択が、結果的に name_ja 空の行を採用している

## 診断手順

### 0) 対象player_idを拾う

UIで名前が空になっている選手を1人選び、player_id を控える。

または、CSVファイルから直接探す：

```bash
# 空の選手を探す（PowerShell）
Select-String -Path "_data/master_csv_calculated/batting_2025_PL_from_master.csv" -Pattern '^[^,]*,[^,]*,[^,]*,[^,]*,,' | Select-Object -First 5
```

### 1) 診断スクリプトを実行

```bash
python scripts/diagnose_empty_name_ja.py <player_id> [year] [league]
```

例：
```bash
python scripts/diagnose_empty_name_ja.py 21423824 1988 CL
```

### 2) 結果の解釈

#### 原因B（取得/パース失敗）の場合

- `http_status` が 200以外
- `outcome` が FAILED/ERROR系
- `http_status=200` なのに `name_ja` が空

**対処**: 段階2のスクレイピングを再実行するか、HTMLキャッシュを確認

#### 原因C（段階3の選択ロジック）の場合

- 段階2には `name_ja` があるのに、段階3で空になっている
- 同一player_idで複数行があり、「name_jaが入ってる行」も存在する

**対処**: `build_player_id_to_roman_full.py` の選択ロジックを確認・修正

#### 原因A（段階5の上書き事故）の場合

- 元CSVに `player_name_ja` が入っていたのに、適用後に空になっている

**対処**: `apply_roman_to_master_csvs.py` を修正

**修正案**:
```python
# player_name_jaを上書きする際、空の場合は元の値を維持
if name_ja and name_ja.strip():
    row['player_name_ja'] = name_ja
# 空の場合は上書きしない（元の値を維持）
```

## 注意事項

現在の `apply_roman_to_master_csvs.py` を確認したところ、`player_name_ja` を上書きする処理は見当たりません。`player_name_en`（romanName）のみを更新しています。

もし `player_name_ja` が空になる問題が発生している場合、別のスクリプトが原因の可能性があります。

## 関連ファイル

- `output/master/player_id_name_kana_official.csv`: 段階2の生データ
- `output/master/player_id_to_roman_full.csv`: 段階3の最終辞書
- `_data/master_csv/batting_YYYY_{CL|PL}_from_master.csv`: 元CSV
- `_data/master_csv_calculated/batting_YYYY_{CL|PL}_from_master.csv`: 適用後CSV




