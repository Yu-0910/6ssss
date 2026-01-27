# @vercel/analytics エラーの修正

## エラー内容

```
Error: Cannot find module './vendor-chunks/@vercel.js'
```

## 原因

`.next`ディレクトリを削除した後に再ビルドした際、`@vercel/analytics`のモジュールが正しく解決されない問題が再発しました。

## 修正内容

`components/AnalyticsWrapper.tsx`を動的インポートに変更しました。これにより、開発環境でもビルド時にエラーが発生しなくなります。

## 解決手順

### 1. .nextディレクトリを削除

```powershell
Remove-Item -Recurse -Force .next
```

または、手動で`.next`フォルダを削除してください。

### 2. 開発サーバーを再起動

```powershell
npm run dev
```

### 3. ブラウザで確認

エラーが解消されているか確認してください。

## 修正後のコード

`components/AnalyticsWrapper.tsx`は、`useEffect`内で動的に`@vercel/analytics`をインポートするように変更されました。これにより：

- 開発環境では`@vercel/analytics`を読み込まない（エラー回避）
- 本番環境でのみ動的に読み込む
- ビルド時にモジュール解決エラーが発生しない
