# Cloudflare R2 ＋ Vercel ランキングデータ公開 設定計画書

ランキングJSONを Cloudflare R2 に配置し、Vercel 上のアプリから `RANKINGS_BASE_URL` 経由で参照するための設定手順を、**Phase（段階）** に分けてまとめる。  
関連: `docs/ranking_data_externalization_plan.md`、`docs/external_storage_setup_guide.md`

**前提（公開状況・デプロイ方針）**: **サイトは既に Vercel からデプロイ済み**である。**Vercel にはランキングデータを載せない**。`public/data/rankings/` は .vercelignore で除外されており、Vercel へデプロイするのは**アプリ本体（コード）のみ**（一括でデータを含めた公開は重く不可能なため、R2 へ移行する）。Phase 1〜2 は既存プロジェクトのまま実施可能。Phase 3 は既存の Vercel プロジェクトに環境変数を追加し、Redeploy する。Phase 4 の表示確認はプレビューURL（テスト時）または本番URL（本番切替後）で行う。

---

## 目的

- **Cloudflare R2**: ランキング用JSON（`data/rankings/{年}/{リーグ}/*.json`）をホストするストレージとして利用する。
- **Vercel**: 環境変数 `RANKINGS_BASE_URL` に R2 の公開URLを設定し、アプリのプロキシ（`/data/rankings/[...path]`）がそのURLへ転送する。

### 方針: まずテスト

- **本計画では本番（Production）は変更しない。テストのみ行う。**
- Phase 3 で `RANKINGS_BASE_URL` は **Preview** と **Development** にのみ設定する（**Production には設定しない**）。
- 本番サイトは従来どおり（R2 を参照しない）。プレビューURL（Vercel の Preview デプロイ）やローカルで R2 からの取得を確認する。
- テストで問題がなければ、別途 Production にも同じ環境変数を設定して Redeploy し、本番切り替えを行う。

---

## Phase 一覧

| Phase | 内容 | ゴール | 状況 |
|-------|------|--------|------|
| **Phase 1** | Cloudflare R2 の準備 | バケット作成・公開アクセス有効化まで完了 | ✅ 実施済み |
| **Phase 2** | テストファイルのアップロードと公開URL確認 | test.json で R2 の公開URLが動作することを確認し、ベースURLをメモ | 未実施 |
| **Phase 3** | Vercel に RANKINGS_BASE_URL を設定（テスト用: Preview / Development のみ） | 環境変数設定・Redeploy まで完了 | 未実施 |
| **Phase 4** | ランキングデータのアップロード | R2 に `data/rankings/...` を配置し、プレビューで表示確認 | 未実施 |

### 現状（R2 ベースURL）

- **Phase 1 は実施済み**（アカウント・バケット作成・公開アクセス有効化済み）。
- **R2 の公開ベースURL（RANKINGS_BASE_URL の値）**:
  ```
  https://pub-41ff9f32fcf748529b7036f73f9e04e5.r2.dev
  ```
- Phase 3 では**テストのため**、上記を Vercel の `RANKINGS_BASE_URL` に **Preview と Development のみ**で設定する（本番 Production には設定しない）。末尾に `/` は付けない。

---

## Phase 1: Cloudflare R2 の準備

**内容**

- Cloudflare アカウントの作成・ログイン
- R2 バケットの作成（例: バケット名 `rankings-data`）
- R2 の公開アクセス（Public Access）の有効化（カスタムドメイン or R2.dev サブドメイン）
- バケットの設定で「公開URL」が有効になっていることの確認

**実施手順**

1. [Cloudflare R2](https://developers.cloudflare.com/r2/) にアクセス
2. アカウント作成（既存の場合はログイン）
3. R2 → Create bucket → バケット名を入力して作成
4. バケットの設定で「Public access」または「公開URL」を有効化
5. 公開用のドメイン（R2.dev サブドメイン等）が発行されることを確認

**想定ネガティブポイントと解決策**

| ネガティブポイント | 解決策 |
|--------------------|--------|
| 公開アクセスの項目が見つからない | バケット詳細 → Settings または「ドメイン」タブで「R2.dev サブドメインを有効化」等を探す。Cloudflare の UI 変更時は公式ドキュメントを参照。 |
| リージョンの選択 | デフォルトのままでよい。レイテンシを気にする場合は利用者に近いリージョンを選択。 |

**Phase 1 実施メモ（実施済み）**

- アカウント・バケット作成・公開アクセス有効化は完了済み。
- 公開ベースURL: `https://pub-41ff9f32fcf748529b7036f73f9e04e5.r2.dev`

**参照**: Cloudflare ダッシュボードの R2 ドキュメント、`docs/external_storage_setup_guide.md` の「1. 外部ストレージサービスの選択とセットアップ」

---

## Phase 2: テストファイルのアップロードと公開URL確認

**内容**

小さいファイル（test.json）で R2 の公開URLが正しく動作するか確認し、**RANKINGS_BASE_URL の候補**となるベースURLを特定する。

### 2-1. テスト用 JSON の作成

プロジェクト直下などに **test.json** を作成する。

**内容:**

```json
{ "status": "ok" }
```

※ プロジェクト直下に `test.json` が既にある場合はそのまま利用してよい。

**Phase 2 実施メモ（2-1）**: プロジェクト直下に `test.json`（`{ "status": "ok" }`）を用意済み。

### 2-2. R2 バケットへアップロード

- Cloudflare ダッシュボード → **R2** → Phase 1 で作成したバケットを開く
- **Upload** をクリック
- **test.json** を選択してアップロード
- バケット直下に `test.json` が1つある状態にする

**アップロードするファイル**: プロジェクトルートの `test.json`（パス: `c:\Users\short\OneDrive\ドキュメント\デスクトップ\TopPage\test.json` など）。エクスプローラーで開き、このファイルをドラッグ＆ドロップする。

### 2-3. 公開URLの取得と動作確認

- バケット内で **test.json** をクリック
- **Public URL**（公開URL）を確認する  
  **例:** `https://xxxxx.r2.dev/test.json`
- その URL をブラウザで開く
- 画面に **`{ "status": "ok" }`** が表示されれば成功

**本プロジェクトの test.json の公開URL（Phase 1 のベースURL利用）**:  
`https://pub-41ff9f32fcf748529b7036f73f9e04e5.r2.dev/test.json`  
→ 2-2 でアップロード後、上記URLをブラウザで開いて確認する。

### 2-4. ベースURLのメモ

**ベースURL（末尾スラッシュなし）** を記録する。Phase 3 で `RANKINGS_BASE_URL` に設定する。

**例:**

```
https://xxxxx.r2.dev
```

※ アプリ側はこのうしろに `/data/rankings/...` を付けて参照する（`lib/ranking/url.ts` の `getExternalRankingsUrl`）。

**想定ネガティブポイントと解決策**

| ネガティブポイント | 解決策 |
|--------------------|--------|
| Public URL が表示されない | Phase 1 で公開アクセスが有効か再確認。R2.dev サブドメインの有効化が必要な場合あり。 |
| ブラウザで 403 / 404 になる | バケットポリシー・CORS を確認。テスト段階では「パブリック読み取り」が許可されているか確認する。 |

---

## Phase 3: Vercel に RANKINGS_BASE_URL を設定（テスト用）

**内容**

Vercel の環境変数に R2 のベースURL を設定し、**プレビュー・ローカルでのみ** R2 を参照するようにする。本番は変更しない。

**※ サイトは既に Vercel でデプロイ済み**のため、既存プロジェクトに環境変数を追加し、Redeploy するだけでよい。

### 3-1. 環境変数の追加

1. **Vercel** にログイン
2. 対象 **Project** を開く（既にデプロイ済みのプロジェクト）
3. **Settings** → **Environment Variables**
4. 以下を追加する

| Key | Value |
|-----|--------|
| `RANKINGS_BASE_URL` | `https://pub-41ff9f32fcf748529b7036f73f9e04e5.r2.dev` |

**注意（テストのため）**

- **末尾に `/` は付けない**
- **適用先: Preview と Development のみにチェックを入れる。Production にはチェックを入れない。**  
  → 本番サイトは従来どおりのまま。プレビューURL・ローカルでのみ R2 を参照する。

### 3-2. 保存とデプロイ

- **Save** で保存
- **Deployments** から最新のデプロイの「⋯」→ **Redeploy** を実行する（または新規 push でデプロイを生成）。

**確認**

- 本番に切り替えていない限り、**本番URL** では R2 は使われない。
- **プレビューURL**でランキングページを開き、R2 からの取得を確認する。
- この時点では R2 にランキング用JSONがまだない場合、データなしまたはフォールバックになる。Phase 4 でデータをアップロード後に表示確認する。

**想定ネガティブポイントと解決策**

| ネガティブポイント | 解決策 |
|--------------------|--------|
| 環境変数を保存したが反映されない | 環境変数変更後は **Redeploy** が必須。プレビューで確認する場合はプレビューデプロイが再生成されているか確認する。 |
| 誤って Production に設定してしまった | Vercel の Environment Variables で該当変数を編集し、Production のチェックを外して保存。本番を Redeploy すれば従来どおりに戻る。 |
| 末尾に `/` を付けてしまった | `lib/ranking/url.ts` では `replace(/\/+$/, '')` で末尾スラッシュは削られるが、設定時は付けない方が無難。 |

**本番切り替え（テスト後）**

- テストで問題がなければ、同じ `RANKINGS_BASE_URL` を **Production** にも設定し、本番を Redeploy する。その時点で本番サイトが R2 を参照する。

---

## Phase 4: ランキングデータのアップロード

**内容**

`public/data/rankings/` 以下と同一のパス構造で、ランキング用JSONを R2 にアップロードする。アプリは `RANKINGS_BASE_URL` + `/data/rankings/{年}/{リーグ}/{指標}.json` で取得する。

### 4-1. パス構造の維持

R2 上では次の構造を維持する。

```
data/rankings/
  2025/
    PL/
      OPS.json
      打率.json
      ...
    CL/
      OPS.json
      ...
  （必要に応じて他年度・他リーグ）
```

※ バケット直下に `data/rankings/` フォルダを作成し、その中に `2025/PL/`、`2025/CL/` などを配置する。

### 4-2. アップロード方法

- **一括スクリプト（推奨）**: `scripts/upload-rankings-to-r2.mjs` を利用する。**あなたの作業手順**は `docs/phase4_upload_steps.md` にまとめてある（R2 API トークン発行 → 環境変数設定 → `npm install` → スクリプト実行）。
- **ダッシュボード**: R2 バケット内で `data/rankings/2025/PL/` 等のフォルダを作成し、JSON をドラッグ＆ドロップ（件数が多いため非推奨）
- **Wrangler CLI**: `wrangler r2 object put` でファイル単位でアップロード

**対象例（Phase 3 段階的移行の場合）**

- まずは `public/data/rankings/2025/PL/` のみアップロードして動作確認
- 問題なければ `2025/CL/` や他年度を追加

### 4-3. 表示確認（テスト）

- **プレビューURL**（Phase 3 で環境変数を設定したデプロイ）のランキングページ（例: `/ranking/2025/PL`）にアクセスする。
- 指標を切り替えて、JSON が R2 から取得され表示されることを確認する。
- 本番に RANKINGS_BASE_URL を設定していない限り、本番URLでは R2 は参照されない（従来どおりまたはフォールバック）。

**想定ネガティブポイントと解決策**

| ネガティブポイント | 解決策 |
|--------------------|--------|
| ファイル名に日本語が含まれる（打率.json 等） | R2 は UTF-8 のキーをサポート。URL エンコードされるため、アプリ側の `sanitizeMetricForPath` とパスが一致しているか確認する。 |
| 404 が返る | R2 上のパスが `data/rankings/2025/PL/OPS.json` のようになっているか、`getExternalRankingsUrl` が生成する URL と突き合わせる。 |
| キャッシュで古いデータが返る | ブラウザのハードリロード、または R2 / CDN のキャッシュ設定を確認する。 |

**参照**: `docs/external_storage_setup_guide.md` の「2. データのアップロード」

---

## 実行順序（サマリ）

1. **Phase 1**: Cloudflare R2 の準備（バケット・公開アクセス） ✅ 済
2. **Phase 2**: test.json のアップロードと公開URL確認 → ベースURLをメモ
3. **Phase 3**: 既存の Vercel プロジェクトに `RANKINGS_BASE_URL` を **Preview と Development のみ**で設定 → Redeploy
4. **Phase 4**: ランキング用JSONを R2 の `data/rankings/...` にアップロード → プレビューURLで表示確認

---

## チェックリスト

| Phase | 作業 | 確認 |
|-------|------|------|
| 1 | Cloudflare アカウント・R2 バケット作成・公開アクセス有効化 | ✅ 済 |
| 2 | test.json を作成し、R2 にアップロード | ☐ |
| 2 | test.json の Public URL をブラウザで開き、`{ "status": "ok" }` が表示される | ☐ |
| 2 | ベースURLをメモ（本プロジェクト: `https://pub-41ff9f32fcf748529b7036f73f9e04e5.r2.dev`） | ✅ 確定済み |
| 3 | Vercel の Environment Variables に `RANKINGS_BASE_URL` を上記URLで設定（**Preview と Development のみ**、Production はチェックしない） | ☐ |
| 3 | 保存後、プレビューデプロイを生成（Redeploy または push） | ☐ |
| 4 | ランキング用JSONを R2 の `data/rankings/...` にアップロード | ☐ |
| 4 | **プレビューURL**でランキングページのデータ表示を確認（本番は従来どおり） | ☐ |

---

## 参照

- ランキング外部化の全体計画: `docs/ranking_data_externalization_plan.md`
- 外部ストレージ準備・アップロード手順: `docs/external_storage_setup_guide.md`
- アプリ側のURL生成: `lib/ranking/url.ts`（`getExternalRankingsUrl` が `RANKINGS_BASE_URL` を使用）
- プロキシルート: `app/data/rankings/[...path]/route.ts`
