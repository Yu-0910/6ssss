/**
 * Yahoo!ニュース記事ページから元記事URL（publisher URL）を抽出
 * 
 * Yahoo記事ページ（news.yahoo.co.jp/...）から
 * 実際の記事URL（例: hochi.news/articles/..., sanspo.com/article/...）を抽出する
 */

export function normalizeDomain(d: string): string {
  return d.replace(/^https?:\/\//, "").replace(/\/+$/, "").toLowerCase()
}

/**
 * ホスト名を正規化（小文字化 + www.除去）
 */
export function normalizeHost(host: string | null | undefined): string {
  if (!host) return ''
  const normalized = host.toLowerCase().trim()
  // www. を除去
  if (normalized.startsWith('www.')) {
    return normalized.substring(4)
  }
  return normalized
}

function isAllowedDomainUrl(u: string, allowed: string[]): boolean {
  try {
    const host = new URL(u).hostname.toLowerCase()
    return allowed.map(normalizeDomain).some((d) => host === d || host.endsWith(`.${d}`))
  } catch {
    return false
  }
}

/**
 * URLが許可されたドメインに一致するかチェック（normalizeHost 前提）
 */
function isAllowedUrl(url: string, allowedDomains: string[]): boolean {
  try {
    const urlObj = new URL(url)
    const host = normalizeHost(urlObj.hostname)
    
    // allowedDomainsも正規化してSet化
    const normalizedAllowed = new Set(
      allowedDomains.map(d => normalizeDomain(d)).map(d => normalizeHost(d))
    )
    
    // Yahooドメインは除外
    if (host.includes('yahoo.co.jp') || host.includes('yahoo.com')) {
      return false
    }
    
    return normalizedAllowed.has(host) || 
           Array.from(normalizedAllowed).some(allowed => host.endsWith(`.${allowed}`))
  } catch {
    return false
  }
}

function extractJsonLdBlocks(html: string): string[] {
  const blocks: string[] = []
  const re = /<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(html))) {
    const raw = m[1]?.trim()
    if (raw) blocks.push(raw)
  }
  return blocks
}

export function tryFindUrlInJsonLd(obj: any, allowedDomains: string[]): string | null {
  const candidates: string[] = []
  const push = (v: any) => {
    if (typeof v === "string") candidates.push(v)
    if (v && typeof v === "object" && typeof v.url === "string") candidates.push(v.url)
  }

  push(obj?.url)
  push(obj?.mainEntityOfPage)
  push(obj?.isBasedOn)
  push(obj?.isBasedOnUrl)
  push(obj?.sameAs)

  if (Array.isArray(obj?.isBasedOn)) obj.isBasedOn.forEach(push)
  if (Array.isArray(obj?.mainEntityOfPage)) obj.mainEntityOfPage.forEach(push)
  if (Array.isArray(obj?.sameAs)) obj.sameAs.forEach(push)

  for (const c of candidates) {
    if (isAllowedDomainUrl(c, allowedDomains)) return c
  }
  return null
}

export function extractAllowedUrlsFromHtml(html: string, allowedDomains: string[]): string[] {
  const urls: string[] = []
  const re = /href=["'](https?:\/\/[^"']+)["']/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(html))) {
    const u = m[1]
    if (u && isAllowedDomainUrl(u, allowedDomains)) urls.push(u)
  }
  // 直書きURLも拾う（保険）
  for (const d of allowedDomains.map(normalizeDomain)) {
    const re2 = new RegExp(`https?:\\/\\/[^\\s"'<>]*${d.replace(/\./g, "\\.")}[^\\s"'<>]*`, "gi")
    const ms = html.match(re2) ?? []
    for (const u of ms) if (isAllowedDomainUrl(u, allowedDomains)) urls.push(u)
  }
  return Array.from(new Set(urls))
}

/**
 * HTMLから allowedDomains に一致するホストを抽出（URLがなくてもホストのみ抽出）
 */
/**
 * __NEXT_DATA__ スクリプトタグからJSONを抽出
 */
function extractNextDataJson(html: string): any | null {
  const match = html.match(/<script[^>]*id=["']__NEXT_DATA__["'][^>]*type=["']application\/json["'][^>]*>([\s\S]*?)<\/script>/i)
  if (!match || !match[1]) {
    return null
  }
  
  try {
    const jsonStr = match[1].trim()
    return JSON.parse(jsonStr)
  } catch {
    return null
  }
}

/**
 * オブジェクトを再帰探索してallowedDomainsを含むURL候補を抽出
 */
function findAllowedUrlsInObject(
  obj: any,
  allowedDomains: string[],
  depth: number = 0,
  maxDepth: number = 12
): string[] {
  if (depth > maxDepth) return []
  
  const candidates: string[] = []
  
  if (typeof obj === 'string') {
    // 文字列からURL候補を抽出
    const urlPatterns = [
      // 通常URL
      /https?:\/\/[^\s"',\)\]\}]+/gi,
      // JSONエスケープURL (\/)
      /https?:\\\/\\\/[^\s"',\)\]\}]+/gi,
      // URLエンコード
      /https?%3A%2F%2F[^\s"',\)\]\}]+/gi,
    ]
    
    for (const pattern of urlPatterns) {
      const matches = obj.match(pattern) ?? []
      for (const match of matches) {
        let url: string | null = null
        
        // 優先1: 通常URL
        if (match.startsWith('http://') || match.startsWith('https://')) {
          url = match.trim().replace(/[,\)\]\}]$/, '')
        }
        // 優先2: JSONエスケープを戻す
        else if (match.includes('\\/')) {
          try {
            const unescaped = match.replace(/\\\//g, '/').replace(/\\"/g, '"').trim()
            if (unescaped.startsWith('http://') || unescaped.startsWith('https://')) {
              url = unescaped.replace(/[,\)\]\}]$/, '')
            }
          } catch {
            // 無視
          }
        }
        // 優先3: URLデコード
        else if (match.includes('%')) {
          try {
            const decoded = decodeURIComponent(match)
            if (decoded.startsWith('http://') || decoded.startsWith('https://')) {
              url = decoded.trim().replace(/[,\)\]\}]$/, '')
            }
          } catch {
            // 無視
          }
        }
        
        if (url && isAllowedUrl(url, allowedDomains)) {
          candidates.push(url)
        }
      }
    }
  } else if (Array.isArray(obj)) {
    for (const item of obj) {
      candidates.push(...findAllowedUrlsInObject(item, allowedDomains, depth + 1, maxDepth))
    }
  } else if (obj && typeof obj === 'object') {
    for (const key in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        candidates.push(...findAllowedUrlsInObject(obj[key], allowedDomains, depth + 1, maxDepth))
      }
    }
  }
  
  return Array.from(new Set(candidates))
}

/**
 * HTML全文から強制的にURL候補を抽出（スクリプト内のエスケープURLも含む）
 */
export function findAllowedUrlsInRawText(text: string, allowedDomains: string[]): string[] {
  const candidates: string[] = []
  const normalizedAllowed = allowedDomains.map(d => normalizeDomain(d)).map(d => normalizeHost(d))
  
  for (const domain of normalizedAllowed) {
    const domainEscaped = domain.replace(/\./g, '\\.')
    
    // 正規URL: https?://(www.)?{domain}/...
    const normalPattern = new RegExp(`https?:\\/\\/(www\\.)?${domainEscaped}[^\\s"'<>\\)\\]\\}]+`, 'gi')
    const normalMatches = text.match(normalPattern) ?? []
    for (const match of normalMatches) {
      const url = match.trim().replace(/[,\)\]\}]$/, '')
      if (isAllowedUrl(url, allowedDomains)) {
        candidates.push(url)
      }
    }
    
    // JSONエスケープURL: https?:\\\/\\\/{domain}\\\/...
    const jsonPattern = new RegExp(`https?:\\\\\\/\\\\\\/(www\\.)?${domainEscaped}[^\\s"'<>\\)\\]\\}]+`, 'gi')
    const jsonMatches = text.match(jsonPattern) ?? []
    for (const match of jsonMatches) {
      try {
        const unescaped = match.replace(/\\\//g, '/').replace(/\\"/g, '"').trim()
        const url = unescaped.replace(/[,\)\]\}]$/, '')
        if (isAllowedUrl(url, allowedDomains)) {
          candidates.push(url)
        }
      } catch {
        // 無視
      }
    }
    
    // クエリ内URL: (u|url|link)=https%3A%2F%2F{domain}%2F...
    const queryPattern = new RegExp(`(?:[?&])(?:u|url|link)=https?%3A%2F%2F(www\\.)?${domainEscaped}[^\\s"'<>&]+`, 'gi')
    const queryMatches = text.match(queryPattern) ?? []
    for (const match of queryMatches) {
      try {
        const urlParam = match.replace(/^[?&](?:u|url|link)=/, '')
        const decoded = decodeURIComponent(urlParam)
        if (isAllowedUrl(decoded, allowedDomains)) {
          candidates.push(decoded)
        }
      } catch {
        // 無視
      }
    }
  }
  
  return Array.from(new Set(candidates))
}

export function extractAllowedHostsFromHtml(html: string, allowedDomains: string[]): string[] {
  const hosts: string[] = []
  const normalizedAllowed = allowedDomains.map(normalizeDomain).map(normalizeHost)
  
  // href からホストを抽出
  const hrefRe = /href=["']https?:\/\/([^"'/?#]+)/gi
  let m: RegExpExecArray | null
  while ((m = hrefRe.exec(html))) {
    const host = normalizeHost(m[1])
    if (normalizedAllowed.some(allowed => host === allowed || host.endsWith(`.${allowed}`))) {
      hosts.push(host)
    }
  }
  
  // 直書きホストも拾う
  for (const d of normalizedAllowed) {
    const hostRe = new RegExp(`https?:\\/\\/(www\\.)?${d.replace(/\./g, "\\.")}`, "gi")
    const ms = html.match(hostRe) ?? []
    for (const match of ms) {
      try {
        // matchが完全なURL形式でない場合があるので、http://を補完
        const urlStr = match.startsWith('http://') || match.startsWith('https://') 
          ? match 
          : `https://${match}`
        const url = new URL(urlStr)
        const host = normalizeHost(url.hostname)
        if (!hosts.includes(host)) {
          hosts.push(host)
        }
      } catch {
        // URLパース失敗は無視
      }
    }
  }
  
  return Array.from(new Set(hosts))
}

/**
 * 媒体名からホスト名へのマッピング
 */
export function publisherNameToHost(name: string): string | null {
  const nameLower = name.toLowerCase()
  const mappings: Record<string, string> = {
    'スポーツ報知': 'hochi.news',
    '報知': 'hochi.news',
    'hochi': 'hochi.news',
    'サンケイスポーツ': 'sanspo.com',
    'サンスポ': 'sanspo.com',
    'sanspo': 'sanspo.com',
  }
  
  for (const [key, host] of Object.entries(mappings)) {
    if (nameLower.includes(key.toLowerCase())) {
      return host
    }
  }
  
  return null
}

/**
 * pickup HTMLからYahoo記事URL（/articles/<id>）を抽出
 */
function extractYahooArticlesUrlFromPickup(
  pickupHtml: string,
  commentsUrl?: string | null,
  debug = false
): { articlesUrl: string | null; method: "comments" | "html" | "raw" | "none"; candidates: string[] } {
  const candidates: string[] = []
  
  // A) commentsUrlが /articles/<id>/comments なら、/commentsを外して articlesUrlを作る
  if (commentsUrl) {
    const commentsMatch = commentsUrl.match(/^(https?:\/\/news\.yahoo\.co\.jp\/articles\/[0-9a-f]{16,})\/comments/i)
    if (commentsMatch && commentsMatch[1]) {
      const articlesUrl = commentsMatch[1]
      if (debug) {
        console.log(`[YahooResolve] Extracted articlesUrl from commentsUrl: ${articlesUrl}`)
      }
      return { articlesUrl, method: "comments", candidates: [articlesUrl] }
    }
  }
  
  // B) pickup HTMLから articlesUrlを抽出（allowedDomainsではなく、Yahoo articles自体を探す）
  // パターン1: 完全なURL形式
  const fullUrlPattern = /https?:\/\/news\.yahoo\.co\.jp\/articles\/[0-9a-f]{16,}/gi
  const fullMatches = pickupHtml.match(fullUrlPattern) ?? []
  for (const match of fullMatches) {
    const url = match.trim().replace(/[,\)\]\}]$/, '')
    if (!candidates.includes(url)) {
      candidates.push(url)
    }
  }
  
  // パターン2: 相対パス形式（/articles/...）
  const relativePattern = /\/articles\/[0-9a-f]{16,}/gi
  const relativeMatches = pickupHtml.match(relativePattern) ?? []
  for (const match of relativeMatches) {
    const path = match.trim().replace(/[,\)\]\}]$/, '')
    const url = `https://news.yahoo.co.jp${path}`
    if (!candidates.includes(url)) {
      candidates.push(url)
    }
  }
  
  // パターン3: JSONエスケープされたURL
  const escapedPattern = /https?:\\\/\\\/news\.yahoo\.co\.jp\\\/articles\\\/[0-9a-f]{16,}/gi
  const escapedMatches = pickupHtml.match(escapedPattern) ?? []
  for (const match of escapedMatches) {
    try {
      const unescaped = match.replace(/\\\//g, '/').replace(/\\"/g, '"').trim()
      const url = unescaped.replace(/[,\)\]\}]$/, '')
      if (!candidates.includes(url)) {
        candidates.push(url)
      }
    } catch {
      // 無視
    }
  }
  
  // パターン4: URLエンコードされたURL
  const encodedPattern = /https?%3A%2F%2Fnews\.yahoo\.co\.jp%2Farticles%2F[0-9a-f]{16,}/gi
  const encodedMatches = pickupHtml.match(encodedPattern) ?? []
  for (const match of encodedMatches) {
    try {
      const decoded = decodeURIComponent(match)
      const url = decoded.trim().replace(/[,\)\]\}]$/, '')
      if (!candidates.includes(url)) {
        candidates.push(url)
      }
    } catch {
      // 無視
    }
  }
  
  // 候補から最初の妥当なものを選択
  let uniqueCandidates = Array.from(new Set(candidates)).slice(0, 10)
  
  if (uniqueCandidates.length > 0) {
    const method = fullMatches.length > 0 ? "html" : "raw"
    const articlesUrl = uniqueCandidates[0]
    if (debug) {
      console.log(`[YahooResolve] Extracted articlesUrl from pickup HTML (${method}): ${articlesUrl}`)
      console.log(`[YahooResolve] Found ${uniqueCandidates.length} articles candidates:`, uniqueCandidates.slice(0, 5))
    }
    return { articlesUrl, method, candidates: uniqueCandidates }
  }
  
  // C) pickup HTML内の "articles/" を含む文字列を片っ端から候補化
  const fallbackPattern = /["']([^"']*\/articles\/[^"']*[0-9a-f]{16,}[^"']*)["']/gi
  const fallbackMatches = pickupHtml.match(fallbackPattern) ?? []
  for (const match of fallbackMatches) {
    const extracted = match.replace(/^["']|["']$/g, '')
    if (extracted.includes('/articles/')) {
      let url: string | null = null
      
      if (extracted.startsWith('http://') || extracted.startsWith('https://')) {
        url = extracted
      } else if (extracted.startsWith('/')) {
        url = `https://news.yahoo.co.jp${extracted.split(/[,\s\)\]\}]/)[0]}`
      } else {
        const articlesMatch = extracted.match(/(articles\/[0-9a-f]{16,})/i)
        if (articlesMatch) {
          url = `https://news.yahoo.co.jp/${articlesMatch[1]}`
        }
      }
      
      if (url && !uniqueCandidates.includes(url)) {
        uniqueCandidates.push(url)
      }
    }
  }
  
  if (uniqueCandidates.length > 0) {
    const articlesUrl = uniqueCandidates[0]
    if (debug) {
      console.log(`[YahooResolve] Extracted articlesUrl from fallback search: ${articlesUrl}`)
    }
    return { articlesUrl, method: "raw", candidates: uniqueCandidates.slice(0, 10) }
  }
  
  if (debug) {
    console.warn(`[YahooResolve] Failed to extract articlesUrl from pickup HTML`)
  }
  
  return { articlesUrl: null, method: "none", candidates: [] }
}

/**
 * HTMLから媒体名を抽出（画像altやヘッダーテキストから）
 */
export function extractPublisherNameFromHtml(html: string): string | null {
  // 画像alt属性から抽出
  const imgAltRe = /<img[^>]+alt=["']([^"']+)["']/gi
  let m: RegExpExecArray | null
  while ((m = imgAltRe.exec(html))) {
    const alt = m[1]
    if (alt.includes('報知') || alt.includes('サンケイ') || alt.includes('サンスポ')) {
      return alt
    }
  }
  
  // ヘッダー付近のテキストから抽出（最初の10000文字以内）
  const headerText = html.substring(0, 10000)
  const textMatches = [
    /(スポーツ報知|報知)/i,
    /(サンケイスポーツ|サンスポ)/i,
  ]
  
  for (const re of textMatches) {
    const match = headerText.match(re)
    if (match && match[1]) {
      return match[1]
    }
  }
  
  return null
}

/**
 * Yahoo記事ページから抽出した情報
 */
export type YahooOriginalInfo = {
  originalUrl: string | null
  publisherHost: string | null
  publisherName: string | null
  debugInfo?: {
    pickupUrl?: string
    commentsUrl?: string | null
    guid?: string | null
    pickupFetch?: {
      ok: boolean
      status: number
      finalUrl: string
      contentType: string | null
      bytes: number
    }
    extractedArticlesCandidates?: string[] // 最大10件
    chosenArticlesUrl?: string | null
    chosenArticlesBy?: "comments" | "html" | "raw" | "none"
    articlesFetch?: {
      ok: boolean
      status: number
      finalUrl: string
      contentType: string | null
      bytes: number
    }
    originalCandidates?: {
      html: string[]
      jsonld: string[]
      raw: string[]
    }
    chosenOriginalUrl?: string | null
    chosenOriginalBy?: "html" | "jsonld" | "raw" | "none"
    publisherHostSource?: string | null
  }
}

/**
 * Yahoo記事ページから元記事URLと配信元情報を抽出（2段階解決版）
 * 
 * 段階1: pickup URL (/pickup/...) から Yahoo記事URL (/articles/<id>) を抽出
 * 段階2: Yahoo記事URL から 元記事URL (hochi.news / sanspo.com 等) を抽出
 */
export async function resolveYahooOriginalInfo(
  yahooArticleUrl: string,
  allowedDomains: string[],
  debug = false,
  commentsUrl?: string | null,
  guid?: string | null
): Promise<YahooOriginalInfo> {
  const result: YahooOriginalInfo = {
    originalUrl: null,
    publisherHost: null,
    publisherName: null,
  }

  // debugInfo用の変数
  let fetchInfo: YahooOriginalInfo["debugInfo"] = undefined

  try {
    if (debug || process.env.NODE_ENV === 'development') {
      console.log(`[YahooResolve] Starting 2-stage resolution for: ${yahooArticleUrl}`)
      console.log(`[YahooResolve] Allowed domains: [${allowedDomains.join(', ')}]`)
      if (commentsUrl) console.log(`[YahooResolve] Comments URL: ${commentsUrl}`)
      if (guid) console.log(`[YahooResolve] GUID: ${guid}`)
    }

    // ===== 段階1: pickup HTMLから Yahoo記事URL (/articles/<id>) を抽出 =====
    const pickupRes = await fetch(yahooArticleUrl, {
      redirect: "follow",
      cache: "no-store" as RequestCache,
      headers: {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "ja,en-US;q=0.9,en;q=0.8",
      },
    })

    const pickupFinalUrl = pickupRes.url || yahooArticleUrl
    const pickupContentType = pickupRes.headers.get('content-type')
    const pickupHtml = await pickupRes.text()
    const pickupBytes = pickupHtml.length

    // debugInfo初期化
    if (debug) {
      fetchInfo = {
        pickupUrl: yahooArticleUrl,
        commentsUrl: commentsUrl || null,
        guid: guid || null,
        pickupFetch: {
          ok: pickupRes.ok,
          status: pickupRes.status,
          finalUrl: pickupFinalUrl,
          contentType: pickupContentType,
          bytes: pickupBytes,
        },
        extractedArticlesCandidates: [],
        chosenArticlesUrl: null,
        chosenArticlesBy: "none",
      }
    }

    if (!pickupRes.ok) {
      if (debug || process.env.NODE_ENV === 'development') {
        console.warn(`[YahooResolve] HTTP ${pickupRes.status} for pickup URL: ${yahooArticleUrl}`)
      }
      if (debug && fetchInfo) {
        result.debugInfo = fetchInfo
      }
      return result
    }

    // pickup HTMLから articles URLを抽出
    const articlesResult = extractYahooArticlesUrlFromPickup(pickupHtml, commentsUrl, debug)
    const articlesUrl = articlesResult.articlesUrl

    if (debug && fetchInfo) {
      fetchInfo.extractedArticlesCandidates = articlesResult.candidates.slice(0, 10)
      fetchInfo.chosenArticlesUrl = articlesUrl
      fetchInfo.chosenArticlesBy = articlesResult.method
    }

    if (!articlesUrl) {
      if (debug || process.env.NODE_ENV === 'development') {
        console.warn(`[YahooResolve] Failed to extract articles URL from pickup: ${yahooArticleUrl}`)
      }
      if (debug && fetchInfo) {
        result.debugInfo = fetchInfo
      }
      return result
    }

    if (debug || process.env.NODE_ENV === 'development') {
      console.log(`[YahooResolve] Extracted articles URL: ${articlesUrl} (method: ${articlesResult.method})`)
    }

    // ===== 段階2: articles HTMLから 元記事URL (allowedDomains) を抽出 =====
    const articlesRes = await fetch(articlesUrl, {
      redirect: "follow",
      cache: "no-store" as RequestCache,
      headers: {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "ja,en-US;q=0.9,en;q=0.8",
      },
    })

    const articlesFinalUrl = articlesRes.url || articlesUrl
    const articlesContentType = articlesRes.headers.get('content-type')
    const articlesHtml = await articlesRes.text()
    const articlesBytes = articlesHtml.length

    if (debug && fetchInfo) {
      fetchInfo.articlesFetch = {
        ok: articlesRes.ok,
        status: articlesRes.status,
        finalUrl: articlesFinalUrl,
        contentType: articlesContentType,
        bytes: articlesBytes,
      }
      fetchInfo.originalCandidates = {
        html: [],
        jsonld: [],
        raw: [],
      }
      fetchInfo.chosenOriginalUrl = null
      fetchInfo.chosenOriginalBy = "none"
    }

    if (!articlesRes.ok) {
      if (debug || process.env.NODE_ENV === 'development') {
        console.warn(`[YahooResolve] HTTP ${articlesRes.status} for articles URL: ${articlesUrl}`)
      }
      if (debug && fetchInfo) {
        result.debugInfo = fetchInfo
      }
      return result
    }

    if (debug || process.env.NODE_ENV === 'development') {
      console.log(`[YahooResolve] Articles HTML length: ${articlesHtml.length} bytes`)
    }

    // A) HTMLリンクから allowedDomains を含むURLを抽出
    const allowedUrls = extractAllowedUrlsFromHtml(articlesHtml, allowedDomains)
    if (debug && fetchInfo && fetchInfo.originalCandidates) {
      fetchInfo.originalCandidates.html = allowedUrls.slice(0, 3)
    }
    
    if (allowedUrls.length > 0) {
      // トップページ（/ のみ）を除外して候補をフィルタ
      const articleUrls = allowedUrls.filter(url => {
        try {
          const urlObj = new URL(url)
          // パスが / のみ、またはパスが空の場合は除外
          return urlObj.pathname !== '/' && urlObj.pathname.length > 1
        } catch {
          return true // パース失敗は除外しない
        }
      })
      
      // 記事URLが見つかった場合はそれを使用、なければ全候補を使用
      const candidatesToUse = articleUrls.length > 0 ? articleUrls : allowedUrls
      
      // 複数候補がある場合: 完全一致のhostを優先、それでも複数なら記事URLを優先
      let selected = candidatesToUse[0]
      
      const normalizedAllowed = new Set(allowedDomains.map(d => normalizeDomain(d)).map(d => normalizeHost(d)))
      const exactMatches = candidatesToUse.filter(url => {
        try {
          const urlObj = new URL(url)
          const host = normalizeHost(urlObj.hostname)
          return normalizedAllowed.has(host)
        } catch {
          return false
        }
      })
      
      if (exactMatches.length > 0) {
        // 記事URL（トップページ以外）を優先
        const articleExactMatches = exactMatches.filter(url => {
          try {
            const urlObj = new URL(url)
            return urlObj.pathname !== '/' && urlObj.pathname.length > 1
          } catch {
            return false
          }
        })
        selected = articleExactMatches.length > 0 ? articleExactMatches[0] : exactMatches[0]
      }
      
      // 複数候補がある場合は記事URLを優先（トップページでないものを選択）
      if (candidatesToUse.length > 1) {
        const articleOnly = candidatesToUse.filter(url => {
          try {
            const urlObj = new URL(url)
            return urlObj.pathname !== '/' && urlObj.pathname.length > 1
          } catch {
            return false
          }
        })
        if (articleOnly.length > 0) {
          selected = articleOnly[0]
        }
      }
      
      result.originalUrl = selected
      if (debug && fetchInfo) {
        fetchInfo.chosenOriginalUrl = selected
        fetchInfo.chosenOriginalBy = "html"
      }
      
      try {
        const url = new URL(selected)
        result.publisherHost = normalizeHost(url.hostname)
      } catch {
        // URLパース失敗は無視
      }
      
      if (debug || process.env.NODE_ENV === 'development') {
        console.log(`[YahooResolve] Resolved via HTML links: ${articlesUrl} -> ${selected}`)
      }
      if (debug && fetchInfo) {
        result.debugInfo = fetchInfo
      }
      return result
    }

    // B) JSON-LDから拾う
    const blocks = extractJsonLdBlocks(articlesHtml)
    const jsonLdCandidates: string[] = []
    
    if (debug || process.env.NODE_ENV === 'development') {
      console.log(`[YahooResolve] Found ${blocks.length} JSON-LD blocks`)
    }
    
    for (const b of blocks) {
      try {
        const parsed = JSON.parse(b)
        const items = Array.isArray(parsed) ? parsed : [parsed]
        for (const it of items) {
          const u = tryFindUrlInJsonLd(it, allowedDomains)
          if (u) {
            if (jsonLdCandidates.length < 3) {
              jsonLdCandidates.push(u)
            }
            
            result.originalUrl = u
            if (debug && fetchInfo) {
              fetchInfo.chosenOriginalUrl = u
              fetchInfo.chosenOriginalBy = "jsonld"
            }
            
            try {
              const url = new URL(u)
              result.publisherHost = normalizeHost(url.hostname)
            } catch {
              // URLパース失敗は無視
            }
            
            if (debug || process.env.NODE_ENV === 'development') {
              console.log(`[YahooResolve] Resolved via JSON-LD: ${articlesUrl} -> ${u}`)
            }
            if (debug && fetchInfo) {
              if (fetchInfo.originalCandidates) {
                fetchInfo.originalCandidates.jsonld = jsonLdCandidates
              }
              result.debugInfo = fetchInfo
            }
            return result
          }
        }
      } catch (parseError) {
        // JSONパースエラーは無視
      }
    }
    
    if (debug && fetchInfo && fetchInfo.originalCandidates) {
      fetchInfo.originalCandidates.jsonld = jsonLdCandidates
    }

    // C) HTML全文から強制探索
    const rawTextUrls = findAllowedUrlsInRawText(articlesHtml, allowedDomains)
    
    if (debug && fetchInfo && fetchInfo.originalCandidates) {
      fetchInfo.originalCandidates.raw = rawTextUrls.slice(0, 3)
    }
    
    if (rawTextUrls.length > 0) {
      const selected = rawTextUrls[0]
      result.originalUrl = selected
      if (debug && fetchInfo) {
        fetchInfo.chosenOriginalUrl = selected
        fetchInfo.chosenOriginalBy = "raw"
      }
      
      try {
        const url = new URL(selected)
        result.publisherHost = normalizeHost(url.hostname)
      } catch {
        // URLパース失敗は無視
      }
      
      if (debug || process.env.NODE_ENV === 'development') {
        console.log(`[YahooResolve] Found ${rawTextUrls.length} allowed URLs via raw text:`, rawTextUrls.slice(0, 3))
        console.log(`[YahooResolve] Resolved via raw text: ${articlesUrl} -> ${selected}`)
      }
      if (debug && fetchInfo) {
        result.debugInfo = fetchInfo
      }
      return result
    }

    // D) originalUrlが取れなかった場合、publisherHostを抽出（配信元判定用）
    const allowedHosts = extractAllowedHostsFromHtml(articlesHtml, allowedDomains)
    if (allowedHosts.length > 0) {
      result.publisherHost = allowedHosts[0]
      if (debug || process.env.NODE_ENV === 'development') {
        console.log(`[YahooResolve] Extracted publisherHost from HTML: ${allowedHosts[0]}`)
      }
    } else {
      // 媒体名からホスト名を推定
      const publisherName = extractPublisherNameFromHtml(articlesHtml)
      if (publisherName) {
        result.publisherName = publisherName
        const hostFromName = publisherNameToHost(publisherName)
        if (hostFromName) {
          result.publisherHost = hostFromName
          if (debug || process.env.NODE_ENV === 'development') {
            console.log(`[YahooResolve] Extracted publisherHost from name: ${publisherName} -> ${hostFromName}`)
          }
        }
      }
    }

    if (debug && fetchInfo) {
      if (result.publisherHost) {
        fetchInfo.publisherHostSource = result.publisherHost
      }
    }

    if (debug || process.env.NODE_ENV === 'development') {
      if (!result.originalUrl && !result.publisherHost) {
        console.warn(`[YahooResolve] Failed to resolve: ${yahooArticleUrl} -> ${articlesUrl} (no allowed domain URL or host found)`)
      } else if (!result.originalUrl && result.publisherHost) {
        console.log(`[YahooResolve] No originalUrl but publisherHost found: ${result.publisherHost}`)
      }
    }

    // debugModeのときだけdebugInfoを設定
    if (debug && fetchInfo) {
      result.debugInfo = fetchInfo
    }

    return result
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error)
    if (debug || process.env.NODE_ENV === 'development') {
      console.error(`[YahooResolve] Error resolving ${yahooArticleUrl}:`, errorMessage)
    }
    // エラー時もdebugInfoがあれば設定
    if (debug && fetchInfo) {
      fetchInfo.chosenOriginalBy = "none"
      result.debugInfo = fetchInfo
    }
    return result
  }
}

/**
 * Yahoo記事ページから元記事URLを抽出（互換性のためのラッパー）
 */
/**
 * Yahoo記事ページから元記事URLを抽出（互換性のためのラッパー）
 */
export async function resolveYahooOriginalUrl(
  yahooArticleUrl: string,
  allowedDomains: string[],
  debug = false
): Promise<string | null> {
  const info = await resolveYahooOriginalInfo(yahooArticleUrl, allowedDomains, debug)
  return info.originalUrl
}

