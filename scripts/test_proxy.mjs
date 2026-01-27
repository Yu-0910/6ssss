/**
 * Cloudflare Workersプロキシのテストスクリプト
 * 
 * このスクリプトは、Cloudflare Workersプロキシが正しく動作しているかをテストします。
 * 
 * 使用方法:
 *   node scripts/test_proxy.mjs <プロキシURL>
 * 
 * 例:
 *   node scripts/test_proxy.mjs https://dmenu-proxy.your-subdomain.workers.dev
 */

const proxyUrl = process.argv[2]

if (!proxyUrl) {
  console.error('使用方法: node scripts/test_proxy.mjs <プロキシURL>')
  console.error('例: node scripts/test_proxy.mjs https://dmenu-proxy.your-subdomain.workers.dev')
  process.exit(1)
}

console.log('='.repeat(80))
console.log('[Proxy Test] Testing Cloudflare Workers proxy...')
console.log('[Proxy Test] Proxy URL:', proxyUrl)
console.log('='.repeat(80))

async function testProxy() {
  try {
    console.log('\n[Step 1] Sending GET request to proxy...')
    const startTime = Date.now()
    
    const response = await fetch(proxyUrl, {
      method: 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
      },
    })
    
    const elapsed = Date.now() - startTime
    
    console.log(`[Step 1] ✓ Response received (${elapsed}ms)`)
    console.log(`[Step 1] Status: ${response.status} ${response.statusText}`)
    console.log(`[Step 1] Content-Type: ${response.headers.get('Content-Type')}`)
    console.log(`[Step 1] X-Proxy-Source: ${response.headers.get('X-Proxy-Source') || 'N/A'}`)
    console.log(`[Step 1] X-Dmenu-Status: ${response.headers.get('X-Dmenu-Status') || 'N/A'}`)
    
    if (!response.ok) {
      const errorText = await response.text()
      console.error(`[Step 1] ✗ Proxy returned error: ${errorText.substring(0, 500)}`)
      process.exit(1)
    }
    
    console.log('\n[Step 2] Parsing response body...')
    const text = await response.text()
    console.log(`[Step 2] ✓ Response body length: ${text.length} bytes`)
    
    console.log('\n[Step 3] Validating JSON...')
    let json
    try {
      json = JSON.parse(text)
      console.log('[Step 3] ✓ Valid JSON')
    } catch (parseError) {
      console.error('[Step 3] ✗ Invalid JSON:', parseError.message)
      console.error('[Step 3] Response preview (first 500 chars):')
      console.error(text.substring(0, 500))
      process.exit(1)
    }
    
    console.log('\n[Step 4] Validating dmenu API structure...')
    if (json.news_list && json.news_list.news && Array.isArray(json.news_list.news)) {
      console.log(`[Step 4] ✓ Valid dmenu API structure`)
      console.log(`[Step 4] News count: ${json.news_list.news.length}`)
      
      if (json.news_list.news.length > 0) {
        const firstItem = json.news_list.news[0]
        console.log('\n[Step 4] Sample article:')
        console.log(`  Title: ${firstItem.news_title?.substring(0, 50)}...`)
        console.log(`  Source: ${firstItem.news_ip_name || 'N/A'}`)
        console.log(`  URL: ${firstItem.news_origin_url || firstItem.news_url || 'N/A'}`)
        console.log(`  Published: ${firstItem.news_publish_datetime || 'N/A'}`)
      }
    } else {
      console.error('[Step 4] ✗ Invalid dmenu API structure')
      console.error('[Step 4] Expected: { news_list: { news: [...] } }')
      console.error('[Step 4] Got:', Object.keys(json))
      process.exit(1)
    }
    
    console.log('\n' + '='.repeat(80))
    console.log('[Result] ✓ Proxy test PASSED')
    console.log(`[Result] Total time: ${elapsed}ms`)
    console.log(`[Result] Articles found: ${json.news_list.news.length}`)
    console.log('='.repeat(80))
    
  } catch (error) {
    console.error('\n' + '='.repeat(80))
    console.error('[Result] ✗ Proxy test FAILED')
    console.error('[Result] Error:', error.message)
    if (error.stack) {
      console.error('[Result] Stack:', error.stack)
    }
    console.error('='.repeat(80))
    process.exit(1)
  }
}

testProxy()







