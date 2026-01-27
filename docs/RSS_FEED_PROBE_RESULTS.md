# RSSフィードプローブ結果

## 調査日時
2026年1月17日

## 調査対象

### 1. Number Web（プロ野球）
- **状態**: URLを特定中
- **一般的なパターンをテスト**: すべて404
  - `https://number.bunshun.jp/feed/pro-baseball`
  - `https://number.bunshun.jp/rss/pro-baseball`
  - `https://number.bunshun.jp/feed/baseball`
  - `https://number.bunshun.jp/rss/baseball`
  - `https://number.bunshun.jp/list/feed/pro-baseball`
  - `https://number.bunshun.jp/list/rss/pro-baseball`
- **次のアクション**: 
  - Number WebのRSS案内ページ（https://number.bunshun.jp/list/feed）をブラウザで確認
  - 「プロ野球」カテゴリのリンク先URLを特定

### 2. スポーツ報知
- **状態**: 候補URLすべて404
- **テストしたURL**:
  - `https://hochi.news/rss/` → 404
  - `https://hochi.news/rss.xml` → 404
  - `https://hochi.news/feed` → 404
  - `https://hochi.news/feed.xml` → 404
  - `https://hochi.news/atom.xml` → 404
  - `https://hochi.news/rss/sports.xml` → 404
  - `https://hochi.news/rss/baseball.xml` → 404
- **結論**: 公式RSSフィードが見つかりませんでした
- **次のアクション**: 
  - サイトマップやメタタグを確認
  - 別の方法を検討

### 3. サンケイスポーツ
- **状態**: 候補URLすべて404
- **テストしたURL**:
  - `https://www.sanspo.com/rss/` → 404
  - `https://www.sanspo.com/rss.xml` → 404
  - `https://www.sanspo.com/feed` → 404
  - `https://www.sanspo.com/feed.xml` → 404
  - `https://www.sanspo.com/atom.xml` → 404
  - `https://www.sanspo.com/rss/sports.xml` → 404
  - `https://www.sanspo.com/rss/baseball.xml` → 404
- **結論**: 公式RSSフィードが見つかりませんでした
- **次のアクション**: 
  - サイトマップやメタタグを確認
  - 別の方法を検討

## プローブスクリプト

### `scripts/probe_feed_urls.mjs`
- 候補URLの配列をテスト
- HTTPステータス、Content-Type、先頭200文字を確認
- `<rss`または`<feed`を含む場合に「RSS/Atom」と判定
- 結果をJSON形式で出力

### 使い方
```bash
node scripts/probe_feed_urls.mjs
```

## 次のステップ

1. **Number WebのRSS URLを手動で確認**
   - https://number.bunshun.jp/list/feed をブラウザで開く
   - 「プロ野球」カテゴリのリンク先URLを確認
   - `config/rss_feeds.json`に追加

2. **スポーツ報知・サンケイスポーツ**
   - 公式RSSが見つからない場合は、代替案を検討
   - サイトマップやメタタグの確認
   - 非公式フィードの検討









