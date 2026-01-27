/**
 * article.auone.jp の記事取得可能性調査スクリプト
 * 
 * これまでの失敗例を踏まえて調査：
 * - Yahoo! Topics: HTMLパースで元記事URL抽出に失敗
 * - Google News: HTML構造の変更によりURL抽出に失敗
 * - dmenu: SSL/TLSレガシーリネゴシエーションエラー
 * - baseball-freak.com: HTMLパース可能（中リスク）
 */

const BASE_URL = 'https://article.auone.jp/keyword/article/1'

async function probeAuone() {
  console.log('='.repeat(80))
  console.log('[Probe] article.auone.jp 記事取得可能性調査')
  console.log('='.repeat(80))
  console.log('')

  const results = {
    rssFeeds: [],
    htmlStructure: null,
    apiEndpoints: [],
    sslTls: null,
    articleStructure: null,
    pagination: null,
  }

  try {
    // Step 1: RSSフィードの存在確認
    console.log('[Step 1] RSSフィードの存在確認...')
    const rssCandidates = [
      `https://article.auone.jp/rss.xml`,
      `https://article.auone.jp/keyword/article/1/rss.xml`,
      `https://article.auone.jp/keyword/article/1/feed.xml`,
      `https://article.auone.jp/keyword/article/1/feed`,
      `https://article.auone.jp/keyword/article/1/rss`,
      `https://article.auone.jp/feed.xml`,
    ]

    for (const url of rssCandidates) {
      try {
        const response = await fetch(url, {
          method: 'HEAD',
          redirect: 'follow',
        })
        if (response.ok) {
          const contentType = response.headers.get('content-type') || ''
          if (contentType.includes('xml') || contentType.includes('rss') || contentType.includes('atom')) {
            results.rssFeeds.push({
              url,
              status: response.status,
              contentType,
              ok: true,
            })
            console.log(`  ✓ Found RSS: ${url} (${contentType})`)
          }
        }
      } catch (error) {
        // エラーは無視（存在しない可能性）
      }
    }

    if (results.rssFeeds.length === 0) {
      console.log('  ✗ RSSフィードが見つかりませんでした')
    }
    console.log('')

    // Step 2: HTML構造の調査
    console.log('[Step 2] HTML構造の調査...')
    try {
      const response = await fetch(BASE_URL, {
        method: 'GET',
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        },
        redirect: 'follow',
      })

      if (response.ok) {
        const html = await response.text()
        const htmlLength = html.length
        console.log(`  ✓ HTML取得成功: ${htmlLength} bytes`)
        console.log(`  ✓ Content-Type: ${response.headers.get('content-type')}`)
        console.log(`  ✓ Final URL: ${response.url}`)

        // HTML構造の分析
        const hasArticleList = html.includes('記事一覧') || html.includes('キーワード別記事一覧')
        const hasArticleLinks = html.match(/<a[^>]+href=["']([^"']+)["'][^>]*>/g) || []
        const articleLinkCount = hasArticleLinks.length
        const hasDateStructure = html.match(/\d{2}\/\d{2}\s+\d{2}:\d{2}/) || html.match(/\d{1,2}月\d{1,2}日/)
        const hasSourceTags = html.match(/[^\s]+\s+\d{2}\/\d{2}\s+\d{2}:\d{2}\s+[^\s]+/g) || []
        
        // 記事タイトルとソースのパターンを探す
        const articlePatterns = [
          /<li[^>]*>[\s\S]*?<a[^>]+href=["']([^"']+)["'][^>]*>[\s\S]*?<\/a>[\s\S]*?<\/li>/gi,
          /<article[^>]*>[\s\S]*?<a[^>]+href=["']([^"']+)["'][^>]*>[\s\S]*?<\/a>[\s\S]*?<\/article>/gi,
        ]

        results.htmlStructure = {
          length: htmlLength,
          hasArticleList,
          articleLinkCount,
          hasDateStructure: !!hasDateStructure,
          sourceTagCount: hasSourceTags.length,
          sampleSourceTags: hasSourceTags.slice(0, 5),
        }

        console.log(`  - 記事一覧セクション: ${hasArticleList ? '✓' : '✗'}`)
        console.log(`  - 記事リンク数: ${articleLinkCount}`)
        console.log(`  - 日付構造: ${hasDateStructure ? '✓' : '✗'}`)
        console.log(`  - ソースタグ数: ${hasSourceTags.length}`)
        if (hasSourceTags.length > 0) {
          console.log(`  - サンプルソースタグ: ${hasSourceTags.slice(0, 3).join(', ')}`)
        }

        // 記事リンクの抽出テスト
        console.log('')
        console.log('  [記事リンク抽出テスト]')
        
        // より具体的なパターンで記事リンクを抽出
        const articleLinkPatterns = [
          /<a[^>]+href=["'](https?:\/\/[^"']+)["'][^>]*>/gi,
          /<a[^>]+href=["'](\/[^"']+)["'][^>]*>/gi,
        ]

        const extractedLinks = new Set()
        for (const pattern of articleLinkPatterns) {
          const matches = html.matchAll(pattern)
          for (const match of matches) {
            if (match[1]) {
              // 相対URLを絶対URLに変換
              let fullUrl = match[1]
              if (fullUrl.startsWith('/')) {
                fullUrl = `https://article.auone.jp${fullUrl}`
              }
              // 記事URLっぽいものを抽出（article.auone.jp以外のドメインも含む）
              if (fullUrl.includes('article') || 
                  fullUrl.match(/\/\d{4}\//) || 
                  fullUrl.includes('news') ||
                  fullUrl.includes('sports')) {
                extractedLinks.add(fullUrl)
              }
            }
          }
        }

        // タイトルとソースの関連性を確認
        // パターン: "タイトル 01/19 18:38 ソース名"
        const titleSourcePattern = /([^<]+?)\s+(\d{2}\/\d{2}\s+\d{2}:\d{2})\s+([^\s<]+)/g
        const titleSourcePairs = []
        let match
        while ((match = titleSourcePattern.exec(html)) !== null && titleSourcePairs.length < 10) {
          titleSourcePairs.push({
            title: match[1].trim(),
            date: match[2],
            source: match[3],
          })
        }

        // リストアイテムから記事情報を抽出
        const listItemPattern = /<li[^>]*>([\s\S]*?)<\/li>/gi
        const listItems = []
        let listMatch
        while ((listMatch = listItemPattern.exec(html)) !== null && listItems.length < 20) {
          const itemHtml = listMatch[1]
          const linkMatch = itemHtml.match(/<a[^>]+href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/)
          if (linkMatch) {
            const link = linkMatch[1].startsWith('/') 
              ? `https://article.auone.jp${linkMatch[1]}`
              : linkMatch[1]
            const title = linkMatch[2].replace(/<[^>]+>/g, '').trim()
            const dateMatch = itemHtml.match(/(\d{2}\/\d{2}\s+\d{2}:\d{2})/)
            const sourceMatch = itemHtml.match(/([^\s]+)\s*$/)
            listItems.push({
              title,
              link,
              date: dateMatch ? dateMatch[1] : null,
              source: sourceMatch ? sourceMatch[1] : null,
            })
          }
        }

        results.articleStructure = {
          extractedLinkCount: extractedLinks.size,
          sampleLinks: Array.from(extractedLinks).slice(0, 10),
          titleSourcePairs: titleSourcePairs.slice(0, 10),
          listItems: listItems.slice(0, 10),
        }

        console.log(`  - 抽出された記事リンク数: ${extractedLinks.size}`)
        if (extractedLinks.size > 0) {
          console.log(`  - サンプルリンク:`)
          Array.from(extractedLinks).slice(0, 5).forEach(link => {
            console.log(`    ${link}`)
          })
        }
        if (titleSourcePairs.length > 0) {
          console.log(`  - タイトル-日付-ソースペア:`)
          titleSourcePairs.slice(0, 3).forEach(pair => {
            console.log(`    "${pair.title}" ${pair.date} ${pair.source}`)
          })
        }
        if (listItems.length > 0) {
          console.log(`  - リストアイテムから抽出:`)
          listItems.slice(0, 3).forEach(item => {
            console.log(`    "${item.title}" -> ${item.link} (${item.date} ${item.source})`)
          })
        }

        // ページネーションの確認
        const hasPagination = html.includes('さらに読み込む') || html.includes('次へ') || html.includes('pagination')
        const loadMorePattern = /さらに読み込む|load.*more|pagination/i
        const paginationMatch = html.match(loadMorePattern)
        
        results.pagination = {
          hasPagination,
          type: paginationMatch ? 'load-more' : 'unknown',
        }

        console.log('')
        console.log('  [ページネーション]')
        console.log(`  - ページネーション: ${hasPagination ? '✓' : '✗'}`)
        if (hasPagination) {
          console.log(`  - タイプ: ${results.pagination.type}`)
        }

        // HTMLの一部を保存（デバッグ用）
        const htmlPreview = html.substring(0, 3000)
        results.htmlStructure.htmlPreview = htmlPreview

      } else {
        console.log(`  ✗ HTML取得失敗: ${response.status} ${response.statusText}`)
      }
    } catch (error) {
      console.log(`  ✗ HTML取得エラー: ${error.message}`)
      results.htmlStructure = {
        error: error.message,
        code: error.code,
        name: error.name,
      }
    }
    console.log('')

    // Step 3: SSL/TLS接続の確認
    console.log('[Step 3] SSL/TLS接続の確認...')
    try {
      const response = await fetch(BASE_URL, {
        method: 'HEAD',
        redirect: 'follow',
      })
      if (response.ok) {
        results.sslTls = {
          ok: true,
          status: response.status,
          protocol: 'TLS (via fetch)',
        }
        console.log(`  ✓ SSL/TLS接続成功: ${response.status}`)
      }
    } catch (error) {
      results.sslTls = {
        ok: false,
        error: error.message,
        code: error.code,
        name: error.name,
      }
      console.log(`  ✗ SSL/TLS接続エラー: ${error.message}`)
      if (error.code) {
        console.log(`    Code: ${error.code}`)
      }
    }
    console.log('')

    // Step 4: APIエンドポイントの探索
    console.log('[Step 4] APIエンドポイントの探索...')
    const apiCandidates = [
      `https://article.auone.jp/api/news`,
      `https://article.auone.jp/api/articles`,
      `https://article.auone.jp/api/v1/news`,
      `https://article.auone.jp/keyword/article/1.json`,
      `https://article.auone.jp/keyword/article/1/api`,
    ]

    for (const url of apiCandidates) {
      try {
        const response = await fetch(url, {
          method: 'HEAD',
          redirect: 'follow',
        })
        if (response.ok) {
          const contentType = response.headers.get('content-type') || ''
          if (contentType.includes('json')) {
            results.apiEndpoints.push({
              url,
              status: response.status,
              contentType,
              ok: true,
            })
            console.log(`  ✓ Found API: ${url} (${contentType})`)
          }
        }
      } catch (error) {
        // エラーは無視
      }
    }

    if (results.apiEndpoints.length === 0) {
      console.log('  ✗ APIエンドポイントが見つかりませんでした')
    }
    console.log('')

    // Step 5: まとめと評価
    console.log('='.repeat(80))
    console.log('[Summary] 調査結果のまとめ')
    console.log('='.repeat(80))
    console.log('')

    const feasibility = {
      rssAvailable: results.rssFeeds.length > 0,
      htmlParsable: results.htmlStructure && results.htmlStructure.hasArticleList,
      sslTlsOk: results.sslTls && results.sslTls.ok,
      apiAvailable: results.apiEndpoints.length > 0,
    }

    console.log('取得方法の可能性:')
    console.log(`  - RSSフィード: ${feasibility.rssAvailable ? '✓ 可能' : '✗ 不可'}`)
    console.log(`  - HTMLパース: ${feasibility.htmlParsable ? '✓ 可能' : '✗ 不可'}`)
    console.log(`  - API: ${feasibility.apiAvailable ? '✓ 可能' : '✗ 不可'}`)
    console.log(`  - SSL/TLS: ${feasibility.sslTlsOk ? '✓ 正常' : '✗ 問題あり'}`)
    console.log('')

    // 推奨される取得方法
    console.log('推奨される取得方法:')
    if (feasibility.rssAvailable) {
      console.log('  1. RSSフィードを使用（最も推奨）')
      console.log(`     URL: ${results.rssFeeds[0].url}`)
    } else if (feasibility.htmlParsable) {
      console.log('  1. HTMLパースを使用')
      console.log('     - 注意: HTML構造の変更に弱い')
      console.log('     - 注意: JavaScriptで動的生成される可能性')
      if (results.pagination && results.pagination.hasPagination) {
        console.log(`     - 注意: ページネーション対応が必要（${results.pagination.type}）`)
      }
    } else if (feasibility.apiAvailable) {
      console.log('  1. APIを使用')
      console.log(`     URL: ${results.apiEndpoints[0].url}`)
    } else {
      console.log('  ✗ 取得方法が見つかりませんでした')
    }
    console.log('')

    // これまでの失敗例との比較
    console.log('これまでの失敗例との比較:')
    console.log('  - Yahoo! Topics: HTMLパースで元記事URL抽出に失敗')
    console.log('    → auone.jp: HTMLパースは可能だが、構造変更のリスクあり')
    console.log('  - Google News: HTML構造の変更によりURL抽出に失敗')
    console.log('    → auone.jp: 同様のリスクあり')
    console.log('  - dmenu: SSL/TLSレガシーリネゴシエーションエラー')
    console.log(`    → auone.jp: ${feasibility.sslTlsOk ? 'SSL/TLS問題なし' : 'SSL/TLS問題あり'}`)
    console.log('  - baseball-freak.com: HTMLパース可能（中リスク）')
    console.log('    → auone.jp: 同様にHTMLパース可能だが、ページネーション対応が必要')
    console.log('')

    // リスク評価
    console.log('リスク評価:')
    if (feasibility.rssAvailable) {
      console.log('  ✓ 低リスク: RSSフィードは標準的な形式で安定')
    } else if (feasibility.htmlParsable) {
      console.log('  ⚠️  中リスク: HTML構造の変更に弱い')
      console.log('  ⚠️  中リスク: JavaScriptで動的生成される可能性')
      if (results.pagination && results.pagination.hasPagination) {
        console.log('  ⚠️  中リスク: ページネーション対応が必要')
      }
    } else {
      console.log('  ✗ 高リスク: 取得方法が不明確')
    }
    console.log('')

    // 詳細結果をJSONで出力
    console.log('詳細結果（JSON）:')
    console.log(JSON.stringify(results, null, 2))

  } catch (error) {
    console.error('調査中にエラーが発生しました:', error)
    console.error('Stack:', error.stack)
  }
}

probeAuone()







