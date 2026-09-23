$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot;Set-Location $root
$env:UV_CACHE_DIR="$root\.uv-cache"
if(-not(Test-Path "$root\tools\uv.exe")){New-Item -ItemType Directory -Path "$root\tools" -Force|Out-Null;Invoke-WebRequest 'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip' -OutFile "$root\tools\uv.zip";Expand-Archive "$root\tools\uv.zip" "$root\tools" -Force}
& "$root\tools\uv.exe" sync
$npm=(Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
if(-not $npm){$bundled=Resolve-Path "$root\..\.tools\node-v22.23.2-win-x64\npm.cmd" -ErrorAction SilentlyContinue;if($bundled){$npm=$bundled.Path}else{throw 'npm not found. Install Node.js 22+.'}}
& $npm install
Write-Host 'Bootstrap complete.' -ForegroundColor Green
