param([string]$Workbook='$PSScriptRoot\..\data\input\Far_East_Asset_List.xlsx')
$ErrorActionPreference='Stop';$root=Split-Path -Parent $PSScriptRoot;Set-Location $root;$env:UV_CACHE_DIR="$root\.uv-cache"
& "$root\tools\uv.exe" run python scripts\download_ura_data.py
& "$root\tools\uv.exe" run python scripts\refresh_public_data.py
& "$root\tools\uv.exe" run python scripts\ingest_portfolio.py --workbook $Workbook
& "$root\tools\uv.exe" run python scripts\build_full_model.py
& "$root\tools\uv.exe" run python scripts\export_zoning_exceptions.py
