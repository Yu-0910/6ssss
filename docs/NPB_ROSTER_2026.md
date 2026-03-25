# 2026年NPB選手名簿

[NPB公示ページ](https://npb.jp/announcement/2026/) を基にした2026年支配下選手名簿。

## データ形式

`_data/npb_roster_2026.csv`

| 列 | 説明 |
|----|------|
| npb_player_id | NPB BISの選手ID |
| name_ja | 日本語名 |
| name_en | 英字名（BISページから取得） |
| team | 球団名 |
| team_code | アプリ用チームコード (H, G, S, D, C, DB, F, M, E, L, Bs, Hs) |
| position | ポジション |
| uniform_no | 背番号 |
| throw_hand | 投: R=右投, L=左投 |
| bat_hand | 打: R=右打, L=左打, B=両打 |
| is_new_2026 | 2026年新規支配下登録: 1=該当, 0=該当せず |

## 生成手順

```powershell
py scripts/build_npb_roster_2026.py
```

- 全785名の利き手取得のため約10〜15分
- 高速テスト時: `--skip-handedness` で名簿のみ取得

## データページでの利用

- **API**: `GET /api/roster/2026` … 名簿JSON
- **ライブラリ**: `lib/npbRoster.ts`
  - `getNpbRoster2026()` … 全選手
  - `getPlayerHandedness(nameJa)` … 日本語名から利き手
  - `getPlayerHandednessById(npbPlayerId)` … IDから利き手
  - `getNewPlayers2026()` … 新規登録選手のみ

## 新規選手の選手ページ

新規登録選手は `/players/選手名` でアクセス可能。  
ローマ字表示用に `playerRomanNames` へ追加する場合:

```powershell
py scripts/generate_new_players_roman_for_app.py
```

出力を `app/players/[playerId]/page.tsx` の `playerRomanNames` にマージしてください。
