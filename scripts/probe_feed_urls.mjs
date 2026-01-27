/**
 * RSS/AtomフィードURLの候補をテストして、有効なものを検出するスクリプト
 * 
 * 使い方:
 *   node scripts/probe_feed_urls.mjs
 * 
 * 注意: Node.js 18以降が必要（fetch APIが標準で利用可能）
 */

/**
 * 候補URLをテスト
 * @param {string} url - テストするURL
 * @param {number} timeout - タイムアウト（ミリ秒）
 * @returns {Promise<{url: string, status: number, contentType: string, isValid: boolean, preview: string, error?: string}>}
 */
async function probeUrl(url, timeout = 5000) {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
      },
    });

    clearTimeout(timeoutId);

    const status = response.status;
    const contentType = response.headers.get('content-type') || '';

    // 先頭200文字を取得
    const text = await response.text();
    const preview = text.substring(0, 200);

    // RSS/Atom判定: 先頭付近に "<rss" か "<feed" が含まれているか
    const normalizedPreview = preview.toLowerCase().trim();
    const hasRss = normalizedPreview.includes('<rss') || normalizedPreview.includes('<?xml version="1.0"');
    const hasFeed = normalizedPreview.includes('<feed');
    
    const isValid = status === 200 && (hasRss || hasFeed);

    return {
      url,
      status,
      contentType,
      isValid,
      preview: preview.replace(/\n/g, ' ').substring(0, 150),
      feedType: hasRss ? 'rss' : hasFeed ? 'atom' : 'unknown',
    };
  } catch (error) {
    const errorMessage = error.name === 'AbortError' ? 'Timeout' : error.message;
    return {
      url,
      status: 0,
      contentType: '',
      isValid: false,
      preview: '',
      error: errorMessage,
    };
  }
}

/**
 * メイン処理
 */
async function main() {
  const candidateUrls = {
    'スポーツ報知': [
      'https://hochi.news/rss/',
      'https://hochi.news/rss.xml',
      'https://hochi.news/feed',
      'https://hochi.news/feed.xml',
      'https://hochi.news/atom.xml',
      'https://hochi.news/rss/sports.xml',
      'https://hochi.news/rss/baseball.xml',
    ],
    'サンケイスポーツ': [
      'https://www.sanspo.com/rss/',
      'https://www.sanspo.com/rss.xml',
      'https://www.sanspo.com/feed',
      'https://www.sanspo.com/feed.xml',
      'https://www.sanspo.com/atom.xml',
      'https://www.sanspo.com/rss/sports.xml',
      'https://www.sanspo.com/rss/baseball.xml',
    ],
  };

  console.log('=== RSS/AtomフィードURLプローブ開始 ===\n');

  const results = {};

  for (const [sourceName, urls] of Object.entries(candidateUrls)) {
    console.log(`\n[${sourceName}] ${urls.length}個の候補URLをテスト中...\n`);

    results[sourceName] = [];

    for (const url of urls) {
      process.stdout.write(`  テスト中: ${url} ... `);
      const result = await probeUrl(url);
      results[sourceName].push(result);

      if (result.isValid) {
        console.log(`✓ 有効 (${result.feedType.toUpperCase()}, status: ${result.status})`);
      } else if (result.error) {
        console.log(`✗ エラー: ${result.error}`);
      } else {
        console.log(`✗ 無効 (status: ${result.status}, RSS/Atom形式ではない)`);
      }
    }
  }

  // 結果サマリー
  console.log('\n\n=== プローブ結果サマリー ===\n');

  for (const [sourceName, resultList] of Object.entries(results)) {
    const validUrls = resultList.filter(r => r.isValid);
    
    console.log(`[${sourceName}]`);
    if (validUrls.length === 0) {
      console.log('  → 有効なRSS/Atomフィードが見つかりませんでした。\n');
    } else {
      console.log(`  → ${validUrls.length}個の有効なフィードが見つかりました:\n`);
      validUrls.forEach((result) => {
        console.log(`    ✓ ${result.url}`);
        console.log(`      タイプ: ${result.feedType.toUpperCase()}, Status: ${result.status}, Content-Type: ${result.contentType}`);
        console.log(`      プレビュー: ${result.preview}\n`);
      });
    }
  }

  // JSON形式で出力（設定ファイルに追加する際に便利）
  console.log('\n=== 設定ファイル用JSON（有効なフィードのみ） ===\n');
  const jsonOutput = {};
  for (const [sourceName, resultList] of Object.entries(results)) {
    const validUrls = resultList.filter(r => r.isValid);
    if (validUrls.length > 0) {
      jsonOutput[sourceName] = validUrls.map(r => ({
        name: sourceName,
        url: r.url,
        type: r.feedType,
        contentType: r.contentType,
      }));
    }
  }
  console.log(JSON.stringify(jsonOutput, null, 2));
}

main().catch(console.error);

