# サーバー起動エラーのトラブルシューティング

## エラー: "localhost 接続が拒否されました"

### 原因

1. **サーバーが起動していない**
   - ビルドエラーで起動に失敗している可能性
   - ポートが既に使用されている可能性

2. **パスの問題**
   - 日本語を含むパス（`デスクトップ`）でPowerShellが正しく動作しない可能性

### 解決方法

#### 方法1: 手動でサーバーを起動

1. **ターミナルを開く**（Cursorの統合ターミナルまたはPowerShell）

2. **プロジェクトディレクトリに移動**
   ```powershell
   cd "C:\Users\short\OneDrive\ドキュメント\デスクトップ\TopPage"
   ```

3. **サーバーを起動**
   ```powershell
   npm run dev
   ```

4. **起動確認**
   - ターミナルに `Ready` や `Local: http://localhost:3000` が表示されることを確認
   - エラーメッセージがないか確認

#### 方法2: ポートが使用されている場合

1. **ポート3000と3001を確認**
   ```powershell
   Get-NetTCPConnection -LocalPort 3000,3001
   ```

2. **使用中のプロセスを停止**
   ```powershell
   Get-Process -Name node | Stop-Process -Force
   ```

3. **再度サーバーを起動**

#### 方法3: ビルドエラーを確認

1. **.nextディレクトリを削除**
   ```powershell
   Remove-Item -Recurse -Force .next
   ```

2. **node_modulesを再インストール（必要に応じて）**
   ```powershell
   npm install
   ```

3. **サーバーを起動**
   ```powershell
   npm run dev
   ```

### 確認事項

1. **package.jsonが存在するか**
   - プロジェクトルートに `package.json` があることを確認

2. **node_modulesが存在するか**
   - `npm install` を実行しているか確認

3. **TypeScriptの型エラー**
   - 型エラーがあるとビルドに失敗する可能性があります
   - エディタで型エラーを確認してください

### よくあるエラー

#### "Cannot find module"
- `node_modules` を削除して `npm install` を再実行

#### "Port 3000 is already in use"
- 既存のNode.jsプロセスを停止
- または別のポートを使用（`npm run dev -- -p 3001`）

#### パスの問題（日本語を含むパス）
- プロジェクトを英語のみのパスに移動することを検討
- または、短いパス名を使用
