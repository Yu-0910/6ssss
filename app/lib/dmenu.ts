/**
 * dmenuスポーツ（service.smt.docomo.ne.jp）からニュース記事を取得するモジュール
 * 
 * エンドポイントURL: プローブ実行後、bestEndpointをここに設定
 * 
 * プロキシ経由の取得:
 * - 環境変数 DMENU_PROXY_URL が設定されている場合、Cloudflare Workersプロキシ経由で取得
 * - プロキシ経由の場合、SSL/TLSレガシーリネゴシエーションの問題を回避できる
 */

import https from 'https'
import fs from 'fs'
import path from 'path'

// プロキシURLの取得
const DMENU_PROXY_URL = process.env.DMENU_PROXY_URL
const USE_PROXY = !!DMENU_PROXY_URL

// 直接接続用のエンドポイント（フォールバック用）
const DMENU_API_ENDPOINT_DIRECT = 'https://service.smt.docomo.ne.jp/portal/sports/data/news/news_list_0000.json'

// 使用するエンドポイント
const DMENU_API_ENDPOINT = USE_PROXY ? DMENU_PROXY_URL! : DMENU_API_ENDPOINT_DIRECT

// ログファイルに出力するヘルパー関数
function writeLogToFile(message: string, data?: any) {
  try {
    const logsDir = path.join(process.cwd(), 'logs')
    if (!fs.existsSync(logsDir)) {
      fs.mkdirSync(logsDir, { recursive: true })
    }
    const logFile = path.join(logsDir, 'dmenu_fetch.log')
    const timestamp = new Date().toISOString()
    const logEntry = `[${timestamp}] ${message}${data ? '\n' + JSON.stringify(data, null, 2) : ''}\n`
    fs.appendFileSync(logFile, logEntry, 'utf-8')
  } catch (error) {
    // ログファイル書き込み失敗は無視（コンソールには出力）
    console.error('[Dmenu] Failed to write log to file:', error)
  }
}

export interface DmenuNewsItem {
  news_title: string
  news_ip_name: string
  news_origin_url: string
  news_url: string
  news_thumbnail: string
  news_publish_datetime: string
}

export interface DmenuNewsList {
  news_list: {
    news_list_id: string
    news_list_title: string
    more_link_title: string
    news: DmenuNewsItem[]
  }
}

export interface NormalizedArticle {
  title: string
  url: string
  publishedAt: string
  imageUrl: string
  sourceName: string
}

export interface DmenuDebugInfo {
  listPageUrl: string
  bestEndpoint: string
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

// この定数は削除（上で定義済み）

/**
 * dmenuからニュース記事を取得
 * 
 * @param debugMode デバッグモード（デバッグ情報を返す）
 * @returns 正規化された記事の配列とデバッグ情報
 */
export async function fetchDmenuNews(debugMode: boolean = false): Promise<{
  articles: NormalizedArticle[]
  debugInfo?: DmenuDebugInfo
}> {
  const debugInfo: DmenuDebugInfo = {
    listPageUrl: 'https://service.smt.docomo.ne.jp/portal/sports/baseball_j/index.html',
    bestEndpoint: DMENU_API_ENDPOINT,
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
      
      // dmenuサーバーのSSL/TLSレガシーリネゴシエーション問題に対処
      // 注意: 本番環境ではより安全な方法を使用すべき
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
            rejectUnauthorized: false, // SSL証明書検証をスキップ（開発環境のみ）
            secureProtocol: 'TLSv1_2_method', // TLS 1.2を強制（レガシーリネゴシエーション対応）
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

    // news_list.newsを正規化形式に変換
    const articles: NormalizedArticle[] = json.news_list.news.map(item => {
      // 公開日時をISO形式に変換
      // 形式: "2026/01/18 22:48:45" -> "2026-01-18T22:48:45.000Z"
      let publishedAt = ''
      try {
        const dateStr = item.news_publish_datetime.replace(/\//g, '-').replace(' ', 'T')
        const date = new Date(dateStr)
        if (!isNaN(date.getTime())) {
          publishedAt = date.toISOString()
        }
      } catch (error) {
        // パース失敗時は現在時刻を使用
        publishedAt = new Date().toISOString()
      }

      // news_origin_urlを使用（UTMパラメータなしの元記事URL）
      // もしnews_origin_urlがなければnews_urlを使用
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
