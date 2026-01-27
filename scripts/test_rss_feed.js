/**
 * RSSフィードの動作確認用スクリプト
 * Node.jsで直接実行してRSSフィードが取得できるかテストする
 */

const Parser = require('rss-parser')

const parser = new Parser({
  timeout: 10000,
  headers: {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
  },
})

const testFeeds = [
  { name: 'スポーツニッポン', url: 'https://www.sponichi.co.jp/baseball/news.rdf' },
  { name: '日刊スポーツ', url: 'https://www.nikkansports.com/baseball/news/rss.xml' },
  { name: 'スポーツ報知', url: 'https://hochi.news/sports/baseball/rss.xml' },
]

async function testRSSFeed(feed) {
  console.log(`\n[テスト] ${feed.name} (${feed.url})`)
  try {
    const feedData = await parser.parseURL(feed.url)
    console.log(`  ✓ 取得成功`)
    console.log(`  - タイトル: ${feedData.title || 'N/A'}`)
    console.log(`  - 記事数: ${feedData.items?.length || 0}`)
    if (feedData.items && feedData.items.length > 0) {
      console.log(`  - 最初の記事: ${feedData.items[0].title || 'N/A'}`)
    }
    return true
  } catch (error) {
    console.error(`  ✗ 取得失敗: ${error.message}`)
    if (error.message.includes('404')) {
      console.error(`    → URLが無効の可能性があります`)
    } else if (error.message.includes('403') || error.message.includes('401')) {
      console.error(`    → 認証が必要な可能性があります`)
    } else if (error.message.includes('timeout') || error.message.includes('ETIMEDOUT')) {
      console.error(`    → タイムアウト: 接続に時間がかかりすぎています`)
    } else if (error.message.includes('ECONNREFUSED')) {
      console.error(`    → 接続拒否: ネットワークエラーまたはURLが無効`)
    }
    return false
  }
}

async function main() {
  console.log('RSSフィードの動作確認を開始します...\n')
  
  const results = await Promise.allSettled(
    testFeeds.map(feed => testRSSFeed(feed))
  )
  
  const successCount = results.filter(r => r.status === 'fulfilled' && r.value).length
  const failCount = results.length - successCount
  
  console.log(`\n=== 結果 ===`)
  console.log(`成功: ${successCount}/${testFeeds.length}`)
  console.log(`失敗: ${failCount}/${testFeeds.length}`)
}

main().catch(console.error)









