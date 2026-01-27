/**
 * dmenu API プロキシ (Cloudflare Workers)
 * 
 * このWorkerは、Node.jsアプリからdmenu APIへのリクエストを中継します。
 * Cloudflare Workersの環境では、レガシーSSL/TLSリネゴシエーションの問題が発生しないため、
 * dmenuサーバーとの通信が可能です。
 */

export default {
  async fetch(request) {
    // CORSプリフライトリクエストの処理
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, User-Agent, Accept, Accept-Language, Referer',
          'Access-Control-Max-Age': '86400', // 24時間
        },
      })
    }

    // GETリクエストのみ許可
    if (request.method !== 'GET') {
      return new Response(JSON.stringify({ error: 'Method not allowed' }), {
        status: 405,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      })
    }

    // dmenu APIエンドポイント
    const dmenuUrl = 'https://service.smt.docomo.ne.jp/portal/sports/data/news/news_list_0000.json'
    
    // リクエストヘッダーを設定
    // Cloudflare Workersのfetchは、レガシーSSL/TLSに対応しているため、
    // 特別な設定なしでdmenuサーバーと通信できます
    const headers = new Headers()
    headers.set('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    headers.set('Accept', 'application/json, text/html, */*')
    headers.set('Accept-Language', 'ja,en-US;q=0.9,en;q=0.8')
    headers.set('Referer', 'https://service.smt.docomo.ne.jp/portal/sports/baseball_j/index.html')

    try {
      // dmenu APIにリクエスト
      // Cloudflare Workersのfetchは、自動的にSSL/TLSハンドシェイクを処理します
      const response = await fetch(dmenuUrl, {
        method: 'GET',
        headers: headers,
        // Cloudflare Workersは自動的にリダイレクトを処理します
        redirect: 'follow',
      })

      // レスポンスのステータスを確認
      if (!response.ok) {
        const errorText = await response.text()
        console.error(`[Proxy] dmenu API returned ${response.status}: ${errorText.substring(0, 200)}`)
        
        return new Response(JSON.stringify({ 
          error: `dmenu API returned ${response.status}`,
          status: response.status,
          statusText: response.statusText,
        }), {
          status: response.status,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        })
      }

      // レスポンスボディを取得
      const data = await response.text()

      // JSONの妥当性を確認（オプション）
      try {
        JSON.parse(data)
      } catch (parseError) {
        console.error('[Proxy] Invalid JSON response from dmenu API')
        return new Response(JSON.stringify({ 
          error: 'Invalid JSON response from dmenu API',
          dataPreview: data.substring(0, 200),
        }), {
          status: 502,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        })
      }

      // 成功レスポンスを返す
      // Cloudflare Workersのキャッシュを活用（5分間キャッシュ）
      return new Response(data, {
        status: 200,
        headers: {
          'Content-Type': response.headers.get('Content-Type') || 'application/json',
          'Access-Control-Allow-Origin': '*',
          'Cache-Control': 'public, max-age=300', // 5分間キャッシュ
          'X-Proxy-Source': 'cloudflare-workers',
          'X-Dmenu-Status': response.status.toString(),
        },
      })
    } catch (error) {
      // エラーハンドリング
      console.error('[Proxy] Error fetching from dmenu API:', error)
      
      return new Response(JSON.stringify({ 
        error: 'Proxy error',
        message: error.message,
        stack: error.stack,
      }), {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      })
    }
  },
}







