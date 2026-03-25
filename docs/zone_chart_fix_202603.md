# ゾーンチャート取得の不具合修正（2026/3）

## 事象

2表2番 前川 右京の安打がコース別成績の図に反映されていない。

## 原因

1. **チャートの選択**: 一球速報ページにはコース図が2つある。
   - `#nxt_batt` 内の簡易図（次の打者セクション）
   - 「詳しい投球内容」セクション内の図（投球テーブル直上）
   
   従来は「詳しい投球内容」を含む**最初の**テーブルからチャートを取得していたが、ページ構造によっては誤ったチャートを参照する可能性があった。

2. **pitch_no の不一致**: チャート内のボール番号と投球テーブルの番号が一致しない場合がある。
   - チャート: 打席内番号（1, 2, 3...）
   - 投球数列: 試合通算番号（10, 11, 12...）の場合あり
   
   `pitch_no in zone_by_pitch` が常に成立するとは限らず、zone が取得できず空になるケースがあった。

## 修正内容

### scrape_yahoo_pitch_details.py

1. **チャート選択の改善**
   - 投球テーブル（球種・球速・結果）と同じ `bb-splits__item` セクション内の `allocationChartBg` を優先して使用
   - 投球リスト直上＝下側の図を確実に参照するように変更

2. **pitch_no マッチングのフォールバック**
   - `pitch_no` でマッチしない場合、行インデックス（1, 2, 3...）で再試行
   - チャートが打席内番号を使う場合に正しく対応

## 再発防止

- ゾーン取得ロジックのコメントを追加（2つのチャートの存在を明記）
- チャートは必ず投球テーブルと同じセクション内のものを使用
- pitch_no と row_index の両方で zone マッチを試行

## 検証方法

```bash
# 2表2番のHTMLを取得してパース確認
python scripts/fetch_pitcher_zone_stats.py --game-id 2021040084 --pitcher-id 2103788 --save-debug

# zone が取得できているか確認（2表2番 前川 中安 = zone 12 想定）
# debug_pitches JSON で zone_id が空でないことを確認
```

## 補足

- 前川の安打は zone 12（中央やや内角）に分類。zone 10（外角・中高め）との混同に注意。
- vsLeft（対左打者）の zone 12 に集計される。名簿で「前川 右京」が左打者として照合されていることを確認。

---

## 追記: 前川の安打が図に反映されない問題（別原因）

### 原因

`is_settlement_result()` が「中安」「左安」「右安」を決着球として認識していなかった。

- 「中安[詰り、バット折れる...]」→ `安打` を含まないため `is_settlement_result` が False
- 決着球でないと判断され、zone 集計から除外されていた

### 修正

`fetch_pitcher_zone_stats.py` および `reaggregate_from_debug.mjs` の `is_settlement_result` に以下を追加:

```python
if re.match(r"^(左安|右安|中安)", s):
    return True
```

### 再集計

```bash
python scripts/fetch_pitcher_zone_stats.py --game-id 2021040084 --pitcher-id 2103788 --from-debug
# または
node scripts/reaggregate_from_debug.mjs
```
