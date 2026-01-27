/**
 * dmenuスポーツ（service.smt.docomo.ne.jp）のXHR/JSON APIを自動で探索するプローブスクリプト
 * 
 * 実行方法: node scripts/probe_dmenu_xhr.mjs
 */

import { readFileSync, writeFileSync, mkdirSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'
import https from 'https'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const projectRoot = join(__dirname, '..')

// dmenuニュース一覧ページ
const DMENU_LIST_PAGE_URL = 'https://service.smt.docomo.ne.jp/portal/sports/baseball_j/index.html'

// ログ出力先
const LOGS_DIR = join(projectRoot, 'logs', 'dmenu_probe')
const URLS_FILE = join(LOGS_DIR, 'urls.txt')
const RESPONSES_DIR = join(LOGS_DIR, 'responses')
const JSON_DIR = join(LOGS_DIR, 'json')

// スリープ用のヘルパー
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms))

// URLを正規化（サニタイズしてファイル名に使用）
const sanitizeUrl = (url) => {
  return url
    .replace(/^https?:\/\//, '')
    .replace(/[^a-zA-Z0-9._-]/g, '_')
    .substring(0, 100)
}

// URL候補を抽出する正規表現パターン
const URL_PATTERNS = [
  /https?:\/\/[^\s"'<>{}()]+/gi,  // 一般的なURL
  /\/api\/[^\s"'<>{}()]+/gi,      // /api/ を含むパス
  /\.json[^\s"'<>]*/gi,           // .json を含むURL
]

// キーワードを含むURLを優先的に抽出
const KEYWORDS = ['news', 'article', 'topics', 'list', 'ranking', 'api', 'json']

/**
 * HTMLからscriptタグのsrc属性を抽出
 */
function extractScriptSrcs(html) {
  const scriptSrcPattern = /<script[^>]+src=["']([^"']+)["'][^>]*>/gi
  const srcs = []
  let match
  while ((match = scriptSrcPattern.exec(html)) !== null) {
    srcs.push(match[1])
  }
  return srcs
}

/**
 * テキストからURL候補を抽出
 */
function extractUrlCandidates(text) {
  const candidates = new Set()
  
  // パターンマッチング
  for (const pattern of URL_PATTERNS) {
    let match
    while ((match = pattern.exec(text)) !== null) {
      const url = match[0]
      if (url.length > 10 && url.length < 500) {  // 妥当な長さ
        candidates.add(url)
      }
    }
  }
  
  return Array.from(candidates)
}

/**
 * 相対URLを絶対URLに変換
 */
function resolveUrl(baseUrl, relativeUrl) {
  try {
    return new URL(relativeUrl, baseUrl).href
  } catch {
    return null
  }
}

/**
 * 候補URLをスコア付け（キーワードマッチを優先）
 */
function scoreUrl(url) {
  let score = 0
  const urlLower = url.toLowerCase()
  
  // キーワードマッチ
  for (const keyword of KEYWORDS) {
    if (urlLower.includes(keyword)) {
      score += 10
    }
  }
  
  // APIパス
  if (urlLower.includes('/api/')) {
    score += 20
  }
  
  // JSON
  if (urlLower.includes('.json')) {
    score += 15
  }
  
  // dmenuドメイン
  if (urlLower.includes('service.smt.docomo.ne.jp')) {
    score += 5
  }
  
  return score
}

/**
 * JSONレスポンスのスコア付け（ニュース記事データかどうか判定）
 */
function scoreJsonResponse(json) {
  let score = 0
  
  // 配列の場合
  if (Array.isArray(json)) {
    score += 10
    if (json.length > 0) {
      const firstItem = json[0]
      if (typeof firstItem === 'object' && firstItem !== null) {
        // ニュース記事らしいフィールドをチェック
        if ('title' in firstItem) score += 20
        if ('url' in firstItem || 'link' in firstItem) score += 15
        if ('publishedAt' in firstItem || 'date' in firstItem || 'time' in firstItem) score += 10
        if ('image' in firstItem || 'thumbnail' in firstItem) score += 10
      }
    }
  } else if (typeof json === 'object' && json !== null) {
    // オブジェクトの場合
    if ('items' in json && Array.isArray(json.items)) {
      score += 20
    }
    if ('articles' in json && Array.isArray(json.articles)) {
      score += 20
    }
    if ('data' in json && Array.isArray(json.data)) {
      score += 15
    }
  }
  
  return score
}

/**
 * HTTPリクエスト（簡易版）
 * dmenuサーバーのSSL/TLS問題に対処（開発環境のみ）
 */
async function fetchUrl(url, options = {}) {
  let timeout = null
  
  try {
    // dmenuサーバーのSSL/TLSレガシーリネゴシエーション問題に対処
    // 注意: 本番環境ではより安全な方法を使用すべき
    const originalRejectUnauthorized = process.env.NODE_TLS_REJECT_UNAUTHORIZED
    process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0'
    
    try {
      const urlObj = new URL(url)
      const response = await new Promise((resolve, reject) => {
        const requestOptions = {
          hostname: urlObj.hostname,
          port: urlObj.port || 443,
          path: urlObj.pathname + urlObj.search,
          method: options.method || 'GET',
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Referer': DMENU_LIST_PAGE_URL,
            ...options.headers,
          },
          agent: new https.Agent({
            rejectUnauthorized: false,
            secureProtocol: 'TLSv1_2_method',
          }),
        }
        
        timeout = setTimeout(() => {
          req.destroy()
          reject(new Error('Request timeout'))
        }, 15000)
        
        const req = https.request(requestOptions, (res) => {
          let data = ''
          res.on('data', (chunk) => {
            data += chunk
          })
          res.on('end', () => {
            if (timeout) clearTimeout(timeout)
            // Response-like objectを作成
            resolve({
              ok: res.statusCode >= 200 && res.statusCode < 300,
              status: res.statusCode,
              statusText: res.statusMessage,
              headers: res.headers,
              text: async () => data,
              json: async () => JSON.parse(data),
            })
          })
        })
        
        req.on('error', (error) => {
          if (timeout) clearTimeout(timeout)
          reject(error)
        })
        
        req.end()
      })
      
      // 環境変数を元に戻す
      if (originalRejectUnauthorized !== undefined) {
        process.env.NODE_TLS_REJECT_UNAUTHORIZED = originalRejectUnauthorized
      } else {
        delete process.env.NODE_TLS_REJECT_UNAUTHORIZED
      }
      
      return response
    } catch (innerError) {
      // 環境変数を元に戻す
      if (originalRejectUnauthorized !== undefined) {
        process.env.NODE_TLS_REJECT_UNAUTHORIZED = originalRejectUnauthorized
      } else {
        delete process.env.NODE_TLS_REJECT_UNAUTHORIZED
      }
      throw innerError
    }
  } catch (error) {
    if (timeout) clearTimeout(timeout)
    // より詳細なエラー情報を提供
    const errorMsg = error.message || String(error)
    const enhancedError = new Error(`fetch failed for ${url}: ${errorMsg}`)
    enhancedError.cause = error
    enhancedError.originalError = error
    throw enhancedError
  }
}

/**
 * メイン処理
 */
async function main() {
  console.log('[Probe] Starting dmenu XHR probe...')
  console.log(`[Probe] Target page: ${DMENU_LIST_PAGE_URL}`)
  
  // ログディレクトリを作成
  mkdirSync(LOGS_DIR, { recursive: true })
  mkdirSync(RESPONSES_DIR, { recursive: true })
  mkdirSync(JSON_DIR, { recursive: true })
  
  // 1. dmenuニュース一覧ページをGET
  console.log('\n[Step 1] Fetching dmenu list page...')
  let html
  try {
    const response = await fetchUrl(DMENU_LIST_PAGE_URL)
    html = await response.text()
    console.log(`[Step 1] ✓ Success (${html.length} bytes)`)
  } catch (error) {
    console.error(`[Step 1] ✗ Failed: ${error.message}`)
    if (error.cause) {
      console.error(`[Step 1] Error cause:`, error.cause)
      
      // SSL/TLSエラーの場合の説明
      if (error.cause.code === 'ERR_SSL_UNSAFE_LEGACY_RENEGOTIATION_DISABLED') {
        console.error(`\n[Step 1] SSL/TLS Error: Unsafe legacy renegotiation disabled`)
        console.error(`[Step 1] This is likely due to dmenu server using legacy SSL/TLS protocol.`)
        console.error(`[Step 1] Please check if the URL is accessible from your browser:`)
        console.error(`[Step 1] ${DMENU_LIST_PAGE_URL}`)
        console.error(`[Step 1] \nNote: This probe script may need to be run with special SSL settings.`)
        console.error(`[Step 1] Alternative: Use a browser devtools to inspect XHR requests instead.`)
      }
    }
    if (error.stack) {
      console.error(`[Step 1] Error stack:`, error.stack)
    }
    // fetchが利用できない場合の詳細情報
    if (typeof fetch === 'undefined') {
      console.error(`[Step 1] Note: fetch is not available. Node.js version: ${process.version}`)
      console.error(`[Step 1] Please use Node.js 18+ or install node-fetch package`)
    }
    process.exit(1)
  }
  
  // 2. script srcを抽出
  console.log('\n[Step 2] Extracting script sources...')
  const scriptSrcs = extractScriptSrcs(html)
  console.log(`[Step 2] ✓ Found ${scriptSrcs.length} script tags`)
  
  // 3. 各JSファイルからURL候補を抽出
  console.log('\n[Step 3] Extracting URL candidates from scripts...')
  const urlCandidates = new Set()
  
  // HTMLから直接URL候補を抽出
  const htmlCandidates = extractUrlCandidates(html)
  htmlCandidates.forEach(url => {
    const resolved = resolveUrl(DMENU_LIST_PAGE_URL, url)
    if (resolved) urlCandidates.add(resolved)
  })
  
  // 各JSファイルから抽出（最大10ファイル）
  let jsFilesProcessed = 0
  for (const scriptSrc of scriptSrcs.slice(0, 10)) {
    const jsUrl = resolveUrl(DMENU_LIST_PAGE_URL, scriptSrc)
    if (!jsUrl) continue
    
    try {
      await sleep(300)  // 負荷軽減
      const response = await fetchUrl(jsUrl)
      if (response.ok) {
        const jsContent = await response.text()
        const jsCandidates = extractUrlCandidates(jsContent)
        jsCandidates.forEach(url => {
          const resolved = resolveUrl(jsUrl, url)
          if (resolved) urlCandidates.add(resolved)
        })
        jsFilesProcessed++
      }
    } catch (error) {
      // エラーは無視して続行
    }
  }
  
  console.log(`[Step 3] ✓ Processed ${jsFilesProcessed} JS files, found ${urlCandidates.size} unique URL candidates`)
  
  // 4. 候補URLをスコア付けしてソート
  console.log('\n[Step 4] Scoring and sorting candidates...')
  const scoredCandidates = Array.from(urlCandidates)
    .map(url => ({ url, score: scoreUrl(url) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 30)  // 上位30件のみ試行
  
  // 候補URLをファイルに保存
  const urlsText = scoredCandidates.map(c => `${c.score}\t${c.url}`).join('\n')
  writeFileSync(URLS_FILE, urlsText, 'utf-8')
  console.log(`[Step 4] ✓ Saved ${scoredCandidates.length} candidates to ${URLS_FILE}`)
  
  // 5. 候補URLを実際にGETしてみる
  console.log('\n[Step 5] Testing candidate URLs...')
  const results = []
  
  for (let i = 0; i < scoredCandidates.length; i++) {
    const { url, score } = scoredCandidates[i]
    console.log(`[Step 5] Testing ${i + 1}/${scoredCandidates.length}: ${url.substring(0, 80)}...`)
    
    try {
      await sleep(300)  // 負荷軽減
      const response = await fetchUrl(url)
      const contentType = response.headers.get('content-type') || 'unknown'
      const content = await response.text()
      
      const result = {
        url,
        score,
        status: response.status,
        contentType,
        bytes: content.length,
        preview: content.substring(0, 200),
        isJson: contentType.includes('application/json') || content.trim().startsWith('{') || content.trim().startsWith('['),
      }
      
      // レスポンス概要を保存
      const sanitized = sanitizeUrl(url)
      const responseFile = join(RESPONSES_DIR, `${sanitized}.txt`)
      const responseText = `URL: ${url}\nStatus: ${response.status}\nContent-Type: ${contentType}\nBytes: ${content.length}\n\nPreview:\n${result.preview}\n`
      writeFileSync(responseFile, responseText, 'utf-8')
      
      // JSONの場合は解析して保存
      if (result.isJson) {
        try {
          const json = JSON.parse(content)
          const jsonScore = scoreJsonResponse(json)
          result.jsonScore = jsonScore
          result.json = json
          
          const jsonFile = join(JSON_DIR, `${sanitized}.json`)
          writeFileSync(jsonFile, JSON.stringify(json, null, 2), 'utf-8')
        } catch (parseError) {
          // JSONパース失敗は無視
        }
      }
      
      results.push(result)
    } catch (error) {
      // エラーはログに記録するが続行
      const sanitized = sanitizeUrl(url)
      const responseFile = join(RESPONSES_DIR, `${sanitized}.txt`)
      writeFileSync(responseFile, `URL: ${url}\nError: ${error.message}\n`, 'utf-8')
    }
  }
  
  console.log(`[Step 5] ✓ Tested ${results.length} URLs`)
  
  // 6. bestEndpointを決定
  console.log('\n[Step 6] Determining best endpoint...')
  const jsonResults = results.filter(r => r.isJson && r.jsonScore !== undefined)
  const bestResult = jsonResults.sort((a, b) => {
    const scoreA = (a.score || 0) + (a.jsonScore || 0)
    const scoreB = (b.score || 0) + (b.jsonScore || 0)
    return scoreB - scoreA
  })[0]
  
  console.log('\n' + '='.repeat(80))
  if (bestResult) {
    console.log(`[Result] Best Endpoint: ${bestResult.url}`)
    console.log(`[Result] URL Score: ${bestResult.score}`)
    console.log(`[Result] JSON Score: ${bestResult.jsonScore}`)
    console.log(`[Result] Status: ${bestResult.status}`)
    console.log(`[Result] Content-Type: ${bestResult.contentType}`)
    console.log(`[Result] Bytes: ${bestResult.bytes}`)
    console.log('='.repeat(80))
  } else {
    console.log('[Result] No suitable JSON endpoint found')
    console.log(`[Result] Tested ${results.length} URLs, ${jsonResults.length} returned JSON`)
    console.log('='.repeat(80))
  }
  
  console.log('\n[Probe] Complete!')
  console.log(`- URLs file: ${URLS_FILE}`)
  console.log(`- Responses: ${RESPONSES_DIR}`)
  console.log(`- JSON files: ${JSON_DIR}`)
}

main().catch(error => {
  console.error('[Fatal]', error)
  process.exit(1)
})

