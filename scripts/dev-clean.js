/**
 * 開発サーバー起動前に .next/dev をクリアする（ロック競合対策）
 */
const fs = require('fs');
const path = require('path');

const devDir = path.join(process.cwd(), '.next', 'dev');
try {
  if (fs.existsSync(devDir)) {
    fs.rmSync(devDir, { recursive: true, force: true });
    console.log('[DEV] .next/dev をクリアしました');
  }
} catch (e) {
  // 無視
}
