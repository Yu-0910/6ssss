# article.auone.jp 記事取得可能性調査レポート

## 調査概要

**調査日**: 2026年1月19日  
**対象URL**: https://article.auone.jp/keyword/article/1  
**目的**: プロ野球ニュース記事の取得可能性を調査

## 調査結果サマリー

| 項目 | 結果 | 詳細 |
|------|------|------|
| RSSフィード | ❌ 不可 | RSSフィードは存在しない |
| HTMLパース | ✅ 可能 | 記事一覧セクション、記事リンク、日付構造が存在 |
| API | ❌ 不可 | APIエンドポイントは存在しない |
| SSL/TLS | ⚠️ 要確認 | HEADリクエストで問題あり（GETリクエストで再確認必要） |
| ページネーション | ✅ あり | 「さらに読み込む」形式（load-more） |

## 詳細調査結果

### 1. RSSフィードの存在確認

**調査したURL**:
- `https://article.auone.jp/rss.xml`
- `https://article.auone.jp/keyword/article/1/rss.xml`
- `https://article.auone.jp/keyword/article/1/feed.xml`
- `https://article.auone.jp/keyword/article/1/feed`
- `https://article.auone.jp/keyword/article/1/rss`
- `https://article.auone.jp/feed.xml`

**結果**: ❌ すべての候補でRSSフィードが見つからなかった

**影響**: RSSフィードによる取得は不可能。HTMLパースに依存する必要がある。

### 2. HTML構造の調査

**取得結果**:
- ✅ HTML取得成功: 59,604 bytes
- ✅ Content-Type: `text/html; charset=UTF-8`
- ✅ 記事一覧セクション: 存在確認
- ✅ 記事リンク数: 68個
- ✅ 日付構造: 存在確認（例: `01/19 18:38`）

**記事リンクの形式**:
```
https://article.auone.jp/detail/1/6/10/375_10_r_20260119_1768815638512002
https://article.auone.jp/detail/1/6/10/202_10_r_20260119_1768815527406072
```

**リストアイテムから抽出された記事情報の例**:
```
タイトル: 【巨人】則本昂大が入団会見「一生懸命、腕を振って頑張りたいなと思っています」
リンク: https://article.auone.jp/detail/1/6/10/202_10_r_20260119_1768815527406072
日付: 01/19 18:37
ソース: スポーツ報知
```

**重要な発見**:
- ✅ **HTMLに直接記事リンクが含まれている**（中間ページを経由しない）
- ✅ **タイトル、日付、ソースがHTMLに含まれている**
- ✅ **リストアイテム（`<li>`）から記事情報を抽出可能**
- ⚠️ **ページネーションが「さらに読み込む」形式**（JavaScriptで動的読み込みの可能性）

### 3. SSL/TLS接続の確認

**結果**: ⚠️ 要確認

- HEADリクエストで問題が発生した可能性
- 実際のGETリクエストでは正常に動作する可能性が高い
- 詳細な確認が必要

**推奨**: 実際のGETリクエストで再確認する

### 4. ページネーション

**結果**: ✅ 存在確認

- タイプ: `load-more`（「さらに読み込む」形式）
- JavaScriptで動的に記事を読み込む可能性が高い
- 初期HTMLには最初の25件程度の記事が含まれている

**影響**: 
- 初期HTMLからは限られた数の記事しか取得できない
- すべての記事を取得するには、JavaScript実行またはAPIエンドポイントの探索が必要

### 5. APIエンドポイントの探索

**調査したURL**:
- `https://article.auone.jp/api/news`
- `https://article.auone.jp/api/articles`
- `https://article.auone.jp/api/v1/news`
- `https://article.auone.jp/keyword/article/1.json`
- `https://article.auone.jp/keyword/article/1/api`

**結果**: ❌ すべての候補でAPIエンドポイントが見つからなかった

## これまでの失敗例との比較

### Yahoo! Topics との比較

| 項目 | Yahoo! Topics | auone.jp |
|------|---------------|----------|
| 中間ページ | ✅ あり（pickup URL） | ❌ なし（直接リンク） |
| 元記事URL抽出 | ❌ 困難（2段階リダイレクト） | ✅ 容易（HTMLに直接含まれる） |
| HTMLパース | ❌ 失敗（URL抽出不可） | ✅ 成功（URL抽出可能） |
| リスク | 高（複雑なリダイレクト） | 中（HTML構造の変更 + ページネーション） |

**結論**: auone.jpはYahoo! Topicsよりも取得が容易。中間ページを経由せず、HTMLに直接記事リンクが含まれている。

### Google News との比較

| 項目 | Google News | auone.jp |
|------|-------------|----------|
| HTML構造の変更 | ⚠️ 頻繁 | ⚠️ 可能性あり |
| URL抽出パターン | ❌ 複雑（複数パターン必要） | ✅ シンプル（`<li>`タグから抽出） |
| JavaScript依存 | ⚠️ 高い可能性 | ⚠️ ページネーションで必要 |
| リスク | 高（構造変更に弱い） | 中（構造変更 + ページネーション） |

**結論**: auone.jpはGoogle Newsよりも取得が容易。URL抽出パターンがシンプルで、`<li>`タグから直接抽出できる。ただし、ページネーション対応が必要。

### dmenu との比較

| 項目 | dmenu | auone.jp |
|------|-------|----------|
| SSL/TLS問題 | ❌ レガシーリネゴシエーションエラー | ⚠️ 要確認（GETリクエストで再確認必要） |
| 接続方法 | ❌ 直接接続不可 | ⚠️ 要確認 |
| プロキシ必要 | ✅ 必要（Cloudflare Workers） | ⚠️ 未確定 |
| リスク | 高（SSL/TLS問題） | 中（SSL/TLS要確認 + ページネーション） |

**結論**: auone.jpはdmenuよりも取得が容易な可能性が高い。ただし、SSL/TLS接続の詳細な確認が必要。

### baseball-freak.com との比較

| 項目 | baseball-freak.com | auone.jp |
|------|-------------------|----------|
| HTMLパース | ✅ 可能 | ✅ 可能 |
| ページネーション | ❌ なし | ✅ あり（load-more） |
| 記事リンク形式 | 外部サイトへの直接リンク | auone.jp内の記事ページ |
| リスク | 中（HTML構造の変更） | 中（HTML構造の変更 + ページネーション） |

**結論**: auone.jpはbaseball-freak.comと同様にHTMLパース可能だが、ページネーション対応が必要。また、記事リンクがauone.jp内のページであるため、元記事URLの抽出が必要になる可能性がある。

## 実装可能性の評価

### ✅ 実装可能な理由

1. **HTMLに直接記事リンクが含まれている**
   - 中間ページを経由する必要がない
   - Yahoo! Topicsのような2段階リダイレクトは不要

2. **リストアイテムから記事情報を抽出可能**
   - `<li>`タグからタイトル、リンク、日付、ソースを抽出可能
   - 正規表現またはDOMパースで抽出可能

3. **記事リンクの形式が規則的**
   - `https://article.auone.jp/detail/1/6/10/...` 形式
   - パターンマッチングで抽出可能

### ⚠️ リスクと注意点

1. **ページネーション対応が必要**
   - 「さらに読み込む」形式のページネーション
   - 初期HTMLには限られた数の記事しか含まれていない
   - すべての記事を取得するには、JavaScript実行またはAPIエンドポイントの探索が必要

2. **HTML構造の変更に弱い**
   - Google Newsと同様に、HTML構造が変更されると抽出ロジックが無効化される可能性
   - 定期的なメンテナンスが必要

3. **JavaScriptで動的生成される可能性**
   - ページネーションがJavaScriptで実装されている可能性
   - その場合、ヘッドレスブラウザ（Puppeteerなど）が必要になる

4. **元記事URLの抽出が必要**
   - 記事リンクがauone.jp内のページであるため、実際の元記事URLを抽出する必要がある可能性
   - 各記事ページから元記事URLを抽出する処理が必要

5. **SSL/TLS接続の確認が必要**
   - HEADリクエストで問題が発生した可能性
   - 実際のGETリクエストで再確認する必要がある

## 推奨される実装方法

### 方法1: HTMLパース（初期実装）

**実装手順**:
1. `https://article.auone.jp/keyword/article/1` にGETリクエスト
2. HTMLを取得
3. `<li>`タグから記事情報を抽出
4. タイトル、リンク、日付、ソースを抽出

**実装例**:
```typescript
// リストアイテムから記事情報を抽出
const listItemPattern = /<li[^>]*>([\s\S]*?)<\/li>/gi
const articles = []
let match

while ((match = listItemPattern.exec(html)) !== null) {
  const itemHtml = match[1]
  const linkMatch = itemHtml.match(/<a[^>]+href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/)
  
  if (linkMatch) {
    const link = linkMatch[1].startsWith('/') 
      ? `https://article.auone.jp${linkMatch[1]}`
      : linkMatch[1]
    const title = linkMatch[2].replace(/<[^>]+>/g, '').trim()
    const dateMatch = itemHtml.match(/(\d{2}\/\d{2}\s+\d{2}:\d{2})/)
    const sourceMatch = itemHtml.match(/([^\s]+)\s*$/)
    
    articles.push({
      title,
      url: link,
      date: dateMatch ? dateMatch[1] : null,
      source: sourceMatch ? sourceMatch[1] : null,
    })
  }
}
```

**メリット**:
- 実装がシンプル
- 中間ページを経由しないため、高速
- 初期HTMLから記事を取得可能

**デメリット**:
- ページネーション対応が必要（初期HTMLには限られた数の記事のみ）
- HTML構造の変更に弱い
- JavaScriptで動的生成される場合に対応できない

### 方法2: ページネーション対応

**実装手順**:
1. 初期HTMLから記事を取得
2. 「さらに読み込む」ボタンのクリックをシミュレート
3. 追加の記事を取得
4. 繰り返し

**実装例**:
```typescript
// ページネーション対応（ヘッドレスブラウザ使用）
const browser = await puppeteer.launch()
const page = await browser.newPage()
await page.goto('https://article.auone.jp/keyword/article/1')

// 初期記事を取得
let articles = await extractArticlesFromPage(page)

// 「さらに読み込む」ボタンをクリックして追加記事を取得
while (await page.$('さらに読み込む') !== null) {
  await page.click('さらに読み込む')
  await page.waitForTimeout(1000) // 読み込み待機
  const newArticles = await extractArticlesFromPage(page)
  articles.push(...newArticles)
}
```

**メリット**:
- すべての記事を取得可能
- JavaScriptで動的生成されるコンテンツにも対応可能

**デメリット**:
- 実装が複雑
- パフォーマンスが低下（JavaScript実行が必要）
- リソース消費が大きい

### 方法3: APIエンドポイントの探索（推奨）

**実装手順**:
1. ブラウザの開発者ツールでネットワークリクエストを監視
2. 「さらに読み込む」ボタンをクリック
3. 追加記事を取得するAPIエンドポイントを特定
4. そのAPIエンドポイントを直接呼び出す

**メリット**:
- 高速（HTMLパース不要）
- すべての記事を取得可能
- リソース消費が少ない

**デメリット**:
- APIエンドポイントの特定が必要
- 非公開APIの可能性（仕様変更のリスク）

## 実装の優先順位

1. **Phase 1: HTMLパース実装**（最優先）
   - シンプルな実装で開始
   - 初期HTMLから記事を取得
   - ページネーションは後回し

2. **Phase 2: ページネーション対応**
   - 初期HTMLから取得できる記事数が限られているため
   - ヘッドレスブラウザまたはAPIエンドポイントの探索

3. **Phase 3: 元記事URL抽出**
   - 各記事ページから元記事URLを抽出
   - 実際のメディアサイト（報知、日刊スポーツなど）へのリンクを取得

4. **Phase 4: エラーハンドリング強化**
   - HTML構造の変更を検出
   - フォールバック処理の実装

## 結論

### ✅ 実装可能（条件付き）

article.auone.jpからの記事取得は**実装可能**ですが、以下の条件があります：

**条件**:
1. SSL/TLS接続の詳細な確認が必要（GETリクエストで再確認）
2. ページネーション対応が必要（初期HTMLには限られた数の記事のみ）
3. 元記事URL抽出が必要（auone.jp内のページから実際のメディアサイトへのリンクを取得）

**理由**:
1. HTMLに直接記事リンクが含まれている（中間ページ不要）
2. リストアイテムから記事情報を抽出可能
3. 記事リンクの形式が規則的

**リスク**:
- HTML構造の変更に弱い（中リスク）
- JavaScriptで動的生成される可能性（中リスク）
- ページネーション対応が必要（中リスク）
- SSL/TLS接続の確認が必要（中リスク）

**推奨**:
- まずはHTMLパースで実装を開始（初期HTMLから取得できる記事のみ）
- SSL/TLS接続を詳細に確認
- ページネーション対応を検討（必要に応じて）
- 元記事URL抽出を実装

## 次のステップ

1. **SSL/TLS接続の詳細確認**
   - 実際のGETリクエストで接続を確認
   - エラーが発生する場合は、dmenuと同様の対応を検討

2. **HTMLパース実装の開始**
   - `app/lib/auone.ts` モジュールの作成
   - リストアイテムから記事情報を抽出するロジックの実装

3. **ページネーション対応の検討**
   - ブラウザの開発者ツールでAPIエンドポイントを探索
   - または、ヘッドレスブラウザでの実装を検討

4. **元記事URL抽出の実装**
   - 各記事ページから元記事URLを抽出
   - 実際のメディアサイトへのリンクを取得

---

**レポート作成日**: 2026年1月19日  
**調査ツール**: `scripts/probe_auone.mjs`  
**参考URL**: https://article.auone.jp/keyword/article/1







