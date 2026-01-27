/**
 * auone.jpのHTML構造をデバッグするスクリプト
 * 
 * 実際のHTMLから記事情報がどのように抽出されるかを確認
 */

const BASE_URL = 'https://article.auone.jp/keyword/article/1'

async function debugAuoneHtml() {
  console.log('='.repeat(80))
  console.log('[Debug] auone.jp HTML構造のデバッグ')
  console.log('='.repeat(80))
  console.log('')

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

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const html = await response.text()

    // リストアイテムを抽出
    const listItemPattern = /<li[^>]*>([\s\S]*?)<\/li>/gi
    let match
    let count = 0

    console.log('[Sample] 最初の5つのリストアイテムのHTML構造:')
    console.log('')

    while ((match = listItemPattern.exec(html)) !== null && count < 5) {
      const itemHtml = match[1]
      const linkMatch = itemHtml.match(/<a[^>]+href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/i)
      
      if (linkMatch && linkMatch[1].includes('article.auone.jp/detail')) {
        count++
        console.log(`--- Item ${count} ---`)
        console.log(`Link: ${linkMatch[1]}`)
        console.log(`Link Text (raw): ${linkMatch[2].substring(0, 200)}`)
        console.log(`Link Text (cleaned): ${linkMatch[2].replace(/<[^>]+>/g, '').trim().substring(0, 200)}`)
        
        // 日付を抽出
        const dateMatch = itemHtml.match(/(\d{2}\/\d{2}\s+\d{2}:\d{2})/)
        if (dateMatch) {
          console.log(`Date: ${dateMatch[1]}`)
          const afterDate = itemHtml.substring(dateMatch.index + dateMatch[0].length)
          console.log(`After Date (raw, first 200 chars): ${afterDate.substring(0, 200)}`)
          console.log(`After Date (cleaned, first 200 chars): ${afterDate.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().substring(0, 200)}`)
        }
        
        // ソースを抽出（複数のパターンを試す）
        const sourcePatterns = [
          /(\d{2}\/\d{2}\s+\d{2}:\d{2})\s+([A-Za-z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\s\-\.]+)/,
          /<span[^>]*>([^<]+)<\/span>/,
          />([A-Za-z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\s\-\.]+)</,
        ]
        
        for (let i = 0; i < sourcePatterns.length; i++) {
          const sourceMatch = itemHtml.match(sourcePatterns[i])
          if (sourceMatch) {
            console.log(`Source Pattern ${i + 1}: ${sourceMatch[sourceMatch.length - 1]}`)
          }
        }
        
        console.log(`Full HTML (first 500 chars): ${itemHtml.substring(0, 500)}`)
        console.log('')
      }
    }

    console.log('='.repeat(80))
    console.log('[Debug] 完了')
    console.log('='.repeat(80))

  } catch (error) {
    console.error('エラー:', error.message)
    if (error.stack) {
      console.error('Stack:', error.stack)
    }
  }
}

debugAuoneHtml()







