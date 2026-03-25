#!/usr/bin/env node
/**
 * Phase 4: public/data/rankings/ を R2 に同一パス構造でアップロードする。
 * R2 キー: data/rankings/{年}/{リーグ}/{ファイル名}
 *
 * 前提: あなたの作業が必要
 * - Cloudflare ダッシュボードで R2 API トークン（Access Key ID / Secret）を発行する
 * - 以下の環境変数を設定してから実行する
 *
 *   CLOUDFLARE_ACCOUNT_ID   … ダッシュボードの「アカウント ID」
 *   R2_ACCESS_KEY_ID        … R2 Manage R2 API Tokens で作成した ID
 *   R2_SECRET_ACCESS_KEY    … 同上の Secret
 *   R2_BUCKET_NAME          … バケット名（例: rankings-data）
 *
 * 実行例:
 *   node scripts/upload-rankings-to-r2.mjs           # アップロード実行
 *   node scripts/upload-rankings-to-r2.mjs --dry-run # 対象一覧のみ表示（アップロードしない）
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '..');
const RANKINGS_DIR = path.join(PROJECT_ROOT, 'public', 'data', 'rankings');

const DRY_RUN = process.argv.includes('--dry-run');
const CONCURRENCY = 5;

function* walkFiles(dirAbs, baseDir) {
  const entries = fs.readdirSync(dirAbs, { withFileTypes: true });
  for (const e of entries) {
    const full = path.join(dirAbs, e.name);
    if (e.isDirectory()) {
      yield* walkFiles(full, baseDir);
    } else if (e.isFile()) {
      const ext = path.extname(e.name).toLowerCase();
      if (ext === '.json') {
        const relative = path.relative(baseDir, full).replace(/\\/g, '/');
        yield { localPath: full, r2Key: `data/rankings/${relative}` };
      }
    }
  }
}

function collectUploadList() {
  if (!fs.existsSync(RANKINGS_DIR)) {
    console.error('Error: public/data/rankings が存在しません。');
    process.exit(1);
  }
  return [...walkFiles(RANKINGS_DIR, RANKINGS_DIR)];
}

async function uploadWithS3(list) {
  const accountId = process.env.CLOUDFLARE_ACCOUNT_ID || process.env.R2_ACCOUNT_ID;
  const accessKeyId = process.env.R2_ACCESS_KEY_ID;
  const secretAccessKey = process.env.R2_SECRET_ACCESS_KEY;
  const bucket = process.env.R2_BUCKET_NAME;

  if (!accountId || !accessKeyId || !secretAccessKey || !bucket) {
    console.error('次の環境変数を設定してください（Cloudflare R2 の API トークン発行が必要です）:');
    if (!accountId) console.error('  - CLOUDFLARE_ACCOUNT_ID または R2_ACCOUNT_ID');
    if (!accessKeyId) console.error('  - R2_ACCESS_KEY_ID');
    if (!secretAccessKey) console.error('  - R2_SECRET_ACCESS_KEY');
    if (!bucket) console.error('  - R2_BUCKET_NAME');
    console.error('\n手順: docs/phase4_upload_steps.md を参照してください。');
    process.exit(1);
  }

  const endpoint = `https://${accountId}.r2.cloudflarestorage.com`;
  const { S3Client, PutObjectCommand } = await import('@aws-sdk/client-s3');
  const client = new S3Client({
    region: 'auto',
    endpoint,
    credentials: { accessKeyId, secretAccessKey },
  });

  let done = 0;
  const total = list.length;
  const run = async (item) => {
    const body = fs.readFileSync(item.localPath);
    await client.send(
      new PutObjectCommand({
        Bucket: bucket,
        Key: item.r2Key,
        Body: body,
        ContentType: 'application/json',
      })
    );
    done++;
    if (done % 50 === 0 || done === total) {
      console.log(`Uploaded ${done}/${total} ...`);
    }
  };

  for (let i = 0; i < list.length; i += CONCURRENCY) {
    const batch = list.slice(i, i + CONCURRENCY);
    await Promise.all(batch.map(run));
  }
}

async function main() {
  const list = collectUploadList();
  console.log(`対象: ${list.length} ファイル (public/data/rankings/ の .json のみ)`);
  if (list.length === 0) {
    console.log('アップロード対象がありません。');
    return;
  }

  if (DRY_RUN) {
    console.log('--dry-run のためアップロードは行いません。先頭 20 件:');
    list.slice(0, 20).forEach(({ r2Key }) => console.log('  ', r2Key));
    if (list.length > 20) console.log(`  ... 他 ${list.length - 20} 件`);
    return;
  }

  console.log('R2 へアップロードを開始します...');
  await uploadWithS3(list);
  console.log(`完了: ${list.length} ファイルをアップロードしました。`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
