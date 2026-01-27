/**
 * auone.jpの記事ページから画像URLを取得する方法を調査
 */

const ARTICLE_URL = process.argv[2] || 'https://article.auone.jp/detail/1/6/10/202_10_r_20260119_1768815527406072'

async function debugAuoneArticle() {
  console.log('='.repeat(80))
  console.log('[Debug] auone.jp 記事ページの画像URL取得方法調査')
  console.log('='.repeat(80))
  console.log('')

  try {
    console.log(`[Step 1] 記事ページを取得: ${ARTICLE_URL}`)
    const response = await fetch(ARTICLE_URL, {
      method: 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
      },
      redirect: 'follow',
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const html = await response.text()
    console.log(`  ✓ HTML取得成功: ${html.length} bytes`)
    console.log('')

    // OGP画像を抽出
    console.log('[Step 2] OGP画像の抽出...')
    const ogImageMatch = html.match(/<meta\s+property=["']og:image["'][^>]*content=["']([^"']+)["']/i)
    if (ogImageMatch) {
      console.log(`  ✓ og:image: ${ogImageMatch[1]}`)
    } else {
      console.log('  ✗ og:image が見つかりませんでした')
    }

    // Twitter画像を抽出
    const twitterImageMatch = html.match(/<meta\s+name=["']twitter:image["'][^>]*content=["']([^"']+)["']/i)
    if (twitterImageMatch) {
      console.log(`  ✓ twitter:image: ${twitterImageMatch[1]}`)
    } else {
      console.log('  ✗ twitter:image が見つかりませんでした')
    }

    // 元記事URLを抽出（リダイレクト先またはOGP URL）
    console.log('')
    console.log('[Step 3] 元記事URLの抽出...')
    const ogUrlMatch = html.match(/<meta\s+property=["']og:url["'][^>]*content=["']([^"']+)["']/i)
    if (ogUrlMatch) {
      console.log(`  ✓ og:url: ${ogUrlMatch[1]}`)
    } else {
      console.log('  ✗ og:url が見つかりませんでした')
    }

    const canonicalMatch = html.match(/<link\s+rel=["']canonical["'][^>]*href=["']([^"']+)["']/i)
    if (canonicalMatch) {
      console.log(`  ✓ canonical: ${canonicalMatch[1]}`)
    } else {
      console.log('  ✗ canonical が見つかりませんでした')
    }

    // リダイレクト先を確認
    if (response.url !== ARTICLE_URL) {
      console.log(`  ✓ リダイレクト先: ${response.url}`)
    }

    // 画像URLの候補を探す
    console.log('')
    console.log('[Step 4] 画像URLの候補を探索...')
    const imagePatterns = [
      /<img[^>]+src=["']([^"']+)["']/gi,
      /background-image:\s*url\(([^)]+)\)/gi,
      /<meta\s+property=["']og:image["'][^>]*content=["']([^"']+)["']/gi,
    ]

    const imageUrls = new Set()
    for (const pattern of imagePatterns) {
      const matches = html.matchAll(pattern)
      for (const match of matches) {
        if (match[1] && (match[1].includes('http') || match[1].includes('portal.st-img.jp'))) {
          imageUrls.add(match[1])
        }
      }
    }

    console.log(`  - 見つかった画像URL数: ${imageUrls.size}`)
    if (imageUrls.size > 0) {
      console.log('  - サンプル画像URL:')
      Array.from(imageUrls).slice(0, 5).forEach((url, index) => {
        console.log(`    [${index + 1}] ${url}`)
      })
    }

    // 記事本文の画像を探す
    console.log('')
    console.log('[Step 5] 記事本文の画像を探索...')
    const articleImageMatch = html.match(/<article[^>]*>[\s\S]*?<img[^>]+src=["']([^"']+)["']/i)
    if (articleImageMatch) {
      console.log(`  ✓ 記事本文の画像: ${articleImageMatch[1]}`)
    } else {
      console.log('  ✗ 記事本文の画像が見つかりませんでした')
    }

    // サムネイル画像を探す
    const thumbnailMatch = html.match(/news__thumbnail[^>]*background-image:\s*url\(([^)]+)\)/i)
    if (thumbnailMatch) {
      console.log(`  ✓ サムネイル画像: ${thumbnailMatch[1]}`)
    } else {
      console.log('  ✗ サムネイル画像が見つかりませんでした')
    }

    console.log('')
    console.log('='.repeat(80))
    console.log('[Summary] 調査結果')
    console.log('='.repeat(80))
    console.log('')
    console.log('推奨される画像取得方法:')
    if (ogImageMatch) {
      console.log('  1. og:image メタタグから取得（最優先）')
      console.log(`     URL: ${ogImageMatch[1]}`)
    } else if (twitterImageMatch) {
      console.log('  1. twitter:image メタタグから取得')
      console.log(`     URL: ${twitterImageMatch[1]}`)
    } else if (thumbnailMatch) {
      console.log('  1. サムネイル画像から取得')
      console.log(`     URL: ${thumbnailMatch[1]}`)
    } else {
      console.log('  ✗ 画像URLが見つかりませんでした')
    }

  } catch (error) {
    console.error('エラー:', error.message)
    if (error.stack) {
      console.error('Stack:', error.stack)
    }
  }
}

debugAuoneArticle()







