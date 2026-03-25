# Phase 4: R2 へランキングデータをアップロードする手順（あなたの作業）

Phase 3 まで完了している前提で、**あなただけが行う作業**をまとめます。スクリプトは用意済みです。

---

## 1. Cloudflare で R2 API トークンを発行する（必須）

1. [Cloudflare ダッシュボード](https://dash.cloudflare.com) にログインする。
2. 左メニュー **R2** を開く。
3. **Overview** または **Manage R2 API Tokens** から **Create API token**（API トークンを作成）をクリックする。
4. 権限は **Object Read & Write** でよい。対象は「このアカウントのすべてのバケット」または該当バケットのみでよい。
5. 作成後、**Access Key ID** と **Secret Access Key** を**一度だけ表示**されるので、コピーして安全な場所に保存する（Secret は再表示できない）。
6. あわせて **アカウント ID** を控える（ダッシュボード右列や URL の `dash.cloudflare.com/<アカウントID>` で確認できる）。

---

## 2. 環境変数を設定する

次の 4 つを、**リポジトリにコミットせず**、手元のターミナルまたは `.env.local`（git に含めない）で設定します。

| 変数名 | 例 | 説明 |
|--------|-----|------|
| `CLOUDFLARE_ACCOUNT_ID` | （ダッシュボードのアカウント ID） | 必須 |
| `R2_ACCESS_KEY_ID` | （API トークン作成時に表示された ID） | 必須 |
| `R2_SECRET_ACCESS_KEY` | （API トークン作成時の Secret） | 必須 |
| `R2_BUCKET_NAME` | `rankings-data` | Phase 1 で作ったバケット名 |

**PowerShell で 1 回だけ設定する例（そのターミナルだけで有効）:**

```powershell
$env:CLOUDFLARE_ACCOUNT_ID = "あなたのアカウントID"
$env:R2_ACCESS_KEY_ID = "作成したAccess Key ID"
$env:R2_SECRET_ACCESS_KEY = "作成したSecret Access Key"
$env:R2_BUCKET_NAME = "rankings-data"
```

※ バケット名は Phase 1 で付けた名前（例: `rankings-data`）に合わせてください。

---

## 3. 依存関係を入れる

プロジェクトルートで:

```bash
npm install
```

（`@aws-sdk/client-s3` が devDependency として入ります。）

---

## 4. ドライランで対象を確認する（任意）

アップロードせず、対象ファイル数とパスだけ確認する:

```bash
node scripts/upload-rankings-to-r2.mjs --dry-run
```

`public/data/rankings/` 以下の `.json` が何件あるかと、先頭 20 件の R2 キーが表示されます。

---

## 5. アップロードを実行する

同じターミナルで（環境変数を設定したまま）:

```bash
node scripts/upload-rankings-to-r2.mjs
```

- 完了まで数分〜十数分かかることがあります（約 1.4 万ファイル）。
- 50 件ごとに進捗が表示されます。
- エラーが出た場合は、表示されたメッセージと上記の環境変数・バケット名を確認してください。

---

## 6. アップロード後の確認

- R2 の公開 URL で 1 件だけ確認する例:  
  `https://pub-41ff9f32fcf748529b7036f73f9e04e5.r2.dev/data/rankings/2025/PL/OPS.json`  
  （Phase 1 のベースURL + `/data/rankings/2025/PL/OPS.json`）
- プレビュー環境（Phase 3 で `RANKINGS_BASE_URL` を設定したデプロイ）でランキングページを開き、表示が問題ないか確認する。

---

## まとめ：あなたの作業だけ

| 番号 | 作業 | 備考 |
|------|------|------|
| 1 | Cloudflare で R2 API トークンを作成し、Access Key ID・Secret・アカウント ID を控える | ダッシュボードで実施 |
| 2 | 上記 4 つの環境変数を設定する | リポジトリに含めない |
| 3 | `npm install` を実行する | 初回のみ |
| 4 | `node scripts/upload-rankings-to-r2.mjs --dry-run` で対象確認（任意） | |
| 5 | `node scripts/upload-rankings-to-r2.mjs` でアップロード実行 | |
| 6 | プレビューURLでランキング表示を確認する | |

関連: `docs/cloudflare_r2_vercel_setup_plan.md`（Phase 4）、`docs/rankings_full_externalization_plan.md`
