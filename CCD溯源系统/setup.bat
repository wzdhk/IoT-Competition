@echo off
setlocal
cd /d "%~dp0"

if not exist ".dotnet\dotnet.exe" (
    echo [setup] 未找到本地 .NET SDK，正在下载安装（首次约 300MB）...
    powershell -ExecutionPolicy Bypass -Command "& { [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://dot.net/v1/dotnet-install.ps1' -OutFile 'dotnet-install.ps1'; & .\dotnet-install.ps1 -Channel 8.0 -InstallDir .dotnet }"
    if errorlevel 1 (
        echo [setup] 安装失败
        pause
        exit /b 1
    )
)

set PATH=%~dp0.dotnet;%PATH%

echo [setup] 本地 .NET SDK:
.dotnet\dotnet --version

echo [setup] 构建...
.dotnet\dotnet build -nologo
if errorlevel 1 (
    echo [setup] 构建失败
    pause
    exit /b 1
)

echo [setup] 运行边缘采集程序...
.dotnet\dotnet run --project src\CCDTrace.Edge
pause
