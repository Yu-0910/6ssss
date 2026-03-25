# ランキングデータ外部化計画書

## 目的（ミニ改善）

VercelのFunctionサイズ超過の原因となっている巨大データ（`public/data/rankings` と `output/*`）をアプリ本体（Next.js）から分離し、ランキング表示を「外部URLから取得」に切り替える。ユーザー体験（URL/見た目）は変更しない。

**追加要件:**
- 外部化後もユーザー体験を変えず、CORSやキャッシュ事故を防ぐため、以下を実装する：
  - **同一オリジンに見せる**: ブラウザは常に自サイトのURLにアクセス（プロキシ経由）
  - **URL生成を一元化**: すべての参照先を1箇所（ヘルパー関数）に集約
  - **キャッシュ制御**: 適切なCache-Controlヘッダーで古いデータ表示を防止
  - **段階移行**: 最初は2025/PLだけ外部化して検証

## 実施内容

### 0. デプロイに載せない設定を追加

**作業内容:**
- ルートに `.vercelignore` を作成し、以下を除外：
  - `output/backups/`
  - `output/html_cache/`
  - `output/reports/`
  - `output/master/`
  - `public/data/rankings/`
- ルートの `.gitignore` に同じ除外を追記
- すでにGitに入っている巨大データはトラッキング解除：
  ```bash
  git rm -r --cached public/data/rankings output/backups output/html_cache output/reports output/master
  ```
  （ローカルファイルは削除せず、Gitの追跡のみ解除）

**目的:** Vercelデプロイ時に巨大データを除外し、Functionサイズを削減

### 1. 同一オリジンに見せる（推奨）

**作業内容:**
- `/data/rankings/*` を外部ストレージへプロキシするルートを作成
  - ブラウザは常に自サイト `https://<your-site>/data/rankings/...` にアクセスする
- 実装: Next.js の route handler (`app/data/rankings/[...path]/route.ts`) で GET を受け、
  `${process.env.RANKINGS_BASE_URL}${pathname_after_/data/rankings}` を fetch して
  そのまま body を返す（streamでOK）
- 返すレスポンスに Cache-Control を付ける（後述の3で詳細）

**実装例:**
```typescript
// app/data/rankings/[...path]/route.ts
export async function GET(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const resolvedParams = await params
  const pathSegments = resolvedParams.path || []
  const relativePath = pathSegments.join('/')
  
  const baseUrl = process.env.RANKINGS_BASE_URL
  if (!baseUrl) {
    // フォールバック: ローカルファイル参照
    // または 404
    return new Response('RANKINGS_BASE_URL not configured', { status: 500 })
  }
  
  const externalUrl = `${baseUrl}/data/rankings/${relativePath}`
  const response = await fetch(externalUrl)
  
  if (!response.ok) {
    return new Response('Failed to fetch ranking data', { status: response.status })
  }
  
  // Cache-Control ヘッダーを設定（後述の3で詳細）
  const headers = new Headers(response.headers)
  headers.set('Cache-Control', 'public, max-age=300, s-maxage=300, stale-while-revalidate=600')
  
  return new Response(response.body, {
    status: response.status,
    headers,
  })
}
```

**目的:** 
- CORS設定をほぼ不要にする（ブラウザが外部URLに直接アクセスしない）
- ユーザー体験を変えずに外部化を実現

### 2. URL生成を1箇所にまとめる

**作業内容:**
- `getRankingsUrl(path: string)` のようなヘルパー関数を1つ作成
- ルール: path は必ず `/` 始まりに正規化し、二重スラッシュを防ぐ
- APIルート / ランキングページ側での参照はすべてこの関数を経由させる
  （直書きの `${RANKINGS_BASE_URL}/...` を消す）

**実装例:**
```typescript
// lib/ranking/url.ts
export function getRankingsUrl(path: string): string {
  // パスを正規化: 必ず / で始まり、二重スラッシュを防ぐ
  const normalizedPath = '/' + path.replace(/^\/+/, '').replace(/\/+/g, '/')
  
  // プロキシ経由でアクセス（同一オリジン）
  return normalizedPath
}
```

**使用例:**
```typescript
// 従来: const url = `${process.env.RANKINGS_BASE_URL}/data/rankings/2025/PL/OPS.json`
// 変更後:
import { getRankingsUrl } from '@/lib/ranking/url'
const url = getRankingsUrl('data/rankings/2025/PL/OPS.json')
```

**目的:** 
- 将来の置換を容易にする（すべての参照先を1箇所に集約）
- パス生成ロジックの一貫性を保つ

### 3. キャッシュ事故防止（古いランキングが残る問題の対策）

**作業内容:**
- 上のプロキシ（`/data/rankings/*`）のレスポンスヘッダーに以下を設定：
  ```
  Cache-Control: public, max-age=300, s-maxage=300, stale-while-revalidate=600
  ```
  （5分キャッシュ＋裏で再検証）
- もし毎日更新なら `max-age` をもう少し長くしてもOKだが、まずは短めで安全に

**設定値の意味:**
- `max-age=300`: ブラウザが5分間キャッシュを保持
- `s-maxage=300`: CDN（Vercel Edge）が5分間キャッシュを保持
- `stale-while-revalidate=600`: キャッシュが古くなっても10分間は古いデータを返しつつ、裏で再検証

**目的:** 
- データ更新後も古いランキングが表示される問題を防止
- 適切なキャッシュでパフォーマンスも維持

### 4. 段階移行（最初は2025/PLだけ）

**作業内容:**
- 外部化の対象を最初は `2025/pl` だけにして検証できるようにする
- 環境変数 `RANKINGS_EXTERNALIZE_SCOPE` を用意し、scope外は従来のローカル参照 or 404 にする
- 動作確認が取れたら scope を広げていく

**実装例:**
```typescript
// lib/ranking/url.ts
export function getRankingsUrl(path: string): string {
  const normalizedPath = '/' + path.replace(/^\/+/, '').replace(/\/+/g, '/')
  
  // 段階移行: scope をチェック
  const scope = process.env.RANKINGS_EXTERNALIZE_SCOPE || ''
  if (scope) {
    // scope が設定されている場合、対象外のパスはローカル参照にフォールバック
    const scopes = scope.split(',').map(s => s.trim().toLowerCase())
    const pathLower = normalizedPath.toLowerCase()
    
    const isInScope = scopes.some(s => pathLower.includes(s))
    if (!isInScope) {
      // scope外: ローカルファイル参照（開発環境）または404
      if (process.env.NODE_ENV === 'development') {
        return normalizedPath // ローカルファイル参照
      }
      // 本番環境では404またはエラー
      throw new Error(`Path ${normalizedPath} is not in externalization scope`)
    }
  }
  
  return normalizedPath
}
```

**環境変数の設定例:**
- `RANKINGS_EXTERNALIZE_SCOPE=2025_pl` （最初は2025/PLだけ）
- `RANKINGS_EXTERNALIZE_SCOPE=2025_pl,2025_cl` （拡張時）

**目的:** 
- リスクを最小化して段階的に移行
- 問題が発生した場合の影響範囲を限定

### 5. 仕上げ

**作業内容:**
- 変更をコミットして push
- Vercel の環境変数に以下を設定：
  - `RANKINGS_BASE_URL`: 外部ストレージのベースURL（例: `https://your-storage.example.com`）
  - `RANKINGS_EXTERNALIZE_SCOPE`: 外部化対象のスコープ（例: `2025_pl`）
- ランキング画面が同じURLのまま動くことを確認

**注意:**
- ブラウザが外部URLに直接アクセスしない構成にすることで CORS 設定をほぼ不要にする
- すべての参照先を1箇所（ヘルパー or `/data/rankings` プロキシ）に寄せて、将来の置換を容易にする

## 実行フェーズ

### Phase 1: 準備（デプロイ除外設定）

**目的:** 巨大データをデプロイから除外し、Functionサイズを削減

**作業内容:**
- `.vercelignore` の作成（`output/*`, `public/data/rankings/` を除外）
- `.gitignore` の更新（同じ除外を追加）
- Gitトラッキング解除（`git rm -r --cached`）

**完了条件:**
- [ ] `.vercelignore` が作成されている
- [ ] `.gitignore` が更新されている
- [ ] Gitトラッキングが解除されている（`git status` で確認）
- [ ] 変更をコミット

**所要時間:** 約30分

---

### Phase 2: 基盤実装（プロキシ・URL生成・キャッシュ）

**目的:** 外部化の基盤となる機能を実装（まだ外部化は行わない）

**作業内容:**
- プロキシルート（`app/data/rankings/[...path]/route.ts`）の実装
- URL生成ヘルパー関数（`lib/ranking/url.ts`）の実装
- キャッシュ制御（Cache-Controlヘッダー）の実装
- 段階移行機能（`RANKINGS_EXTERNALIZE_SCOPE`）の実装

**完了条件:**
- [ ] プロキシルートが実装されている
- [ ] URL生成ヘルパー関数が実装されている
- [ ] キャッシュヘッダーが設定されている
- [ ] 段階移行機能が実装されている
- [ ] 開発環境で動作確認（ローカルファイル参照で動作することを確認）
- [ ] 変更をコミット

**注意:**
- この時点では `RANKINGS_BASE_URL` は未設定のまま
- プロキシルートはエラーを返すが、既存の機能には影響しない
- 段階移行機能により、scope外のパスは従来通り動作する

**所要時間:** 約2-3時間

---

### Phase 3: 段階的移行（2025/PLのみ外部化）

**目的:** 最小限の範囲（2025/PL）で外部化を検証

**前提条件:**
- Phase 1, 2が完了していること
- 外部ストレージに `2025/PL` のデータがアップロード済みであること

**作業内容:**
- Vercelの環境変数を設定：
  - `RANKINGS_BASE_URL`: 外部ストレージのベースURL
  - `RANKINGS_EXTERNALIZE_SCOPE=2025_pl`
- プロキシルートが正常に動作することを確認
- 2025/PLのランキングページが正常に表示されることを確認
- 他の年度・リーグ（scope外）が従来通り動作することを確認

**完了条件:**
- [ ] Vercelの環境変数が設定されている
- [ ] 2025/PLのランキングデータが外部URLから取得できている
- [ ] 2025/PLのランキングページが正常に表示される
- [ ] 他の年度・リーグが従来通り動作する（ローカルファイル参照）
- [ ] エラーハンドリングが適切に動作する
- [ ] キャッシュが適切に機能している
- [ ] 本番環境で動作確認完了

**検証期間:** 1-2週間（問題が発生しないことを確認）

**所要時間:** 約1時間（設定と検証）

---

### Phase 4: 拡張（他の年度・リーグへの拡張）

**目的:** 検証が完了したら、他の年度・リーグも外部化

**前提条件:**
- Phase 3が完了し、1-2週間問題なく動作していること
- 外部ストレージに他の年度・リーグのデータがアップロード済みであること

**作業内容:**
- 外部ストレージに他の年度・リーグのデータをアップロード
- `RANKINGS_EXTERNALIZE_SCOPE` を拡張（例: `2025_pl,2025_cl`）
- 各年度・リーグのランキングページが正常に表示されることを確認

**拡張の順序（推奨）:**
1. 2025/CL（2025/PLと同じ年度）
2. 2024/PL, 2024/CL（前年度）
3. その他の年度・リーグ

**完了条件:**
- [ ] 外部ストレージにデータがアップロードされている
- [ ] `RANKINGS_EXTERNALIZE_SCOPE` が更新されている
- [ ] 対象の年度・リーグのランキングページが正常に表示される
- [ ] 本番環境で動作確認完了

**所要時間:** 各拡張につき約30分（データアップロード時間を除く）

---

### Phase 5: 完全移行（全データ外部化）

**目的:** すべてのランキングデータを外部化

**前提条件:**
- Phase 4が完了し、すべての主要な年度・リーグで問題なく動作していること

**作業内容:**
- 外部ストレージに残りのデータをアップロード
- `RANKINGS_EXTERNALIZE_SCOPE` を削除または全対象に設定
- すべてのランキングページが正常に表示されることを確認
- ローカルファイル（`public/data/rankings/`）の削除を検討（オプション）

**完了条件:**
- [ ] すべてのデータが外部ストレージにアップロードされている
- [ ] すべてのランキングページが正常に表示される
- [ ] 本番環境で動作確認完了
- [ ] ドキュメントを更新（データ更新のワークフローなど）

**所要時間:** 約1時間（データアップロード時間を除く）

---

## フェーズ間の確認事項

各フェーズ完了後、以下を確認してから次フェーズに進む：

- [ ] 既存機能が正常に動作している（回帰テスト）
- [ ] エラーハンドリングが適切に動作している
- [ ] パフォーマンスに問題がない
- [ ] ログにエラーが出ていない
- [ ] ユーザーからの報告がない（本番環境の場合）

## 想定されるネガティブポイントとその予防策

### 1. 外部URLの可用性・パフォーマンス問題

**リスク:**
- 外部ストレージがダウンした場合、ランキングが表示できない
- 外部URLへのアクセスが遅い場合、ユーザー体験が悪化

**予防策:**
- 外部ストレージは信頼性の高いサービス（例: Cloudflare R2, AWS S3, Vercel Blob）を使用
- エラーハンドリングを実装し、外部URL取得失敗時は適切なエラーメッセージを表示
- タイムアウト設定を追加（例: 5秒）
- プロキシ経由でアクセスするため、CORSエラーは発生しない（同一オリジン）
- 必要に応じてリトライロジックを実装

### 2. 環境変数の設定漏れ

**リスク:**
- 本番環境で `RANKINGS_BASE_URL` が未設定の場合、ランキングが表示できない
- ステージング環境で設定を忘れる可能性

**予防策:**
- 環境変数の存在チェックを実装し、未設定時は明確なエラーメッセージを表示
- 開発環境ではローカルファイル参照にフォールバック
- デプロイ前に環境変数の設定を確認するチェックリストを作成
- READMEに環境変数の設定方法を明記

### 3. パス構造の不一致

**リスク:**
- 外部ストレージのパス構造が現在の `public/data/rankings` と異なる場合、データ取得に失敗
- ファイル名の大文字小文字の違いによる問題

**予防策:**
- 外部ストレージにアップロードする際、現在のパス構造を完全に維持
- **URL生成を一元化**（`getRankingsUrl` 関数）により、パス生成ロジックを一箇所で管理
- 開発環境で外部URLのパス構造を検証するテストを追加

### 4. データの更新タイミング

**リスク:**
- ローカルでデータを更新した後、外部ストレージへのアップロードを忘れる
- 外部ストレージとローカルのデータが不一致になる

**予防策:**
- データ更新のワークフローを文書化
- 自動アップロードスクリプトを作成（オプション）
- データ更新時に外部ストレージへのアップロードをチェックリストに追加

### 5. 開発環境での動作確認の困難さ

**リスク:**
- 開発環境で外部URLをテストするのが難しい
- ローカル開発時に外部ストレージへのアクセスが必要になる

**予防策:**
- 開発環境では `RANKINGS_BASE_URL` が未設定の場合、ローカルファイル参照にフォールバック
- 開発環境でも外部URLをテストできるオプションを提供（環境変数で切り替え可能）
- モックサーバーやスタブデータを用意（オプション）

### 6. Git履歴の肥大化（既存データ）

**リスク:**
- 既存のGit履歴に巨大データが含まれているため、リポジトリサイズが大きいまま
- クローンやフェッチが遅い

**予防策:**
- 既存のGit履歴から巨大データを完全に削除する場合は、`git filter-branch` や `git filter-repo` を検討（注意: 履歴を書き換えるため、チーム全体での調整が必要）
- 現時点では `git rm --cached` で今後追跡しないようにするのみ（既存履歴は残る）
- 必要に応じて、新しいリポジトリを作成して履歴をクリーンアップすることを検討

### 7. キャッシュの問題

**リスク:**
- 外部URLから取得したデータが適切にキャッシュされない
- データ更新後も古いデータが表示される

**予防策:**
- **プロキシレスポンスにCache-Controlヘッダーを設定**（`max-age=300, s-maxage=300, stale-while-revalidate=600`）
- 短めのキャッシュ時間（5分）で安全に開始し、必要に応じて調整
- `stale-while-revalidate` により、古いデータを返しつつ裏で再検証
- データ更新時にキャッシュをクリアする仕組みを検討（将来的）

### 8. セキュリティリスク

**リスク:**
- 外部URLが公開されている場合、不正アクセスの可能性
- 環境変数が漏洩する可能性

**予防策:**
- 外部ストレージのアクセス制御を適切に設定（必要に応じて署名付きURLを使用）
- 環境変数はVercelの環境変数管理機能を使用し、Gitにコミットしない
- `.env` ファイルを `.gitignore` に追加（既に追加済みか確認）

## 実装の優先順位

1. **高優先度（必須）:**
   - `.vercelignore` の作成
   - `.gitignore` の更新
   - Gitトラッキング解除
   - プロキシルート（`/data/rankings/[...path]`）の実装
   - URL生成ヘルパー関数（`getRankingsUrl`）の実装
   - キャッシュ制御（Cache-Controlヘッダー）の実装
   - 段階移行機能（`RANKINGS_EXTERNALIZE_SCOPE`）の実装

2. **中優先度（推奨）:**
   - エラーハンドリングの実装
   - タイムアウト設定
   - 開発環境での動作確認
   - フォールバック機能（ローカルファイル参照）

3. **低優先度（将来検討）:**
   - リトライロジック
   - 自動アップロードスクリプト
   - Git履歴の完全クリーンアップ
   - キャッシュクリア機能

## 検証項目

実装完了後、以下を確認:

- [ ] `.vercelignore` が正しく設定されているか
- [ ] `.gitignore` が正しく設定されているか
- [ ] Gitトラッキングが解除されているか（`git status` で確認）
- [ ] プロキシルート（`/data/rankings/[...path]`）が正常に動作するか
- [ ] ブラウザが同一オリジン（自サイトのURL）にアクセスしているか（CORSエラーが発生しないか）
- [ ] URL生成ヘルパー関数（`getRankingsUrl`）がすべての参照箇所で使用されているか
- [ ] キャッシュヘッダー（Cache-Control）が正しく設定されているか
- [ ] 段階移行機能（`RANKINGS_EXTERNALIZE_SCOPE`）が正常に動作するか
- [ ] scope外のパスが適切に処理されるか（ローカル参照 or 404）
- [ ] 開発環境でローカルファイル参照が動作するか（`RANKINGS_BASE_URL` 未設定時）
- [ ] 環境変数未設定時のエラーメッセージが適切か
- [ ] 外部URLからのデータ取得が正常に動作するか（本番環境で確認）
- [ ] エラーハンドリングが適切に動作するか
- [ ] タイムアウト設定が適切か
- [ ] Vercelの環境変数（`RANKINGS_BASE_URL`, `RANKINGS_EXTERNALIZE_SCOPE`）が正しく設定されているか
- [ ] ランキング画面が同じURLのまま動くことを確認（ユーザー体験が変わっていないか）

## 参考情報

- VercelのFunctionサイズ制限: 50MB（圧縮後）
- 対象データの推定サイズ: 要確認（`public/data/rankings` と `output/*` のサイズを確認）
- 外部ストレージの候補: Cloudflare R2, AWS S3, Vercel Blob, GitHub Releases

## 実装のポイント

### 同一オリジン化のメリット
- **CORS設定が不要**: ブラウザが外部URLに直接アクセスしないため、CORSエラーが発生しない
- **セキュリティ**: 外部ストレージのURLを直接公開する必要がない
- **ユーザー体験**: URLが変わらないため、ブックマークやリンクがそのまま機能する

### URL生成の一元化のメリット
- **保守性**: パス生成ロジックを変更する場合、1箇所の修正で済む
- **一貫性**: すべての参照箇所で同じパス生成ロジックを使用
- **将来の拡張**: 外部ストレージのURL構造が変わっても、ヘルパー関数を修正するだけで対応可能

### 段階移行のメリット
- **リスク最小化**: 問題が発生した場合の影響範囲を限定
- **検証容易**: 小規模な範囲で動作確認してから拡張
- **ロールバック容易**: 問題が発生した場合、scopeを空にするだけで元に戻せる
