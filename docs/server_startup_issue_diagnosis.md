# サーバー起動問題の診断

## 状況

サーバーは起動しているように見えますが、実際には接続できない、またはページが表示されない。

## 確認すべきポイント

### 1. ターミナルの出力を確認

サーバー起動時に以下のメッセージが表示されることを確認：

```
[DEV_START] CWD: C:\Users\short\OneDrive\ドキュメント\デスクトップ\TopPage
   ▲ Next.js 15.2.4
   - Local:        http://localhost:3000
   - Network:      http://10.68.109.186:3000

 ✓ Starting...
 ✓ Ready in X seconds
 ○ Compiling / ...
```

**問題がある場合:**
- `✗` マークが表示される
- エラーメッセージが表示される
- `Compiling` の後にエラーが表示される

### 2. コンパイルエラーを確認

Next.jsはページにアクセスしたときにコンパイルを開始します。以下のエラーが発生する可能性があります：

- **TypeScriptの型エラー**
- **モジュールが見つからないエラー**
- **構文エラー**

### 3. ブラウザの開発者ツールを確認

1. `F12` で開発者ツールを開く
2. **Consoleタブ**でエラーを確認
3. **Networkタブ**でリクエストの状態を確認

## よくある問題と解決方法

### 問題1: コンパイルエラーでページが表示されない

**症状:**
- サーバーは起動している
- ブラウザでアクセスするとエラーページが表示される
- ターミナルにエラーメッセージが表示される

**解決方法:**
1. ターミナルのエラーメッセージを確認
2. エラー内容に応じて修正
3. 特に、最近追加したコード（`export const dynamic`、`csvPath`の追加など）を確認

### 問題2: 型エラーでビルドが失敗

**症状:**
- TypeScriptの型エラーが表示される
- ページがコンパイルされない

**解決方法:**
- `next.config.mjs`で`ignoreBuildErrors: true`が設定されているので、通常は問題ありません
- ただし、重大なエラーがある場合は修正が必要

### 問題3: モジュールが見つからない

**症状:**
- `Cannot find module` エラー
- `Module not found` エラー

**解決方法:**
```powershell
# node_modulesを再インストール
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
npm install
```

## デバッグ手順

### ステップ1: サーバーを完全に停止

```powershell
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force
```

### ステップ2: .nextを削除

```powershell
Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue
```

### ステップ3: サーバーを起動してエラーを確認

```powershell
npm run dev
```

**ターミナルに表示されるエラーメッセージをすべてコピーしてください。**

### ステップ4: ブラウザでアクセス

- `http://localhost:3000` にアクセス
- 開発者ツール（F12）のConsoleタブでエラーを確認

## エラーメッセージの共有

以下の情報を共有してください：

1. **ターミナルのエラーメッセージ**（完全な出力）
2. **ブラウザのConsoleタブのエラー**
3. **Networkタブのリクエスト状態**（失敗しているリクエストがあれば）

これらの情報があれば、原因を特定できます。
