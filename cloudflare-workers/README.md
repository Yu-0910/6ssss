# Cloudflare Workers dmenu プロキシ

このディレクトリには、dmenu APIへのプロキシとして機能するCloudflare Workersスクリプトが含まれています。

## 概要

Node.jsアプリケーションから直接dmenu APIにアクセスすると、SSL/TLSレガシーリネゴシエーションエラーが発生します。このプロキシは、Cloudflare Workersの環境でdmenu APIにアクセスし、Node.jsアプリにレスポンスを返します。

## セットアップ手順

### 1. Cloudflareアカウントの作成

1. [Cloudflare](https://www.cloudflare.com/) にアクセス
2. アカウントを作成（無料プランで利用可能）

### 2. Workers & Pages ダッシュボードへのアクセス

1. Cloudflareダッシュボードにログイン
2. 左メニューから「Workers & Pages」を選択
3. 「Create application」をクリック

### 3. Workerの作成

1. 「Create Worker」を選択
2. Worker名を入力（例: `dmenu-proxy`）
3. 「Deploy」をクリック

### 4. コードのデプロイ

1. エディタで `dmenu-proxy.js` の内容をコピー
2. Cloudflare Workersエディタに貼り付け
3. 「Save and deploy」をクリック

### 5. Worker URLの確認

1. デプロイ後、Worker URLが表示されます
2. 例: `https://dmenu-proxy.your-subdomain.workers.dev`
3. このURLをコピー

### 6. 動作確認

ブラウザまたはcurlでアクセスして確認：

```bash
curl https://dmenu-proxy.your-subdomain.workers.dev
```

正常に動作していれば、dmenu APIのJSONレスポンスが返ってきます。

## Next.jsアプリへの統合

### 環境変数の設定

`.env.local` ファイルに以下を追加：

```env
DMENU_PROXY_URL=https://dmenu-proxy.your-subdomain.workers.dev
```

### コードの修正

`app/lib/dmenu.ts` を修正して、プロキシURLを使用するようにします（計画書のPhase 2を参照）。

## トラブルシューティング

### エラー: CORSエラー

- Cloudflare WorkersのCORSヘッダーが正しく設定されているか確認
- ブラウザの開発者ツールでレスポンスヘッダーを確認

### エラー: 502 Bad Gateway

- dmenu APIが利用可能か確認
- Cloudflare Workersのログを確認

### エラー: Invalid JSON

- dmenu APIのレスポンス形式が変更されていないか確認
- レスポンスの最初の200文字をログで確認

## カスタマイズ

### キャッシュ時間の変更

`dmenu-proxy.js` の `Cache-Control` ヘッダーを変更：

```javascript
'Cache-Control': 'public, max-age=600', // 10分に変更
```

### エラーハンドリングの強化

エラーレスポンスに詳細な情報を追加する場合は、`catch` ブロックを修正してください。

## コスト

Cloudflare Workersの無料プランでは：
- 1日10万リクエストまで無料
- CPU時間: 10ms/リクエスト（無料プラン）
- 通常の使用では十分な制限です

## セキュリティ

- プロキシは公開エンドポイントのため、レート制限を検討してください
- 必要に応じて、認証トークンやAPIキーを追加してください







