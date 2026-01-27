/**
 * 日刊スポーツMLBのRSSフィードから取得したpubDateの形式を調査
 */

const RSS_URL = 'https://www.nikkansports.com/baseball/mlb/atom.xml'

async function debugNikkansportsMLB() {
  console.log('='.repeat(80))
  console.log('[Debug] 日刊スポーツMLB RSSフィードのpubDate形式調査')
  console.log('='.repeat(80))
  console.log('')

  try {
    console.log(`[Step 1] RSSフィードを取得: ${RSS_URL}`)
    const response = await fetch(RSS_URL, {
      method: 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      },
      redirect: 'follow',
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const xml = await response.text()
    console.log(`  ✓ XML取得成功: ${xml.length} bytes`)
    console.log('')

    // XMLをパース
    console.log('[Step 2] XMLをパース...')
    const Parser = (await import('rss-parser')).default
    const parser = new Parser({
      customFields: {
        item: ['published', 'updated'],
      },
    })

    const feed = await parser.parseString(xml)
    console.log(`  ✓ パース成功: ${feed.items.length}件の記事`)
    console.log('')

    // 最初の5件のpubDateを確認
    console.log('[Step 3] 最初の5件のpubDate形式を確認:')
    console.log('')
    feed.items.slice(0, 5).forEach((item, index) => {
      console.log(`--- Item ${index + 1} ---`)
      console.log(`Title: ${item.title?.substring(0, 50)}...`)
      console.log(`pubDate (raw): ${item.pubDate}`)
      console.log(`published (raw): ${item.published}`)
      console.log(`isoDate (raw): ${item.isoDate}`)
      
      // pubDateをDateオブジェクトに変換
      if (item.pubDate) {
        const date = new Date(item.pubDate)
        console.log(`pubDate parsed: ${date.toISOString()}`)
        console.log(`pubDate isValid: ${!isNaN(date.getTime())}`)
      }
      
      // isoDateをDateオブジェクトに変換
      if (item.isoDate) {
        const date = new Date(item.isoDate)
        console.log(`isoDate parsed: ${date.toISOString()}`)
        console.log(`isoDate isValid: ${!isNaN(date.getTime())}`)
      }
      
      // publishedをDateオブジェクトに変換
      if (item.published) {
        const date = new Date(item.published)
        console.log(`published parsed: ${date.toISOString()}`)
        console.log(`published isValid: ${!isNaN(date.getTime())}`)
      }
      
      console.log('')
    })

    // すべての記事のpubDateを確認
    console.log('[Step 4] すべての記事のpubDateを時系列で確認:')
    console.log('')
    const itemsWithDates = feed.items.map(item => {
      let date = null
      let dateSource = 'none'
      
      if (item.isoDate) {
        date = new Date(item.isoDate)
        dateSource = 'isoDate'
      } else if (item.published) {
        date = new Date(item.published)
        dateSource = 'published'
      } else if (item.pubDate) {
        date = new Date(item.pubDate)
        dateSource = 'pubDate'
      }
      
      return {
        title: item.title,
        date,
        dateSource,
        pubDate: item.pubDate,
        published: item.published,
        isoDate: item.isoDate,
      }
    }).filter(item => item.date !== null)

    // 時系列でソート
    itemsWithDates.sort((a, b) => {
      if (!a.date || !b.date) return 0
      return b.date.getTime() - a.date.getTime()
    })

    itemsWithDates.forEach((item, index) => {
      console.log(`[${index + 1}] ${item.date?.toISOString()} (${item.dateSource}) - ${item.title?.substring(0, 50)}...`)
    })

    console.log('')
    console.log('='.repeat(80))
    console.log('[Summary] 調査結果')
    console.log('='.repeat(80))
    console.log('')
    console.log(`総記事数: ${feed.items.length}`)
    console.log(`日付情報がある記事数: ${itemsWithDates.length}`)
    console.log(`日付情報がない記事数: ${feed.items.length - itemsWithDates.length}`)
    console.log('')
    console.log('推奨されるpublishedAtフィールドの設定:')
    console.log('  1. isoDate を優先（最も正確）')
    console.log('  2. published を次に優先')
    console.log('  3. pubDate を最後に使用（形式が様々なため）')

  } catch (error) {
    console.error('エラー:', error.message)
    if (error.stack) {
      console.error('Stack:', error.stack)
    }
  }
}

debugNikkansportsMLB()

