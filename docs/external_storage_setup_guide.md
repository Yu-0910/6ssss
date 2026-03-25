# 外部ストレージ準備ガイド

Phase 3（段階的移行）に進む前に、外部ストレージの準備が必要です。

## 必要な作業

### 1. 外部ストレージサービスの選択とセットアップ

以下のいずれかのサービスを選択してセットアップしてください：

#### 推奨サービス

**A. Cloudflare R2（推奨）**
- **メリット**: 無料枠が大きい、CDN統合、CORS設定不要（プロキシ経由のため）
- **セットアップ手順**:
  1. [Cloudflare R2](https://developers.cloudflare.com/r2/) にアクセス
  2. アカウント作成（既にCloudflareアカウントがある場合はログイン）
  3. R2バケットを作成
  4. バケット名を記録（例: `rankings-data`）
  5. 公開読み取りアクセスを有効化（Public Access）

**B. AWS S3**
- **メリット**: 実績豊富、信頼性が高い
- **セットアップ手順**:
  1. [AWS S3](https://aws.amazon.com/s3/) にアクセス
  2. バケットを作成
  3. バケットポリシーで公開読み取りアクセスを設定
  4. バケット名とリージョンを記録

**C. Vercel Blob**
- **メリット**: Vercelと統合、設定が簡単
- **セットアップ手順**:
  1. VercelダッシュボードでBlobストレージを作成
  2. ストア名を記録

**D. GitHub Releases（小規模データ向け）**
- **メリット**: 無料、GitHubと統合
- **デメリット**: ファイルサイズ制限あり（100MB/ファイル）

### 2. データのアップロード（2025/PLのみ）

**重要**: Phase 3では2025/PLのみを外部化するため、まずはこのデータだけをアップロードします。

#### アップロード対象

以下のディレクトリ内のすべてのJSONファイル：
```
public/data/rankings/2025/PL/
```

**ファイル例:**
- `OPS.json`
- `打率.json`
- `AVG.json`
- `HR.json`
- `BABIP.json`
- など（約72ファイル）

#### パス構造の維持

**重要**: 外部ストレージでも、現在のパス構造を完全に維持してください。

**現在の構造:**
```
public/data/rankings/2025/PL/OPS.json
```

**外部ストレージでの構造（例）:**
```
data/rankings/2025/PL/OPS.json
```

または、バケットのルートに `data/rankings/` ディレクトリを作成して、その中に `2025/PL/` を配置。

#### アップロード方法

**A. Cloudflare R2 の場合**

1. **R2 API トークンの作成**
   - Cloudflareダッシュボード → R2 → Manage R2 API Tokens
   - 新しいAPIトークンを作成（読み書き権限）

2. **アップロード方法（選択肢）**

   **方法1: Cloudflareダッシュボードから**
   - R2バケットを開く
   - `data/rankings/2025/PL/` ディレクトリを作成
   - ファイルをドラッグ&ドロップでアップロード

   **方法2: Wrangler CLI を使用**
   ```bash
   # Wranglerのインストール
   npm install -g wrangler
   
   # ログイン
   wrangler login
   
   # ファイルをアップロード
   wrangler r2 object put data/rankings/2025/PL/OPS.json --file=public/data/rankings/2025/PL/OPS.json
   ```

   **方法3: スクリプトで一括アップロード（推奨）**
   - 後述の「アップロードスクリプト」を参照

**B. AWS S3 の場合**

1. **AWS CLI のインストールと設定**
   ```bash
   aws configure
   ```

2. **アップロード**
   ```bash
   aws s3 sync public/data/rankings/2025/PL/ s3://your-bucket-name/data/rankings/2025/PL/
   ```

**C. Vercel Blob の場合**

1. **Vercel CLI のインストール**
   ```bash
   npm install -g vercel
   ```

2. **アップロード（Vercel Blob SDK を使用）**
   - 後述の「アップロードスクリプト」を参照

### 3. 公開URLの確認

アップロード後、以下のURLでアクセスできることを確認してください：

**例（Cloudflare R2）:**
```
https://your-account-id.r2.cloudflarestorage.com/data/rankings/2025/PL/OPS.json
```

**例（AWS S3）:**
```
https://your-bucket-name.s3.amazonaws.com/data/rankings/2025/PL/OPS.json
```

**重要**: 
- URLは必ず `https://` で始まること
- パス構造が `data/rankings/2025/PL/{ファイル名}.json` になっていること
- ブラウザで直接アクセスしてJSONが表示されること（CORSエラーが出ても問題なし、プロキシ経由でアクセスするため）

### 4. ベースURLの決定

外部ストレージのベースURLを決定します。

**例（Cloudflare R2）:**
```
https://your-account-id.r2.cloudflarestorage.com
```

**例（AWS S3）:**
```
https://your-bucket-name.s3.amazonaws.com
```

**注意**: 
- 末尾にスラッシュ（`/`）は不要
- `data/rankings/` は含めない（プロキシルートで自動的に追加される）

## アップロードスクリプト（オプション）

一括アップロード用のスクリプトを作成することもできます。必要に応じて作成します。

### Cloudflare R2 用アップロードスクリプト例

```typescript
// scripts/upload_to_r2.ts
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3'
import * as fs from 'fs'
import * as path from 'path'

const accountId = process.env.CLOUDFLARE_ACCOUNT_ID
const accessKeyId = process.env.CLOUDFLARE_R2_ACCESS_KEY_ID
const secretAccessKey = process.env.CLOUDFLARE_R2_SECRET_ACCESS_KEY
const bucketName = process.env.CLOUDFLARE_R2_BUCKET_NAME

const s3Client = new S3Client({
  region: 'auto',
  endpoint: `https://${accountId}.r2.cloudflarestorage.com`,
  credentials: {
    accessKeyId: accessKeyId!,
    secretAccessKey: secretAccessKey!,
  },
})

async function uploadFile(localPath: string, remotePath: string) {
  const fileContent = fs.readFileSync(localPath)
  
  const command = new PutObjectCommand({
    Bucket: bucketName,
    Key: remotePath,
    Body: fileContent,
    ContentType: 'application/json',
  })
  
  await s3Client.send(command)
  console.log(`✅ Uploaded: ${remotePath}`)
}

async function uploadDirectory(localDir: string, remotePrefix: string) {
  const files = fs.readdirSync(localDir, { withFileTypes: true })
  
  for (const file of files) {
    const localPath = path.join(localDir, file.name)
    const remotePath = `${remotePrefix}/${file.name}`
    
    if (file.isDirectory()) {
      await uploadDirectory(localPath, remotePath)
    } else if (file.name.endsWith('.json')) {
      await uploadFile(localPath, remotePath)
    }
  }
}

async function main() {
  const localPath = path.join(process.cwd(), 'public', 'data', 'rankings', '2025', 'PL')
  const remotePrefix = 'data/rankings/2025/PL'
  
  console.log(`Uploading from ${localPath} to ${remotePrefix}...`)
  await uploadDirectory(localPath, remotePrefix)
  console.log('✅ Upload complete!')
}

main().catch(console.error)
```

## チェックリスト

外部ストレージの準備が完了したら、以下を確認してください：

- [ ] 外部ストレージサービスを選択・セットアップした
- [ ] 2025/PLのデータ（約72ファイル）をアップロードした
- [ ] パス構造が `data/rankings/2025/PL/{ファイル名}.json` になっている
- [ ] ベースURLで直接アクセスできることを確認した（例: `https://.../data/rankings/2025/PL/OPS.json`）
- [ ] ベースURLを記録した（Vercelの環境変数設定で使用）

## 次のステップ

外部ストレージの準備が完了したら、Phase 3に進みます：

1. Vercelの環境変数を設定
   - `RANKINGS_BASE_URL`: 外部ストレージのベースURL
   - `RANKINGS_EXTERNALIZE_SCOPE`: `2025_pl`
2. 動作確認
3. 問題なければ、他の年度・リーグも段階的に外部化

## トラブルシューティング

### ファイルが見つからない（404エラー）

- パス構造を確認（`data/rankings/2025/PL/` になっているか）
- ファイル名の大文字小文字を確認
- 外部ストレージの公開設定を確認

### CORSエラー

- **問題なし**: プロキシ経由でアクセスするため、CORSエラーは発生しません
- ブラウザで直接アクセスしてCORSエラーが出ても、プロキシ経由なら問題ありません

### タイムアウトエラー

- 外部ストレージのリージョンを確認（可能であれば、Vercelと同じリージョンに配置）
- ネットワーク接続を確認

## 参考リンク

- [Cloudflare R2 Documentation](https://developers.cloudflare.com/r2/)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [Vercel Blob Documentation](https://vercel.com/docs/storage/vercel-blob)
