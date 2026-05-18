param(
    [string]$Name = "DeepLiveCam",
    [string]$Entry = "run.py",
    [string]$Dist = "dist"
)

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "PyInstaller not found. Installing..." -ForegroundColor Yellow
    pip install pyinstaller
}

Write-Host "Building $Entry into a single executable named $Name..." -ForegroundColor Cyan
pyinstaller --onefile --name $Name $Entry --distpath $Dist

if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "Build finished. Output: $Dist\$Name" -ForegroundColor Green
