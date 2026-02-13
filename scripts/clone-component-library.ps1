# Clone Untitled UI Next.js starter kit as the component library (used by MCP + generator)
$Repo = "https://github.com/untitleduico/untitledui-nextjs-starter-kit.git"
$Target = Join-Path $PSScriptRoot ".." "component-library"
if (Test-Path $Target) {
    Write-Host "component-library already exists. Pulling latest..."
    Set-Location $Target
    git pull
    Set-Location $PSScriptRoot
} else {
    Write-Host "Cloning Untitled UI starter kit to component-library..."
    git clone $Repo $Target
}
Write-Host "Done. Component library at: $Target"
