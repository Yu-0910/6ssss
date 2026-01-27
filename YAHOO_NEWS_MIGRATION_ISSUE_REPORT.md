# Yahoo!ニュース移行問題レポート

## 1. 概要

Google News経由で取得していたサンケイスポーツとスポーツ報知の記事を、Yahoo!ニュースに切り替えたが、記事が表示されない問題が発生した。

## 2. 背景

### 2.1 初期状態
- **サンケイスポーツ**: Google News RSS経由で取得（`site:sanspo.com` でフィルタリング）
- **スポーツ報知**: Google News RSS経由で取得（`site:hochi.news` でフィルタリング）
- 両方とも正常に動作していた

### 2.2 変更要求
Google NewsからYahoo!ニュースへの移行を実施。

## 3. 実施した変更

### 3.1 設定ファイルの変更（`config/rss_feeds.json`）

**変更前:**
```json
{
  "name": "スポーツ報知（Google News経由）",
  "enabled": true,
  "allowedDomains": ["hochi.news"]
},
{
  "name": "サンケイスポーツ（Google News経由）",
  "enabled": true,
  "allowedDomains": ["www.sanspo.com", "sanspo.com"]
},
{
  "name": "Yahoo Topics Sports",
  "type": "yahoo_topics",
  "enabled": false,
  "disabled": true,
  "allowedDomains": ["hochi.news", "sanspo.com", "www.sanspo.com"]
}
```

**変更後:**
```json
{
  "name": "スポーツ報知（Google News経由）",
  "enabled": false,
  "disabled": true,
  "allowedDomains": ["hochi.news"]
},
{
  "name": "サンケイスポーツ（Google News経由）",
  "enabled": false,
  "disabled": true,
  "allowedDomains": ["www.sanspo.com", "sanspo.com"]
},
{
  "name": "Yahoo Topics Sports",
  "type": "yahoo_topics",
  "enabled": true,
  "allowedDomains": ["hochi.news", "sanspo.com", "www.sanspo.com"]
}
```

### 3.2 技術的な変更点

1. **Google Newsフィードの無効化**
   - `enabled: false`, `disabled: true` に変更

2. **Yahoo Topicsフィードの有効化**
   - `enabled: true` に変更
   - `disabled` プロパティを削除

3. **既存のYahoo Topics処理ロジックの活用**
   - `app/lib/yahooResolve.ts` の `resolveYahooOriginalUrl` 関数を使用
   - `app/api/articles/route.ts` のYahoo Topics処理フローを使用

## 4. 発生した問題

### 4.1 症状
- **Number Web**: 正常に取得・表示されている
- **サンケイスポーツ**: 表示されない
- **スポーツ報知**: 表示されない
- **日刊スポーツ**: 正常に取得・表示されている（Google Newsではない）

### 4.2 影響範囲
- Yahoo Topics Sportsフィードから取得されるべき記事が表示されない
- 他のRSSフィード（Number Web、日刊スポーツ）は正常に動作

## 5. 問題分析

### 5.1 Yahoo Topics処理フロー

Yahoo Topics RSSの処理は以下のフローで実施されている：

```
1. RSSフィード取得
   ↓
2. rss-parserでパース → parsedItems配列を生成
   ↓
3. 各アイテムをループ処理
   ↓
4. resolveYahooOriginalUrl() でYahoo記事ページから元記事URLを抽出
   ↓
5. resolvedUrl が null の場合 → 記事をスキップ（continue）
   ↓
6. resolvedUrl が取得できた場合 → ドメインフィルタリング
   ↓
7. allowedDomains に一致する場合のみ記事として追加
```

### 5.2 記事がスキップされる原因

`app/api/articles/route.ts` の1433-1442行目で以下のロジックが実装されている：

```typescript
// Yahoo Topics RSSで解決前のURL（news.yahoo.co.jp）はスキップ
if (isYahooTopics && checkDomain.includes('yahoo.co.jp') && !resolvedUrl) {
  // resolvedUrlが取得できない場合は記事をスキップ（元記事URLが特定できないため）
  console.warn(`[API] Article ${itemIndex + 1} (Yahoo Topics): No resolvedUrl, skipping`)
  continue
}
```

**問題点:**
- `resolveYahooOriginalUrl()` が `null` を返すと、記事がスキップされる
- Yahoo記事ページ（`news.yahoo.co.jp`）から元記事URL（`hochi.news`、`sanspo.com`）を抽出できていない可能性が高い

### 5.3 resolveYahooOriginalUrl() の実装

`app/lib/yahooResolve.ts` では以下の方法でURL抽出を試みている：

1. **HTMLリンクからの抽出** (`extractAllowedUrlsFromHtml`)
   - `<a href="...">` から `allowedDomains` に一致するURLを抽出
   - 正規表現で直接URLを検索

2. **JSON-LDからの抽出** (`extractJsonLdBlocks` → `tryFindUrlInJsonLd`)
   - `<script type="application/ld+json">` から構造化データを抽出
   - `url`, `mainEntityOfPage`, `isBasedOn`, `sameAs` などをチェック

**考えられる失敗原因:**
- Yahoo記事ページのHTML構造が変更されている
- 元記事URLへのリンクが期待される形式ではない
- JSON-LDに元記事URLが含まれていない
- `allowedDomains` のドメイン判定ロジックに問題がある

## 6. 実施した解決策と結果

### 6.1 解決策1: デバッグログの強化

**実施内容:**
- `resolveYahooOriginalUrl()` に詳細なデバッグログを追加
  - 開始時のURLとallowedDomainsをログ出力
  - HTML取得後の長さをログ出力
  - HTMLリンクから抽出したURL数をログ出力
  - JSON-LDブロック数をログ出力
  - 解決成功/失敗時の詳細をログ出力

**変更ファイル:**
- `app/lib/yahooResolve.ts`

**期待された効果:**
- どの段階で失敗しているかを特定できる
- 実際に取得されているHTMLの内容を確認できる

**結果:**
- デバッグログは追加されたが、実際の動作確認まで至っていない
- **状況は変わらず**（ユーザー報告）

### 6.2 解決策2: Yahoo Topics処理フローのデバッグログ追加

**実施内容:**
- `app/api/articles/route.ts` のYahoo Topics処理部分にログを追加
  - RSSパース後のアイテム数をログ出力
  - 処理開始時のアイテム数とallowedDomainsをログ出力
  - 各アイテム処理時の詳細をログ出力

**期待された効果:**
- Yahoo Topics RSSから記事が取得できているかを確認できる
- `resolveYahooOriginalUrl()` が呼ばれているかを確認できる

**結果:**
- デバッグログは追加されたが、実際の動作確認まで至っていない
- **状況は変わらず**（ユーザー報告）

### 6.3 解決策がうまくいかなかった理由

1. **根本原因が特定できていない**
   - デバッグログを追加したが、実際のログ出力を確認していない
   - サーバーログや `/api/articles?debug=1` の結果を分析していない

2. **Yahoo記事ページのHTML構造への理解不足**
   - 実際のYahoo記事ページのHTML構造を確認していない
   - 元記事URLがどのように埋め込まれているかを調査していない

3. **段階的な検証が不足**
   - Yahoo RSSから記事が取得できているか（パース段階）
   - `resolveYahooOriginalUrl()` が呼ばれているか
   - `resolveYahooOriginalUrl()` がどのURLを返しているか
   といった段階的な検証を行っていない

## 7. 想定される原因

### 7.1 最も可能性が高い原因

**`resolveYahooOriginalUrl()` が `null` を返している**

- Yahoo記事ページ（`news.yahoo.co.jp`）から元記事URLを抽出できていない
- HTML構造が想定と異なる可能性
- `extractAllowedUrlsFromHtml()` または `tryFindUrlInJsonLd()` が期待通りに動作していない

### 7.2 その他の可能性

1. **Yahoo RSSフィードの取得・パースに問題**
   - RSSフィード自体が取得できていない
   - `rss-parser` でパースできていない
   - `parsedItems` 配列が空

2. **ドメインフィルタリングで除外されている**
   - `resolvedUrl` は取得できているが、`allowedDomains` の判定で除外されている
   - ドメイン正規化の問題（例: `www.sanspo.com` vs `sanspo.com`）

3. **タイムアウトやネットワークエラー**
   - Yahoo記事ページの取得に失敗している
   - タイムアウトが短すぎる

## 8. 次のステップ（推奨される調査方法）

### 8.1 サーバーログの確認

以下のログを確認し、どの段階で問題が発生しているかを特定する：

```
[API] Yahoo Topics RSS: Parsed X items
[API] Yahoo Topics: Starting to process X parsed items
[YahooResolve] Starting resolution for: ...
[YahooResolve] Found X allowed URLs from HTML links: ...
[YahooResolve] Failed to resolve: ...
[API] Article X (Yahoo Topics): No resolvedUrl, skipping
```

### 8.2 デバッグAPIエンドポイントの確認

`/api/articles?debug=1` にアクセスし、以下の情報を確認：

- `fetchOk`: RSSフィードの取得が成功しているか
- `itemsLength`: パースされたアイテム数
- `finalArticleCount`: 最終的に記事として追加された数
- `firstItemKeys`: 最初のアイテムの構造

### 8.3 実際のYahoo記事ページの調査

実際のYahoo記事ページ（`news.yahoo.co.jp/...`）を確認し、以下を調査：

1. **HTML内のリンク構造**
   - `<a href="...">` で元記事URLへのリンクが存在するか
   - どのような形式で埋め込まれているか

2. **JSON-LDの構造**
   - `<script type="application/ld+json">` に元記事URLが含まれているか
   - どのプロパティに含まれているか

3. **URL抽出ロジックの検証**
   - `extractAllowedUrlsFromHtml()` が正しく動作するか
   - `tryFindUrlInJsonLd()` が正しく動作するか

### 8.4 代替案の検討

1. **Google Newsに戻す**
   - 一時的な回避策として、Google Newsに戻す
   - ただし、Google Newsの画像取得問題が解決していない可能性がある

2. **Yahoo Topics RSSの直接フィルタリング**
   - RSSフィードのタイトルや説明文に「報知」「サンケイ」が含まれる記事のみを抽出
   - ただし、誤判定の可能性がある

3. **別のRSSソースの検討**
   - 報知やサンケイスポーツの公式RSS（存在する場合）
   - 他のニュースアグリゲーター

## 9. 技術的な詳細

### 9.1 Yahoo Topics処理のコードフロー

**ファイル: `app/api/articles/route.ts`**

1. **RSS判定** (989行目)
   ```typescript
   const isYahooTopics = feedConfig.type === 'yahoo_topics' || feedConfig.url.includes('yahoo.co.jp/rss')
   ```

2. **RSSパース** (1093-1198行目)
   - 通常のRSSパーサーでパース
   - `parsedItems` 配列を生成

3. **URL解決** (1272-1297行目)
   ```typescript
   resolvedUrl = await resolveYahooOriginalUrl(item.link, allowedDomains, debugMode)
   ```

4. **ドメインチェック** (1433-1442行目)
   ```typescript
   if (isYahooTopics && checkDomain.includes('yahoo.co.jp') && !resolvedUrl) {
     continue  // 記事をスキップ
   }
   ```

### 9.2 resolveYahooOriginalUrl() の実装詳細

**ファイル: `app/lib/yahooResolve.ts`**

1. **HTML取得** (78-89行目)
   - Yahoo記事ページをGET
   - HTMLを取得

2. **HTMLリンク抽出** (91-94行目)
   ```typescript
   const allowedUrls = extractAllowedUrlsFromHtml(html, allowedDomains)
   if (allowedUrls.length > 0) return allowedUrls[0]
   ```

3. **JSON-LD抽出** (96-113行目)
   ```typescript
   const blocks = extractJsonLdBlocks(html)
   for (const b of blocks) {
     const parsed = JSON.parse(b)
     const u = tryFindUrlInJsonLd(parsed, allowedDomains)
     if (u) return u
   }
   ```

4. **失敗時** (115行目)
   ```typescript
   return null
   ```

## 10. まとめ

### 10.1 現在の状況

- Yahoo!ニュースに切り替えたが、サンケイスポーツと報知の記事が表示されない
- デバッグログは追加したが、実際のログ出力を確認していない
- 根本原因は特定できていない

### 10.2 最も可能性の高い原因

`resolveYahooOriginalUrl()` が `null` を返し、記事がスキップされている可能性が高い。

### 10.3 必要な作業

1. **サーバーログの確認** - どの段階で失敗しているかを特定
2. **デバッグAPIの確認** - RSSパース結果を確認
3. **実際のYahoo記事ページの調査** - HTML構造を確認
4. **段階的な検証** - 各処理段階で問題がないか確認

### 10.4 今後の方針

サーバーログとデバッグ情報を確認し、具体的な失敗箇所を特定してから、適切な修正を行う必要がある。








