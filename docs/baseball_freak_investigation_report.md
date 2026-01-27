# baseball-freak.com 記事取得可能性調査レポート

## 調査概要

**調査日**: 2026年1月19日  
**対象URL**: https://baseball-freak.com/  
**目的**: プロ野球ニュース記事の取得可能性を調査

## 調査結果サマリー

| 項目 | 結果 | 詳細 |
|------|------|------|
| RSSフィード | ❌ 不可 | RSSフィードは存在しない |
| HTMLパース | ✅ 可能 | ニュースセクション、記事リンク、ソースタグが存在 |
| API | ❌ 不可 | APIエンドポイントは存在しない |
| SSL/TLS | ✅ 正常 | 接続問題なし |

## 詳細調査結果

### 1. RSSフィードの存在確認

**調査したURL**:
- `https://baseball-freak.com/rss.xml`
- `https://baseball-freak.com/feed.xml`
- `https://baseball-freak.com/feed`
- `https://baseball-freak.com/rss`
- `https://baseball-freak.com/news/rss.xml`
- `https://baseball-freak.com/news/feed.xml`

**結果**: ❌ すべての候補でRSSフィードが見つからなかった

**影響**: RSSフィードによる取得は不可能。HTMLパースに依存する必要がある。

### 2. HTML構造の調査

**取得結果**:
- ✅ HTML取得成功: 53,388 bytes
- ✅ Content-Type: `text/html; charset=UTF-8`
- ✅ ニュースセクション: 存在確認
- ✅ 記事リンク数: 111個
- ✅ 日付構造: 存在確認（例: `01月19日`）
- ✅ ソースタグ数: 11個

**ソースタグの例**:
- 【スポーツ報知】
- 【日刊スポーツ】
- 【サンスポ】
- 【スポニチ】
- 【ロッテ】

**記事リンク抽出テスト**:
- 抽出された記事リンク数: 8個
- サンプルリンク:
  - `https://www.nikkansports.com/baseball/news/202601190000948.html`
  - `http://www.sponichi.co.jp/baseball/news/2026/01/19/kiji/20260119s00001173236000c.html`
  - `https://hochi.news/articles/20260119-OHT1T51194.html`
  - `http://www.sanspo.com//article/20260119-WQT5XVXWTZKFPIKRAWEYWTZKFPIKRAWEYFV27XY/`

**ソース-リンクペアの例**:
```
【スポーツ報知】 -> https://www.nikkansports.com/baseball/news/202601190000948.html
【日刊スポーツ】 -> http://www.sanspo.com//article/20260119-WQT5XVXWTZKFPIKRAWEYFV27XY/
【サンスポ】 -> http://www.sponichi.co.jp/baseball/news/2026/01/19/kiji/20260119s00001173236000c.html
【スポニチ】 -> https://full-count.jp/2026/01/19/post1892872/
```

**重要な発見**:
- ✅ **HTMLに直接元記事URLが含まれている**（中間ページを経由しない）
- ✅ **ソースタグとリンクの関連性が明確**
- ✅ **複数のメディア（報知、日刊スポーツ、サンスポ、スポニチなど）の記事が含まれている**

### 3. SSL/TLS接続の確認

**結果**: ✅ 正常

- 接続成功: HTTP 200
- SSL/TLSエラーなし
- dmenuのようなレガシーリネゴシエーション問題は発生しない

### 4. APIエンドポイントの探索

**調査したURL**:
- `https://baseball-freak.com/api/news`
- `https://baseball-freak.com/api/articles`
- `https://baseball-freak.com/api/v1/news`
- `https://baseball-freak.com/news.json`
- `https://baseball-freak.com/articles.json`

**結果**: ❌ すべての候補でAPIエンドポイントが見つからなかった

## これまでの失敗例との比較

### Yahoo! Topics との比較

| 項目 | Yahoo! Topics | baseball-freak.com |
|------|---------------|-------------------|
| 中間ページ | ✅ あり（pickup URL） | ❌ なし（直接リンク） |
| 元記事URL抽出 | ❌ 困難（2段階リダイレクト） | ✅ 容易（HTMLに直接含まれる） |
| HTMLパース | ❌ 失敗（URL抽出不可） | ✅ 成功（URL抽出可能） |
| リスク | 高（複雑なリダイレクト） | 中（HTML構造の変更） |

**結論**: baseball-freak.comはYahoo! Topicsよりも取得が容易。中間ページを経由せず、HTMLに直接元記事URLが含まれている。

### Google News との比較

| 項目 | Google News | baseball-freak.com |
|------|-------------|-------------------|
| HTML構造の変更 | ⚠️ 頻繁 | ⚠️ 可能性あり |
| URL抽出パターン | ❌ 複雑（複数パターン必要） | ✅ シンプル（`<a href>`タグ） |
| JavaScript依存 | ⚠️ 高い可能性 | ⚠️ 可能性あり |
| リスク | 高（構造変更に弱い） | 中（構造変更に弱い） |

**結論**: baseball-freak.comはGoogle Newsよりも取得が容易。URL抽出パターンがシンプルで、`<a href>`タグから直接抽出できる。

### dmenu との比較

| 項目 | dmenu | baseball-freak.com |
|------|-------|-------------------|
| SSL/TLS問題 | ❌ レガシーリネゴシエーションエラー | ✅ 問題なし |
| 接続方法 | ❌ 直接接続不可 | ✅ 直接接続可能 |
| プロキシ必要 | ✅ 必要（Cloudflare Workers） | ❌ 不要 |
| リスク | 高（SSL/TLS問題） | 低（標準的なHTTPS） |

**結論**: baseball-freak.comはdmenuよりも取得が容易。SSL/TLS問題がなく、標準的なHTTPS接続で取得できる。

## 実装可能性の評価

### ✅ 実装可能な理由

1. **HTMLに直接元記事URLが含まれている**
   - 中間ページを経由する必要がない
   - Yahoo! Topicsのような2段階リダイレクトは不要

2. **ソースタグとリンクの関連性が明確**
   - 【スポーツ報知】などのソースタグの直後にリンクが存在
   - 正規表現で抽出可能

3. **SSL/TLS問題なし**
   - 標準的なHTTPS接続で取得可能
   - dmenuのような特殊な対応は不要

4. **複数のメディアの記事が含まれている**
   - 報知、日刊スポーツ、サンスポ、スポニチなど
   - 1つのソースから複数のメディアの記事を取得可能

### ⚠️ リスクと注意点

1. **HTML構造の変更に弱い**
   - Google Newsと同様に、HTML構造が変更されると抽出ロジックが無効化される可能性
   - 定期的なメンテナンスが必要

2. **JavaScriptで動的生成される可能性**
   - 現在はHTMLに直接含まれているが、将来的にJavaScriptで動的生成される可能性
   - その場合、ヘッドレスブラウザ（Puppeteerなど）が必要になる

3. **RSSフィードが存在しない**
   - RSSフィードによる取得は不可能
   - HTMLパースに完全に依存する必要がある

## 推奨される実装方法

### 方法1: HTMLパース（推奨）

**実装手順**:
1. `https://baseball-freak.com/` にGETリクエスト
2. HTMLを取得
3. 正規表現でソースタグ（【...】）とリンクを抽出
4. ソースタグとリンクのペアを作成
5. 各リンクから記事情報を取得

**実装例**:
```typescript
// ソースタグとリンクの抽出
const sourceLinkPattern = /【([^】]+)】[^<]*<a[^>]+href=["']([^"']+)["'][^>]*>/g
const matches = html.matchAll(sourceLinkPattern)

const articles = []
for (const match of matches) {
  const source = match[1]
  const link = match[2]
  articles.push({
    source,
    url: link,
  })
}
```

**メリット**:
- 実装がシンプル
- 中間ページを経由しないため、高速
- SSL/TLS問題なし

**デメリット**:
- HTML構造の変更に弱い
- JavaScriptで動的生成される場合に対応できない

### 方法2: ヘッドレスブラウザ（将来の対応）

HTML構造が変更されたり、JavaScriptで動的生成されるようになった場合の対応。

**実装手順**:
1. Puppeteerでページを読み込む
2. JavaScriptの実行を待つ
3. DOMから記事リンクを抽出

**メリット**:
- JavaScriptで動的生成されるコンテンツにも対応可能

**デメリット**:
- 実装が複雑
- パフォーマンスが低下（JavaScript実行が必要）
- リソース消費が大きい

## 実装の優先順位

1. **Phase 1: HTMLパース実装**（最優先）
   - シンプルな実装で開始
   - 現在のHTML構造に基づいて実装

2. **Phase 2: エラーハンドリング強化**
   - HTML構造の変更を検出
   - フォールバック処理の実装

3. **Phase 3: ヘッドレスブラウザ対応**（必要に応じて）
   - HTMLパースが失敗した場合のフォールバック
   - JavaScriptで動的生成される場合の対応

## 結論

### ✅ 実装可能

baseball-freak.comからの記事取得は**実装可能**です。

**理由**:
1. HTMLに直接元記事URLが含まれている（中間ページ不要）
2. ソースタグとリンクの関連性が明確
3. SSL/TLS問題なし
4. 複数のメディアの記事が1つのソースから取得可能

**リスク**:
- HTML構造の変更に弱い（中リスク）
- JavaScriptで動的生成される可能性（中リスク）

**推奨**:
- まずはHTMLパースで実装を開始
- 定期的なメンテナンスとエラーハンドリングを実装
- 必要に応じてヘッドレスブラウザ対応を検討

## 次のステップ

1. **HTMLパース実装の開始**
   - `app/lib/baseballFreak.ts` モジュールの作成
   - ソースタグとリンクの抽出ロジックの実装

2. **テストと検証**
   - 実際のHTMLから記事を抽出できるか確認
   - エラーハンドリングのテスト

3. **統合**
   - `app/api/articles/route.ts` に統合
   - 既存のRSSフィードと並行して動作

---

**レポート作成日**: 2026年1月19日  
**調査ツール**: `scripts/probe_baseball_freak.mjs`







