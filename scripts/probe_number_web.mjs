/**
 * Number Webのプロ野球RSS URLを探すスクリプト
 */

const candidateUrls = [
  'https://number.bunshun.jp/feed/pro-baseball',
  'https://number.bunshun.jp/rss/pro-baseball',
  'https://number.bunshun.jp/feed/baseball',
  'https://number.bunshun.jp/rss/baseball',
  'https://number.bunshun.jp/list/feed/pro-baseball',
  'https://number.bunshun.jp/list/rss/pro-baseball',
];

console.log('=== Number Webプロ野球RSS URLプローブ ===\n');

for (const url of candidateUrls) {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      },
    });

    clearTimeout(timeoutId);

    const status = response.status;
    const contentType = response.headers.get('content-type') || '';
    const text = await response.text();
    const preview = text.substring(0, 200).toLowerCase();

    const isRss = preview.includes('<rss') || preview.includes('<?xml version="1.0"');
    const isAtom = preview.includes('<feed');

    if (status === 200 && (isRss || isAtom)) {
      console.log(`✓ ${url}`);
      console.log(`  タイプ: ${isRss ? 'RSS' : 'Atom'}, Status: ${status}, Content-Type: ${contentType}`);
      console.log(`  プレビュー: ${text.substring(0, 150).replace(/\n/g, ' ')}\n`);
    } else {
      console.log(`✗ ${url} (status: ${status}, RSS/Atom: ${isRss || isAtom})`);
    }
  } catch (error) {
    const errorMessage = error.name === 'AbortError' ? 'Timeout' : error.message;
    console.log(`✗ ${url} (エラー: ${errorMessage})`);
  }
}









