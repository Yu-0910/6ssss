# player_name_jaが空の選手の原因を診断する（PowerShell版）

param(
    [Parameter(Mandatory=$true)]
    [string]$PlayerId,
    
    [int]$Year = 0,
    [string]$League = ""
)

$projectRoot = $PSScriptRoot | Split-Path -Parent

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "=== player_name_jaが空の原因診断 ===" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan
Write-Host "対象player_id: $PlayerId" -ForegroundColor Yellow
if ($Year -gt 0 -and $League) {
    Write-Host "対象年度・リーグ: $Year年 $Leagueリーグ`n" -ForegroundColor Yellow
}

# 段階2のチェック
Write-Host "📖 段階2: player_id_name_kana_official.csv をチェック中..." -ForegroundColor Cyan
$stage2Path = Join-Path $projectRoot "output\master\player_id_name_kana_official.csv"

if (-not (Test-Path $stage2Path)) {
    Write-Host "  ❌ ファイルが見つかりません: $stage2Path" -ForegroundColor Red
    exit 1
}

$stage2Rows = Import-Csv $stage2Path -Encoding UTF8 | Where-Object { $_.player_id -eq $PlayerId }

if ($stage2Rows.Count -eq 0) {
    Write-Host "  ❌ player_id $PlayerId が見つかりません" -ForegroundColor Red
    exit 1
}

Write-Host "  ✅ $($stage2Rows.Count)行見つかりました" -ForegroundColor Green
foreach ($row in $stage2Rows) {
    Write-Host "  - http_status: $($row.http_status)" -ForegroundColor White
    Write-Host "  - outcome: $($row.outcome)" -ForegroundColor White
    Write-Host "  - name_ja: '$($row.name_ja)'" -ForegroundColor White
    Write-Host "  - name_kana: '$($row.name_kana)'" -ForegroundColor White
    Write-Host "  - roman_official: '$($row.roman_official)'" -ForegroundColor White
    Write-Host ""
}

$hasNameJa = $stage2Rows | Where-Object { $_.name_ja -and $_.name_ja.Trim() } | Measure-Object | Select-Object -ExpandProperty Count
$httpStatus = $stage2Rows[0].http_status
$outcome = $stage2Rows[0].outcome

# 原因Bの判定
$causeB = $false
if ($httpStatus -ne "200" -or $outcome -match "FAILED|ERROR|NETWORK_ERROR") {
    Write-Host "  🔍 原因B（取得失敗）の可能性が高い" -ForegroundColor Yellow
    Write-Host "     - http_statusが200以外、またはoutcomeが失敗系`n" -ForegroundColor Gray
    $causeB = $true
} elseif (-not $hasNameJa -and $httpStatus -eq "200") {
    Write-Host "  🔍 原因B（パース失敗）の可能性が高い" -ForegroundColor Yellow
    Write-Host "     - http_status=200なのにname_jaが空`n" -ForegroundColor Gray
    $causeB = $true
}

# 段階3のチェック
Write-Host "📖 段階3: player_id_to_roman_full.csv をチェック中..." -ForegroundColor Cyan
$stage3Path = Join-Path $projectRoot "output\master\player_id_to_roman_full.csv"

if (Test-Path $stage3Path) {
    $stage3Rows = Import-Csv $stage3Path -Encoding UTF8 | Where-Object { $_.player_id -eq $PlayerId }
    
    if ($stage3Rows.Count -eq 0) {
        Write-Host "  ❌ player_id $PlayerId が見つかりません`n" -ForegroundColor Red
    } else {
        Write-Host "  ✅ 見つかりました" -ForegroundColor Green
        Write-Host "  - name_ja: '$($stage3Rows[0].name_ja)'`n" -ForegroundColor White
        
        # 原因Cの判定
        $causeC = $false
        if ($hasNameJa -and -not $stage3Rows[0].name_ja) {
            Write-Host "  🔍 原因C（段階3の選択ロジック）の可能性が高い" -ForegroundColor Yellow
            Write-Host "     - 段階2にはname_jaがあるのに、段階3で空になっている`n" -ForegroundColor Gray
            $causeC = $true
        }
    }
} else {
    Write-Host "  ⚠️ ファイルが見つかりません: $stage3Path`n" -ForegroundColor Yellow
}

# 段階0/5のチェック
Write-Host "📖 段階0/5: 元CSVと適用後CSVをチェック中..." -ForegroundColor Cyan

$originalPath = ""
$appliedPath = ""

if ($Year -gt 0 -and $League) {
    $originalPath = Join-Path $projectRoot "_data\master_csv\batting_$Year`_$League`_from_master.csv"
    $appliedPath = Join-Path $projectRoot "_data\master_csv_calculated\batting_$Year`_$League`_from_master.csv"
} else {
    # 全CSVを検索
    $originalFiles = Get-ChildItem -Path (Join-Path $projectRoot "_data\master_csv") -Filter "batting_*_from_master.csv" -ErrorAction SilentlyContinue
    $appliedFiles = Get-ChildItem -Path (Join-Path $projectRoot "_data\master_csv_calculated") -Filter "batting_*_from_master.csv" -ErrorAction SilentlyContinue
    
    foreach ($file in $originalFiles) {
        $rows = Import-Csv $file.FullName -Encoding UTF8 | Where-Object { $_.player_id -eq $PlayerId }
        if ($rows.Count -gt 0) {
            $originalPath = $file.FullName
            break
        }
    }
    
    foreach ($file in $appliedFiles) {
        $rows = Import-Csv $file.FullName -Encoding UTF8 | Where-Object { $_.player_id -eq $PlayerId }
        if ($rows.Count -gt 0) {
            $appliedPath = $file.FullName
            break
        }
    }
}

$originalNameJa = ""
$appliedNameJa = ""

if ($originalPath -and (Test-Path $originalPath)) {
    $originalRows = Import-Csv $originalPath -Encoding UTF8 | Where-Object { $_.player_id -eq $PlayerId }
    if ($originalRows.Count -gt 0) {
        Write-Host "  ✅ 元CSVで見つかりました: $(Split-Path $originalPath -Leaf)" -ForegroundColor Green
        $originalNameJa = $originalRows[0].player_name_ja
        Write-Host "  - player_name_ja: '$originalNameJa'" -ForegroundColor White
    }
} else {
    Write-Host "  ⚠️ 元CSVで見つかりませんでした" -ForegroundColor Yellow
}

if ($appliedPath -and (Test-Path $appliedPath)) {
    $appliedRows = Import-Csv $appliedPath -Encoding UTF8 | Where-Object { $_.player_id -eq $PlayerId }
    if ($appliedRows.Count -gt 0) {
        Write-Host "  ✅ 適用後CSVで見つかりました: $(Split-Path $appliedPath -Leaf)" -ForegroundColor Green
        $appliedNameJa = $appliedRows[0].player_name_ja
        Write-Host "  - player_name_ja: '$appliedNameJa'`n" -ForegroundColor White
    }
} else {
    Write-Host "  ⚠️ 適用後CSVで見つかりませんでした`n" -ForegroundColor Yellow
}

# 原因Aの判定
$causeA = $false
if ($originalNameJa -and -not $appliedNameJa) {
    Write-Host "  🔍 原因A（段階5の上書き事故）の可能性が高い" -ForegroundColor Yellow
    Write-Host "     - 元CSVにはplayer_name_jaがあるのに、適用後に空になっている`n" -ForegroundColor Gray
    $causeA = $true
}

# 判定結果
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "=== 判定結果 ===" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

$causes = @()
if ($causeA) { $causes += "A" }
if ($causeB) { $causes += "B" }
if ($causeC) { $causes += "C" }

if ($causes.Count -eq 0) {
    Write-Host "  ⚠️ 明確な原因を特定できませんでした" -ForegroundColor Yellow
    Write-Host "  - 追加の調査が必要です`n" -ForegroundColor Gray
} else {
    Write-Host "  🔍 原因候補: $($causes -join ', ')" -ForegroundColor Green
    if ($causes -contains "A") {
        Write-Host "     - A: 段階5（apply_roman_to_master_csvs.py）が空のname_jaで上書き" -ForegroundColor White
    }
    if ($causes -contains "B") {
        Write-Host "     - B: 段階2で取得/パース失敗" -ForegroundColor White
    }
    if ($causes -contains "C") {
        Write-Host "     - C: 段階3の選択ロジックで空の行を採用" -ForegroundColor White
    }
    Write-Host ""
}

if ($causes -contains "A") {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "=== 原因Aの場合の修正案 ===" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "apply_roman_to_master_csvs.py を修正:" -ForegroundColor Yellow
    Write-Host "  - player_name_jaを上書きする際、空の場合は元の値を維持" -ForegroundColor White
    Write-Host "  - 例コードはドキュメントを参照" -ForegroundColor Gray
    Write-Host ""
}

