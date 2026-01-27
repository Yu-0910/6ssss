# スポーツ報知記事取得問題 - 原因と解決策レポート

## 概要

スポーツ報知（hochi.news）の記事をRSSフィード経由で取得する際に発生した問題と、それに対する解決策の試行錯誤をまとめたレポートです。

**作成日**: 2026年1月18日  
**対象サイト**: https://hochi.news  
**目的**: スポーツ報知のプロ野球記事をRSS経由で自動取得し、表示する

---

## 1. 問題の本質

### 1.1 初期の問題認識

スポーツ報知は**公式RSSフィードを提供していない**（404エラー）。そのため、公式RSS経由での記事取得は不可能。

```
https://hochi.news/sports/baseball/rss.xml → 404 Not Found
```

### 1.2 代替手段の必要性

公式RSSが存在しないため、以下の代替手段を検討：

1. **Yahoo!ニュースRSS経由** - Yahoo!ニュースがhochi.newsの記事を転載している可能性
2. **Google News RSS経由** - Google News検索結果のRSSフィードを使用

---

## 2. 試行した解決策と問題点

### 2.1 解決策1: Yahoo!ニュースRSS経由での取得

#### 2.1.1 実装内容

Yahoo!ニュースのスポーツRSSフィードから、スポーツ報知の記事のみを抽出する方法を試行。

- **RSS URL**: `https://news.yahoo.co.jp/rss/categories/sports.xml`
- **フィルタリング方法**: キーワードフィルタ（「報知」「スポーツ報知」を含む記事のみ）

#### 2.1.2 失敗理由

1. **Yahoo!ニュースRSSには元のソースURLが含まれない**
   - RSS項目の`<link>`要素は常にYahoo!ニュースのURL（`https://news.yahoo.co.jp/...`）を指す
   - 元記事のURL（`https://hochi.news/...`）がRSS内に存在しない
   - そのため、ドメインフィルタリング（`allowedDomains`）が不可能

2. **キーワードフィルタは無効**
   - 記事のタイトルや説明文に「報知」「スポーツ報知」という文字列は**通常含まれない**
   - 野球記事の内容に「報知」というメディア名が含まれることはない
   - キーワードマッチングでは正しく抽出できない

#### 2.1.3 結論

Yahoo!ニュースRSSから特定メディアの記事を抽出するのは**技術的に不可能**。

---

### 2.2 解決策2: Google News RSS経由での取得

#### 2.2.1 実装内容

Google Newsの検索結果RSSフィードを使用し、`site:hochi.news`クエリでスポーツ報知の記事のみを検索。

- **RSS URL**: 
  ```
  https://news.google.com/rss/search?q=site%3Ahochi.news%20(%E3%83%97%E3%83%AD%E9%87%8E%E7%90%83%20OR%20NPB%20OR%20%E9%87%8E%E7%90%83)&hl=ja&gl=JP&ceid=JP:ja
  ```
  - `site:hochi.news` - hochi.newsドメインのみを検索
  - `(プロ野球 OR NPB OR 野球)` - キーワードで野球記事に絞り込み

- **フィルタリング方法**: `allowedDomains: ["hochi.news"]`でドメインフィルタリング

#### 2.2.2 Google News RSSの構造

Google News RSSは以下の構造を持つ：

```xml
<item>
  <title>記事タイトル</title>
  <link>https://news.google.com/articles/...</link>
  <source url="https://hochi.news">スポーツ報知</source>
  <pubDate>...</pubDate>
</item>
```

**重要なポイント**:
- `<source>`要素に元記事のURL（`url="https://hochi.news"`）と名前（`スポーツ報知`）が含まれる
- `<link>`要素はGoogle NewsのリダイレクトURL（元記事URLではない）

#### 2.2.3 実装時の課題と解決策

##### 課題1: `rss-parser`が`<source>`要素を正しくパースしない

**問題**:
- `rss-parser`ライブラリがGoogle News RSSの`<source>`要素を標準的な方法でパースしない
- `item.source`が`undefined`または不正確な値になる

**解決策**:
- `fast-xml-parser`を使用してGoogle News RSSを直接XMLパース
- `<source>`要素から`url`属性とテキスト内容を明示的に抽出

```typescript
function parseGoogleNewsRss(xmlContent: string): Array<{
  title: string
  link: string
  pubDate: string
  sourceUrl?: string
  sourceName?: string
}> {
  const parser = new XMLParser({
    ignoreAttributes: false,
    attributeNamePrefix: '@_',
  })
  
  const feed = parser.parse(xmlContent)
  const items = feed.rss?.channel?.item || []
  
  return items.map((item: any) => ({
    title: item.title || '',
    link: item.link || '',
    pubDate: item.pubDate || '',
    sourceUrl: item.source?.['@_url'],  // <source url="...">
    sourceName: item.source?.['#text'] || item.source,  // <source>テキスト内容
  }))
}
```

##### 課題2: ドメインフィルタリングの実装

**実装**:
- `item.sourceUrl`を優先的に使用（存在しない場合は`item.link`を使用）
- `allowedDomains`配列に含まれるドメインのみを許可

```typescript
if (feedConfig.allowedDomains && feedConfig.allowedDomains.length > 0) {
  const targetUrl = item.sourceUrl || item.link  // sourceUrlを優先
  const domain = new URL(targetUrl).hostname
  const isAllowed = feedConfig.allowedDomains.some(allowedDomain => {
    return domain === allowedDomain || domain.endsWith(`.${allowedDomain}`)
  })
  if (!isAllowed) {
    continue  // フィルタリング
  }
}
```

##### 課題3: ネットワークエラーとリトライ機構

**問題**:
- Google News RSSの取得が失敗することがある
- タイムアウトや一時的なネットワークエラー

**解決策**:
- `fetchWithRetry`関数を実装
  - 最大2回リトライ
  - 指数バックオフ（500ms → 1500ms）
  - カスタムヘッダー（User-Agent、Accept）
  - 15秒のタイムアウト

---

### 2.3 解決策3: デバッグ機能の追加

#### 2.3.1 API側デバッグモード

**実装**:
- `/api/articles?debug=1`で詳細なデバッグ情報を取得可能

**デバッグ情報の内容**:
- 各フィードの取得ステータス（HTTPステータス、Content-Type）
- パースされたアイテム数
- 最初のアイテムの構造（`sourceUrl`、`sourceName`の有無）
- ドメインフィルタリング前後の記事数
- 最終的に取得された記事数

#### 2.3.2 クライアント側デバッグ

**実装**:
- `ArticlesListClient.tsx`にクライアント側デバッグログを追加
- ソース別の記事数集計
- ドメイン別の記事数集計

---

## 3. 現在の実装状況

### 3.1 RSSフィード設定

`config/rss_feeds.json`:

```json
{
  "name": "スポーツ報知（Google News経由）",
  "url": "https://news.google.com/rss/search?q=site%3Ahochi.news%20(...)",
  "enabled": true,
  "allowedDomains": ["hochi.news"]
}
```

### 3.2 実装の流れ

1. **RSS取得**
   - `fetchWithRetry`でGoogle News RSSを取得
   - タイムアウト15秒、最大2回リトライ

2. **パース**
   - Google News RSSの場合: `fast-xml-parser`で直接XMLパース
   - 通常RSSの場合: `rss-parser`を使用

3. **フィルタリング**
   - `allowedDomains`が指定されている場合、`item.sourceUrl`をチェック
   - ドメインが一致するもののみを採用

4. **記事データの正規化**
   - `source`: フィード名を使用（「スポーツ報知（Google News経由）」）
   - `sourceUrl`: 元記事のURL（`hochi.news/...`）
   - `sourceName`: ソース名（「スポーツ報知」）

---

## 4. 今後の課題と改善案

### 4.1 潜在的な問題点

1. **Google News RSSの依存**
   - Google Newsのサービス変更や仕様変更の影響を受ける可能性
   - レート制限やアクセス制限の可能性

2. **`sourceUrl`の信頼性**
   - Google News RSSの`<source>`要素の構造が変更される可能性
   - XMLパースが失敗する可能性

3. **記事数の制限**
   - Google News RSSは最新の記事のみを返す（通常20-30件程度）
   - 過去の記事取得には不向き

### 4.2 改善案

1. **フォールバック機構の強化**
   - Google News RSSが失敗した場合の代替手段を検討
   - キャッシュ期間の調整

2. **モニタリングとアラート**
   - 記事取得失敗率の監視
   - 自動通知機能

3. **データの信頼性向上**
   - 複数のソースからの取得（例: Google News + Yahoo! News）
   - データの重複排除と検証

---

## 5. まとめ

### 5.1 解決できたこと

- ✅ スポーツ報知の記事をGoogle News RSS経由で取得できるようになった
- ✅ ドメインフィルタリングにより、hochi.newsの記事のみを正確に抽出
- ✅ デバッグ機能により、問題の診断が容易になった

### 5.2 解決できなかったこと

- ❌ 公式RSSフィードの提供（hochi.news側の問題）
- ❌ Yahoo!ニュースRSSからの抽出（技術的に不可能）

### 5.3 結論

**現在の実装（Google News RSS経由）は、公式RSSが存在しない状況での最適解**と考えられる。

ただし、Google Newsのサービスに依存するため、長期的には以下のリスクがある：

1. Google Newsの仕様変更
2. レート制限やアクセス制限
3. サービス終了の可能性（低いがゼロではない）

これらのリスクを考慮し、定期的なモニタリングとフォールバック計画の検討を推奨する。

---

## 参考資料

### 実装ファイル

- `config/rss_feeds.json` - RSSフィード設定
- `app/api/articles/route.ts` - 記事取得API（RSSパース、フィルタリング）
- `app/components/ArticlesListClient.tsx` - クライアント側コンポーネント

### 使用ライブラリ

- `rss-parser` (v3.13.0) - 通常RSSフィードのパース
- `fast-xml-parser` (v5.3.3) - Google News RSSの直接XMLパース

### Google News RSSのドキュメント

- [Google News RSS Search](https://news.google.com/rss)








