/**
 * auone.ts モジュールのテストスクリプト
 * 
 * 使用方法:
 *   node scripts/test_auone.mjs [API_URL]
 * 
 * 例:
 *   node scripts/test_auone.mjs http://localhost:3000/api/articles?debug=1
 */

const API_URL = process.argv[2] || 'http://localhost:3000/api/articles?debug=1'

async function testAuone() {
  console.log('='.repeat(80))
  console.log('[Test] auone.ts モジュールのテスト（API経由）')
  console.log('='.repeat(80))
  console.log('')

  try {
    console.log('[Step 1] APIエンドポイントにアクセス...')
    console.log(`  URL: ${API_URL}`)
    
    const response = await fetch(API_URL)
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    const data = await response.json()

    console.log('')
    console.log('[Step 2] 結果の確認...')
    
    // auone記事を抽出
    const auoneArticles = data.articles?.filter(a => a.id?.startsWith('auone-')) || []
    console.log(`  - 全記事数: ${data.articles?.length || 0}`)
    console.log(`  - auone記事数: ${auoneArticles.length}`)
    
    if (data.auoneDebug) {
      const debug = data.auoneDebug
      console.log(`  - HTML長: ${debug.htmlLength} bytes`)
      console.log(`  - 抽出数: ${debug.extractedCount}`)
      console.log(`  - サンプル記事数: ${debug.sampleArticles?.length || 0}`)
      
      if (debug.errors && debug.errors.length > 0) {
        console.log(`  - エラー数: ${debug.errors.length}`)
        debug.errors.forEach((error, index) => {
          console.log(`    [${index + 1}] ${error}`)
        })
      }
    } else {
      console.log('  - デバッグ情報: なし（debugModeがfalseの可能性）')
    }

    console.log('')
    console.log('[Step 3] auone記事のサンプル:')
    if (auoneArticles.length > 0) {
      auoneArticles.slice(0, 5).forEach((article, index) => {
        console.log(`  [${index + 1}] ${article.title}`)
        console.log(`      URL: ${article.link}`)
        console.log(`      日付: ${article.date} (${article.publishedAt || 'N/A'})`)
        console.log(`      ソース: ${article.source}`)
        console.log('')
      })
    } else {
      console.log('  ✗ auone記事が取得できませんでした')
      if (data.auoneDebug) {
        console.log('  デバッグ情報:')
        console.log(JSON.stringify(data.auoneDebug, null, 2))
      }
    }

    console.log('')
    console.log('='.repeat(80))
    if (auoneArticles.length > 0) {
      console.log('[Result] ✓ テスト成功')
      console.log(`[Result] ${auoneArticles.length}件のauone記事を取得`)
    } else {
      console.log('[Result] ✗ テスト失敗: auone記事が取得できませんでした')
      if (data.auoneDebug?.errors) {
        console.log('[Result] エラー:', data.auoneDebug.errors.join(', '))
      }
    }
    console.log('='.repeat(80))

  } catch (error) {
    console.error('')
    console.error('='.repeat(80))
    console.error('[Result] ✗ テスト失敗')
    console.error('[Result] エラー:', error.message)
    if (error.stack) {
      console.error('[Result] Stack:', error.stack)
    }
    console.error('='.repeat(80))
    process.exit(1)
  }
}

testAuone()

