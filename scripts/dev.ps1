$root=Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:UV_CACHE_DIR="$root\.uv-cache"
$env:LOCALAPPDATA="$root\.localappdata"
New-Item -ItemType Directory -Force $env:UV_CACHE_DIR,$env:LOCALAPPDATA | Out-Null
$npm=(Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
if(-not $npm){
  $nodeRoot=(Resolve-Path "$root\..\.tools\node-v22.23.2-win-x64").Path
  $env:PATH="$nodeRoot;$env:PATH"
  $npm="$nodeRoot\npm.cmd"
}
& $npm run dev
