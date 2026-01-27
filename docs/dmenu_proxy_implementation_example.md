# dmenu プロキシ統合実装例

このドキュメントでは、Cloudflare Workersプロキシを使用してdmenu APIにアクセスする実装例を示します。

## 実装手順

### Step 1: 環境変数の設定

`.env.local` ファイルに以下を追加：

```env
# dmenu APIプロキシURL（Cloudflare Workers）
DMENU_PROXY_URL=https://dmenu-proxy.your-subdomain.workers.dev

# プロキシを使用するかどうか（true/false）
# プロキシURLが設定されている場合は自動的にtrueになる
USE_DMENU_PROXY=true
```

### Step 2: `app/lib/dmenu.ts` の修正

以下のように修正します：

```typescript
import https from 'https'
import fs from 'fs'
import path from 'path'

// ... 既存のコード（writeLogToFile関数など） ...

// プロキシURLの取得
const DMENU_PROXY_URL = process.env.DMENU_PROXY_URL
const USE_PROXY = !!DMENU_PROXY_URL

// 直接接続用のエンドポイント（フォールバック用）
const DMENU_API_ENDPOINT_DIRECT = 'https://service.smt.docomo.ne.jp/portal/sports/data/news/news_list_0000.json'

// 使用するエンドポイント
const DMENU_API_ENDPOINT = USE_PROXY ? DMENU_PROXY_URL! : DMENU_API_ENDPOINT_DIRECT

export async function fetchDmenuNews(debugMode: boolean = false): Promise<{
  articles: NormalizedArticle[]
  debugInfo?: DmenuDebugInfo
}> {
  const debugInfo: DmenuDebugInfo = {
    listPageUrl: 'https://service.smt.docomo.ne.jp/portal/sports/baseball_j/index.html',
    bestEndpoint: USE_PROXY ? DMENU_PROXY_URL! : DMENU_API_ENDPOINT_DIRECT,
    endpointFetch: {
      ok: false,
      status: 0,
      contentType: null,
      bytes: 0,
    },
    parsedCount: 0,
    sampleArticles: [],
  }

  try {
    const startLog = { 
      url: DMENU_API_ENDPOINT, 
      ts: new Date().toISOString(),
      useProxy: USE_PROXY,
    }
    console.log("FETCH START:", startLog)
    writeLogToFile("FETCH START", startLog)
    
    if (debugMode) {
      console.log(`[Dmenu] Fetching from ${USE_PROXY ? 'proxy' : 'direct'}:`, DMENU_API_ENDPOINT)
    }

    let text: string

    if (USE_PROXY) {
      // ===== プロキシ経由の取得 =====
      // Cloudflare WorkersがSSL/TLSを処理するため、標準fetchを使用
      const response = await fetch(DMENU_API_ENDPOINT, {
        method: 'GET',
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          'Accept': 'application/json, text/html, */*',
          'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        },
        // Next.jsのfetchは自動的にタイムアウトを処理
        next: { revalidate: 300 }, // 5分間キャッシュ
      })

      const responseLog = { 
        url: DMENU_API_ENDPOINT, 
        status: response.status, 
        ts: new Date().toISOString(),
        useProxy: true,
      }
      console.log("FETCH GOT RESPONSE:", responseLog)
      writeLogToFile("FETCH GOT RESPONSE", responseLog)

      debugInfo.endpointFetch.ok = response.ok
      debugInfo.endpointFetch.status = response.status
      debugInfo.endpointFetch.contentType = response.headers.get('content-type') || null

      if (!response.ok) {
        const errorText = await response.text()
        const errorMsg = `Proxy returned ${response.status}: ${response.statusText}`
        if (debugMode) {
          console.error('[Dmenu] Proxy error:', errorMsg)
          console.error('[Dmenu] Response body (first 500 chars):', errorText.substring(0, 500))
        }
        throw new Error(errorMsg)
      }

      text = await response.text()
      debugInfo.endpointFetch.bytes = text.length

    } else {
      // ===== 直接接続（フォールバック） =====
      // 既存のhttps.requestコードを使用
      // （SSL/TLSエラーが発生する可能性があるが、フォールバックとして残す）
      
      const originalRejectUnauthorized = process.env.NODE_TLS_REJECT_UNAUTHORIZED
      process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0'
      
      try {
        text = await new Promise<string>((resolve, reject) => {
          const url = new URL(DMENU_API_ENDPOINT_DIRECT)
          const options = {
            hostname: url.hostname,
            port: url.port || 443,
            path: url.pathname + url.search,
            method: 'GET',
            headers: {
              'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
              'Accept': 'application/json, text/html, */*',
              'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
              'Referer': 'https://service.smt.docomo.ne.jp/portal/sports/baseball_j/index.html',
            },
            agent: new https.Agent({
              rejectUnauthorized: false,
              secureProtocol: 'TLSv1_2_method',
            }),
          }

          const req = https.request(options, (res) => {
            const responseLog = { 
              url: DMENU_API_ENDPOINT_DIRECT, 
              status: res.statusCode, 
              ts: new Date().toISOString(),
              useProxy: false,
            }
            console.log("FETCH GOT RESPONSE:", responseLog)
            writeLogToFile("FETCH GOT RESPONSE", responseLog)
            
            debugInfo.endpointFetch.ok = res.statusCode !== undefined && res.statusCode >= 200 && res.statusCode < 300
            debugInfo.endpointFetch.status = res.statusCode || 0
            debugInfo.endpointFetch.contentType = res.headers['content-type'] || null

            if (debugMode) {
              console.log('[Dmenu] Response status:', res.statusCode, 'ok:', debugInfo.endpointFetch.ok)
            }

            let data = ''
            res.on('data', (chunk) => {
              data += chunk
            })
            res.on('end', () => {
              debugInfo.endpointFetch.bytes = data.length
              
              if (debugMode) {
                console.log('[Dmenu] Response body length:', data.length, 'bytes')
                console.log('[Dmenu] Response body (first 200 chars):', data.substring(0, 200))
              }

              if (!debugInfo.endpointFetch.ok) {
                const errorMsg = `dmenu API returned ${res.statusCode}: ${res.statusMessage || 'Unknown'}`
                if (debugMode) {
                  console.error('[Dmenu] Fetch failed:', errorMsg)
                  console.error('[Dmenu] Response body (first 500 chars):', data.substring(0, 500))
                }
                reject(new Error(errorMsg))
                return
              }

              resolve(data)
            })
          })

          req.on('error', (error: any) => {
            // エラーオブジェクトのすべてのプロパティを取得
            const errorDetails: any = {
              url: DMENU_API_ENDPOINT_DIRECT,
              message: error?.message,
              code: error?.code,
              name: error?.name,
              errno: error?.errno,
              syscall: error?.syscall,
              cause: error?.cause,
              stack: error?.stack,
              useProxy: false,
            }
            
            // エラーオブジェクトのすべての列挙可能なプロパティを追加
            if (error && typeof error === 'object') {
              for (const key in error) {
                if (!errorDetails.hasOwnProperty(key)) {
                  try {
                    errorDetails[key] = error[key]
                  } catch (e) {
                    errorDetails[key] = '[Cannot serialize]'
                  }
                }
              }
            }
            
            console.error("FETCH FAILED:", errorDetails)
            writeLogToFile("FETCH FAILED", errorDetails)
            const errorMsg = error instanceof Error ? error.message : String(error)
            if (debugMode) {
              console.error('[Dmenu] Request error:', errorMsg)
            }
            reject(new Error(`Request failed: ${errorMsg}`))
          })

          req.setTimeout(10000, () => {
            req.destroy()
            reject(new Error('Request timeout'))
          })

          req.end()
        })
      } finally {
        // 環境変数を元に戻す
        if (originalRejectUnauthorized !== undefined) {
          process.env.NODE_TLS_REJECT_UNAUTHORIZED = originalRejectUnauthorized
        } else {
          delete process.env.NODE_TLS_REJECT_UNAUTHORIZED
        }
      }
    }

    // ===== JSONパースと記事の変換 =====
    // （プロキシ経由・直接接続共通）
    const json: DmenuNewsList = JSON.parse(text)

    const articles: NormalizedArticle[] = json.news_list.news.map(item => {
      let publishedAt = ''
      try {
        const dateStr = item.news_publish_datetime.replace(/\//g, '-').replace(' ', 'T')
        const date = new Date(dateStr)
        if (!isNaN(date.getTime())) {
          publishedAt = date.toISOString()
        }
      } catch (error) {
        publishedAt = new Date().toISOString()
      }

      const url = item.news_origin_url || item.news_url

      return {
        title: item.news_title,
        url: url,
        publishedAt: publishedAt,
        imageUrl: item.news_thumbnail || '/placeholder.svg',
        sourceName: item.news_ip_name || 'dmenu',
      }
    })

    debugInfo.parsedCount = articles.length
    debugInfo.sampleArticles = articles.slice(0, 3).map(a => ({
      title: a.title,
      url: a.url,
      publishedAt: a.publishedAt,
      imageUrl: a.imageUrl,
    }))

    return {
      articles,
      debugInfo: debugMode ? debugInfo : undefined,
    }
  } catch (error: any) {
    const errorLog = {
      url: DMENU_API_ENDPOINT,
      message: error?.message,
      code: error?.code,
      name: error?.name,
      errno: error?.errno,
      syscall: error?.syscall,
      cause: error?.cause,
      stack: error?.stack,
      useProxy: USE_PROXY,
    }
    console.error("FETCH FAILED:", errorLog)
    writeLogToFile("FETCH FAILED", errorLog)
    
    const errorMessage = error instanceof Error ? error.message : String(error)
    const errorStack = error instanceof Error ? error.stack : undefined
    
    console.error('[Dmenu] Failed to fetch news:', errorMessage)
    if (debugMode && errorStack) {
      console.error('[Dmenu] Error stack:', errorStack)
    }
    
    // デバッグ情報にエラーメッセージを追加
    if (debugMode) {
      debugInfo.endpointFetch = {
        ...debugInfo.endpointFetch,
        error: errorMessage,
      }
    }
    
    // エラー時は空配列を返す（500エラーにしない）
    return {
      articles: [],
      debugInfo: debugMode ? debugInfo : undefined,
    }
  }
}
```

### Step 3: デバッグ情報の更新

`DmenuDebugInfo` インターフェースに `useProxy` フィールドを追加（オプション）：

```typescript
export interface DmenuDebugInfo {
  listPageUrl: string
  bestEndpoint: string
  useProxy?: boolean  // 追加
  endpointFetch: {
    ok: boolean
    status: number
    contentType: string | null
    bytes: number
    error?: string
  }
  parsedCount: number
  sampleArticles: Array<{
    title: string
    url: string
    publishedAt: string
    imageUrl: string
  }>
}
```

## テスト手順

### 1. プロキシの動作確認

```bash
curl https://dmenu-proxy.your-subdomain.workers.dev
```

正常に動作していれば、JSONレスポンスが返ってきます。

### 2. Next.jsアプリでの確認

1. `.env.local` に `DMENU_PROXY_URL` を設定
2. 開発サーバーを再起動
3. `http://localhost:3000/api/articles?debug=1` にアクセス
4. `dmenuDebug` を確認：
   - `endpointFetch.ok === true`
   - `parsedCount > 0`
   - `useProxy: true`（追加した場合）

### 3. ログファイルの確認

```bash
Get-Content logs/dmenu_fetch.log -Tail 20
```

`useProxy: true` が記録され、`FETCH GOT RESPONSE` が成功していることを確認してください。

## トラブルシューティング

### プロキシが動作しない

1. Cloudflare Workersのログを確認
2. Worker URLが正しいか確認
3. CORSエラーが発生していないか確認

### 環境変数が読み込まれない

1. `.env.local` ファイルがプロジェクトルートにあるか確認
2. 開発サーバーを再起動
3. `process.env.DMENU_PROXY_URL` をログで確認

### フォールバックが動作しない

- プロキシURLが設定されていない場合、直接接続にフォールバックします
- ただし、SSL/TLSエラーが発生するため、記事取得は失敗します







