# dmenuニュース取得統合レポート

## 概要

このレポートでは、dmenuスポーツ（service.smt.docomo.ne.jp）からニュース記事を取得してサイトに表示するまでのフローと、実装中に発生した問題、および試行した解決策とその結果をまとめます。

## 現在の実装フロー

### 1. フロントエンド（ブラウザ）からのリクエスト

**場所**: `app/components/ArticlesListClient.tsx`

- ページ読み込み時に`useEffect`フックが実行される
- `/api/articles`エンドポイントにGETリクエストを送信
- レスポンスを受け取り、Reactの状態（`setArticles`）を更新

### 2. API Route（サーバー側）での処理開始

**場所**: `app/api/articles/route.ts` (GET関数)

- リクエストを受け取り、デバッグモードやキャッシュクリアパラメータをチェック
- メモリキャッシュを確認（有効期限内ならキャッシュを返す）
- キャッシュが無効な場合、dmenuから記事を取得する処理を開始

### 3. dmenu APIへのリクエスト

**場所**: `app/lib/dmenu.ts` (`fetchDmenuNews`関数)

- `fetchDmenuNews(debugMode)`が呼び出される
- エンドポイント: `https://service.smt.docomo.ne.jp/portal/sports/data/news/news_list_0000.json`
- Node.jsの`https`モジュールを使用してHTTPSリクエストを送信

### 4. JSONレスポンスのパースと正規化

**場所**: `app/lib/dmenu.ts`

- JSONレスポンスをパース
- `DmenuNewsItem`を`NormalizedArticle`形式に変換
  - 日付をISO形式（`YYYY-MM-DDTHH:mm:ss.sssZ`）に変換
  - 画像URLとソース名を設定
  - 元記事URL（`news_origin_url`）を優先的に使用

### 5. Article型への変換

**場所**: `app/api/articles/route.ts`

- `NormalizedArticle`を`Article`型に変換
- 日付を`YYYY.MM.DD`形式に変換
- 記事配列に追加

### 6. RSSフィード記事との統合

**場所**: `app/api/articles/route.ts`

- RSSフィードから取得した記事をdmenu記事に追加
- すべての記事を1つの配列に統合

### 7. レスポンスの返却

**場所**: `app/api/articles/route.ts`

- デバッグモード: デバッグ情報を含むJSONを返す
- 通常モード: 記事配列のみを返す（日付でソート、新しい順）
- メモリキャッシュに保存（1時間有効）

### 8. フロントエンドでの表示

**場所**: `app/components/ArticlesListClient.tsx`

- レスポンスを受け取り、記事配列を抽出
- Reactの状態を更新
- コンポーネントが再レンダリングされ、記事リストが表示される

## 発生している問題

### 問題1: SSL/TLSレガシーリネゴシエーションエラー

**エラーメッセージ**:
```
Request failed: write EPROTO 4C080000:error:0A000152:SSL routines:final_renegotiate:unsafe legacy renegotiation disabled:openssl\ssl\statem\extensions.c:949:
```

**発生箇所**: `app/lib/dmenu.ts` の `fetchDmenuNews` 関数内

**原因**:
- dmenuサーバー（service.smt.docomo.ne.jp）が古いSSL/TLSプロトコル（レガシーリネゴシエーション）を使用している
- Node.jsの新しいバージョンでは、セキュリティ上の理由からレガシーリネゴシエーションがデフォルトで無効化されている
- そのため、HTTPS接続の確立時にエラーが発生する

**影響**:
- dmenuからの記事取得が完全に失敗する
- `dmenuDebug.endpointFetch.ok: false`
- `dmenuDebug.endpointFetch.status: 0`
- `dmenuDebug.parsedCount: 0`
- 結果として、dmenuの記事がサイトに表示されない

## 試行した解決策とその結果

### 解決策1: Next.jsの標準`fetch` APIを使用

**実装内容**:
```typescript
const response = await fetch(DMENU_API_ENDPOINT, {
  headers: {
    'User-Agent': 'Mozilla/5.0 ...',
    'Accept': 'application/json, text/html, */*',
    // ...
  },
  next: { revalidate: 0 },
})
```

**結果**: ❌ 失敗

**理由**:
- Next.jsの`fetch` APIは、Node.jsの標準`fetch`実装を使用している
- 標準`fetch`では、SSL/TLSの詳細な設定（`agent`オプションなど）ができない
- レガシーリネゴシエーション問題に対処するためのカスタム設定が不可能

### 解決策2: Node.jsの`https`モジュール + `https.Agent`を使用

**実装内容**:
```typescript
import https from 'https'

const text = await new Promise<string>((resolve, reject) => {
  const url = new URL(DMENU_API_ENDPOINT)
  const options = {
    hostname: url.hostname,
    port: url.port || 443,
    path: url.pathname + url.search,
    method: 'GET',
    headers: { /* ... */ },
    agent: new https.Agent({
      rejectUnauthorized: false, // SSL証明書検証をスキップ
    }),
  }
  
  const req = https.request(options, (res) => {
    // レスポンス処理
  })
  
  req.end()
})
```

**結果**: ❌ 失敗

**理由**:
- `rejectUnauthorized: false`は証明書検証をスキップするが、レガシーリネゴシエーション問題には対処できない
- エラーメッセージは変わらず「unsafe legacy renegotiation disabled」が発生

### 解決策3: `secureProtocol`オプションを追加

**実装内容**:
```typescript
agent: new https.Agent({
  rejectUnauthorized: false,
  secureProtocol: 'TLSv1_2_method', // TLS 1.2を強制
}),
```

**結果**: ❌ 失敗

**理由**:
- `secureProtocol: 'TLSv1_2_method'`は使用するTLSバージョンを指定するが、レガシーリネゴシエーションの有効/無効には影響しない
- Node.jsのOpenSSL実装では、レガシーリネゴシエーションは環境変数レベルで制御される
- `https.Agent`のオプションだけでは解決できない

### 解決策4: 環境変数`NODE_TLS_REJECT_UNAUTHORIZED`を設定

**実装内容**:
```typescript
// dmenuサーバーのSSL/TLSレガシーリネゴシエーション問題に対処
const originalRejectUnauthorized = process.env.NODE_TLS_REJECT_UNAUTHORIZED
process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0'

try {
  // https.request()を実行
} finally {
  // 環境変数を元に戻す
  if (originalRejectUnauthorized !== undefined) {
    process.env.NODE_TLS_REJECT_UNAUTHORIZED = originalRejectUnauthorized
  } else {
    delete process.env.NODE_TLS_REJECT_UNAUTHORIZED
  }
}
```

**結果**: ❌ 失敗（現在の状態）

**理由**:
- `NODE_TLS_REJECT_UNAUTHORIZED = '0'`は証明書検証を無効化するが、レガシーリネゴシエーションの有効化にはならない
- レガシーリネゴシエーションを有効にするには、Node.jsの起動時に`--tls-legacy-renegotiation`フラグが必要
- しかし、このフラグはNext.jsの開発サーバーや本番環境で設定するのが困難

### 解決策5（参考）: probeスクリプトでの成功例

**実装内容**: `scripts/probe_dmenu_xhr.mjs`

probeスクリプトでは、同じエンドポイントへのリクエストが成功している可能性がある。しかし、probeスクリプトは独立したNode.jsスクリプトとして実行されるため、Next.jsの実行環境とは異なる。

**違い**:
- probeスクリプト: 直接`node`コマンドで実行される
- Next.js API Route: Next.jsのランタイム環境内で実行される

## 現在の状態

### エラー状況

- **エラー発生**: ✅ 確認済み
- **エラータイプ**: SSL/TLSレガシーリネゴシエーション無効化エラー
- **影響範囲**: dmenuからの記事取得が完全に失敗
- **フォールバック**: RSSフィードからの記事取得は正常に動作

### デバッグ情報

`/api/articles?debug=1`のレスポンス例:
```json
{
  "dmenuDebug": {
    "listPageUrl": "https://service.smt.docomo.ne.jp/portal/sports/baseball_j/news.html",
    "bestEndpoint": "https://service.smt.docomo.ne.jp/portal/sports/data/news/news_list_0000.json",
    "endpointFetch": {
      "ok": false,
      "status": 0,
      "contentType": null,
      "bytes": 0,
      "error": "Request failed: write EPROTO 4C080000:error:0A000152:SSL routines:final_renegotiate:unsafe legacy renegotiation disabled:openssl\\ssl\\statem\\extensions.c:949:\n"
    },
    "parsedCount": 0,
    "sampleArticles": []
  }
}
```

## 今後の対応方針

### オプション1: Node.js起動フラグの設定

**方法**:
- Next.jsの起動時に`--tls-legacy-renegotiation`フラグを追加
- `package.json`の`dev`スクリプトを修正:
  ```json
  "scripts": {
    "dev": "node --tls-legacy-renegotiation node_modules/.bin/next dev"
  }
  ```

**課題**:
- 本番環境（Vercel等）での設定が困難な可能性
- セキュリティ上の懸念（レガシーリネゴシエーションは脆弱性がある）

### オプション2: プロキシサーバーの使用

**方法**:
- 中間プロキシサーバーを経由してdmenu APIにアクセス
- プロキシサーバー側でSSL/TLS問題を解決

**課題**:
- 追加のインフラが必要
- レイテンシの増加

### オプション3: 代替データソースの検討

**方法**:
- dmenu以外のデータソースを検討
- または、dmenuのHTMLページをスクレイピング（APIではなく）

**課題**:
- データソースの変更が必要
- HTMLスクレイピングは脆弱（HTML構造変更に弱い）

### オプション4: 外部サービス/ライブラリの使用

**方法**:
- `node-fetch`や`axios`などのHTTPクライアントライブラリを使用
- より柔軟なSSL/TLS設定が可能な可能性

**課題**:
- 追加の依存関係
- 同様の問題が発生する可能性

## 結論

現在、dmenuからの記事取得はSSL/TLSレガシーリネゴシエーション問題により完全に失敗しています。これまで試した解決策（標準`fetch`、`https.Agent`、環境変数設定）はいずれも効果がありませんでした。

根本的な解決には、Node.jsの起動フラグ（`--tls-legacy-renegotiation`）の設定が必要ですが、Next.jsの実行環境では設定が困難です。代替案として、プロキシサーバーの使用や、データソースの変更を検討する必要があります。

## 関連ファイル

- `app/lib/dmenu.ts`: dmenu記事取得モジュール
- `app/api/articles/route.ts`: API Route（記事取得エンドポイント）
- `app/components/ArticlesListClient.tsx`: フロントエンドコンポーネント
- `scripts/probe_dmenu_xhr.mjs`: dmenu APIエンドポイント探索スクリプト

## 更新履歴

- 2026-01-19: 初版作成
  - フローの説明
  - 問題点の特定
  - 試行した解決策の記録







