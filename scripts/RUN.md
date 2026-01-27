# スクリプト実行ガイド

## PowerShellでの実行時の注意事項

### コメント行の扱い

PowerShellでは、`#` で始まるコメント行をコピペすると、コマンドに渡ってしまう可能性があります。

**❌ 避けるべき例:**
```powershell
# これはコメント
py scripts/validate_outputs.py --max-year 1937
```

**✅ 推奨:**
```powershell
py scripts/validate_outputs.py --max-year 1937
```

コメントは別行に書くか、実行コマンドのみをコピペしてください。

### レポート閲覧

Markdownレポートを閲覧する際は、`type` コマンドと `more` を使用してください：

```powershell
type output\reports\audit_rankings_structure.md | more
```

`morepy` のような連結事故を防ぐため、`type` と `more` を組み合わせて使用します。

## 実行コマンド

### ランキング構造監査

```powershell
py scripts/audit_rankings_structure.py --from-year 1950 --to-year 2024
```

### バリデーション

```powershell
py scripts/validate_outputs.py --max-year 1937
```




## ✅ 監査ルール（ファイル名）
- 表示名 BB/K はファイル名で BB_K に正規化（sanitize_filename準拠）
- 監査/生成ともに sanitize_filename の出力を正とする（手作業のBB-Kは禁止）
















