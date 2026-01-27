# `@vercel.js`モジュールエラーの解決方法

## エラー内容

```
Error: Cannot find module './vendor-chunks/@vercel.js'
```

## 原因

`.next`ディレクトリを削除した後、Next.jsの再ビルドが不完全な状態で、`@vercel/analytics`パッケージのvendor-chunkが正しく生成されていない。

## 解決方法

### 方法1: キャッシュを完全にクリアして再起動（推奨）

```powershell
# 1. .nextディレクトリを削除
Remove-Item -Recurse -Force .next

# 2. 開発サーバーを再起動
npm run dev
```

### 方法2: node_modulesも再インストール（方法1で解決しない場合）

```powershell
# 1. .nextディレクトリを削除
Remove-Item -Recurse -Force .next

# 2. node_modulesを削除（オプション）
Remove-Item -Recurse -Force node_modules

# 3. パッケージを再インストール
npm install

# 4. 開発サーバーを起動
npm run dev
```

### 方法3: Next.jsのキャッシュもクリア

```powershell
# 1. すべてのキャッシュを削除
Remove-Item -Recurse -Force .next
Remove-Item -Recurse -Force node_modules/.cache -ErrorAction SilentlyContinue

# 2. 開発サーバーを再起動
npm run dev
```

## 確認事項

- `package.json`に`@vercel/analytics`が含まれているか確認
- `node_modules/@vercel/analytics`が存在するか確認
- 開発サーバーが正常に起動するか確認
