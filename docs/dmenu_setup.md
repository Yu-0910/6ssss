# dmenuニュース取得のセットアップ

このドキュメントでは、dmenuスポーツ（service.smt.docomo.ne.jp）からニュース記事を取得するためのセットアップ手順を説明します。

## 概要

Yahoo! Topics RSSからの記事取得を削除し、dmenuスポーツのJSON/APIを直接叩いて記事を取得する方式に切り替えました。

## セットアップ手順

### 1. dmenuのXHR/JSON APIを探索（プローブ）

まず、dmenuのニュース一覧ページが使用しているJSON/APIエンドポイントを自動で探索します。

```bash
npm run probe:dmenu
```

このコマンドを実行すると、以下の処理が行われます：

1. dmenuニュース一覧ページ（`https://service.smt.docomo.ne.jp/portal/sports/baseball_j/news.html`）を取得
2. HTMLからscriptタグのsrc属性を抽出
3. 各JSファイルからURL候補を抽出（正規表現で探索）
4. 候補URLをスコア付け（API/JSON/キーワードマッチを優先）
5. 上位30件を実際にGETしてテスト
6. JSONレスポンスを解析してニュース記事らしさをスコア付け
7. **bestEndpoint**を決定

### 2. プローブ結果の確認

プローブ実行後、以下のディレクトリに結果が保存されます：

```
logs/dmenu_probe/
├── urls.txt              # 見つけた候補URL一覧（スコア付き）
├── responses/            # レスポンス概要（各URLのstatus/content-type/preview）
└── json/                 # JSONが取れた場合のファイル
```

#### bestEndpointの確認

プローブスクリプトの最後に、**bestEndpoint**が表示されます：

```
================================================================================
[Result] Best Endpoint: https://service.smt.docomo.ne.jp/api/news/list.json
[Result] URL Score: 35
[Result] JSON Score: 60
[Result] Status: 200
[Result] Content-Type: application/json
[Result] Bytes: 12345
================================================================================
```

この`Best Endpoint`が、dmenuからニュース記事を取得する際に使用するAPIエンドポイントです。

### 3. dmenu取得モジュールの実装

bestEndpointが確定したら、`app/lib/dmenu.ts`に取得モジュールを実装します（実装済み）。

### 4. APIルートの確認

`/api/articles?debug=1`をブラウザで開いて、dmenu経由の記事が取得できているか確認します。

debug=1のレスポンスには、以下の情報が含まれます：

```json
{
  "mode": "debug",
  "articles": [...],
  "feeds": [...],
  "dmenuDebug": {
    "listPageUrl": "https://service.smt.docomo.ne.jp/portal/sports/baseball_j/news.html",
    "bestEndpoint": "https://service.smt.docomo.ne.jp/api/news/list.json",
    "endpointFetch": {
      "ok": true,
      "status": 200,
      "contentType": "application/json",
      "bytes": 12345
    },
    "parsedCount": 10,
    "sampleArticles": [
      {
        "title": "記事タイトル1",
        "url": "https://...",
        "publishedAt": "2026-01-18T12:00:00Z",
        "imageUrl": "https://..."
      },
      ...
    ]
  }
}
```

### 5. トラブルシューティング

#### プローブでbestEndpointが見つからない場合

- `logs/dmenu_probe/urls.txt`を確認し、候補URLが抽出されているか確認
- `logs/dmenu_probe/responses/`を確認し、レスポンスのステータスを確認
- プローブスクリプトを再実行（dmenuのページ構造が変更されている可能性）

#### `/api/articles?debug=1`でエラーが出る場合

- dmenuのAPIエンドポイントが変更されている可能性
- `app/lib/dmenu.ts`の`DMENU_API_ENDPOINT`を最新のbestEndpointに更新
- プローブを再実行してbestEndpointを再確認

#### 記事が取得できていない場合

- `dmenuDebug.endpointFetch.ok`が`false`の場合、APIエンドポイントへのアクセスに失敗
- `dmenuDebug.parsedCount`が`0`の場合、JSONパースに失敗している可能性
- `logs/dmenu_probe/json/`に保存されたJSONファイルを確認

## 注意事項

- **取得頻度は控えめに**：dmenuのAPIに負荷をかけないよう、キャッシュや間隔を必ず入れる
- **エラー処理**：APIが取れないときは`/api/articles`は500にせず空配列で返す
- **Yahoo由来の取得は完全に削除済み**：config/rss_feeds.jsonからYahoo Topics Sportsを無効化

## 関連ファイル

- `scripts/probe_dmenu_xhr.mjs` - dmenuのXHR/JSON APIを自動探索するプローブスクリプト
- `app/lib/dmenu.ts` - dmenuからニュース記事を取得するモジュール
- `app/api/articles/route.ts` - `/api/articles`エンドポイント（dmenuを統合）
- `config/rss_feeds.json` - RSSフィード設定（Yahoo Topics Sportsは無効化済み）








