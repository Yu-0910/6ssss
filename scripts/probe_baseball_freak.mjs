/**
 * baseball-freak.com の記事取得可能性調査スクリプト
 * 
 * これまでの失敗例を踏まえて調査：
 * - Yahoo! Topics: HTMLパースで元記事URL抽出に失敗
 * - Google News: HTML構造の変更によりURL抽出に失敗
 * - dmenu: SSL/TLSレガシーリネゴシエーションエラー
 */

const BASE_URL = 'https://baseball-freak.com'

async function probeBaseballFreak() {
  console.log('='.repeat(80))
  console.log('[Probe] baseball-freak.com 記事取得可能性調査')
  console.log('='.repeat(80))
  console.log('')

  const results = {
    rssFeeds: [],
    htmlStructure: null,
    apiEndpoints: [],
    sslTls: null,
    articleStructure: null,
  }

  try {
    // Step 1: RSSフィードの存在確認
    console.log('[Step 1] RSSフィードの存在確認...')
    const rssCandidates = [
      `${BASE_URL}/rss.xml`,
      `${BASE_URL}/feed.xml`,
      `${BASE_URL}/feed`,
      `${BASE_URL}/rss`,
      `${BASE_URL}/news/rss.xml`,
      `${BASE_URL}/news/feed.xml`,
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
        const hasNewsSection = html.includes('プロ野球ニュース') || html.includes('ニュース')
        const hasArticleLinks = html.match(/<a[^>]+href=["']([^"']+)["'][^>]*>/g) || []
        const articleLinkCount = hasArticleLinks.length
        const hasDateStructure = html.includes('01月19日') || html.match(/\d{1,2}月\d{1,2}日/)
        const hasSourceTags = html.match(/【[^】]+】/g) || []

        results.htmlStructure = {
          length: htmlLength,
          hasNewsSection,
          articleLinkCount,
          hasDateStructure,
          sourceTagCount: hasSourceTags.length,
          sampleSourceTags: hasSourceTags.slice(0, 5),
        }

        console.log(`  - ニュースセクション: ${hasNewsSection ? '✓' : '✗'}`)
        console.log(`  - 記事リンク数: ${articleLinkCount}`)
        console.log(`  - 日付構造: ${hasDateStructure ? '✓' : '✗'}`)
        console.log(`  - ソースタグ数: ${hasSourceTags.length}`)
        if (hasSourceTags.length > 0) {
          console.log(`  - サンプルソースタグ: ${hasSourceTags.slice(0, 3).join(', ')}`)
        }

        // 記事リンクの抽出テスト
        console.log('')
        console.log('  [記事リンク抽出テスト]')
        const articleLinkPatterns = [
          /<a[^>]+href=["']([^"']*\/news\/[^"']+)["'][^>]*>/gi,
          /<a[^>]+href=["']([^"']*article[^"']+)["'][^>]*>/gi,
          /<a[^>]+href=["']([^"']*\/\d{4}\/[^"']+)["'][^>]*>/gi,
        ]

        const extractedLinks = new Set()
        for (const pattern of articleLinkPatterns) {
          const matches = html.matchAll(pattern)
          for (const match of matches) {
            if (match[1] && !match[1].startsWith('#')) {
              extractedLinks.add(match[1])
            }
          }
        }

        // ソースタグとリンクの関連性を確認
        const sourceLinkPairs = []
        const sourcePattern = /【([^】]+)】/g
        let sourceMatch
        while ((sourceMatch = sourcePattern.exec(html)) !== null && sourceLinkPairs.length < 10) {
          const source = sourceMatch[1]
          const afterSource = html.substring(sourceMatch.index + sourceMatch[0].length, sourceMatch.index + 500)
          const linkMatch = afterSource.match(/<a[^>]+href=["']([^"']+)["'][^>]*>/)
          if (linkMatch) {
            sourceLinkPairs.push({
              source,
              link: linkMatch[1],
            })
          }
        }

        results.articleStructure = {
          extractedLinkCount: extractedLinks.size,
          sampleLinks: Array.from(extractedLinks).slice(0, 5),
          sourceLinkPairs: sourceLinkPairs.slice(0, 5),
        }

        console.log(`  - 抽出された記事リンク数: ${extractedLinks.size}`)
        if (extractedLinks.size > 0) {
          console.log(`  - サンプルリンク:`)
          Array.from(extractedLinks).slice(0, 3).forEach(link => {
            console.log(`    ${link}`)
          })
        }
        if (sourceLinkPairs.length > 0) {
          console.log(`  - ソース-リンクペア:`)
          sourceLinkPairs.slice(0, 3).forEach(pair => {
            console.log(`    【${pair.source}】 -> ${pair.link}`)
          })
        }

        // HTMLの一部を保存（デバッグ用）
        const htmlPreview = html.substring(0, 2000)
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
      `${BASE_URL}/api/news`,
      `${BASE_URL}/api/articles`,
      `${BASE_URL}/api/v1/news`,
      `${BASE_URL}/news.json`,
      `${BASE_URL}/articles.json`,
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
      htmlParsable: results.htmlStructure && results.htmlStructure.hasNewsSection,
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
    console.log('    → baseball-freak.com: HTMLパースは可能だが、構造変更のリスクあり')
    console.log('  - Google News: HTML構造の変更によりURL抽出に失敗')
    console.log('    → baseball-freak.com: 同様のリスクあり')
    console.log('  - dmenu: SSL/TLSレガシーリネゴシエーションエラー')
    console.log(`    → baseball-freak.com: ${feasibility.sslTlsOk ? 'SSL/TLS問題なし' : 'SSL/TLS問題あり'}`)
    console.log('')

    // リスク評価
    console.log('リスク評価:')
    if (feasibility.rssAvailable) {
      console.log('  ✓ 低リスク: RSSフィードは標準的な形式で安定')
    } else if (feasibility.htmlParsable) {
      console.log('  ⚠️  中リスク: HTML構造の変更に弱い')
      console.log('  ⚠️  中リスク: JavaScriptで動的生成される可能性')
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

probeBaseballFreak()







