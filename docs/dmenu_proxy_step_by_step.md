# dmenu プロキシ統合 ステップバイステップガイド

このガイドでは、Cloudflare Workersプロキシを使用してdmenu APIにアクセスする実装を、段階的に進めます。

## 実装の全体像

```
[Next.js App] → [Cloudflare Workers] → [dmenu API]
     ↓                ↓                      ↓
  Node.js      (SSL/TLS処理)        (レガシーSSL/TLS)
```

## Phase 1: Cloudflare Workersプロキシの作成 ✅

### Step 1.1: Cloudflareアカウントの作成

1. [Cloudflare](https://www.cloudflare.com/) にアクセス
2. アカウントを作成（無料プランで利用可能）

### Step 1.2: Workerの作成

1. Cloudflareダッシュボードにログイン
2. 左メニューから「Workers & Pages」を選択
3. 「Create application」→「Create Worker」を選択
4. Worker名を入力（例: `dmenu-proxy`）
5. 「Deploy」をクリック

### Step 1.3: コードのデプロイ

1. `cloudflare-workers/dmenu-proxy.js` の内容をコピー
2. Cloudflare Workersエディタに貼り付け
3. 「Save and deploy」をクリック

### Step 1.4: Worker URLの確認

1. デプロイ後、Worker URLが表示されます
2. 例: `https://dmenu-proxy.your-subdomain.workers.dev`
3. このURLをコピー（次のステップで使用）

### Step 1.5: プロキシの動作確認

プロジェクトルートで以下を実行：

```bash
npm run test:proxy https://dmenu-proxy.your-subdomain.workers.dev
```

正常に動作していれば、以下のような出力が表示されます：

```
================================================================================
[Result] ✓ Proxy test PASSED
[Result] Total time: XXXms
[Result] Articles found: XX
================================================================================
```

## Phase 2: Next.jsアプリの修正 ✅

### Step 2.1: 環境変数の設定

1. `.env.local.example` をコピーして `.env.local` を作成：

```bash
cp .env.local.example .env.local
```

2. `.env.local` を開き、プロキシURLを設定：

```env
DMENU_PROXY_URL=https://dmenu-proxy.your-subdomain.workers.dev
```

### Step 2.2: コードの確認

`app/lib/dmenu.ts` は既にプロキシ対応済みです。以下の機能が実装されています：

- ✅ 環境変数 `DMENU_PROXY_URL` の読み込み
- ✅ プロキシ経由と直接接続の自動切り替え
- ✅ プロキシ経由時は標準`fetch`を使用
- ✅ 直接接続時は既存の`https.request`を使用（フォールバック）
- ✅ 詳細なログ出力（`logs/dmenu_fetch.log`）

### Step 2.3: 開発サーバーの再起動

環境変数を変更した場合は、開発サーバーを再起動してください：

```bash
# 開発サーバーを停止（Ctrl+C）
# その後、再起動
npm run dev
```

## Phase 3: テストと検証

### Step 3.1: APIエンドポイントの確認

ブラウザで以下にアクセス：

```
http://localhost:3000/api/articles?debug=1
```

### Step 3.2: レスポンスの確認

以下の項目を確認してください：

1. **`dmenuDebug.endpointFetch.ok === true`**
   - プロキシ経由で正常に取得できている

2. **`dmenuDebug.parsedCount > 0`**
   - 記事が正しくパースされている

3. **`dmenuDebug.bestEndpoint`**
   - プロキシURLが表示されている（`https://dmenu-proxy...`）

4. **`articles`配列にdmenu記事が含まれている**
   - `source` が `dmenu` の記事が表示されている

### Step 3.3: ログファイルの確認

```bash
Get-Content logs/dmenu_fetch.log -Tail 20
```

以下のログが表示されることを確認：

```
[YYYY-MM-DDTHH:mm:ss.sssZ] FETCH START
{
  "url": "https://dmenu-proxy...",
  "ts": "...",
  "useProxy": true
}
[YYYY-MM-DDTHH:mm:ss.sssZ] FETCH GOT RESPONSE
{
  "url": "https://dmenu-proxy...",
  "status": 200,
  "ts": "...",
  "useProxy": true
}
```

### Step 3.4: ターミナルログの確認

開発サーバーのターミナルで、以下のログが表示されることを確認：

```
FETCH START: { url: '...', ts: '...', useProxy: true }
FETCH GOT RESPONSE: { url: '...', status: 200, ts: '...', useProxy: true }
FETCH GOT RESPONSE: dmenu fetchDmenuNews completed { articleCount: XX, ts: '...' }
```

## Phase 4: トラブルシューティング

### 問題1: プロキシが動作しない

**症状**: `npm run test:proxy` が失敗する

**確認事項**:
1. Cloudflare Workersが正しくデプロイされているか
2. Worker URLが正しいか
3. Cloudflare Workersのログを確認

**解決策**:
- Cloudflare Workersダッシュボードでログを確認
- Worker URLを再確認
- `dmenu-proxy.js` のコードを再確認

### 問題2: 環境変数が読み込まれない

**症状**: `useProxy: false` が表示される

**確認事項**:
1. `.env.local` ファイルがプロジェクトルートにあるか
2. `DMENU_PROXY_URL` が正しく設定されているか
3. 開発サーバーを再起動したか

**解決策**:
```bash
# .env.localの内容を確認
cat .env.local

# 開発サーバーを再起動
npm run dev
```

### 問題3: CORSエラー

**症状**: ブラウザでCORSエラーが表示される

**確認事項**:
1. Cloudflare WorkersのCORSヘッダーが正しく設定されているか
2. ブラウザの開発者ツールでレスポンスヘッダーを確認

**解決策**:
- `cloudflare-workers/dmenu-proxy.js` のCORS設定を確認
- `Access-Control-Allow-Origin: *` が設定されているか確認

### 問題4: 記事が取得できない

**症状**: `parsedCount: 0` または `articleCount: 0`

**確認事項**:
1. プロキシが正常に動作しているか（`npm run test:proxy`）
2. dmenu APIのレスポンス形式が変更されていないか
3. ログファイルでエラーを確認

**解決策**:
- プロキシのテストを実行して、JSONレスポンスを確認
- ログファイルの `FETCH FAILED` を確認

## 次のステップ

### オプション1: キャッシュの最適化

Cloudflare Workersのキャッシュを活用して、パフォーマンスを向上させます：

```javascript
// dmenu-proxy.js の Cache-Control を調整
'Cache-Control': 'public, max-age=600', // 10分に変更
```

### オプション2: エラーハンドリングの強化

プロキシエラー時の詳細なログを追加します。

### オプション3: 複数プロキシのサポート

フォールバック用の複数プロキシURLをサポートします。

## 完了チェックリスト

- [ ] Cloudflare Workersプロキシがデプロイされている
- [ ] `npm run test:proxy` が成功する
- [ ] `.env.local` に `DMENU_PROXY_URL` が設定されている
- [ ] 開発サーバーが再起動されている
- [ ] `/api/articles?debug=1` でdmenu記事が取得できる
- [ ] `dmenuDebug.endpointFetch.ok === true`
- [ ] `dmenuDebug.parsedCount > 0`
- [ ] ログファイルに `useProxy: true` が記録されている







