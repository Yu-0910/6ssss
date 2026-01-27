/**
 * Google News RSSから取得したURLを元記事URL（publisher URL）に解決
 * 
 * Google NewsのリダイレクトURL（news.google.com/articles/...）を
 * 実際の記事URL（例: hochi.news/articles/..., sanspo.com/article/...）に変換する
 */

type AllowedDomains = string[]

// キャッシュエントリの型
type CacheEntry = {
  url: string | null
  expiresAt: number
}

// キャッシュキー（googleNewsUrl + allowedDomainsのハッシュ）
type CacheKey = string

// メモリキャッシュ（Map: cacheKey -> CacheEntry）
const urlCache = new Map<CacheKey, CacheEntry>()

// キャッシュTTL: 成功時は24時間、失敗時は10秒
const CACHE_TTL_MS = 24 * 60 * 60 * 1000
const CACHE_TTL_FAILURE_MS = 10 * 1000

// タイムアウト: 12秒（デフォルト）
const RESOLVE_TIMEOUT_MS = 12000

// 同時実行数制限: 4
const MAX_CONCURRENT_REQUESTS = 4

// 1リクエスト内での解決件数制限（レート制限対策）
const MAX_RESOLVE_PER_REQUEST = 15
let resolveCountInRequest = 0
let activeRequestCount = 0
const requestQueue: Array<{
  resolve: (value: string | null) => void
  reject: (error: Error) => void
  url: string
  allowedDomains: AllowedDomains
  timeoutMs?: number
}> = []

/**
 * ドメインを正規化（プロトコルや末尾スラッシュを除去）
 */
function normalizeDomain(d: string): string {
  return d.replace(/^https?:\/\//, '').replace(/\/+$/, '').toLowerCase()
}

/**
 * URLが許可されたドメインに一致するかチェック
 * - hostname === domain または
 * - hostname.endsWith('.domain') の場合に true を返す
 */
function isAllowedDomain(u: string, allowed: AllowedDomains): boolean {
  try {
    const host = new URL(u).hostname.toLowerCase()
    return allowed
      .map(normalizeDomain)
      .some((d) => host === d || host.endsWith(`.${d}`))
  } catch {
    return false
  }
}

/**
 * 候補URLの中から最初の許可されたドメインを返す
 */
function pickFirstAllowed(candidates: string[], allowed: AllowedDomains): string | null {
  for (const c of candidates) {
    if (c && isAllowedDomain(c, allowed)) {
      return c
    }
  }
  return null
}

/**
 * Google URLパラメータをデコード
 * 例: https://www.google.com/url?url=https%3A%2F%2Fsanspo.com%2F...&...
 */
function decodeGoogleUrlParam(raw: string): string | null {
  try {
    const u = new URL(raw)
    const urlParam = u.searchParams.get('url')
    if (!urlParam) return null
    const decoded = decodeURIComponent(urlParam)
    return decoded
  } catch {
    return null
  }
}

/**
 * Google News URLから記事IDを抽出
 * 例: /articles/<ID> または /rss/articles/<ID> または /__i/rss/rd/articles/<ID>
 */
function extractGoogleNewsId(url: string): string | null {
  try {
    // /articles/<ID> パターン
    let match = url.match(/\/articles\/([^?/]+)/)
    if (match && match[1]) {
      return match[1]
    }
    
    // /rss/articles/<ID> パターン
    match = url.match(/\/rss\/articles\/([^?/]+)/)
    if (match && match[1]) {
      return match[1]
    }
    
    // /__i/rss/rd/articles/<ID> パターン
    match = url.match(/\/__i\/rss\/rd\/articles\/([^?/]+)/)
    if (match && match[1]) {
      return match[1]
    }
    
    return null
  } catch {
    return null
  }
}

/**
 * Google Newsページからbatchexecute用のパラメータを取得（c-wiz[data-p]方式）
 * HTMLから c-wiz[data-p] を抽出してJSONオブジェクトを復元
 */
async function getBatchExecuteParams(googleNewsUrl: string): Promise<any | null> {
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), RESOLVE_TIMEOUT_MS)

    const response = await fetch(googleNewsUrl, {
      redirect: 'follow',
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.8,en;q=0.7',
      },
      cache: 'no-store' as RequestCache,
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`[Resolve] HTTP ${response.status} ${response.statusText} for ${googleNewsUrl}`)
      }
      return null
    }

    const html = await response.text()
    
    // c-wiz[data-p] 属性を抽出
    const dataPMatch = html.match(/<c-wiz[^>]*data-p=["']([^"']+)["']/i)
    if (!dataPMatch || !dataPMatch[1]) {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`[Resolve] Could not extract c-wiz[data-p] from ${googleNewsUrl}`)
      }
      return null
    }
    
    const dataPValue = dataPMatch[1]
    
    // "%.@." を '["garturlreq",' に置換してJSONとして復元
    const jsonStr = dataPValue.replace(/"%\.@\./g, '["garturlreq",')
    
    try {
      const parsed = JSON.parse(jsonStr)
      if (process.env.NODE_ENV === 'development') {
        console.log(`[Resolve] Extracted data-p JSON from ${googleNewsUrl}`)
      }
      return parsed
    } catch (parseError) {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`[Resolve] Failed to parse data-p JSON: ${jsonStr.substring(0, 200)}...`)
      }
      return null
    }
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.warn(`[Resolve] Error getting batch execute params for ${googleNewsUrl}:`, error)
    }
    return null
  }
}

/**
 * batchexecuteエンドポイントを使ってpublisher URLを解決（直接API方式・改善版）
 * 
 * (1) preflight: Google News URLをGETしてトークン（f.sid/bl/at）を抽出
 * (2) batchexecute POST: garturlreq形式のf.reqでPOST、トークン付与
 * (3) 解析: garturlresを最優先で抽出、JSONデコード
 */
async function resolveViaBatchExecuteDirect(
  googleNewsUrl: string,
  allowedDomains: AllowedDomains,
  timeoutMs?: number
): Promise<string | null> {
  try {
    // pathnameを抽出（クエリを除く）
    let sourcePath: string
    let articleId: string | null = null
    try {
      const url = new URL(googleNewsUrl)
      sourcePath = url.pathname // 例: /rss/articles/CBMi...
      
      // /rss/articles/ の場合は /articles/ に変換
      if (sourcePath.startsWith('/rss/articles/')) {
        sourcePath = sourcePath.replace('/rss/', '/')
      }
      
      // 記事IDを抽出（garturlreqで使用）
      articleId = extractGoogleNewsId(googleNewsUrl)
    } catch {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`[Resolve] Invalid Google News URL: ${googleNewsUrl}`)
      }
      return null
    }

    const timeout = timeoutMs || RESOLVE_TIMEOUT_MS

    // (1) preflight: トークン抽出
    let fSid: string | null = null
    let bl: string | null = null
    let at: string | null = null

    try {
      // URLを正規化（hl/gl/ceidを付与）
      const preflightUrl = googleNewsUrl.includes('?') 
        ? googleNewsUrl.replace(/([?&])(hl|gl|ceid)=[^&]*/g, '').replace(/&$/, '') + '&hl=ja&gl=JP&ceid=JP:ja'
        : googleNewsUrl + '?hl=ja&gl=JP&ceid=JP:ja'
      
      const controller1 = new AbortController()
      const timeoutId1 = setTimeout(() => controller1.abort(), timeout)

      const preflightResponse = await fetch(preflightUrl, {
        redirect: 'follow',
        signal: controller1.signal,
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        },
        cache: 'no-store' as RequestCache,
      })

      clearTimeout(timeoutId1)

      if (preflightResponse.ok) {
        const html = await preflightResponse.text()
        
        // f.sid を抽出
        const fSidMatch = html.match(/"f\.sid"\s*:\s*"(\d+)"/) || html.match(/"f\.sid":\s*(\d+)/)
        if (fSidMatch) fSid = fSidMatch[1]
        
        // bl を抽出
        const blMatch = html.match(/"bl"\s*:\s*"([^"]+)"/) || html.match(/"bl":\s*"([^"]+)"/)
        if (blMatch) bl = blMatch[1]
        
        // at を抽出（複数パターンを試行）
        const atMatch = html.match(/"at"\s*:\s*"([^"]+)"/) || html.match(/at=([^&"]+)/) || html.match(/"at":\s*"([^"]+)"/)
        if (atMatch) at = atMatch[1]
        
        if (process.env.NODE_ENV === 'development') {
          console.log(`[Resolve] Preflight tokens - f.sid: ${fSid ? 'found' : 'missing'}, bl: ${bl ? 'found' : 'missing'}, at: ${at ? 'found' : 'missing'}`)
        }
      } else {
        if (process.env.NODE_ENV === 'development') {
          console.warn(`[Resolve] Preflight HTTP ${preflightResponse.status}`)
        }
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`[Resolve] Preflight error (continuing without tokens):`, error instanceof Error ? error.message : String(error))
      }
    }

    // (2) batchexecute POST URLを構築
    const encodedSourcePath = encodeURIComponent(sourcePath)
    const apiUrlParams = new URLSearchParams({
      rpcids: 'Fbv4je',
      'source-path': encodedSourcePath,
      hl: 'ja',
      gl: 'JP',
      'soc-app': '140',
      'soc-platform': '1',
      'soc-device': '1',
      rt: 'c',
    })
    
    // トークンがあれば追加
    if (fSid) apiUrlParams.set('f.sid', fSid)
    if (bl) apiUrlParams.set('bl', bl)
    
    const apiUrl = `https://news.google.com/_/DotsSplashUi/data/batchexecute?${apiUrlParams.toString()}`

    // f.req を garturlreq 形式で作成
    const articleIdForReq = articleId || sourcePath.split('/').pop() || ''
    const garturlreqParams = articleIdForReq ? [articleIdForReq] : [sourcePath, "", null, null, null, null, null, null, null, null, 2, 0, 0, 0]
    const fReqArray = [["Fbv4je", JSON.stringify(["garturlreq", ...garturlreqParams]), null, "generic"]]
    const fReq = JSON.stringify(fReqArray)

    const bodyParams = new URLSearchParams({
      'f.req': fReq
    })
    if (at) {
      bodyParams.set('at', at)
    }

    if (process.env.NODE_ENV === 'development') {
      console.log(`[Resolve] BatchExecute Direct API POST: ${apiUrl}`)
      console.log(`[Resolve] f.req contains garturlreq: ${fReq.includes('garturlreq')}`)
    }

    const controller2 = new AbortController()
    const timeoutId2 = setTimeout(() => controller2.abort(), timeout)

    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'Referer': 'https://news.google.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
      },
      body: bodyParams.toString(),
      signal: controller2.signal,
      cache: 'no-store' as RequestCache,
    })

    clearTimeout(timeoutId2)

    if (!response.ok) {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`[Resolve] BatchExecute Direct API HTTP ${response.status} ${response.statusText}`)
        if (response.status === 400 || response.status === 403) {
          console.warn(`[Resolve] Status ${response.status} may indicate missing token (at)`)
        } else if (response.status === 429) {
          console.warn(`[Resolve] Status 429: Rate limit exceeded`)
        }
      }
      return null
    }

    let text = await response.text()

    // 先頭の )]}' を除去
    if (text.startsWith(")]}'")) {
      text = text.substring(4)
    }

    // (3) garturlres を最優先で抽出
    let garturlresUrl: string | null = null
    
    // パターン1: エスケープされた形式 \"garturlres\"
    const garturlresMatch1 = text.match(/\\"garturlres\\"\s*,\s*\\"([^\\"]+)\\"/) || 
                             text.match(/"garturlres"\s*,\s*"([^"]+)"/)
    
    if (garturlresMatch1 && garturlresMatch1[1]) {
      try {
        // JSONデコード（\u003d → =, \/ → / など）
        const decoded = JSON.parse(`"${garturlresMatch1[1]}"`)
        garturlresUrl = decoded
      } catch {
        // JSONパース失敗時は手動デコード
        garturlresUrl = garturlresMatch1[1]
          .replace(/\\u003d/g, '=')
          .replace(/\\u0026/g, '&')
          .replace(/\\\//g, '/')
          .replace(/\\"/g, '"')
      }
    }

    // garturlresが見つかった場合、allowedDomainsチェックして返す
    if (garturlresUrl) {
      // news.google.com / google.com など内部URLは除外
      if (!garturlresUrl.includes('news.google.com') && !garturlresUrl.includes('google.com')) {
        if (isAllowedDomain(garturlresUrl, allowedDomains)) {
          if (process.env.NODE_ENV === 'development') {
            console.log(`[Resolve] Resolved via BatchExecute Direct API (garturlres): ${googleNewsUrl} -> ${garturlresUrl}`)
          }
          return garturlresUrl
        }
      }
    }

    // garturlresが見つからなかった場合、従来のURL抽出パターンにフォールバック
    const urlPattern = /https?:\/\/[^\s"',\)\]\}]+/gi
    const matches = text.match(urlPattern) ?? []

    let normalUrl: string | null = null
    let ampUrl: string | null = null

    for (const urlMatch of matches) {
      let url = urlMatch.trim().replace(/[,\)\]\}]$/, '')

      // news.google.com / google.com など内部URLは除外
      if (url.includes('news.google.com') || url.includes('google.com')) {
        continue
      }

      // AMP判定
      const isAmp = url.includes('.amp.') || url.includes('/amp/')

      // allowedDomains に一致するかチェック
      if (isAllowedDomain(url, allowedDomains)) {
        if (isAmp) {
          if (!ampUrl) ampUrl = url
        } else {
          normalUrl = url
          break // 通常URLが見つかったら優先
        }
      }
    }

    const pickedUrl = normalUrl || ampUrl

    if (pickedUrl) {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[Resolve] Resolved via BatchExecute Direct API: ${googleNewsUrl} -> ${pickedUrl}`)
      }
      return pickedUrl
    }

    if (process.env.NODE_ENV === 'development') {
      console.warn(`[Resolve] BatchExecute Direct API: garturlres not found, no allowed domain URL found`)
      if (garturlresUrl) {
        console.warn(`[Resolve] garturlres extracted but not in allowedDomains: ${garturlresUrl}`)
      }
      console.warn(`[Resolve] Extracted URLs: ${matches.slice(0, 5).join(', ')}`)
    }
    return null
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.warn(`[Resolve] Error in resolveViaBatchExecuteDirect:`, error)
    }
    return null
  }
}

/**
 * batchexecuteエンドポイントを使ってpublisher URLを解決（c-wiz[data-p]方式）
 * @deprecated 新しい直接API方式（resolveViaBatchExecuteDirect）を優先使用
 */
async function resolveViaBatchExecute(
  dataPObject: any,
  allowedDomains: AllowedDomains
): Promise<string | null> {
  try {
    // dataPObjectを使ってf.reqを作成
    const fReq = JSON.stringify(dataPObject)

    const body = new URLSearchParams({
      'f.req': fReq
    })

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), RESOLVE_TIMEOUT_MS)

    const response = await fetch('https://news.google.com/_/DotsSplashUi/data/batchexecute?rpcids=Fbv4je', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      },
      body: body.toString(),
      signal: controller.signal,
      cache: 'no-store' as RequestCache,
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`[Resolve] BatchExecute HTTP ${response.status} ${response.statusText}`)
      }
      return null
    }

    const text = await response.text()
    
    // レスポンス文字列から '["garturlres","<URL>",' パターンを抽出
    const urlMatch = text.match(/"garturlres","([^"]+)",/i)
    if (!urlMatch || !urlMatch[1]) {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`[Resolve] Could not extract garturlres from batchExecute response`)
        console.warn(`[Resolve] Response preview: ${text.substring(0, 500)}`)
      }
      return null
    }
    
    const resolvedUrl = urlMatch[1]
    
    // allowedDomains に一致するかチェック
    if (isAllowedDomain(resolvedUrl, allowedDomains)) {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[Resolve] Resolved via BatchExecute: -> ${resolvedUrl}`)
      }
      return resolvedUrl
    }
    
    if (process.env.NODE_ENV === 'development') {
      console.warn(`[Resolve] BatchExecute resolved URL not in allowedDomains: ${resolvedUrl}`)
    }
    return null
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.warn(`[Resolve] Error in resolveViaBatchExecute:`, error)
    }
    return null
  }
}

/**
 * キャッシュキーを生成
 */
function generateCacheKey(url: string, allowedDomains: AllowedDomains): CacheKey {
  const domainsStr = allowedDomains.sort().join(',')
  return `${url}::${domainsStr}`
}

/**
 * リクエスト内の解決件数カウンターをリセット（APIリクエスト開始時に呼ぶ）
 */
export function resetResolveCountInRequest() {
  resolveCountInRequest = 0
}

/**
 * Google News URLを元記事URLに解決（内部実装）
 */
async function resolveGoogleNewsPublisherUrlInternal(
  googleNewsUrl: string,
  allowedDomains: AllowedDomains,
  timeoutMs?: number
): Promise<string | null> {
  // レート制限対策: 1リクエスト内での解決件数制限
  if (resolveCountInRequest >= MAX_RESOLVE_PER_REQUEST) {
    if (process.env.NODE_ENV === 'development') {
      console.warn(`[Resolve] Rate limit: Max ${MAX_RESOLVE_PER_REQUEST} resolves per request reached`)
    }
    return null
  }

  // キャッシュチェック
  const cacheKey = generateCacheKey(googleNewsUrl, allowedDomains)
  const cached = urlCache.get(cacheKey)
  if (cached && cached.expiresAt > Date.now()) {
    if (process.env.NODE_ENV === 'development') {
      console.log(`[Resolve] Cache hit: ${googleNewsUrl} -> ${cached.url || '(null)'}`)
    }
    return cached.url
  }

  // カウンターを増やす
  resolveCountInRequest++

  if (process.env.NODE_ENV === 'development') {
    console.log(`[Resolve] Starting resolution for: ${googleNewsUrl}, allowedDomains: [${allowedDomains.join(', ')}]`)
  }

  try {
    const timeout = timeoutMs || RESOLVE_TIMEOUT_MS

    // A) 最優先: batchexecute直接API方式で解決を試行
    const batchexecuteResult = await resolveViaBatchExecuteDirect(googleNewsUrl, allowedDomains, timeout)
    if (batchexecuteResult) {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[Resolve] Resolved via BatchExecute Direct API: ${googleNewsUrl} -> ${batchexecuteResult}`)
      }
      // キャッシュに保存（成功時は24時間）
      urlCache.set(cacheKey, {
        url: batchexecuteResult,
        expiresAt: Date.now() + CACHE_TTL_MS,
      })
      return batchexecuteResult
    }

    // B) フォールバック: HTML解析方式（従来の方法）
    // タイムアウト付きfetch
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeout)

    try {
      const response = await fetch(googleNewsUrl, {
        redirect: 'follow',
        signal: controller.signal,
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
          'Accept-Language': 'ja,en-US;q=0.8,en;q=0.7',
        },
        cache: 'no-store' as RequestCache,
      })

      clearTimeout(timeoutId)

      // B-1) 最終リダイレクト先が外部ドメインなら最優先で返す
      const finalUrl = response.url
      if (process.env.NODE_ENV === 'development') {
        console.log(`[Resolve] Final URL after redirect: ${finalUrl}`)
      }

      if (finalUrl && !finalUrl.includes('news.google.com') && isAllowedDomain(finalUrl, allowedDomains)) {
        if (process.env.NODE_ENV === 'development') {
          console.log(`[Resolve] Redirect to allowed domain: ${googleNewsUrl} -> ${finalUrl}`)
        }
        // キャッシュに保存（成功時は24時間）
        urlCache.set(cacheKey, {
          url: finalUrl,
          expiresAt: Date.now() + CACHE_TTL_MS,
        })
        return finalUrl
      }

      // B) HTMLから候補抽出してallowedDomainsと照合
      if (!response.ok) {
        if (process.env.NODE_ENV === 'development') {
          console.warn(`[Resolve] HTTP ${response.status} ${response.statusText} for ${googleNewsUrl}`)
        }
        urlCache.set(cacheKey, {
          url: null,
          expiresAt: Date.now() + CACHE_TTL_FAILURE_MS,
        })
        return null
      }

      const html = await response.text()
      if (process.env.NODE_ENV === 'development') {
        console.log(`[Resolve] HTML length: ${html.length} bytes`)
      }

      const candidates: string[] = []

      // B-1) og:urlを抽出
      const ogUrlMatch = html.match(/<meta\s+property=["']og:url["']\s+content=["']([^"']+)["']/i)
      if (ogUrlMatch?.[1]) {
        candidates.push(ogUrlMatch[1])
        if (process.env.NODE_ENV === 'development') {
          console.log(`[Resolve] Found og:url candidate: ${ogUrlMatch[1]}`)
        }
      }

      // B-2) canonicalリンクを抽出
      const canonicalMatch = html.match(/<link\s+rel=["']canonical["']\s+href=["']([^"']+)["']/i)
      if (canonicalMatch?.[1]) {
        candidates.push(canonicalMatch[1])
        if (process.env.NODE_ENV === 'development') {
          console.log(`[Resolve] Found canonical candidate: ${canonicalMatch[1]}`)
        }
      }

      // B-3) google.com/url?url=... を抽出してデコード
      const googleUrlMatches = html.match(/https?:\/\/www\.google\.com\/url\?[^"'\s<>]+/gi) ?? []
      for (const m of googleUrlMatches) {
        const decoded = decodeGoogleUrlParam(m)
        if (decoded) {
          candidates.push(decoded)
          if (process.env.NODE_ENV === 'development') {
            console.log(`[Resolve] Found google.com/url candidate: ${decoded}`)
          }
        }
      }

      // B-4) 生の url=... を拾う（保険）
      const urlParamMatches = html.match(/url=https%3A%2F%2F[^"'\s<>]+/gi) ?? []
      for (const m of urlParamMatches) {
        const raw = m.replace(/^url=/, '')
        try {
          const decoded = decodeURIComponent(raw)
          candidates.push(decoded)
          if (process.env.NODE_ENV === 'development') {
            console.log(`[Resolve] Found url= parameter candidate: ${decoded}`)
          }
        } catch {
          // デコード失敗は無視
        }
      }

      // B-5) 候補の中から許可されたドメインを選択
      let picked = pickFirstAllowed(candidates, allowedDomains)

      // C) 最終フォールバック: batchexecute を使って解決を試行（c-wiz[data-p]方式）
      // ※既に直接API方式は試行済みなので、ここではHTMLからdata-pを抽出する方式のみ
      if (!picked) {
        if (process.env.NODE_ENV === 'development') {
          console.log(`[Resolve] Trying BatchExecute fallback (c-wiz[data-p]): ${googleNewsUrl}`)
        }
        
        const dataPObject = await getBatchExecuteParams(googleNewsUrl)
        if (dataPObject) {
          picked = await resolveViaBatchExecute(dataPObject, allowedDomains)
        } else {
          if (process.env.NODE_ENV === 'development') {
            console.warn(`[Resolve] Could not get BatchExecute params from c-wiz[data-p] for: ${googleNewsUrl}`)
          }
        }
      }

      // キャッシュに保存（成功時は24時間、失敗時は10秒）
      urlCache.set(cacheKey, {
        url: picked,
        expiresAt: Date.now() + (picked ? CACHE_TTL_MS : CACHE_TTL_FAILURE_MS),
      })

      if (picked) {
        if (process.env.NODE_ENV === 'development') {
          console.log(`[Resolve] Resolved: ${googleNewsUrl} -> ${picked}`)
        }
      } else {
        // 詳細なデバッグ情報を出力（本番でも出力して問題を特定）
        console.warn(`[Resolve] Failed to resolve: ${googleNewsUrl}`)
        console.warn(`[Resolve] Final URL: ${finalUrl}`)
        console.warn(`[Resolve] Candidates found: ${candidates.length}, allowedDomains: [${allowedDomains.join(', ')}]`)
        if (candidates.length > 0) {
          console.warn(`[Resolve] All candidates:`, candidates)
          // 各候補がallowedDomainsとマッチしない理由を確認
          for (const c of candidates.slice(0, 5)) {
            try {
              const host = new URL(c).hostname.toLowerCase()
              const normalizedDomains = allowedDomains.map(normalizeDomain)
              const matches = normalizedDomains.some((d) => host === d || host.endsWith(`.${d}`))
              console.warn(`[Resolve] Candidate: ${c} -> host: ${host}, matches: ${matches}`)
            } catch (e) {
              console.warn(`[Resolve] Candidate: ${c} -> invalid URL`)
            }
          }
        } else {
          console.warn(`[Resolve] No candidates extracted. HTML preview (first 1000 chars): ${html.substring(0, 1000)}`)
        }
      }

      return picked
    } catch (error) {
      clearTimeout(timeoutId)
      if (error instanceof Error && error.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.warn(`[Resolve] Timeout: ${googleNewsUrl}`)
        }
        // タイムアウトエラーは再スローせず、nullを返す
        urlCache.set(cacheKey, {
          url: null,
          expiresAt: Date.now() + CACHE_TTL_FAILURE_MS,
        })
        return null
      }
      throw error
    }
  } catch (error) {
    // エラー時はnullを返す（フォールバックを許可）
    const errorMessage = error instanceof Error ? error.message : String(error)
    const errorName = error instanceof Error ? error.name : 'Unknown'
    
    if (process.env.NODE_ENV === 'development') {
      console.warn(`[Resolve] Error resolving ${googleNewsUrl}:`, {
        name: errorName,
        message: errorMessage,
        stack: error instanceof Error ? error.stack : undefined,
      })
    }
    // エラーもキャッシュに保存（失敗時は10秒）
    const cacheKey = generateCacheKey(googleNewsUrl, allowedDomains)
    urlCache.set(cacheKey, {
      url: null,
      expiresAt: Date.now() + CACHE_TTL_FAILURE_MS,
    })
    return null
  }
}

/**
 * リクエストキューを処理
 */
async function processQueue(): Promise<void> {
  if (activeRequestCount >= MAX_CONCURRENT_REQUESTS || requestQueue.length === 0) {
    return
  }

  const request = requestQueue.shift()
  if (!request) {
    return
  }

  const { resolve, reject, url, allowedDomains, timeoutMs } = request
  activeRequestCount++

  try {
    const result = await resolveGoogleNewsPublisherUrlInternal(url, allowedDomains, timeoutMs)
    resolve(result)
  } catch (error) {
    // エラー時もnullを返す（フォールバックを許可）
    resolve(null)
    if (process.env.NODE_ENV === 'development') {
      console.error(`[Resolve] Queue error for ${url}:`, error)
    }
  } finally {
    activeRequestCount--
    // 次のリクエストを処理（非同期で）
    setImmediate(() => {
      processQueue().catch(err => {
        if (process.env.NODE_ENV === 'development') {
          console.error('[Resolve] Queue processing error:', err)
        }
      })
    })
  }
}

/**
 * Google News URLを元記事URLに解決（公開API）
 * 
 * 同時実行数制限とキューイングを管理
 * 
 * @param googleNewsUrl Google NewsのリダイレクトURL
 * @param allowedDomains 許可されたドメインの配列（例: ["hochi.news", "sanspo.com"]）
 * @returns 解決された記事URL、またはnull（解決失敗時）
 */
export async function resolveGoogleNewsPublisherUrl(
  googleNewsUrl: string,
  allowedDomains: AllowedDomains,
  options?: { timeoutMs?: number }
): Promise<string | null> {
  // Google News URLでない場合はそのまま返す
  if (!googleNewsUrl.includes('news.google.com')) {
    return null
  }

  // allowedDomainsが空の場合はnullを返す
  if (!allowedDomains || allowedDomains.length === 0) {
    if (process.env.NODE_ENV === 'development') {
      console.warn(`[Resolve] No allowedDomains provided for ${googleNewsUrl}`)
    }
    return null
  }

  // キューに追加
  return new Promise<string | null>((resolve, reject) => {
    requestQueue.push({ 
      resolve: (value) => {
        try {
          resolve(value)
        } catch (error) {
          reject(error)
        }
      }, 
      reject, 
      url: googleNewsUrl,
      allowedDomains,
      timeoutMs: options?.timeoutMs
    })
    // 非同期でキューを処理（エラーが発生しても次のリクエストを処理できるように）
    setImmediate(() => {
      processQueue().catch(error => {
        // キュー処理のエラーは無視（個別のリクエストのエラーハンドリングに任せる）
        if (process.env.NODE_ENV === 'development') {
          console.error('[Resolve] Queue processing error:', error)
        }
      })
    })
  })
}

/**
 * キャッシュをクリア（デバッグ用）
 */
export function clearResolveCache() {
  urlCache.clear()
  if (process.env.NODE_ENV === 'development') {
    console.log('[Resolve] Cache cleared')
  }
}

/**
 * キャッシュ統計を取得（デバッグ用）
 */
export function getResolveCacheStats() {
  const now = Date.now()
  const validEntries = Array.from(urlCache.values()).filter(
    entry => entry.expiresAt > now
  )
  return {
    totalEntries: urlCache.size,
    validEntries: validEntries.length,
    expiredEntries: urlCache.size - validEntries.length,
  }
}
