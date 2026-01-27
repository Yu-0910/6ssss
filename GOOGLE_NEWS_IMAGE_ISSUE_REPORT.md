# Google News経由記事の画像読み込み問題 - 調査レポート

## 1. 現在の問題状況

### 症状
- Google News経由で取得した記事（サンケイスポーツ、スポーツ報知など）の画像が正常に読み込まれない
- 画像が `/placeholder.svg` として表示される

### 影響範囲
- サンケイスポーツ（Google News経由）
- スポーツ報知（Google News経由）
- その他、Google News RSS経由で取得される記事

---

## 2. 画像取得プロセスの各ステップと問題点

### プロセス全体の流れ

```
1. Google News RSS フィード取得
   ↓
2. item.link (Google News URL) を resolveGoogleNewsPublisherUrl() で解決
   ↓
3. resolvedUrl (元記事URL) が取得できた場合
   ↓
4. fetchOGPImage(resolvedUrl) でOGP画像を取得
   ↓
5. 画像URLを記事データに設定
```

### 各ステップでの問題点

#### **ステップ2: URL解決 (`resolveGoogleNewsPublisherUrl`)**

**実装箇所**: `app/lib/googleNewsResolve.ts`

**処理内容**:
1. キャッシュチェック（6時間TTL）
2. Google News URLにHTTPリクエスト（リダイレクト追従）
3. HTMLから元記事URLを抽出:
   - `og:url` メタタグ
   - `canonical` リンク
   - `google.com/url?url=` パラメータ
   - `url=` パラメータ（URLエンコード済み）
4. フォールバック: BatchExecute API（c-wiz[data-p]方式）

**潜在的な問題点**:
- **タイムアウト**: `RESOLVE_TIMEOUT_MS = 8000ms`（8秒）でタイムアウトする可能性
- **Google側の変更**: Google NewsのHTML構造が変更され、URL抽出パターンが無効化される可能性
- **BatchExecute API**: フォールバック処理が失敗する可能性
- **キャッシュ**: 失敗した結果が1分間キャッシュされ、再試行が抑制される

**確認方法**:
```typescript
// デバッグログで確認
[Resolve] Starting resolution for: ...
[Resolve] Resolved: ... -> ...
// または
[Resolve] Failed to resolve: ...
```

#### **ステップ3-4: 画像取得 (`fetchOGPImage`)**

**実装箇所**: `app/api/articles/route.ts` (941-997行目)

**処理内容**:
1. `resolvedUrl` が存在する場合のみ `fetchOGPImage()` を呼び出す
2. `resolvedUrl` が `null` の場合は画像取得をスキップ（`/placeholder.svg` のまま）

**問題点**:
- **`resolvedUrl` が `null` の場合、画像取得を完全にスキップしている**（988-997行目）
  ```typescript
  if (resolvedUrl) {
    // 画像取得処理
  } else {
    // 画像取得をスキップ → placeholderのまま
    console.warn(`[API] Resolved URL not available for article ${itemIndex + 1}, skipping OGP fetch from Google News URL`)
  }
  ```
- この設計により、URL解決に失敗した場合、画像が取得されない

**`fetchOGPImage` 関数の処理**:
1. HTML取得（タイムアウト: デフォルト5秒、呼び出し時8秒）
2. Google News URL検出時は再帰的に元記事URLを抽出
3. `og:image` または `twitter:image` メタタグから画像URLを抽出
4. 失敗時は `/placeholder.svg` を返す

**潜在的な問題点**:
- **タイムアウト**: 8秒でタイムアウトする可能性
- **OGPメタタグの欠如**: 元記事ページに `og:image` が設定されていない可能性
- **CORS/アクセス制限**: 一部のサイトがボットアクセスをブロックしている可能性
- **再帰処理の失敗**: Google News URLから元記事URLを抽出できない場合

---

## 3. 以前に行った解決策と失敗理由

### 解決策1: Google News URLから直接OGP画像を取得（初期実装）

**実装内容**:
- Google News URL（`item.link`）を直接 `fetchOGPImage()` に渡す
- Google NewsページのHTMLから `og:image` を抽出

**失敗理由**:
- **Google Newsページの `og:image` はGoogle Newsのロゴ画像**を返すため、記事の実際の画像が取得できない
- 結果として、すべての記事で同じGoogle Newsロゴが表示される

**対応**: この方法は廃止され、元記事URLを解決してから画像を取得する方式に変更

---

### 解決策2: `fetchOGPImage` 内でGoogle News URLを検出して元記事URLを抽出

**実装内容** (`app/api/articles/route.ts` 142-256行目):
- `fetchOGPImage()` 関数内で、Google News URL（`news.google.com`）を検出
- HTMLから `og:url`、`canonical`、記事URLパターンを抽出
- 抽出した元記事URLに対して再帰的に `fetchOGPImage()` を呼び出し

**失敗理由**:
- **再帰処理が複雑で、エラーハンドリングが不十分**
- Google NewsページのHTML構造が変更されると、URL抽出パターンが無効化される
- **タイムアウトが発生しやすい**（Google Newsページ取得 + 元記事ページ取得の2段階）
- デバッグが困難（どの段階で失敗したか特定しにくい）

**対応**: この方法は残されているが、優先度は低い（フォールバックとして機能）

---

### 解決策3: `resolveGoogleNewsPublisherUrl` でURL解決してから画像取得

**実装内容** (現在の実装):
1. `resolveGoogleNewsPublisherUrl()` でGoogle News URL → 元記事URLに解決
2. 解決された `resolvedUrl` から `fetchOGPImage()` で画像を取得

**問題点**:
- **`resolvedUrl` が `null` の場合、画像取得を完全にスキップしている**
- URL解決の成功率が低い場合、多くの記事で画像が取得されない
- URL解決と画像取得が分離されているため、URL解決に失敗すると画像取得の機会が失われる

**現在の実装の問題箇所**:
```988:997:app/api/articles/route.ts
} else {
  // 2) resolvedUrlが取得できなかった場合のフォールバック（最終保険）
  // Google News URLでOGPを取得するとGoogleロゴになる可能性があるため、原則として避ける
  if (process.env.NODE_ENV === 'development' || debugMode) {
    if (itemIndex < 3 || (debugMode && itemIndex === 0)) {
      console.warn(`[API] Resolved URL not available for article ${itemIndex + 1}, skipping OGP fetch from Google News URL`)
    }
  }
  // ❌ 問題: placeholderのまま（Google News URLからOGPを取得しない）
  // これにより、URL解決に失敗した場合、画像取得の機会が完全に失われる
}
```

**問題の詳細**:
- `resolvedUrl` が `null` の場合、`fetchOGPImage()` が呼ばれない
- `fetchOGPImage()` 関数内には、Google News URLを検出して元記事URLを抽出する再帰処理が実装されているが、それが実行されない
- 結果として、URL解決に失敗した記事は必ず `/placeholder.svg` が表示される

---

### 解決策4: `resolveGoogleNewsPublisherUrl` の汎用化

**実装内容**:
- 以前は `hochi.news` にハードコードされていた
- `allowedDomains` パラメータを受け取る汎用関数に変更

**結果**:
- サンケイスポーツなど、他のドメインでも動作するようになった
- しかし、**URL解決の成功率自体は改善されていない**

---

### 解決策5: BatchExecute API フォールバック

**実装内容** (`app/lib/googleNewsResolve.ts` 389-403行目):
- URL解決に失敗した場合、Google Newsの `batchexecute` APIを使用
- `c-wiz[data-p]` 属性からパラメータを抽出してAPIを呼び出す

**問題点**:
- **Google Newsの内部APIであり、仕様変更のリスクが高い**
- 実装が複雑で、デバッグが困難
- 成功率が不明（ログで確認が必要）

---

## 4. 根本原因の分析

### 主要な問題

1. **URL解決の失敗率が高い**
   - `resolveGoogleNewsPublisherUrl()` が `null` を返すケースが多い
   - 原因:
     - Google NewsのHTML構造の変更
     - タイムアウト（8秒）
     - Google側のアクセス制限

2. **URL解決失敗時のフォールバックが不十分**
   - `resolvedUrl` が `null` の場合、画像取得を完全にスキップ
   - `fetchOGPImage()` 内の再帰処理（Google News URL検出）が機能していない可能性

3. **エラーハンドリングとログの不足**
   - どの段階で失敗しているか特定しにくい
   - デバッグログが開発環境のみで、本番環境での問題追跡が困難

---

## 5. 推奨される解決策

### 即座に実施すべき対策

#### **対策1: URL解決失敗時のフォールバック強化**

**問題**: `resolvedUrl` が `null` の場合、画像取得を完全にスキップしている

**解決策**:
```typescript
if (resolvedUrl) {
  // 優先: 解決されたURLから画像取得
  const ogpImage = await fetchOGPImage(resolvedUrl, 8000)
  if (ogpImage && ogpImage !== '/placeholder.svg') {
    imageUrl = ogpImage
  }
} else {
  // フォールバック: Google News URLから画像取得を試行
  // fetchOGPImage内の再帰処理に依存
  try {
    const ogpImage = await fetchOGPImage(item.link, 8000)
    if (ogpImage && ogpImage !== '/placeholder.svg') {
      imageUrl = ogpImage
    }
  } catch (error) {
    // エラーは無視（placeholderのまま）
  }
}
```

**メリット**:
- URL解決に失敗しても、画像取得の機会を失わない
- `fetchOGPImage()` 内の再帰処理が機能する場合、画像を取得できる

**デメリット**:
- Google Newsロゴが表示される可能性（ただし、`fetchOGPImage()` 内の再帰処理で回避可能）

---

#### **対策2: デバッグログの強化**

**問題**: どの段階で失敗しているか特定しにくい

**解決策**:
- すべてのエラーケースでログを出力
- URL解決の成功率を統計として記録
- 画像取得の成功率を統計として記録

**実装例**:
```typescript
// URL解決統計
const urlResolveStats = {
  totalAttempts: 0,
  successCount: 0,
  failureCount: 0,
  timeoutCount: 0,
}

// 画像取得統計
const imageFetchStats = {
  totalAttempts: 0,
  successCount: 0,
  failureCount: 0,
  placeholderCount: 0,
}
```

---

#### **対策3: タイムアウト時間の調整**

**問題**: 8秒のタイムアウトが短すぎる可能性

**解決策**:
- URL解決: 8秒 → 10秒に延長
- 画像取得: 8秒 → 10秒に延長
- ただし、全体の処理時間が長くなるため、バランスを考慮

---

### 中長期的な対策

#### **対策4: キャッシュ戦略の見直し**

**問題**: 失敗した結果が1分間キャッシュされ、再試行が抑制される

**解決策**:
- 失敗時のキャッシュTTLを短くする（30秒など）
- または、失敗時のキャッシュを削除して再試行を許可

---

#### **対策5: 並列処理の最適化**

**問題**: 記事ごとに順次処理しているため、全体の処理時間が長い

**解決策**:
- URL解決と画像取得を並列化（ただし、リソース制限に注意）
- バッチ処理で複数の記事を同時に処理

---

#### **対策6: 代替データソースの検討**

**問題**: Google Newsに依存している

**解決策**:
- 各メディアの公式RSSフィードを直接使用（可能な場合）
- または、Yahoo!ニュース経由で取得（ただし、以前の実装で問題があった）

---

## 6. 確認すべきポイント

### デバッグ手順

1. **サーバーログの確認**
   ```bash
   # 開発環境で以下を確認
   [Resolve] Starting resolution for: ...
   [Resolve] Resolved: ... -> ...
   [API] Calling fetchOGPImage for article ...
   [fetchOGPImage] Found og:image: ...
   ```

2. **APIデバッグエンドポイントの確認**
   ```
   GET /api/articles?debug=1
   ```
   - `urlResolve` 統計を確認
   - 各フィードの `finalArticleCount` を確認

3. **実際のURL解決のテスト**
   - Google News URLを手動で `resolveGoogleNewsPublisherUrl()` に渡してテスト
   - 解決されたURLが正しいか確認

4. **画像取得のテスト**
   - 解決されたURLを手動で `fetchOGPImage()` に渡してテスト
   - OGPメタタグが存在するか確認

---

## 7. まとめ

### 現在の問題の根本原因

1. **`resolvedUrl` が `null` の場合、画像取得を完全にスキップしている**
2. **URL解決の成功率が低い**（原因は不明だが、Google NewsのHTML構造変更の可能性）
3. **エラーハンドリングとログが不十分**で、問題の特定が困難

### 優先度の高い対策

1. **URL解決失敗時のフォールバック強化**（即座に実施可能）
2. **デバッグログの強化**（問題の特定に必要）
3. **タイムアウト時間の調整**（必要に応じて）

### 次のステップ

1. サーバーログを確認して、URL解決の成功率を把握
2. 対策1を実装して、フォールバック処理を強化
3. デバッグログを追加して、問題の原因を特定
4. 必要に応じて、タイムアウト時間やキャッシュ戦略を調整

---

**レポート作成日**: 2026年1月18日  
**対象バージョン**: 現在の実装（`app/api/articles/route.ts`, `app/lib/googleNewsResolve.ts`）
