# auone.jp 記事の画像読み込み問題 - 原因と修正レポート

## 問題の概要

auone.jpから取得した記事の画像が読み込めない問題が発生していました。

**症状**: 
- すべてのauone記事で `image: '/placeholder.svg'` が設定されている
- 実際の画像が表示されない

## 原因の調査

### 調査結果

1. **auone.jpの記事ページにはOGP画像が存在する**
   - `og:image` メタタグが存在
   - 例: `https://portal.st-img.jp/thumb/cbb20cc2fcf81e681ad12b0383fa4438_1768815815_l.jpg`

2. **現在の実装では画像URLを取得していない**
   - `app/api/articles/route.ts` で `image: '/placeholder.svg'` とハードコードされている
   - 各記事ページからOGP画像を取得する処理が実装されていない

### HTML構造の確認

auone.jpの記事ページ（`https://article.auone.jp/detail/1/6/10/...`）には以下のメタタグが存在：

```html
<meta property="og:image" content="https://portal.st-img.jp/thumb/..._l.jpg">
<meta name="twitter:image" content="https://portal.st-img.jp/thumb/..._l.jpg">
```

## 修正内容

### 実装した解決策

1. **`fetchOGPImage` 関数を使用してOGP画像を取得**
   - 既存の `fetchOGPImage` 関数を活用
   - auone.jpの記事URLからOGP画像を取得

2. **並列処理で効率化**
   - 5件ずつバッチ処理で並列実行
   - リソース消費を抑制しつつ、処理速度を向上

3. **エラーハンドリング**
   - 画像取得に失敗した場合は `/placeholder.svg` をフォールバック
   - エラーが発生しても記事取得処理は継続

### 実装コード

```typescript
// auoneのAuoneArticleをArticle型に変換
const auoneArticlesPromises = auoneResult.articles.map(async (item) => {
  // ... 日付処理 ...

  // 画像URLを取得（auone.jpの記事ページからOGP画像を取得）
  let imageUrl = '/placeholder.svg'
  try {
    const ogpImage = await fetchOGPImage(item.url, 8000)
    if (ogpImage && ogpImage !== '/placeholder.svg') {
      imageUrl = ogpImage
    }
  } catch (error) {
    // 画像取得エラーは無視（placeholderのまま）
  }

  return {
    id: `auone-${item.url}`,
    title: item.title,
    date: dateStr,
    source: item.source || 'auone.jp',
    image: imageUrl, // OGP画像URLまたはplaceholder
    link: item.url,
    publishedAt: item.publishedAt,
  }
})

// 並列処理を実行（5件ずつバッチ処理）
const auoneArticles: Article[] = []
const batchSize = 5
for (let i = 0; i < auoneArticlesPromises.length; i += batchSize) {
  const batch = auoneArticlesPromises.slice(i, i + batchSize)
  const batchResults = await Promise.all(batch)
  auoneArticles.push(...batchResults)
}
```

## 期待される結果

修正後、以下のようになることが期待されます：

1. **画像URLが正しく取得される**
   - `image` フィールドが `https://portal.st-img.jp/thumb/..._l.jpg` 形式のURLになる
   - `/placeholder.svg` ではなく、実際の画像URLが設定される

2. **画像が表示される**
   - フロントエンドで画像が正しく表示される
   - OGP画像が読み込まれる

3. **パフォーマンス**
   - 並列処理により、複数の記事の画像を効率的に取得
   - タイムアウト（8秒）内に取得できない場合はplaceholderにフォールバック

## 確認方法

1. **開発サーバーを再起動**
   ```bash
   npm run dev
   ```

2. **APIエンドポイントにアクセス**
   ```
   http://localhost:3000/api/articles?debug=1
   ```

3. **確認ポイント**
   - `articles` 配列内のauone記事（`id` が `auone-` で始まる）の `image` フィールドを確認
   - `image` が `/placeholder.svg` 以外のURLになっているか確認
   - 画像URLが `https://portal.st-img.jp/thumb/...` 形式になっているか確認

4. **フロントエンドで確認**
   - ブラウザで `http://localhost:3000` にアクセス
   - auone記事の画像が正しく表示されているか確認

## トラブルシューティング

### 問題1: 画像が依然として `/placeholder.svg` のまま

**原因**:
- `fetchOGPImage` がタイムアウトしている
- OGP画像が存在しない記事がある
- ネットワークエラーが発生している

**確認方法**:
- サーバーログで `[API] OGP image found for auone article` が表示されているか確認
- エラーログで `Failed to fetch OGP image` が表示されていないか確認

**解決策**:
- タイムアウト時間を延長（8秒 → 10秒）
- エラーハンドリングを強化

### 問題2: 画像取得が遅い

**原因**:
- 並列処理のバッチサイズが小さい
- ネットワークが遅い

**解決策**:
- バッチサイズを調整（5件 → 10件）
- キャッシュを活用

### 問題3: 一部の記事で画像が取得できない

**原因**:
- その記事ページにOGP画像が設定されていない
- HTML構造が異なる

**解決策**:
- エラーログを確認
- 該当記事のHTML構造を調査

## 今後の改善

1. **キャッシュの追加**
   - 取得した画像URLをキャッシュして、同じ記事の再取得を高速化

2. **画像URLの検証**
   - 取得した画像URLが実際にアクセス可能か確認
   - 404エラーの場合はplaceholderにフォールバック

3. **デバッグ情報の追加**
   - 画像取得の成功率を記録
   - `auoneDebug` に画像取得情報を追加

---

**レポート作成日**: 2026年1月19日  
**修正ファイル**: `app/api/articles/route.ts`  
**調査ツール**: `scripts/debug_auone_article.mjs`







