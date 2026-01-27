# `_document.js`エラーの解決方法

## エラー内容

```
Error: ENOENT: no such file or directory, open 'C:\Users\short\OneDrive\ドキュメント\デスクトップ\TopPage\.next\server\pages\_document.js'
```

## 原因

Next.jsが`pages-manifest.json`に`/_document`を登録していますが、実際のファイルが存在しません。このプロジェクトはApp Routerを使用しているため、Pages Routerの`_document.js`は不要です。

## 解決方法

### 1. `.next`ディレクトリを完全に削除（完了済み）

```powershell
Remove-Item -Recurse -Force .next
```

### 2. 開発サーバーを再起動

```powershell
npm run dev
```

これで、Next.jsが正しく再ビルドし、`pages-manifest.json`が正しく生成されるはずです。

### 3. それでも解決しない場合

`node_modules`のキャッシュもクリア：

```powershell
# .nextを削除
Remove-Item -Recurse -Force .next

# node_modulesのキャッシュを削除
Remove-Item -Recurse -Force node_modules/.cache -ErrorAction SilentlyContinue

# 開発サーバーを再起動
npm run dev
```

## 確認事項

- このプロジェクトはApp Routerを使用している（`app/`ディレクトリ）
- `pages/`ディレクトリは存在しない
- `pages-manifest.json`はNext.jsが自動生成するファイル
