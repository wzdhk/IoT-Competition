$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
if (-not (Test-Path '.dotnet\dotnet.exe')) {
    Write-Host '[setup] 未找到本地 .NET SDK，首次安装约 300MB...' -ForegroundColor Yellow
    if (-not (Test-Path 'dotnet-install.ps1')) {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri 'https://dot.net/v1/dotnet-install.ps1' -OutFile 'dotnet-install.ps1'
    }
    & .\dotnet-install.ps1 -Channel 8.0 -InstallDir .dotnet
}
$env:PATH = "$root\.dotnet;$env:PATH"
Write-Host ('[setup] 本地 .NET SDK: ' + (& .\.dotnet\dotnet --version)) -ForegroundColor Green
Write-Host '[setup] 构建...' -ForegroundColor Cyan
& .\.dotnet\dotnet build -nologo
if ($LASTEXITCODE -ne 0) { Write-Host '[setup] 构建失败' -ForegroundColor Red; Read-Host '按回车退出'; exit 1 }
Write-Host '[setup] 运行边缘采集程序...' -ForegroundColor Cyan
& .\.dotnet\dotnet run --project src\CCDTrace.Edge
