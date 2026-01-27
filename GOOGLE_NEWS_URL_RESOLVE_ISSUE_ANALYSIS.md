# Google News URL解決失敗の原因分析レポート

## 問題の状況

### 症状
- `resolveGoogleNewsPublisherUrl()` が常に `null` を返している
- すべてのフォールバックステップ（resolved-ogp, resolved-retry, google-news-fallback）で失敗
- エラー: `NO_ARTICLE_URL_EXTRACTED`

### デバッグ情報から判明したこと
- `urlResolve` 統計: `successCount: 0, failureCount: 10`
- すべてのGoogle News経由の記事でURL解決に失敗
- HTTP 200でHTMLは取得できているが、記事URLを抽出できない

---

## 原因分析

### 1. `resolveGoogleNewsPublisherUrl()` の処理フロー

```typescript
// app/lib/googleNewsResolve.ts の処理順序：

A) リダイレクト先チェック
   → finalUrl が news.google.com 以外かつ allowedDomains に一致するか

B) HTMLから候補抽出
   B-1) og:url メタタグ
   B-2) canonical リンク
   B-3) google.com/url?url=... パターン
   B-4) url=https%3A%2F%2F... パターン

C) batchexecute フォールバック（c-wiz[data-p]方式）
```

### 2. 考えられる原因

#### **原因1: Google NewsのHTML構造が変更された**

**可能性**: 高

**根拠**:
- すべての記事で同じエラーが発生している
- HTTP 200でHTMLは取得できているが、抽出パターンが機能していない
- 最近のGoogle Newsは、JavaScriptで動的にコンテンツを読み込むことが多い

**確認方法**:
- 実際のGoogle NewsページのHTMLを確認
- `og:url`、`canonical`、`google.com/url?url=` パターンが存在するか確認

**対策**:
- HTML構造に合わせて抽出パターンを更新
- 新しい抽出方法を追加（例: JSON-LD、data属性など）

---

#### **原因2: キャッシュに失敗結果が保存されている**

**可能性**: 中

**根拠**:
- 失敗時のキャッシュTTLは10秒に設定されているが、短時間の再試行では同じ結果になる可能性がある
- `resolved-retry` ステップでも `publisherUrl null` となっている

**確認方法**:
- キャッシュをクリアして再試行
- キャッシュキーとTTLを確認

**対策**:
- キャッシュをクリアする機能を追加
- 失敗時のキャッシュTTLをさらに短くする（5秒など）

---

#### **原因3: タイムアウトが発生している**

**可能性**: 低

**根拠**:
- タイムアウトは12秒に設定されている
- HTTP 200でHTMLは取得できているので、タイムアウトは発生していない可能性が高い

**確認方法**:
- サーバーログで `[Resolve] Timeout:` メッセージを確認
- `urlResolve` 統計の `timeoutCount` を確認

**対策**:
- タイムアウト時間を延長（15秒など）
- タイムアウト時のエラーハンドリングを改善

---

#### **原因4: `allowedDomains` のチェックが厳しすぎる**

**可能性**: 中

**根拠**:
- 候補URLは抽出できているが、`allowedDomains` とマッチしない可能性がある
- `normalizeDomain` や `isAllowedDomain` のロジックに問題がある可能性

**確認方法**:
- 抽出された候補URLをログ出力
- 各候補が `allowedDomains` とマッチするか確認

**対策**:
- `isAllowedDomain` のロジックを確認・修正
- ドメイン正規化のロジックを改善

---

#### **原因5: `fetchOGPImageDebug` の再帰処理が機能していない**

**可能性**: 高

**根拠**:
- `google-news-fallback` ステップで `NO_ARTICLE_URL_EXTRACTED` エラーが発生
- `fetchOGPImageDebug` 内の Google News URL からの抽出ロジックが機能していない

**確認方法**:
- `fetchOGPImageDebug` 内の抽出パターンを確認
- 実際のGoogle NewsページのHTMLを確認

**対策**:
- `fetchOGPImageDebug` の抽出パターンを更新
- より柔軟な抽出方法を追加

---

## 推奨される調査手順

### ステップ1: サーバーログの確認

開発サーバーのログで以下を確認：

```bash
[Resolve] Starting resolution for: ...
[Resolve] HTML length: ... bytes
[Resolve] Found og:url candidate: ...
[Resolve] Found canonical candidate: ...
[Resolve] Candidates found: ...
[Resolve] All candidates: [...]
[Resolve] Candidate: ... -> host: ..., matches: ...
[Resolve] No candidates extracted. HTML preview: ...
```

これにより、以下が判明します：
- HTMLは取得できているか
- 候補URLは抽出できているか
- `allowedDomains` チェックで弾かれているか

### ステップ2: 実際のGoogle NewsページのHTMLを確認

実際のGoogle News URLにアクセスして、HTML構造を確認：

```bash
curl -s "https://news.google.com/rss/articles/CBMiYkFVX3lxTE1meXlXUERDMEppZzhIUDdhWC03U1VXMUhkWmZvR2FrNzA0anMzZ3lhS3hJelFpajFkUWVCUF9JcTlZRXNHSHhYb3BTdG1Yekp6akFnTzdpaFk3VkR1QTFmaEl3?oc=5" \
  -H "User-Agent: Mozilla/5.0" | \
  grep -i "og:url\|canonical\|hochi.news\|sanspo.com"
```

### ステップ3: キャッシュの確認

キャッシュが原因の可能性がある場合：

```typescript
// キャッシュをクリア
clearResolveCache()
```

---

## 最も可能性の高い原因

### **Google NewsのHTML構造が変更された**

**理由**:
1. すべての記事で同じエラーが発生している
2. HTTP 200でHTMLは取得できているが、抽出パターンが機能していない
3. 最近のGoogle Newsは、JavaScriptで動的にコンテンツを読み込むことが多い

**確認方法**:
- 実際のGoogle NewsページのHTMLを確認
- `og:url`、`canonical`、`google.com/url?url=` パターンが存在するか確認

**対策**:
1. HTML構造に合わせて抽出パターンを更新
2. 新しい抽出方法を追加（例: JSON-LD、data属性など）
3. `batchexecute` フォールバックの成功率を向上させる

---

## 追加したデバッグログ

以下のデバッグログを追加しました：

### `resolveGoogleNewsPublisherUrl` 内
- 抽出された候補URLのリスト
- 各候補が `allowedDomains` とマッチするかどうか
- 候補が抽出されない場合、HTMLのプレビュー（最初の1000文字）

### `fetchOGPImageDebug` 内
- `og:url` や `canonical` が見つかったかどうか
- 記事URLパターンがマッチしたかどうか
- HTMLの長さと抽出結果

---

## 次のステップ

1. **サーバーログを確認**
   - 開発サーバーを再起動
   - `/api/articles?debug=1` にアクセス
   - サーバーログで `[Resolve]` と `[fetchOGPImageDebug]` のメッセージを確認

2. **実際のHTMLを確認**
   - 実際のGoogle News URLにアクセスしてHTML構造を確認
   - 抽出パターンが機能するか確認

3. **抽出パターンを更新**
   - HTML構造に合わせて抽出パターンを更新
   - 新しい抽出方法を追加

---

**レポート作成日**: 2026年1月18日  
**対象バージョン**: 現在の実装（`app/lib/googleNewsResolve.ts`, `app/api/articles/route.ts`）








