# KisanAlert Web Build & Deploy Script
# Run this in PowerShell: .\build_and_deploy.ps1

Write-Host "===== STEP 1: Building Flutter Web =====" -ForegroundColor Cyan
Set-Location "e:\Users\amolb\Downloads\Telegram Desktop\Agri (1)\Agri\kisanalert_app"
E:\flutter_sdk\bin\flutter.bat build web --release
if ($LASTEXITCODE -ne 0) {
    Write-Host "BUILD FAILED!" -ForegroundColor Red
    exit 1
}
Write-Host "BUILD SUCCESS!" -ForegroundColor Green

Write-Host ""
Write-Host "===== STEP 2: Copying to public folder =====" -ForegroundColor Cyan
Set-Location "e:\Users\amolb\Downloads\Telegram Desktop\Agri (1)\Agri"
robocopy "kisanalert_app\build\web" "public" /S /E /PURGE /MT:32
Write-Host "COPY DONE!" -ForegroundColor Green

Write-Host ""
Write-Host "===== STEP 3: Deploying to Firebase =====" -ForegroundColor Cyan
npx firebase-tools deploy --only hosting --project campusbazaar-84af8
if ($LASTEXITCODE -ne 0) {
    Write-Host "DEPLOY FAILED!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "===== ALL DONE! =====" -ForegroundColor Green
Write-Host "Open https://kisanalert-ai.web.app and press Ctrl+Shift+R" -ForegroundColor Yellow
