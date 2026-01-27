# サーバー接続エラーの解決方法

## エラー: "localhost 接続が拒否されました"

### 確認手順

#### 1. サーバーが起動しているか確認

**Cursorの統合ターミナルで以下を実行:**

```powershell
# プロジェクトディレクトリに移動
cd "C:\Users\short\OneDrive\ドキュメント\デスクトップ\TopPage"

# サーバーを起動
npm run dev
```

**確認ポイント:**
- ターミナルに `[DEV_START] CWD: ...` が表示されるか
- `✓ Ready in X seconds` が表示されるか
- `○ Local: http://localhost:3000` が表示されるか
- エラーメッセージが表示されていないか

#### 2. ポートが使用されているか確認

```powershell
# ポート3000と3001を確認
Get-NetTCPConnection -LocalPort 3000,3001 -ErrorAction SilentlyContinue
```

**ポートが使用されている場合:**
```powershell
# 既存のNode.jsプロセスを停止
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force

# 再度サーバーを起動
npm run dev
```

#### 3. ビルドエラーを確認

```powershell
# .nextディレクトリを削除
Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue

# サーバーを再起動
npm run dev
```

#### 4. 型エラーを確認

エディタで以下のファイルに型エラーがないか確認:
- `app/ranking/[year]/[league]/page.tsx`
- `lib/ranking/loaders.ts`
- `lib/ranking/adapter.ts`
- `lib/ranking/types.ts`
- `components/RankingUI.tsx`

### よくある原因と解決方法

#### 原因1: サーバーが起動していない

**症状:**
- ターミナルにエラーメッセージが表示される
- `Ready` メッセージが表示されない

**解決方法:**
1. ターミナルのエラーメッセージを確認
2. エラー内容に応じて対処

#### 原因2: ポートが既に使用されている

**症状:**
- `Port 3000 is already in use` というエラー

**解決方法:**
```powershell
# 既存のプロセスを停止
Get-Process -Name node | Stop-Process -Force

# 別のポートを使用する場合
npm run dev -- -p 3001
```

#### 原因3: パスの問題（日本語を含むパス）

**症状:**
- PowerShellでパスが正しく認識されない
- `Set-Location` エラーが発生

**解決方法:**
1. Cursorの統合ターミナルを使用（推奨）
2. または、プロジェクトを英語のみのパスに移動

#### 原因4: 型エラーでビルドが失敗

**症状:**
- TypeScriptの型エラーが表示される
- ビルドが完了しない

**解決方法:**
- `next.config.mjs` で `ignoreBuildErrors: true` が設定されているので、通常は問題ありません
- ただし、重大なエラーがある場合は修正が必要です

### デバッグ手順

1. **ターミナルを開く**
   - Cursorの統合ターミナル（`Ctrl + ``）

2. **現在のディレクトリを確認**
   ```powershell
   Get-Location
   ```

3. **package.jsonの存在を確認**
   ```powershell
   Test-Path "package.json"
   ```

4. **サーバーを起動**
   ```powershell
   npm run dev
   ```

5. **エラーメッセージを確認**
   - ターミナルに表示されるエラーメッセージをコピー
   - エラーメッセージに基づいて対処

### 緊急時の対処法

すべての方法が失敗した場合:

1. **完全にクリーンアップ**
   ```powershell
   # .nextを削除
   Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue
   
   # node_modulesを再インストール（必要に応じて）
   Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
   npm install
   
   # サーバーを起動
   npm run dev
   ```

2. **別のターミナルを使用**
   - PowerShellではなく、コマンドプロンプト（cmd）を試す
   - または、Git Bashを試す

3. **ポートを変更**
   ```powershell
   npm run dev -- -p 3001
   ```
   その後、`http://localhost:3001` にアクセス
