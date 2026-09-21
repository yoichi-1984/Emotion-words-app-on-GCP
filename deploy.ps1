<#
.SYNOPSIS
    Google Cloud Run への自動デプロイスクリプト (PowerShell)
.DESCRIPTION
    env/gcp.env または .env から GCP 設定を読み込み、Cloud Run へアプリケーションをデプロイします。
    デプロイ完了後にサービスURLを取得し、OAuth 2.0 のリダイレクトURI設定案内を表示します。
.EXAMPLE
    .\deploy.ps1
    .\deploy.ps1 -DryRun
    .\deploy.ps1 -Region asia-northeast1 -ServiceName kokugo-emotion-words
#>

[CmdletBinding()]
param(
    [string]$ProjectId = "",
    [string]$Region = "asia-northeast1",
    [string]$ServiceName = "kokugo-emotion-words",
    [switch]$DryRun = $false
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " 中学受験 国語 心情語対策アプリ - Cloud Run デプロイツール " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. 環境設定ファイルの検索と読み込み
$envFile = ""
if (Test-Path "env\gcp.env") {
    $envFile = "env\gcp.env"
} elseif (Test-Path ".env") {
    $envFile = ".env"
}

$envVars = @{}
if ($envFile) {
    Write-Host "[INFO] 設定ファイルを読み込み中: $envFile" -ForegroundColor Green
    Get-Content $envFile -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not ($line.StartsWith("#"))) {
            $parts = $line.Split("=", 2)
            if ($parts.Length -eq 2) {
                $key = $parts[0].Trim()
                $val = $parts[1].Trim().Trim('"').Trim("'")
                $envVars[$key] = $val
            }
        }
    }
} else {
    Write-Host "[WARN] 設定ファイル (env/gcp.env または .env) が見つかりません。環境変数から取得を試みます。" -ForegroundColor Yellow
}

# パラメータおよび環境変数の解決
if (-not $ProjectId) {
    $ProjectId = if ($envVars.ContainsKey("GCP_PROJECT_ID") -and $envVars["GCP_PROJECT_ID"]) { $envVars["GCP_PROJECT_ID"] } else { $env:GCP_PROJECT_ID }
}
if (-not $ProjectId) {
    $ProjectId = "kokugo-emotion-words"
}

$clientId = if ($envVars.ContainsKey("GOOGLE_CLIENT_ID")) { $envVars["GOOGLE_CLIENT_ID"] } else { $env:GOOGLE_CLIENT_ID }
$clientSecret = if ($envVars.ContainsKey("GOOGLE_CLIENT_SECRET")) { $envVars["GOOGLE_CLIENT_SECRET"] } else { $env:GOOGLE_CLIENT_SECRET }
$allowedEmails = if ($envVars.ContainsKey("ALLOWED_EMAILS")) { $envVars["ALLOWED_EMAILS"] } else { $env:ALLOWED_EMAILS }
$redirectUri = if ($envVars.ContainsKey("REDIRECT_URI")) { $envVars["REDIRECT_URI"] } else { $env:REDIRECT_URI }

# 設定情報の検証
Write-Host ""
Write-Host "【設定パラメータ】" -ForegroundColor White
Write-Host "  Project ID      : $ProjectId"
Write-Host "  Region          : $Region"
Write-Host "  Service Name    : $ServiceName"
Write-Host "  Client ID       : $(if ($clientId) { $clientId.Substring(0, [Math]::Min(15, $clientId.Length)) + '...' } else { '（未設定）' })"
Write-Host "  Allowed Emails  : $allowedEmails"
Write-Host "  Current Redirect: $redirectUri"
Write-Host ""

if (-not $clientId -or -not $clientSecret -or -not $allowedEmails) {
    Write-Host "[ERROR] 必要な環境変数 (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, ALLOWED_EMAILS) が不足しています。" -ForegroundColor Red
    Write-Host "env/gcp.env に正しい値を設定してください。" -ForegroundColor Red
    exit 1
}

# 2. gcloud CLI の存在確認
$gcloudCmd = (Get-Command gcloud.cmd -ErrorAction SilentlyContinue)
if (-not $gcloudCmd) {
    $gcloudCmd = (Get-Command gcloud -ErrorAction SilentlyContinue)
}
if (-not $gcloudCmd) {
    Write-Host "[ERROR] gcloud コマンドが見つかりません。Google Cloud SDK をインストールしてください。" -ForegroundColor Red
    exit 1
}
$gcloudExe = $gcloudCmd.Source

# 3. デプロイ実行コマンドの構築
# Cloud Run 本番環境では DEV_MODE=False で起動
$envList = @(
    "DEV_MODE=False",
    "GCP_PROJECT_ID=$ProjectId",
    "GOOGLE_CLIENT_ID=$clientId",
    "GOOGLE_CLIENT_SECRET=$clientSecret",
    "ALLOWED_EMAILS=$allowedEmails",
    "REDIRECT_URI=$redirectUri"
)
$envString = $envList -join ","

$deployArgs = @(
    "run", "deploy", $ServiceName,
    "--source", ".",
    "--project", $ProjectId,
    "--region", $Region,
    "--platform", "managed",
    "--allow-unauthenticated",
    "--min-instances", "0",
    "--max-instances", "2",
    "--memory", "512Mi",
    "--cpu", "1",
    "--set-env-vars", $envString
)

Write-Host "[STEP 1] Cloud Run デプロイコマンドの準備完了" -ForegroundColor Cyan
Write-Host "実行コマンド: gcloud $($deployArgs -join ' ')" -ForegroundColor DarkGray
Write-Host ""

if ($DryRun) {
    Write-Host "[INFO] DryRun モードのためデプロイを実行せず終了します。" -ForegroundColor Yellow
    exit 0
}

# 4. デプロイの実行
Write-Host "[STEP 2] Cloud Run へデプロイ中（ソースビルド & コンテナ配備）..." -ForegroundColor Green
& $gcloudExe @deployArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Cloud Run のデプロイに失敗しました (Exit Code: $LASTEXITCODE)。" -ForegroundColor Red
    exit $LASTEXITCODE
}

# 5. サービスURLの取得
Write-Host ""
Write-Host "[STEP 3] デプロイされたサービスの URL を取得中..." -ForegroundColor Green
$serviceUrl = (& $gcloudExe run services describe $ServiceName --project $ProjectId --region $Region --format "value(status.url)").Trim()

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " [OK] Cloud Run デプロイが正常に完了しました！" -ForegroundColor Green
Write-Host " サービス URL: $serviceUrl" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# 6. OAuth 2.0 リダイレクトURI設定の案内
Write-Host "【重要: 次の手順（Google OAuth 2.0 連携設定）】" -ForegroundColor Yellow
Write-Host "本番環境で Google ログインを機能させるため、以下の設定を行ってください:" -ForegroundColor White
Write-Host "1. Google Cloud Console の [APIとサービス] > [認証情報] を開く:"
Write-Host "   https://console.cloud.google.com/apis/credentials?project=$ProjectId"
Write-Host "2. 使用している OAuth 2.0 クライアント ID を選択。"
Write-Host "3. [承認済みのリダイレクト URI] に以下を追加して [保存]:"
Write-Host "   $serviceUrl/" -ForegroundColor Cyan
Write-Host "4. [承認済みの JavaScript 生成元] に以下を追加して [保存]:"
Write-Host "   $serviceUrl" -ForegroundColor Cyan
Write-Host ""

# 7. REDIRECT_URI 環境変数の同期（もし現在の REDIRECT_URI が本番URLと異なる場合）
if ($redirectUri -ne "$serviceUrl/" -and $redirectUri -ne $serviceUrl) {
    Write-Host "[INFO] Cloud Run サービスの REDIRECT_URI を最新 URL ($serviceUrl/) に自動更新します..." -ForegroundColor Green
    & $gcloudExe run services update $ServiceName --project $ProjectId --region $Region --update-env-vars "REDIRECT_URI=$serviceUrl/"
    Write-Host "[OK] REDIRECT_URI を $serviceUrl/ に更新しました。" -ForegroundColor Green
}

Write-Host ""
Write-Host "ブラウザで $serviceUrl にアクセスして動作を確認してください。" -ForegroundColor Green
