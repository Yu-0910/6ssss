# Yahoo Topics 記事抽出問題 - 調査レポート

## 概要

Yahoo Topics Sports RSSフィード（`https://news.yahoo.co.jp/rss/topics/sports.xml`）から取得した記事について、元記事URL（`hochi.news`、`sanspo.com` など）の抽出ができず、`allowedDomains` フィルタによりすべての記事が除外されている問題。

**現状**: `itemsLength: 8` の記事が取得できているが、`finalArticleCount: 0` となり、すべての記事がフィルタで除外されている。

---

## 問題の詳細

### 1. Yahoo Topics RSSの構造

- Yahoo Topics RSSの `item.link` は `https://news.yahoo.co.jp/pickup/6566669?source=rss` 形式
- このURLはYahooの中間ページ（pickupページ）で、実際の元記事URLは含まれていない
- RSSには元記事URLの情報が含まれていないため、記事ページのHTMLから抽出する必要がある

### 2. デバッグ情報からの判明事項

`/api/articles?debug=1` の `yahooDebug` から以下の状況が確認できた：

```json
{
  "itemIndex": 1,
  "itemLink": "https://news.yahoo.co.jp/pickup/6566669?source=rss",
  "resolvedOriginalUrl": null,
  "publisherHost": null,
  "debugInfo": {
    "fetch": {
      "ok": true,
      "status": 200,
      "finalUrl": "https://news.yahoo.co.jp/pickup/6566669?source=rss",
      "contentType": "text/html;charset=UTF-8",
      "bytes": 144216
    },
    "hasNextData": false,
    "candidates": {
      "html": [],
      "jsonld": [],
      "nextData": [],
      "raw": []
    },
    "chosenBy": "none"
  }
}
```

**重要なポイント**:
- HTMLの取得は成功（`status: 200`, `bytes: 144216`）
- `hasNextData: false` - `__NEXT_DATA__` スクリプトタグが存在しない
- すべての抽出レイヤーで候補が0件（`candidates` がすべて空配列）
- 最終的に `chosenBy: "none"` となり、URL抽出に失敗

---

## 実施した解決策と失敗理由

### 解決策1: HTMLリンクからの抽出

**実装内容**:
- `extractAllowedUrlsFromHtml()` 関数を実装
- HTML内の `<a href="...">` タグから `allowedDomains` に一致するURLを抽出
- 正規表現で直書きURLも検索

**結果**: ❌ 失敗

**理由**:
- Yahoo Topics の pickup ページ（`/pickup/...`）には、元記事URLへのリンクがHTMLに含まれていない、または別の形式で埋め込まれている可能性がある
- `candidates.html: []` となり、抽出できなかった

---

### 解決策2: JSON-LDからの抽出

**実装内容**:
- `extractJsonLdBlocks()` で `<script type="application/ld+json">` を抽出
- `tryFindUrlInJsonLd()` でJSON-LDオブジェクト内の `url`, `mainEntityOfPage`, `sameAs` などを探索

**結果**: ❌ 失敗

**理由**:
- Yahoo Topics の pickup ページにはJSON-LDが存在しない、または元記事URL情報が含まれていない
- `candidates.jsonld: []` となり、抽出できなかった

---

### 解決策3: `__NEXT_DATA__` スクリプトからの抽出

**実装内容**:
- `extractNextDataJson()` で `<script id="__NEXT_DATA__">` を抽出
- `findAllowedUrlsInObject()` でJSONオブジェクトを再帰探索（深さ制限12）
- 通常URL、JSONエスケープURL、URLエンコードされたURLをすべて検索

**結果**: ❌ 失敗

**理由**:
- `hasNextData: false` となり、`__NEXT_DATA__` スクリプトタグが存在しない
- Yahoo Topics の pickup ページはNext.jsベースではない、または別の実装方式を使用している可能性がある

---

### 解決策4: HTML全文からの強制抽出

**実装内容**:
- `findAllowedUrlsInRawText()` でHTML全文を対象に正規表現で探索
- 正規URL、JSONエスケープURL（`\/`）、URLエンコード（`%3A%2F%2F`）をすべて検索
- `allowedDomains` に一致するURLパターンを網羅的に抽出

**結果**: ❌ 失敗

**理由**:
- `candidates.raw: []` となり、HTML全文からも候補が見つからなかった
- 元記事URLがHTMLに埋め込まれていない、またはJavaScriptで動的に生成されている可能性がある

---

### 解決策5: `publisherHost` によるフォールバック

**実装内容**:
- `resolveYahooOriginalInfo()` が `originalUrl` を返せない場合でも、`publisherHost` を抽出するように拡張
- `extractAllowedHostsFromHtml()` でHTMLからホスト名を抽出
- `publisherNameToHost()` で媒体名からホスト名をマッピング
- `publisherHost` が `allowedDomains` に一致すれば、Yahoo URLを採用して記事を表示

**結果**: ❌ 失敗

**理由**:
- `publisherHost: null` となり、ホスト名の抽出にも失敗
- HTML内に元記事のドメイン情報が含まれていない、または別の形式で埋め込まれている

---

## 現状の技術的な問題点

### 1. Yahoo Topics の pickup ページの構造

- `https://news.yahoo.co.jp/pickup/6566669?source=rss` は中間ページで、実際の記事ページ（`/articles/...`）へのリダイレクトを含まない可能性がある
- HTMLの144KBは取得できているが、元記事URL情報が含まれていない

### 2. 抽出ロジックの限界

- 現在実装されている4つの抽出レイヤー（HTMLリンク、JSON-LD、`__NEXT_DATA__`、raw全文）すべてで候補が見つからない
- これは、元記事URLがこれらの方法では抽出できない形式で埋め込まれていることを示唆している

### 3. デバッグ情報の有用性

- `yahooDebug` を実装したことで、問題の原因を特定できるようになった
- `fetch.ok: true` だが `candidates` がすべて空であることが判明し、HTMLは取得できているがURL抽出ができていないことが明確になった

---

## 今後の対応方向性

### オプション1: 記事ページURLへのリダイレクト確認

- `https://news.yahoo.co.jp/pickup/6566669?source=rss` にアクセスした際、実際の記事ページ（`/articles/...`）にリダイレクトされるかを確認
- リダイレクトする場合は、`fetch` の `redirect: "follow"` で最終URLを取得できるか確認
- 現状では `finalUrl` が `https://news.yahoo.co.jp/pickup/6566669?source=rss` のままなので、リダイレクトが発生していない可能性がある

### オプション2: JavaScriptで生成されるURLの確認

- Yahoo Topics の pickup ページがJavaScriptで動的に元記事URLを生成している可能性
- この場合、HTMLパースだけでは抽出できず、ヘッドレスブラウザ（Puppeteerなど）が必要になる可能性がある
- ただし、これはパフォーマンスと複雑性のトレードオフがある

### オプション3: RSS URLパターンの変更

- Yahoo Topics RSSのURLパターンを変更して、実際の記事ページ（`/articles/...`）を直接取得できるか確認
- `comments` フィールドに `/articles/...` 形式のURLが含まれている可能性がある（`https://news.yahoo.co.jp/articles/ba177603464f87cd28e1e868f6090f99892171aa/comments`）
- この `/articles/...` ページから元記事URLを抽出できる可能性がある

### オプション4: Google News RSSに戻す

- 現在は `disabled: true` になっているが、Google News RSS（`site:hochi.news`、`site:sanspo.com`）を使用する方法がある
- Google News RSSは `<source url="https://hochi.news">` などの情報を含むため、元記事URLの抽出が比較的容易
- ただし、過去の問題（画像の取得など）があったため、慎重に検討する必要がある

---

## 結論

Yahoo Topics Sports RSSから元記事URLを抽出する試みは、4つの異なる抽出レイヤーを実装したが、すべて失敗した。HTMLは正常に取得できているが（`status: 200`, `bytes: 144216`）、元記事URL情報がHTMLに含まれていないか、JavaScriptで動的に生成されている可能性が高い。

`yahooDebug` を実装したことで、問題の原因を特定できるようになったが、現時点では技術的な解決策が見つかっていない。

次のステップとして、`/articles/...` 形式の記事ページから直接抽出を試みるか、Google News RSSに戻すことを検討する必要がある。








