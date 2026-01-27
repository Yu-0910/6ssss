# dmenu API取得：プロキシ経由解決策 計画書

## 1. 問題の要約

### 1.1 現状の問題
- **エラー**: `ERR_SSL_UNSAFE_LEGACY_RENEGOTIATION_DISABLED`
- **エラーメッセージ**: `write EPROTO ...:error:0A000152:SSL routines:final_renegotiate:unsafe legacy renegotiation disabled`
- **発生箇所**: `app/lib/dmenu.ts` の `https.request()` 呼び出し
- **影響**: dmenuからの記事取得が完全に失敗し、`articleCount: 0` が返される

### 1.2 根本原因
- dmenuサーバー（`service.smt.docomo.ne.jp`）がレガシーなSSL/TLSリネゴシエーション機能を使用
- Node.jsの新しいバージョン（OpenSSL 3.0以降）で、セキュリティ上の理由からレガシーリネゴシエーションがデフォルトで無効化されている
- Node.jsアプリケーション側から直接この制約を回避することができない

## 2. 試行した解決策とその結果

### 2.1 試行1: Next.js標準`fetch` API
- **実装**: `app/lib/dmenu.ts` で `fetch` を使用
- **結果**: ❌ 失敗
- **理由**: `fetch` APIは低レベルなSSL/TLS設定（`rejectUnauthorized`や`secureProtocol`）を直接制御できない

### 2.2 試行2: Node.js `https`モジュール + `https.Agent`
- **実装**: `https.request` と `new https.Agent({ rejectUnauthorized: false })` を使用
- **結果**: ❌ 失敗
- **理由**: 証明書検証をスキップするだけでは、レガシーリネゴシエーションの問題は解決しない

### 2.3 試行3: `secureProtocol: 'TLSv1_2_method'` オプション
- **実装**: `https.Agent` のオプションに `secureProtocol: 'TLSv1_2_method'` を追加
- **結果**: ❌ 失敗
- **理由**: TLS 1.2を強制しても、サーバーがレガシーリネゴシエーションを要求する限り、Node.jsのセキュリティポリシーによって接続が拒否される

### 2.4 試行4: 環境変数 `NODE_TLS_REJECT_UNAUTHORIZED = '0'`
- **実装**: `process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0'` を設定
- **結果**: ❌ 失敗
- **理由**: 証明書検証を無効にするだけで、プロトコルレベルの互換性問題には対処できない

### 2.5 試行5: Node.js起動フラグ `--tls-legacy-renegotiation`
- **実装**: `package.json` のスクリプトに `--tls-legacy-renegotiation` フラグを追加
- **結果**: ❌ 失敗
- **理由**: このフラグは存在しない（`node: bad option` エラー）

### 2.6 結論
Node.jsアプリケーション側から直接SSL/TLSレガシーリネゴシエーションの問題を解決することは**不可能**であることが確認された。

## 3. プロキシ経由解決策の詳細

### 3.1 アーキテクチャ概要

```
[Next.js App] → [プロキシサーバー] → [dmenu API]
     ↓              ↓                    ↓
  Node.js      (SSL/TLS処理)      (レガシーSSL/TLS)
```

### 3.2 プロキシサーバーの役割
1. **SSL/TLSハンドシェイクの処理**: レガシーリネゴシエーションに対応できる環境でdmenuサーバーと通信
2. **プロトコル変換**: レガシーSSL/TLSからモダンなHTTPSへの変換
3. **リクエスト/レスポンスの転送**: Next.jsアプリからdmenu APIへのリクエストを中継

### 3.3 プロキシサーバーの選択肢

#### オプションA: Cloudflare Workers（推奨）
- **メリット**:
  - 無料プランあり（1日10万リクエストまで）
  - グローバルCDNで高速
  - 簡単なデプロイ
  - SSL/TLS処理が自動
- **デメリット**:
  - 外部サービスへの依存
  - 無料プランには制限あり

#### オプションB: Vercel Edge Functions
- **メリット**:
  - Next.jsとの統合が容易
  - 既存のVercelデプロイと統合可能
- **デメリット**:
  - Vercelアカウントが必要
  - 有料プランの可能性

#### オプションC: 自前のNode.jsプロキシサーバー
- **メリット**:
  - 完全な制御
  - カスタマイズ可能
- **デメリット**:
  - インフラ管理が必要
  - SSL/TLS設定が複雑
  - 運用コストが高い

#### オプションD: Nginx/HAProxy等のリバースプロキシ
- **メリット**:
  - 高パフォーマンス
  - 柔軟な設定
- **デメリット**:
  - サーバー管理が必要
  - 設定が複雑

## 4. 実装計画（Cloudflare Workers使用）

### 4.1 Phase 1: Cloudflare Workersプロキシの作成

#### 4.1.1 プロキシスクリプトの作成
**ファイル**: `cloudflare-workers/dmenu-proxy.js`

```javascript
export default {
  async fetch(request) {
    // CORS対応
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      })
    }

    // dmenu APIエンドポイント
    const dmenuUrl = 'https://service.smt.docomo.ne.jp/portal/sports/data/news/news_list_0000.json'
    
    // リクエストヘッダーをコピー（User-Agent等）
    const headers = new Headers()
    headers.set('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    headers.set('Accept', 'application/json, text/html, */*')
    headers.set('Accept-Language', 'ja,en-US;q=0.9,en;q=0.8')
    headers.set('Referer', 'https://service.smt.docomo.ne.jp/portal/sports/baseball_j/index.html')

    try {
      // dmenu APIにリクエスト
      const response = await fetch(dmenuUrl, {
        method: 'GET',
        headers: headers,
      })

      // レスポンスを取得
      const data = await response.text()

      // CORSヘッダーを付けて返す
      return new Response(data, {
        status: response.status,
        headers: {
          'Content-Type': response.headers.get('Content-Type') || 'application/json',
          'Access-Control-Allow-Origin': '*',
          'Cache-Control': 'public, max-age=300', // 5分キャッシュ
        },
      })
    } catch (error) {
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      })
    }
  },
}
```

#### 4.1.2 Cloudflare Workersへのデプロイ
1. Cloudflareアカウントの作成
2. Workers & Pages ダッシュボードで新しいWorkerを作成
3. 上記スクリプトをデプロイ
4. カスタムドメインまたは `*.workers.dev` ドメインでアクセス可能にする

### 4.2 Phase 2: Next.jsアプリの修正

#### 4.2.1 環境変数の追加
**ファイル**: `.env.local`

```env
DMENU_PROXY_URL=https://your-worker.your-subdomain.workers.dev
```

#### 4.2.2 `app/lib/dmenu.ts` の修正

```typescript
// プロキシURLを使用するかどうかの判定
const USE_PROXY = process.env.DMENU_PROXY_URL !== undefined

const DMENU_API_ENDPOINT = USE_PROXY
  ? process.env.DMENU_PROXY_URL!
  : 'https://service.smt.docomo.ne.jp/portal/sports/data/news/news_list_0000.json'

export async function fetchDmenuNews(debugMode: boolean = false): Promise<{
  articles: NormalizedArticle[]
  debugInfo?: DmenuDebugInfo
}> {
  // ... 既存のコード ...

  try {
    if (USE_PROXY) {
      // プロキシ経由: 標準fetchを使用（Cloudflare WorkersがSSL/TLSを処理）
      const response = await fetch(DMENU_API_ENDPOINT, {
        method: 'GET',
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          'Accept': 'application/json, text/html, */*',
          'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        },
      })

      if (!response.ok) {
        throw new Error(`Proxy returned ${response.status}: ${response.statusText}`)
      }

      const text = await response.text()
      const json: DmenuNewsList = JSON.parse(text)
      // ... 既存のパース処理 ...
    } else {
      // 直接接続: 既存のhttps.requestコード（フォールバック用）
      // ... 既存のコード ...
    }
  } catch (error: any) {
    // ... 既存のエラーハンドリング ...
  }
}
```

### 4.3 Phase 3: テストと検証

#### 4.3.1 単体テスト
1. プロキシURLが正しく設定されているか確認
2. プロキシ経由でdmenu APIにアクセスできるか確認
3. レスポンスが正しくパースできるか確認

#### 4.3.2 統合テスト
1. `/api/articles?debug=1` でdmenu記事が取得できるか確認
2. `dmenuDebug` に正しい情報が含まれているか確認
3. エラーハンドリングが正しく動作するか確認

### 4.4 Phase 4: デプロイとモニタリング

#### 4.4.1 デプロイ
1. Cloudflare Workersにプロキシをデプロイ
2. 環境変数を設定
3. Next.jsアプリをデプロイ

#### 4.4.2 モニタリング
1. Cloudflare Workersのログを確認
2. Next.jsアプリのログを確認
3. エラー率を監視

## 5. 代替案

### 5.1 代替データソースの検討
- 他のスポーツニュース提供元（Yahoo Sports、スポーツナビなど）の検討
- RSSフィードの活用

### 5.2 プロキシサーバーの自前運用
- VPS上でNginx/HAProxyを設定
- SSL/TLS設定をカスタマイズしてレガシーリネゴシエーションに対応

## 6. リスクと考慮事項

### 6.1 セキュリティリスク
- **プロキシサーバーの信頼性**: Cloudflare Workersは信頼できるが、自前運用の場合はセキュリティ対策が必要
- **データの機密性**: プロキシ経由でデータが流れるため、HTTPSを使用する

### 6.2 パフォーマンス
- **レイテンシ**: プロキシを経由するため、若干のレイテンシが増加する可能性
- **キャッシュ**: Cloudflare Workersのキャッシュ機能を活用してパフォーマンスを改善

### 6.3 コスト
- **Cloudflare Workers**: 無料プランで1日10万リクエストまで（通常の使用では十分）
- **自前運用**: サーバーコストが発生

### 6.4 依存関係
- **外部サービスへの依存**: Cloudflare Workersがダウンした場合の影響
- **フォールバック**: プロキシが利用できない場合のフォールバック処理

## 7. 実装スケジュール（推奨）

### Week 1: プロキシの作成とテスト
- Day 1-2: Cloudflare Workersプロキシの作成
- Day 3-4: プロキシのテストとデバッグ
- Day 5: ドキュメント作成

### Week 2: Next.jsアプリの統合
- Day 1-2: `app/lib/dmenu.ts` の修正
- Day 3: テストと検証
- Day 4-5: デプロイとモニタリング

## 8. 成功基準

1. ✅ `/api/articles?debug=1` でdmenu記事が取得できる
2. ✅ `dmenuDebug.endpointFetch.ok === true`
3. ✅ `dmenuDebug.parsedCount > 0`
4. ✅ SSL/TLSエラーが発生しない
5. ✅ レスポンス時間が許容範囲内（< 2秒）

## 9. ロールバック計画

プロキシ経由の実装に問題が発生した場合：
1. 環境変数 `DMENU_PROXY_URL` を削除または空にする
2. 既存の直接接続コード（フォールバック）が動作する
3. ただし、SSL/TLSエラーは依然として発生するため、記事取得は失敗する

## 10. 今後の改善

1. **キャッシュ戦略の最適化**: Cloudflare Workersのキャッシュを活用
2. **エラーハンドリングの強化**: プロキシエラー時の詳細なログ
3. **モニタリングの追加**: プロキシの可用性とパフォーマンスの監視
4. **複数プロキシのサポート**: フォールバック用の複数プロキシURLのサポート







