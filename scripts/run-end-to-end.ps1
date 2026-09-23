param(
 [string]$PortfolioWorkbook='$PSScriptRoot\..\data\input\Far_East_Asset_List.xlsx',
 [string]$CompletedUnderwritingWorkbook='',
 [switch]$UseSyntheticPilot
)
$ErrorActionPreference='Stop';$root=Split-Path -Parent $PSScriptRoot;Set-Location $root;$env:UV_CACHE_DIR="$root\.uv-cache";$uv="$root\tools\uv.exe"
& $uv run python scripts\download_ura_data.py
& $uv run python scripts\refresh_public_data.py
& $uv run python scripts\ingest_portfolio.py --workbook $PortfolioWorkbook
if($CompletedUnderwritingWorkbook){& $uv run python scripts\import_underwriting.py --workbook $CompletedUnderwritingWorkbook --strict}
& $uv run python scripts\build_full_model.py
& $uv run python scripts\export_zoning_exceptions.py
& $uv run python scripts\calibrate_models.py
if($UseSyntheticPilot){
 & $uv run python scripts\generate_pilot_history.py
 & $uv run python scripts\train_models.py --allow-synthetic-pilot --version 0.1.0
 & $uv run python scripts\run_pilot_model.py
 & $uv run python scripts\compare_legacy_model.py
 & $uv run python scripts\backtest_models.py
 & $uv run python scripts\run_full_portfolio_v2.py --allow-synthetic-model
}else{
 & $uv run python scripts\train_models.py --version 1.0.0
 & $uv run python scripts\run_full_portfolio_v2.py
}
& $uv run pytest -q
Write-Host 'End-to-end pipeline completed.' -ForegroundColor Green
