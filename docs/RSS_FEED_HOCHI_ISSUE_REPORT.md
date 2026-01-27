# スポーツ報知の記事取得問題 - 調査レポート

## 問題の概要

「最新情報」セクションに、スポーツ報知（hochi.news）の記事が表示されない。

## 経緯

### Phase 1: Yahoo!ニュースRSS経由での取得（失敗）

**目的**: Yahoo!ニュースのスポーツカテゴリRSSから、報知の記事のみを抽出して表示する。

**実装内容**:
- `config/rss_feeds.json`に「スポーツ報知（Yahoo経由）」フィードを追加
  - URL: `https://news.yahoo.co.jp/rss/categories/sports.xml`
  - `allowedDomains: ["hochi.news"]`でフィルタリングを試みる

**問題点**:
1. Yahoo!ニュースRSSの`item.link`は全て`news.yahoo.co.jp/articles/...`形式
   - 元記事のドメイン（`hochi.news`）がURLに含まれない
   - `allowedDomains`フィルタが機能しない

**対処法**:
- キーワードフィルタに変更（`allowedKeywords: ["報知", "スポーツ報知"]`）
  - タイトルや説明文に「報知」が含まれる記事のみを取得

**失敗理由**:
- 実際の記事タイトルや説明文には「報知」や「スポーツ報知」という文字列が含まれない
  - 例: 「巨人・山本由伸が...」のようなタイトルのみ
  - キーワードフィルタは無効

**結論**: Yahoo!ニュースRSSから媒体別抽出は不可能と判断し、アプローチを変更。

---

### Phase 2: Google News RSS経由での取得（進行中・未解決）

**目的**: Google Newsの検索RSS機能（`site:hochi.news`）を使用して報知の記事のみを取得する。

**実装内容**:
- `config/rss_feeds.json`から「スポーツ報知（Yahoo経由）」を削除
- 「スポーツ報知（Google News経由）」フィードを追加
  - URL: `https://news.google.com/rss/search?q=site%3Ahochi.news%20(%E3%83%97%E3%83%AD%E9%87%8E%E7%90%83%20OR%20NPB%20OR%20%E9%87%8E%E7%90%83)&hl=ja&gl=JP&ceid=JP:ja`
  - `site:hochi.news`で検索範囲を制限
  - プロ野球関連のキーワードでフィルタリング

**期待される動作**:
- Google News RSSは`<source url="https://hochi.news">...</source>`要素を含む
- `item.source.url`から元記事のドメインを取得可能
- `allowedDomains`フィルタで`hochi.news`のみを通過させる

**実際の動作確認**:
- `curl`コマンドでRSSを確認した結果、`<source url="https://hochi.news">スポーツ報知</source>`要素は存在することを確認

**問題点**:
- 記事が表示されない（APIレスポンスに含まれていない可能性）

---

## 実施した対処法と失敗理由

### 対処法1: キーワードフィルタの無効化

**実装内容**:
- `app/api/articles/route.ts`からキーワードフィルタのロジックを削除
- コメントで無効化理由を明記

**理由**: 正しい対処だが、これだけでは報知の記事が表示されない問題は解決しない

---

### 対処法2: ドメインフィルタの修正（`item.source`対応）

**実装内容**:
```typescript
// Google News RSSの場合、item.linkは常にnews.google.comなので、item.sourceをチェック
const itemSource = (item as any).source
const itemSourceUrl = itemSource?.url || itemSource?.$.url || itemSource
```

**期待**: `item.source.url`から元記事のドメイン（`hochi.news`）を取得

**問題点**:
1. `customFields`に`source`を追加していなかった
   - rss-parserが`<source>`要素をパースしない可能性
2. `item.source`の構造が不明確
   - rss-parserがどのようにパースするか未確認

**追加実装**: `customFields: { item: ['enclosure', 'media:content', 'links', 'source'] }`
- `source`を追加したが、効果は未確認

---

### 対処法3: デバッグログの追加

**実装内容**:
- 最初のアイテムの構造をログ出力
- 報知の記事数カウント
- エラーログの詳細化

**目的**: 実際のAPIレスポンスで`item.source`がどのようにパースされているかを確認

**現状**: ログの確認が必要（未実施）

---

## 考えられる原因

### 原因1: `item.source`が正しくパースされていない

**可能性**:
- rss-parserが`<source>`要素をサポートしていない
- `customFields`の指定方法が間違っている
- Google News RSSのXML構造が特殊で、標準的なパース方法が機能しない

**確認方法**:
- 開発サーバーのログで`[API] First item structure for スポーツ報知（Google News経由）`を確認
- `source`プロパティが存在するか、どのような構造かを確認

---

### 原因2: RSSフィード自体がエラーを返している

**可能性**:
- Google News RSSのURLが無効
- タイムアウトエラー
- User-Agentによるブロック
- レート制限

**確認方法**:
- `[API] Feed X/Y (スポーツ報知（Google News経由）): FAILED`というエラーログを確認
- エラーメッセージの詳細を確認

---

### 原因3: フィルタリングが過剰に機能している

**可能性**:
- `allowedDomains`が設定されていないが、何らかの理由で記事がフィルタリングされている
- 現在の実装では`allowedDomains`が設定されていないため、フィルタリングは行われないはず

**確認方法**:
- `config/rss_feeds.json`で`allowedDomains`が設定されていないことを確認（✓確認済み）

---

### 原因4: RSSパーサーのバグまたは制限

**可能性**:
- rss-parserライブラリがGoogle News RSSの特殊な構造に対応していない
- `<source>`要素のパースがサポートされていない

**確認方法**:
- rss-parserのドキュメントで`<source>`要素のサポート状況を確認
- 生XMLを直接パースする必要がある可能性

---

## 現在の状況

### 実装済み
- ✅ Yahoo!ニュースRSSフィードの削除
- ✅ Google News RSSフィードの追加
- ✅ キーワードフィルタの無効化
- ✅ `customFields`に`source`を追加
- ✅ ドメインフィルタで`item.source`をチェックするロジック
- ✅ デバッグログの追加

### 未確認・未解決
- ❓ 実際にAPIが記事を取得できているか
- ❓ `item.source`が正しくパースされているか
- ❓ エラーが発生しているか
- ❓ 記事は取得できているが、何らかの理由でフィルタリングされているか

---

## 次のステップ（推奨）

### Step 1: ログの確認
1. 開発サーバーを起動
2. `http://localhost:3000/api/articles`にアクセス
3. ターミナルのログを確認:
   - `[API] Fetching RSS feed: スポーツ報知（Google News経由）`
   - `[API] RSS feed スポーツ報知（Google News経由）: X items found`
   - `[API] First item structure for スポーツ報知（Google News経由）`
   - `[API] Feed X/Y (スポーツ報知（Google News経由）): N articles`

### Step 2: エラーの確認
- `[API] Feed X/Y (スポーツ報知（Google News経由）): FAILED`が出ていないか
- エラーメッセージの詳細を確認

### Step 3: `item.source`の構造確認
- `[API] First item structure`のログで`source`プロパティの値を確認
- `item.source`が`undefined`の場合、rss-parserがサポートしていない可能性

### Step 4: 対処法の検討

#### ケースA: `item.source`がパースされていない場合
- 生XMLを直接パースして`<source>`要素を抽出
- または、rss-parserの設定を変更

#### ケースB: RSSフィードがエラーを返している場合
- URLの検証
- User-Agentの変更
- タイムアウト時間の延長

#### ケースC: 記事は取得できているが表示されない場合
- フロントエンド側の問題の可能性
- APIレスポンスを直接確認

---

## 技術的メモ

### Google News RSSの構造
```xml
<item>
  <title>記事タイトル</title>
  <link>https://news.google.com/rss/articles/...</link>
  <source url="https://hochi.news">スポーツ報知</source>
  ...
</item>
```

### rss-parserの`customFields`設定
```typescript
customFields: {
  item: ['enclosure', 'media:content', 'links', 'source'],
}
```

### `item.source`の想定構造（未確認）
- `item.source.url`: `"https://hochi.news"`
- `item.source.name`: `"スポーツ報知"`
- または単純な文字列: `"https://hochi.news"`

---

## 関連ファイル

- `app/api/articles/route.ts`: RSSフィード取得とパースのロジック
- `config/rss_feeds.json`: RSSフィードの設定
- `app/components/ArticlesListClient.tsx`: フロントエンドの記事表示コンポーネント

---

作成日: 2026年1月
最終更新: 2026年1月









