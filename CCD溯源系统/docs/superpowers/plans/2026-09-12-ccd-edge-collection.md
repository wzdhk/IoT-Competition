# CCD 溯源系统 · 边缘采集层 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在工控机（1）上实现一个与现有 CCD 质检软件并行、非侵入的边缘采集程序：被动旁听 Modbus RTU 逐件结果、读扫码枪 QR、时序绑定、本地 SQLite + 云端 MySQL 入库、汇总统计，并用 WebView2 内嵌 HTML 看板实时展示。

**Architecture:** 分层解耦——纯逻辑（CRC/帧解析/结果解释/绑定队列/汇总）放 `CCDTrace.Core` 库并全部单测；硬件相关（串口、扫码枪、WebView2）通过接口注入隔离；WinForms 外壳 + WebView2 看板做组合根。

**Tech Stack:** C# / .NET 8（`net8.0` 库与测试，`net8.0-windows` 桌面端）；xUnit；`Microsoft.Data.Sqlite`；`MySqlConnector`；`System.IO.Ports`；WinForms + Microsoft.Web.WebView2。

**Spec:** [2026-09-11-ccd-traceability-design.md](../specs/2026-09-11-ccd-traceability-design.md) — 计划从该设计文档推导，实施者须两篇一起读。

## Global Constraints

- 目标框架：库与测试 `net8.0`，桌面端 `net8.0-windows`。
- 命名空间根：`CCDTrace`；库程序集 `CCDTrace.Core`，桌面端 `CCDTrace.Edge`，测试 `CCDTrace.Tests`。
- 不引入 HslCommunication；Modbus RTU 帧解析自研（被动旁听需要字节级组帧，主站库不适用）。
- 所有硬件访问（串口、扫码枪）必须走接口注入，单元测试不得触碰真实串口。
- 数据幂等键：`qr_code`（本地唯一、云端唯一）。
- 配置文件名固定为 `config.json`，生产地 `production_site` 为每台机器固定值。
- 旁听串口**只读**：`SerialPort.Open()` 后绝不调用任何 `Write*` 方法。
- 提交信息使用英文常规式（`feat:` / `test:` / `chore:`）。
- **dotnet CLI 用项目本地 SDK**：本机全局无 .NET SDK；项目 `.dotnet/` 已装 SDK 8.0.425（含 8.0 runtime）。所有构建/测试命令用 `./.dotnet/dotnet`（或每条 shell 命令前 `export PATH="$PWD/.dotnet:$PATH"`）。`.dotnet/` 与 `dotnet-install.ps1` 不入 git。

---

## File Structure

```
D:/桌面/CCD溯源系统/
  CCDTrace.sln
  .gitignore
  README.md
  src/CCDTrace.Core/
    CCDTrace.Core.csproj
    Events/InspectionResult.cs
    Events/ResultEvent.cs
    Events/ScannerEvent.cs
    Models/TraceRecord.cs
    Models/SummaryStats.cs
    Config/AppConfig.cs
    Config/AppConfigLoader.cs
    Modbus/ModbusCrc16.cs
    Modbus/ModbusRtuFrame.cs
    Modbus/ModbusRtuParser.cs
    Modbus/ResultInterpreter.cs
    Modbus/ModbusSniffer.cs
    Serial/ISerialPort.cs
    Serial/SystemSerialPort.cs
    Scanning/ScannerReader.cs
    Correlation/CorrelationQueue.cs
    Summary/SummaryCalculator.cs
    Storage/ITraceStore.cs
    Storage/SqliteTraceStore.cs
    Storage/ICloudStore.cs
    Storage/MySqlCloudStore.cs
    Sync/CloudSyncService.cs
  src/CCDTrace.Edge/
    CCDTrace.Edge.csproj
    Program.cs
    AppRuntime.cs
    MainForm.cs
    MainForm.Designer.cs
    Dashboard/index.html
    Dashboard/app.css
    Dashboard/app.js
  tests/CCDTrace.Tests/
    CCDTrace.Tests.csproj
    ModbusCrc16Tests.cs
    ModbusRtuParserTests.cs
    ResultInterpreterTests.cs
    CorrelationQueueTests.cs
    SummaryCalculatorTests.cs
    AppConfigLoaderTests.cs
    SqliteTraceStoreTests.cs
    CloudSyncServiceTests.cs
    FakeCloudStore.cs
    FakeSerialPort.cs
```

---

### Task 1: 项目脚手架 + git 初始化

**Files:**
- Create: `CCDTrace.sln`, `.gitignore`, `README.md`
- Create: `src/CCDTrace.Core/CCDTrace.Core.csproj`
- Create: `src/CCDTrace.Edge/CCDTrace.Edge.csproj`
- Create: `tests/CCDTrace.Tests/CCDTrace.Tests.csproj`
- Create: `setup.bat`, `setup.ps1`（本地 SDK 一键「打开即用」脚本）

**Interfaces:**
- Produces: 三个可编译的空项目 + 解决方案；后续任务向其中添加文件。

- [ ] **Step 1: 确认 git 已就绪**

仓库已初始化：`main` 分支有初始提交 `fb507d2`，当前在 `edge-collection` 分支。执行 `git status` 确认工作区干净即可，**不要再 `git init` 或 `git branch -M`**。

- [ ] **Step 2: 创建解决方案与项目文件**

`src/CCDTrace.Core/CCDTrace.Core.csproj`:
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <RootNamespace>CCDTrace</RootNamespace>
  </PropertyGroup>
</Project>
```

`tests/CCDTrace.Tests/CCDTrace.Tests.csproj`:
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.11.1" />
    <PackageReference Include="xunit" Version="2.9.2" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.2" />
  </ItemGroup>
  <ItemGroup>
    <ProjectReference Include="..\..\src\CCDTrace.Core\CCDTrace.Core.csproj" />
  </ItemGroup>
</Project>
```

`src/CCDTrace.Edge/CCDTrace.Edge.csproj`:
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>WinExe</OutputType>
    <TargetFramework>net8.0-windows</TargetFramework>
    <UseWindowsForms>true</UseWindowsForms>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <RootNamespace>CCDTrace.Edge</RootNamespace>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Web.WebView2" Version="1.0.2903.40" />
  </ItemGroup>
  <ItemGroup>
    <ProjectReference Include="..\CCDTrace.Core\CCDTrace.Core.csproj" />
  </ItemGroup>
</Project>
```

- [ ] **Step 3: 创建 .gitignore 与 README 骨架**

`.gitignore`:
```gitignore
bin/
obj/
*.user
*.suo
.vs/
trace.db
config.json
.dotnet/
dotnet-install.ps1
```

`README.md`:
```markdown
# CCD 溯源系统 · 边缘采集层

工控机（1）上的非侵入式溯源采集程序：旁听 Modbus RTU 逐件结果 + 扫码枪 QR，
绑定后写入本地 SQLite 与云端 MySQL，WebView2 看板实时展示。

## 构建
dotnet build

## 测试
dotnet test

## 运行
配置 config.json 后：dotnet run --project src/CCDTrace.Edge
```

- [ ] **Step 4: 添加三个项目到解决方案并验证构建**

```bash
export PATH="$PWD/.dotnet:$PATH"
dotnet new sln -n CCDTrace && \
dotnet sln add src/CCDTrace.Core/CCDTrace.Core.csproj \
               src/CCDTrace.Edge/CCDTrace.Edge.csproj \
               tests/CCDTrace.Tests/CCDTrace.Tests.csproj && \
dotnet build
```

Expected: `Build succeeded.`

- [ ] **Step 4b: 创建一键 setup 脚本（打开即用）**

`setup.bat`:
```bat
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
```

`setup.ps1`:
```powershell
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
```

在 `README.md` 追加「打开即用」说明：
```markdown
## 打开即用（一键启动）
双击 `setup.bat`（或 `setup.ps1`）：自动检测本地 .NET SDK（缺失则下载安装），构建并运行。
```

Expected: `setup.bat` / `setup.ps1` 文件存在。

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "chore: scaffold solution, projects, gitignore"
```

---

### Task 2: Modbus CRC16

**Files:**
- Create: `src/CCDTrace.Core/Modbus/ModbusCrc16.cs`
- Test: `tests/CCDTrace.Tests/ModbusCrc16Tests.cs`

**Interfaces:**
- Produces: `ushort ModbusCrc16.Compute(ReadOnlySpan<byte> data)` — 标准 Modbus CRC16，多项式 0xA001，初值 0xFFFF。

- [ ] **Step 1: 写失败测试**

```csharp
using CCDTrace.Modbus;

namespace CCDTrace.Tests;

public class ModbusCrc16Tests
{
    [Fact]
    public void Compute_KnownVector_MatchesSpec()
    {
        // Modbus 规范示例：0x02 0x07 → CRC 0x1241
        Assert.Equal(0x1241, ModbusCrc16.Compute(new byte[] { 0x02, 0x07 }));
    }

    [Fact]
    public void Compute_ReadHoldingRegisterFrame_MatchesSpec()
    {
        // 0x01 0x03 0x00 0x00 0x00 0x0A → CRC 0xC5CD
        Assert.Equal(0xC5CD, ModbusCrc16.Compute(
            new byte[] { 0x01, 0x03, 0x00, 0x00, 0x00, 0x0A }));
    }

    [Fact]
    public void Compute_Empty_IsZero()
    {
        Assert.Equal(0x0000, ModbusCrc16.Compute(Array.Empty<byte>()));
    }
}
```

- [ ] **Step 2: 运行确认失败**

Run: `dotnet test --filter ModbusCrc16Tests`
Expected: FAIL（`ModbusCrc16` 不存在）

- [ ] **Step 3: 实现**

```csharp
namespace CCDTrace.Modbus;

public static class ModbusCrc16
{
    public static ushort Compute(ReadOnlySpan<byte> data)
    {
        ushort crc = 0xFFFF;
        foreach (var b in data)
        {
            crc ^= b;
            for (var i = 0; i < 8; i++)
            {
                if ((crc & 0x0001) != 0)
                {
                    crc >>= 1;
                    crc ^= 0xA001;
                }
                else
                {
                    crc >>= 1;
                }
            }
        }
        return crc;
    }
}
```

- [ ] **Step 4: 运行确认通过**

Run: `dotnet test --filter ModbusCrc16Tests`
Expected: PASS（3 passed）

- [ ] **Step 5: Commit**

```bash
git add src/CCDTrace.Core/Modbus/ModbusCrc16.cs tests/CCDTrace.Tests/ModbusCrc16Tests.cs
git commit -m "feat: add Modbus CRC16 computation"
```

---

### Task 3: Modbus RTU 帧解析

**Files:**
- Create: `src/CCDTrace.Core/Modbus/ModbusRtuFrame.cs`
- Create: `src/CCDTrace.Core/Modbus/ModbusRtuParser.cs`
- Test: `tests/CCDTrace.Tests/ModbusRtuParserTests.cs`

**Interfaces:**
- Consumes: `ModbusCrc16.Compute`
- Produces:
  - `record ModbusRtuFrame(byte SlaveId, byte FunctionCode, ReadOnlyMemory<byte> Data)`
  - `ModbusRtuFrame? ModbusRtuParser.TryParseFrame(ReadOnlySpan<byte> buf, out int consumed)` — 从缓冲区头部解析一帧；数据不足或 CRC 失败返回 null。
  - `bool ModbusRtuParser.TryParseWriteSingleCoil(ModbusRtuFrame frame, out ushort address, out bool value)` — 解析功能码 0x05。
  - `bool ModbusRtuParser.TryParseReadCoilsResponse(ModbusRtuFrame frame, out ReadOnlySpan<byte> bits)` — 解析功能码 0x01 响应。

- [ ] **Step 1: 写失败测试**

```csharp
using CCDTrace.Modbus;

namespace CCDTrace.Tests;

public class ModbusRtuParserTests
{
    private static byte[] Frame(params byte[] body)
    {
        var crc = ModbusCrc16.Compute(body);
        return body.Concat(new byte[] { (byte)(crc & 0xFF), (byte)(crc >> 8) }).ToArray();
    }

    [Fact]
    public void TryParseFrame_WriteSingleCoil_ExtractsAddressAndValue()
    {
        var buf = Frame(0x01, 0x05, 0x00, 0x00, 0xFF, 0x00);

        var frame = ModbusRtuParser.TryParseFrame(buf, out var consumed);

        Assert.NotNull(frame);
        Assert.Equal(buf.Length, consumed);
        Assert.Equal(0x01, frame!.SlaveId);
        Assert.Equal(0x05, frame.FunctionCode);
        Assert.True(ModbusRtuParser.TryParseWriteSingleCoil(frame, out var addr, out var val));
        Assert.Equal((ushort)0, addr);
        Assert.True(val);
    }

    [Fact]
    public void TryParseFrame_WriteSingleCoilOff_SetsValueFalse()
    {
        var buf = Frame(0x01, 0x05, 0x00, 0x02, 0x00, 0x00);

        var frame = ModbusRtuParser.TryParseFrame(buf, out _);

        Assert.NotNull(frame);
        Assert.True(ModbusRtuParser.TryParseWriteSingleCoil(frame!, out _, out var val));
        Assert.False(val);
    }

    [Fact]
    public void TryParseFrame_ReadCoilsResponse_ExtractsBits()
    {
        var buf = Frame(0x01, 0x01, 0x01, 0x03);

        var frame = ModbusRtuParser.TryParseFrame(buf, out _);

        Assert.NotNull(frame);
        Assert.True(ModbusRtuParser.TryParseReadCoilsResponse(frame!, out var bits));
        Assert.Equal(new byte[] { 0x03 }, bits.ToArray());
    }

    [Fact]
    public void TryParseFrame_CorruptedCrc_ReturnsNull()
    {
        var buf = Frame(0x01, 0x05, 0x00, 0x00, 0xFF, 0x00);
        buf[^1] ^= 0xFF; // 破坏最后一个 CRC 字节

        var frame = ModbusRtuParser.TryParseFrame(buf, out _);

        Assert.Null(frame);
    }

    [Fact]
    public void TryParseFrame_IncompleteBuffer_ReturnsNull()
    {
        var full = Frame(0x01, 0x05, 0x00, 0x00, 0xFF, 0x00);
        var partial = full[..^2]; // 去掉 CRC

        Assert.Null(ModbusRtuParser.TryParseFrame(partial, out _));
    }
}
```

- [ ] **Step 2: 运行确认失败**

Run: `dotnet test --filter ModbusRtuParserTests`
Expected: FAIL

- [ ] **Step 3: 实现帧类型与解析器**

`ModbusRtuFrame.cs`:
```csharp
namespace CCDTrace.Modbus;

public sealed record ModbusRtuFrame(byte SlaveId, byte FunctionCode, ReadOnlyMemory<byte> Data);
```

`ModbusRtuParser.cs`:
```csharp
namespace CCDTrace.Modbus;

public static class ModbusRtuParser
{
    public static ModbusRtuFrame? TryParseFrame(ReadOnlySpan<byte> buf, out int consumed)
    {
        consumed = 0;
        if (buf.Length < 4) return null;

        var slave = buf[0];
        var func = buf[1];
        var len = ExpectedLength(func, buf);
        if (len < 0 || buf.Length < len) return null;

        var crcExpected = (ushort)(buf[len - 2] | (buf[len - 1] << 8));
        var crcActual = ModbusCrc16.Compute(buf[..(len - 2)]);
        if (crcExpected != crcActual) return null;

        consumed = len;
        return new ModbusRtuFrame(slave, func, buf[2..(len - 2)].ToArray());
    }

    private static int ExpectedLength(byte func, ReadOnlySpan<byte> buf)
    {
        // 请求帧固定长度；带字节计数的帧(0x0F/0x10/读响应)按第7字节扩展
        return func switch
        {
            0x05 or 0x06 => 8,
            0x0F or 0x10 => buf.Length >= 7 ? 9 + buf[6] : -1,
            >= 0x01 and <= 0x04 => buf.Length >= 3 && LooksLikeReadResponse(buf) ? 5 + buf[2] : 8,
            _ => -1,
        };
    }

    private static bool LooksLikeReadResponse(ReadOnlySpan<byte> buf)
    {
        // 请求帧第3字节是起始地址高字节(通常为0)，响应帧第3字节是字节计数(通常≤8)
        return buf.Length >= 3 && buf[2] is >= 1 and <= 8 && buf[1] is >= 0x01 and <= 0x04;
    }

    public static bool TryParseWriteSingleCoil(ModbusRtuFrame frame, out ushort address, out bool value)
    {
        address = 0; value = false;
        if (frame.FunctionCode != 0x05 || frame.Data.Length < 4) return false;
        address = (ushort)((frame.Data.Span[0] << 8) | frame.Data.Span[1]);
        value = frame.Data.Span[2] == 0xFF && frame.Data.Span[3] == 0x00;
        return true;
    }

    public static bool TryParseReadCoilsResponse(ModbusRtuFrame frame, out ReadOnlySpan<byte> bits)
    {
        bits = default;
        if (frame.FunctionCode != 0x01 || frame.Data.Length < 1) return false;
        var count = frame.Data.Span[0];
        if (frame.Data.Length < 1 + count) return false;
        bits = frame.Data.Span.Slice(1, count);
        return true;
    }
}
```

> 说明：`LooksLikeReadResponse` 是启发式，用于区分功能码 01–04 的请求(8字节)与响应(变长)。地址表与线圈语义属配置，不在解析器内写死。

- [ ] **Step 4: 运行确认通过**

Run: `dotnet test --filter ModbusRtuParserTests`
Expected: PASS（5 passed）

- [ ] **Step 5: Commit**

```bash
git add src/CCDTrace.Core/Modbus/ModbusRtuFrame.cs src/CCDTrace.Core/Modbus/ModbusRtuParser.cs tests/CCDTrace.Tests/ModbusRtuParserTests.cs
git commit -m "feat: add Modbus RTU frame parser"
```

---

### Task 4: 事件模型 + 结果解释器

**Files:**
- Create: `src/CCDTrace.Core/Events/InspectionResult.cs`
- Create: `src/CCDTrace.Core/Events/ResultEvent.cs`
- Create: `src/CCDTrace.Core/Events/ScannerEvent.cs`
- Create: `src/CCDTrace.Core/Config/AppConfig.cs`
- Create: `src/CCDTrace.Core/Modbus/ResultInterpreter.cs`
- Test: `tests/CCDTrace.Tests/ResultInterpreterTests.cs`

**Interfaces:**
- Consumes: `ModbusRtuFrame`, `ModbusRtuParser.TryParseWriteSingleCoil`, `TryParseReadCoilsResponse`
- Produces:
  - `enum InspectionResult { OK, NG }`
  - `record ResultEvent(InspectionResult Result, DateTimeOffset Timestamp, int Station = 0)`
  - `record ScannerEvent(string QrCode, DateTimeOffset Timestamp)`
  - `AppConfig` 及其嵌套 `ScannerConfig`、`SnifferConfig`、`CorrelationConfig`（见下）
  - `ResultInterpreter(SnifferConfig cfg)`，方法 `InspectionResult? TryGetResult(ModbusRtuFrame f)`、`bool IsSensorTrigger(ModbusRtuFrame f)`

- [ ] **Step 1: 写事件模型与配置类型**

`Events/InspectionResult.cs`:
```csharp
namespace CCDTrace.Events;

public enum InspectionResult { OK, NG }
```

`Events/ResultEvent.cs`:
```csharp
namespace CCDTrace.Events;

public sealed record ResultEvent(InspectionResult Result, DateTimeOffset Timestamp, int Station = 0);
```

`Events/ScannerEvent.cs`:
```csharp
namespace CCDTrace.Events;

public sealed record ScannerEvent(string QrCode, DateTimeOffset Timestamp);
```

`Config/AppConfig.cs`:
```csharp
namespace CCDTrace.Config;

public sealed class ScannerConfig
{
    public string Port { get; set; } = "COM4";
    public int BaudRate { get; set; } = 9600;
}

public sealed class SnifferConfig
{
    public string Port { get; set; } = "COM5";
    public int BaudRate { get; set; } = 9600;
    public byte SlaveId { get; set; } = 1;
    public ushort ValveCoilAddress { get; set; } = 0;
    public ushort SensorCoilAddress { get; set; } = 1;
}

public sealed class CorrelationConfig
{
    public int MaxQueueLength { get; set; } = 32;
}

public sealed class AppConfig
{
    public string MachineId { get; set; } = "MACHINE-001";
    public string ProductionSite { get; set; } = "某工厂·1号产线";
    public ScannerConfig Scanner { get; set; } = new();
    public SnifferConfig Sniffer { get; set; } = new();
    public CorrelationConfig Correlation { get; set; } = new();
    public string LocalDbPath { get; set; } = "trace.db";
    public string? CloudConnectionString { get; set; }
    public int StationCount { get; set; } = 4;
}
```

- [ ] **Step 2: 写失败测试（结果解释器）**

```csharp
using CCDTrace.Config;
using CCDTrace.Events;
using CCDTrace.Modbus;

namespace CCDTrace.Tests;

public class ResultInterpreterTests
{
    private static ModbusRtuFrame CoilWrite(byte slave, ushort addr, bool value)
        => new(slave, 0x05, new byte[]
        {
            (byte)(addr >> 8), (byte)(addr & 0xFF),
            value ? (byte)0xFF : (byte)0x00, 0x00,
        });

    [Fact]
    public void TryGetResult_ValveCoilOn_ReturnsNG()
    {
        var cfg = new SnifferConfig { SlaveId = 1, ValveCoilAddress = 5, SensorCoilAddress = 6 };
        var it = new ResultInterpreter(cfg);

        Assert.Equal(InspectionResult.NG, it.TryGetResult(CoilWrite(1, 5, true)));
    }

    [Fact]
    public void TryGetResult_WrongSlave_ReturnsNull()
    {
        var cfg = new SnifferConfig { SlaveId = 1, ValveCoilAddress = 5 };
        var it = new ResultInterpreter(cfg);

        Assert.Null(it.TryGetResult(CoilWrite(2, 5, true)));
    }

    [Fact]
    public void TryGetResult_NonValveCoil_ReturnsNull()
    {
        var cfg = new SnifferConfig { SlaveId = 1, ValveCoilAddress = 5, SensorCoilAddress = 6 };
        var it = new ResultInterpreter(cfg);

        Assert.Null(it.TryGetResult(CoilWrite(1, 6, true)));
    }

    [Fact]
    public void IsSensorTrigger_MatchesConfiguredCoil()
    {
        var cfg = new SnifferConfig { SlaveId = 1, ValveCoilAddress = 5, SensorCoilAddress = 6 };
        var it = new ResultInterpreter(cfg);

        Assert.True(it.IsSensorTrigger(CoilWrite(1, 6, true)));
        Assert.False(it.IsSensorTrigger(CoilWrite(1, 5, true)));
    }
}
```

- [ ] **Step 3: 运行确认失败**

Run: `dotnet test --filter ResultInterpreterTests`
Expected: FAIL（`ResultInterpreter` 不存在）

- [ ] **Step 4: 实现结果解释器**

```csharp
using CCDTrace.Config;
using CCDTrace.Events;

namespace CCDTrace.Modbus;

public sealed class ResultInterpreter
{
    private readonly byte _slaveId;
    private readonly ushort _valveCoil;
    private readonly ushort _sensorCoil;

    public ResultInterpreter(SnifferConfig cfg)
    {
        _slaveId = cfg.SlaveId;
        _valveCoil = cfg.ValveCoilAddress;
        _sensorCoil = cfg.SensorCoilAddress;
    }

    public InspectionResult? TryGetResult(ModbusRtuFrame frame)
    {
        if (frame.SlaveId != _slaveId) return null;
        if (!ModbusRtuParser.TryParseWriteSingleCoil(frame, out var addr, out var value)) return null;
        if (addr != _valveCoil) return null;
        return value ? InspectionResult.NG : InspectionResult.OK;
    }

    public bool IsSensorTrigger(ModbusRtuFrame frame)
    {
        if (frame.SlaveId != _slaveId) return false;
        if (!ModbusRtuParser.TryParseWriteSingleCoil(frame, out var addr, out _)) return false;
        return addr == _sensorCoil;
    }
}
```

- [ ] **Step 5: 运行确认通过**

Run: `dotnet test --filter ResultInterpreterTests`
Expected: PASS（4 passed）

- [ ] **Step 6: Commit**

```bash
git add src/CCDTrace.Core/Events src/CCDTrace.Core/Config/AppConfig.cs src/CCDTrace.Core/Modbus/ResultInterpreter.cs tests/CCDTrace.Tests/ResultInterpreterTests.cs
git commit -m "feat: add event models, config, result interpreter"
```

---

### Task 5: 时序绑定队列

**Files:**
- Create: `src/CCDTrace.Core/Correlation/CorrelationQueue.cs`
- Create: `src/CCDTrace.Core/Models/TraceRecord.cs`
- Test: `tests/CCDTrace.Tests/CorrelationQueueTests.cs`

**Interfaces:**
- Consumes: `ResultEvent`, `ScannerEvent`, `InspectionResult`, `AppConfig`/`CorrelationConfig`
- Produces:
  - `record TraceRecord(string QrCode, InspectionResult Result, DateTimeOffset InspectTime, int Station, string ProductionSite, string Model, string MachineId)`
  - `class CorrelationQueue`：`void EnqueueResult(ResultEvent e)`、`TraceRecord EnqueueScanner(ScannerEvent e, Func<string, TraceRecord> fallback)`、`int ResultBacklog`、`int QrBacklog`

- [ ] **Step 1: 写失败测试**

```csharp
using CCDTrace.Correlation;
using CCDTrace.Events;
using CCDTrace.Models;

namespace CCDTrace.Tests;

public class CorrelationQueueTests
{
    private static TraceRecord MakeRecord(string qr)
        => new(qr, InspectionResult.NG, DateTimeOffset.UtcNow, 0, "SITE", "M1", "MC-1");

    [Fact]
    public void EnqueueScanner_AfterResult_BindsInOrder()
    {
        var q = new CorrelationQueue(4);
        q.EnqueueResult(new ResultEvent(InspectionResult.OK, DateTimeOffset.UtcNow));
        q.EnqueueResult(new ResultEvent(InspectionResult.NG, DateTimeOffset.UtcNow));

        var first = q.EnqueueScanner(new ScannerEvent("QR-A", DateTimeOffset.UtcNow), MakeRecord);
        var second = q.EnqueueScanner(new ScannerEvent("QR-B", DateTimeOffset.UtcNow), MakeRecord);

        Assert.Equal(InspectionResult.OK, first.Result);
        Assert.Equal("QR-A", first.QrCode);
        Assert.Equal(InspectionResult.NG, second.Result);
        Assert.Equal("QR-B", second.QrCode);
    }

    [Fact]
    public void EnqueueScanner_NoResult_UsesFallbackDefault()
    {
        var q = new CorrelationQueue(4);

        var rec = q.EnqueueScanner(new ScannerEvent("QR-X", DateTimeOffset.UtcNow), MakeRecord);

        Assert.Equal("QR-X", rec.QrCode);
        Assert.Equal(InspectionResult.NG, rec.Result); // 结果缺失时保持 fallback 默认值
    }

    [Fact]
    public void EnqueueResult_Overflow_DropsOldest()
    {
        var q = new CorrelationQueue(2);
        q.EnqueueResult(new ResultEvent(InspectionResult.OK, DateTimeOffset.UtcNow));
        q.EnqueueResult(new ResultEvent(InspectionResult.OK, DateTimeOffset.UtcNow));
        q.EnqueueResult(new ResultEvent(InspectionResult.NG, DateTimeOffset.UtcNow)); // 溢出，挤掉最早的 OK

        var rec = q.EnqueueScanner(new ScannerEvent("QR-1", DateTimeOffset.UtcNow), MakeRecord);

        Assert.Equal(InspectionResult.OK, rec.Result); // 队首是第二个 OK
        Assert.Equal(1, q.ResultBacklog);
    }
}
```

- [ ] **Step 2: 运行确认失败**

Run: `dotnet test --filter CorrelationQueueTests`
Expected: FAIL

- [ ] **Step 3: 实现**

`Models/TraceRecord.cs`:
```csharp
using CCDTrace.Events;

namespace CCDTrace.Models;

public sealed record TraceRecord(
    string QrCode,
    InspectionResult Result,
    DateTimeOffset InspectTime,
    int Station,
    string ProductionSite,
    string Model,
    string MachineId);
```

`Correlation/CorrelationQueue.cs`:
```csharp
using CCDTrace.Events;
using CCDTrace.Models;

namespace CCDTrace.Correlation;

public sealed class CorrelationQueue
{
    private readonly int _max;
    private readonly Queue<ResultEvent> _results = new();

    public CorrelationQueue(int maxQueueLength) => _max = maxQueueLength;

    public int ResultBacklog => _results.Count;
    public int QrBacklog { get; private set; }

    public void EnqueueResult(ResultEvent e)
    {
        _results.Enqueue(e);
        while (_results.Count > _max) _results.Dequeue();
    }

    public TraceRecord EnqueueScanner(ScannerEvent e, Func<string, TraceRecord> fallback)
    {
        if (_results.TryDequeue(out var result))
        {
            return fallback(e.QrCode) with
            {
                Result = result.Result,
                InspectTime = result.Timestamp,
                Station = result.Station,
            };
        }

        QrBacklog++;
        return fallback(e.QrCode); // 结果缺失，保持 fallback 默认（调用方约定 NG=待复核）
    }
}
```

> 说明：`fallback` 由调用方提供，用于从运行时上下文（生产地/型号/设备号）构造 `TraceRecord` 模板；绑定成功时仅覆盖 QR/结果/时间/工位。未绑定（结果缺失）时退回 fallback 记录并令 `Result` 保持 fallback 默认值（调用方可用 `Result=NG` 之类标记“待复核”）。

- [ ] **Step 4: 运行确认通过**

Run: `dotnet test --filter CorrelationQueueTests`
Expected: PASS（3 passed）

- [ ] **Step 5: Commit**

```bash
git add src/CCDTrace.Core/Correlation/CorrelationQueue.cs src/CCDTrace.Core/Models/TraceRecord.cs tests/CCDTrace.Tests/CorrelationQueueTests.cs
git commit -m "feat: add correlation queue for QR-result binding"
```

---

### Task 6: 汇总计算器

**Files:**
- Create: `src/CCDTrace.Core/Summary/SummaryCalculator.cs`
- Create: `src/CCDTrace.Core/Models/SummaryStats.cs`
- Test: `tests/CCDTrace.Tests/SummaryCalculatorTests.cs`

**Interfaces:**
- Produces: `record SummaryStats(int TotalCount, int OkCount, int NgCount, double OkRatePercent)`；`class SummaryCalculator`：`void Add(InspectionResult r)`、`SummaryStats Snapshot()`、`void Reset()`

- [ ] **Step 1: 写失败测试**

```csharp
using CCDTrace.Events;
using CCDTrace.Summary;

namespace CCDTrace.Tests;

public class SummaryCalculatorTests
{
    [Fact]
    public void Add_MixedResults_ComputesStats()
    {
        var c = new SummaryCalculator();
        c.Add(InspectionResult.OK);
        c.Add(InspectionResult.NG);
        c.Add(InspectionResult.OK);

        var s = c.Snapshot();

        Assert.Equal(3, s.TotalCount);
        Assert.Equal(2, s.OkCount);
        Assert.Equal(1, s.NgCount);
        Assert.Equal(66.67, s.OkRatePercent, 2);
    }

    [Fact]
    public void Snapshot_Empty_IsZero()
    {
        var s = new SummaryCalculator().Snapshot();

        Assert.Equal(0, s.TotalCount);
        Assert.Equal(0.0, s.OkRatePercent);
    }

    [Fact]
    public void Reset_ClearsCounts()
    {
        var c = new SummaryCalculator();
        c.Add(InspectionResult.OK);
        c.Reset();

        Assert.Equal(0, c.Snapshot().TotalCount);
    }
}
```

- [ ] **Step 2: 运行确认失败**

Run: `dotnet test --filter SummaryCalculatorTests`
Expected: FAIL

- [ ] **Step 3: 实现**

`Models/SummaryStats.cs`:
```csharp
namespace CCDTrace.Models;

public sealed record SummaryStats(int TotalCount, int OkCount, int NgCount, double OkRatePercent);
```

`Summary/SummaryCalculator.cs`:
```csharp
using CCDTrace.Events;
using CCDTrace.Models;

namespace CCDTrace.Summary;

public sealed class SummaryCalculator
{
    private int _total;
    private int _ok;

    public void Add(InspectionResult r)
    {
        _total++;
        if (r == InspectionResult.OK) _ok++;
    }

    public SummaryStats Snapshot()
    {
        var rate = _total == 0 ? 0.0 : _ok * 100.0 / _total;
        return new SummaryStats(_total, _ok, _total - _ok, Math.Round(rate, 2));
    }

    public void Reset() { _total = 0; _ok = 0; }
}
```

- [ ] **Step 4: 运行确认通过**

Run: `dotnet test --filter SummaryCalculatorTests`
Expected: PASS（3 passed）

- [ ] **Step 5: Commit**

```bash
git add src/CCDTrace.Core/Summary/SummaryCalculator.cs src/CCDTrace.Core/Models/SummaryStats.cs tests/CCDTrace.Tests/SummaryCalculatorTests.cs
git commit -m "feat: add summary calculator"
```

---

### Task 7: 配置加载

**Files:**
- Create: `src/CCDTrace.Core/Config/AppConfigLoader.cs`
- Test: `tests/CCDTrace.Tests/AppConfigLoaderTests.cs`

**Interfaces:**
- Consumes: `AppConfig`
- Produces: `static AppConfig AppConfigLoader.Load(string path)` — 读取 JSON，缺失字段用默认值；文件不存在抛 `FileNotFoundException`。

- [ ] **Step 1: 写失败测试**

```csharp
using System.Text.Json;
using CCDTrace.Config;

namespace CCDTrace.Tests;

public class AppConfigLoaderTests
{
    [Fact]
    public void Load_ValidJson_ParsesFields()
    {
        var path = Path.GetTempFileName();
        var json = JsonSerializer.Serialize(new AppConfig
        {
            MachineId = "MC-9",
            ProductionSite = "苏州工厂",
            Sniffer = new SnifferConfig { Port = "COM7", ValveCoilAddress = 12 }
        });
        File.WriteAllText(path, json);

        var cfg = AppConfigLoader.Load(path);

        Assert.Equal("MC-9", cfg.MachineId);
        Assert.Equal("苏州工厂", cfg.ProductionSite);
        Assert.Equal("COM7", cfg.Sniffer.Port);
        Assert.Equal((ushort)12, cfg.Sniffer.ValveCoilAddress);

        File.Delete(path);
    }

    [Fact]
    public void Load_MissingFile_Throws()
    {
        Assert.Throws<FileNotFoundException>(() => AppConfigLoader.Load("no-such-file.json"));
    }
}
```

- [ ] **Step 2: 运行确认失败**

Run: `dotnet test --filter AppConfigLoaderTests`
Expected: FAIL

- [ ] **Step 3: 实现**

```csharp
using System.Text.Json;

namespace CCDTrace.Config;

public static class AppConfigLoader
{
    private static readonly JsonSerializerOptions Options = new() { PropertyNameCaseInsensitive = true };

    public static AppConfig Load(string path)
    {
        if (!File.Exists(path)) throw new FileNotFoundException("配置文件不存在", path);
        var json = File.ReadAllText(path);
        return JsonSerializer.Deserialize<AppConfig>(json, Options) ?? new AppConfig();
    }
}
```

- [ ] **Step 4: 运行确认通过**

Run: `dotnet test --filter AppConfigLoaderTests`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git add src/CCDTrace.Core/Config/AppConfigLoader.cs tests/CCDTrace.Tests/AppConfigLoaderTests.cs
git commit -m "feat: add config loader"
```

---

### Task 8: 本地 SQLite 存储

**Files:**
- Create: `src/CCDTrace.Core/Storage/ITraceStore.cs`
- Create: `src/CCDTrace.Core/Storage/SqliteTraceStore.cs`
- Test: `tests/CCDTrace.Tests/SqliteTraceStoreTests.cs`
- Modify: `src/CCDTrace.Core/CCDTrace.Core.csproj`（加 `Microsoft.Data.Sqlite` 引用）

**Interfaces:**
- Consumes: `TraceRecord`
- Produces:
  - `interface ITraceStore { void Init(); void Upsert(TraceRecord r); IReadOnlyList<TraceRecord> GetUnsynced(int limit = 100); void MarkSynced(string qrCode); }`
  - `SqliteTraceStore(string connectionString)`

- [ ] **Step 1: 加包引用**

在 `CCDTrace.Core.csproj` 加：
```xml
<ItemGroup>
  <PackageReference Include="Microsoft.Data.Sqlite" Version="8.0.11" />
</ItemGroup>
```

- [ ] **Step 2: 写失败测试**

```csharp
using CCDTrace.Events;
using CCDTrace.Models;
using CCDTrace.Storage;

namespace CCDTrace.Tests;

public class SqliteTraceStoreTests
{
    private static TraceRecord Rec(string qr)
        => new(qr, InspectionResult.OK, DateTimeOffset.UtcNow, 0, "SITE", "M1", "MC-1");

    [Fact]
    public void Upsert_ThenGetUnsynced_ReturnsRecord()
    {
        using var store = new SqliteTraceStore("Data Source=:memory:");
        store.Init();
        store.Upsert(Rec("QR-1"));

        var unsynced = store.GetUnsynced();

        Assert.Single(unsynced);
        Assert.Equal("QR-1", unsynced[0].QrCode);
    }

    [Fact]
    public void MarkSynced_RemovesFromUnsynced()
    {
        using var store = new SqliteTraceStore("Data Source=:memory:");
        store.Init();
        store.Upsert(Rec("QR-1"));
        store.MarkSynced("QR-1");

        Assert.Empty(store.GetUnsynced());
    }

    [Fact]
    public void Upsert_SameQrTwice_KeepsSingleRow()
    {
        using var store = new SqliteTraceStore("Data Source=:memory:");
        store.Init();
        store.Upsert(Rec("QR-1"));
        store.Upsert(Rec("QR-1"));

        Assert.Single(store.GetUnsynced());
    }
}
```

- [ ] **Step 3: 运行确认失败**

Run: `dotnet test --filter SqliteTraceStoreTests`
Expected: FAIL

- [ ] **Step 4: 实现**

`Storage/ITraceStore.cs`:
```csharp
using CCDTrace.Models;

namespace CCDTrace.Storage;

public interface ITraceStore
{
    void Init();
    void Upsert(TraceRecord r);
    IReadOnlyList<TraceRecord> GetUnsynced(int limit = 100);
    void MarkSynced(string qrCode);
}
```

`Storage/SqliteTraceStore.cs`:
```csharp
using CCDTrace.Events;
using CCDTrace.Models;
using Microsoft.Data.Sqlite;

namespace CCDTrace.Storage;

public sealed class SqliteTraceStore : ITraceStore, IDisposable
{
    private readonly SqliteConnection _conn;

    public SqliteTraceStore(string connectionString) => _conn = new SqliteConnection(connectionString);

    public void Init()
    {
        _conn.Open();
        using var cmd = _conn.CreateCommand();
        cmd.CommandText = """
            CREATE TABLE IF NOT EXISTS trace_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                qr_code TEXT UNIQUE NOT NULL,
                result TEXT NOT NULL,
                inspect_time TEXT NOT NULL,
                station INTEGER NOT NULL,
                production_site TEXT NOT NULL,
                model TEXT NOT NULL,
                machine_id TEXT NOT NULL,
                synced INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """;
        cmd.ExecuteNonQuery();
    }

    public void Upsert(TraceRecord r)
    {
        using var cmd = _conn.CreateCommand();
        cmd.CommandText = """
            INSERT INTO trace_records
                (qr_code, result, inspect_time, station, production_site, model, machine_id, synced, created_at)
            VALUES
                ($qr, $result, $time, $station, $site, $model, $machine, 0, $created)
            ON CONFLICT(qr_code) DO UPDATE SET
                result = excluded.result,
                inspect_time = excluded.inspect_time;
            """;
        cmd.Parameters.AddWithValue("$qr", r.QrCode);
        cmd.Parameters.AddWithValue("$result", r.Result == InspectionResult.OK ? "OK" : "NG");
        cmd.Parameters.AddWithValue("$time", r.InspectTime.ToString("O"));
        cmd.Parameters.AddWithValue("$station", r.Station);
        cmd.Parameters.AddWithValue("$site", r.ProductionSite);
        cmd.Parameters.AddWithValue("$model", r.Model);
        cmd.Parameters.AddWithValue("$machine", r.MachineId);
        cmd.Parameters.AddWithValue("$created", DateTimeOffset.UtcNow.ToString("O"));
        cmd.ExecuteNonQuery();
    }

    public IReadOnlyList<TraceRecord> GetUnsynced(int limit = 100)
    {
        var list = new List<TraceRecord>();
        using var cmd = _conn.CreateCommand();
        cmd.CommandText = limit > 0
            ? "SELECT qr_code, result, inspect_time, station, production_site, model, machine_id FROM trace_records WHERE synced = 0 ORDER BY id LIMIT $limit;"
            : "SELECT qr_code, result, inspect_time, station, production_site, model, machine_id FROM trace_records WHERE synced = 0 ORDER BY id;";
        if (limit > 0) cmd.Parameters.AddWithValue("$limit", limit);
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            list.Add(new TraceRecord(
                reader.GetString(0),
                reader.GetString(1) == "OK" ? InspectionResult.OK : InspectionResult.NG,
                DateTimeOffset.Parse(reader.GetString(2)),
                reader.GetInt32(3),
                reader.GetString(4),
                reader.GetString(5),
                reader.GetString(6)));
        }
        return list;
    }

    public void MarkSynced(string qrCode)
    {
        using var cmd = _conn.CreateCommand();
        cmd.CommandText = "UPDATE trace_records SET synced = 1 WHERE qr_code = $qr;";
        cmd.Parameters.AddWithValue("$qr", qrCode);
        cmd.ExecuteNonQuery();
    }

    public void Dispose() => _conn.Dispose();
}
```

- [ ] **Step 5: 运行确认通过**

Run: `dotnet test --filter SqliteTraceStoreTests`
Expected: PASS（3 passed）

- [ ] **Step 6: Commit**

```bash
git add src/CCDTrace.Core/Storage/ITraceStore.cs src/CCDTrace.Core/Storage/SqliteTraceStore.cs src/CCDTrace.Core/CCDTrace.Core.csproj tests/CCDTrace.Tests/SqliteTraceStoreTests.cs
git commit -m "feat: add SQLite local trace store"
```

---

### Task 9: 云同步服务

**Files:**
- Create: `src/CCDTrace.Core/Storage/ICloudStore.cs`
- Create: `src/CCDTrace.Core/Storage/MySqlCloudStore.cs`
- Create: `src/CCDTrace.Core/Sync/CloudSyncService.cs`
- Test: `tests/CCDTrace.Tests/CloudSyncServiceTests.cs`
- Test: `tests/CCDTrace.Tests/FakeCloudStore.cs`

**Interfaces:**
- Consumes: `ITraceStore`, `TraceRecord`
- Produces:
  - `interface ICloudStore { Task<bool> PushAsync(TraceRecord r); }`（幂等：云端按 `qr_code` 去重，重复返回 true）
  - `class CloudSyncService(ITraceStore local, ICloudStore cloud)`：`Task<int> RunOnceAsync(int batchSize = 100)` — 拉取未同步记录逐条推，成功则 `MarkSynced`，返回成功条数。

- [ ] **Step 1: 写 Fake 与失败测试**

`FakeCloudStore.cs`:
```csharp
using CCDTrace.Models;
using CCDTrace.Storage;

namespace CCDTrace.Tests;

public sealed class FakeCloudStore : ICloudStore
{
    public List<TraceRecord> Pushed { get; } = new();
    public bool ShouldFail { get; set; }

    public Task<bool> PushAsync(TraceRecord r)
    {
        if (ShouldFail) return Task.FromResult(false);
        Pushed.Add(r);
        return Task.FromResult(true);
    }
}
```

`CloudSyncServiceTests.cs`:
```csharp
using CCDTrace.Events;
using CCDTrace.Models;
using CCDTrace.Storage;
using CCDTrace.Sync;

namespace CCDTrace.Tests;

public class CloudSyncServiceTests
{
    private static TraceRecord Rec(string qr)
        => new(qr, InspectionResult.OK, DateTimeOffset.UtcNow, 0, "SITE", "M1", "MC-1");

    [Fact]
    public async Task RunOnce_PushesUnsyncedAndMarksSynced()
    {
        using var local = new SqliteTraceStore("Data Source=:memory:");
        local.Init();
        local.Upsert(Rec("QR-1"));
        local.Upsert(Rec("QR-2"));
        var cloud = new FakeCloudStore();
        var sync = new CloudSyncService(local, cloud);

        var pushed = await sync.RunOnceAsync();

        Assert.Equal(2, pushed);
        Assert.Equal(2, cloud.Pushed.Count);
        Assert.Empty(local.GetUnsynced());
    }

    [Fact]
    public async Task RunOnce_CloudFails_LeavesRecordsUnsynced()
    {
        using var local = new SqliteTraceStore("Data Source=:memory:");
        local.Init();
        local.Upsert(Rec("QR-1"));
        var cloud = new FakeCloudStore { ShouldFail = true };
        var sync = new CloudSyncService(local, cloud);

        var pushed = await sync.RunOnceAsync();

        Assert.Equal(0, pushed);
        Assert.Single(local.GetUnsynced());
    }
}
```

- [ ] **Step 2: 运行确认失败**

Run: `dotnet test --filter CloudSyncServiceTests`
Expected: FAIL

- [ ] **Step 3: 实现接口与同步服务**

`Storage/ICloudStore.cs`:
```csharp
using CCDTrace.Models;

namespace CCDTrace.Storage;

public interface ICloudStore
{
    Task<bool> PushAsync(TraceRecord r);
}
```

`Sync/CloudSyncService.cs`:
```csharp
using CCDTrace.Storage;

namespace CCDTrace.Sync;

public sealed class CloudSyncService
{
    private readonly ITraceStore _local;
    private readonly ICloudStore _cloud;

    public CloudSyncService(ITraceStore local, ICloudStore cloud)
    {
        _local = local;
        _cloud = cloud;
    }

    public async Task<int> RunOnceAsync(int batchSize = 100)
    {
        var pending = _local.GetUnsynced(batchSize);
        var pushed = 0;
        foreach (var rec in pending)
        {
            if (await _cloud.PushAsync(rec))
            {
                _local.MarkSynced(rec.QrCode);
                pushed++;
            }
        }
        return pushed;
    }
}
```

`Storage/MySqlCloudStore.cs`（真实实现，无单测，仅编译通过）:
```csharp
using CCDTrace.Events;
using CCDTrace.Models;
using MySqlConnector;

namespace CCDTrace.Storage;

public sealed class MySqlCloudStore : ICloudStore
{
    private readonly string _connStr;

    public MySqlCloudStore(string connectionString) => _connStr = connectionString;

    public async Task<bool> PushAsync(TraceRecord r)
    {
        try
        {
            await using var conn = new MySqlConnection(_connStr);
            await conn.OpenAsync();
            await using var cmd = conn.CreateCommand();
            cmd.CommandText = """
                INSERT INTO trace_records
                    (machine_id, qr_code, result, inspect_time, station, production_site, model)
                VALUES
                    (@machine, @qr, @result, @time, @station, @site, @model)
                ON DUPLICATE KEY UPDATE result = VALUES(result);
                """;
            cmd.Parameters.AddWithValue("@machine", r.MachineId);
            cmd.Parameters.AddWithValue("@qr", r.QrCode);
            cmd.Parameters.AddWithValue("@result", r.Result == InspectionResult.OK ? "OK" : "NG");
            cmd.Parameters.AddWithValue("@time", r.InspectTime.UtcDateTime);
            cmd.Parameters.AddWithValue("@station", r.Station);
            cmd.Parameters.AddWithValue("@site", r.ProductionSite);
            cmd.Parameters.AddWithValue("@model", r.Model);
            await cmd.ExecuteNonQueryAsync();
            return true;
        }
        catch
        {
            return false;
        }
    }
}
```

在 `CCDTrace.Core.csproj` 加：`<PackageReference Include="MySqlConnector" Version="2.4.0" />`

- [ ] **Step 4: 运行确认通过**

Run: `dotnet test --filter CloudSyncServiceTests`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git add src/CCDTrace.Core/Storage/ICloudStore.cs src/CCDTrace.Core/Storage/MySqlCloudStore.cs src/CCDTrace.Core/Sync/CloudSyncService.cs src/CCDTrace.Core/CCDTrace.Core.csproj tests/CCDTrace.Tests/CloudSyncServiceTests.cs tests/CCDTrace.Tests/FakeCloudStore.cs
git commit -m "feat: add cloud sync service"
```

---

### Task 10: 串口抽象 + 旁听器 + 扫码读取器

**Files:**
- Create: `src/CCDTrace.Core/Serial/ISerialPort.cs`
- Create: `src/CCDTrace.Core/Serial/SystemSerialPort.cs`
- Create: `src/CCDTrace.Core/Modbus/ModbusSniffer.cs`
- Create: `src/CCDTrace.Core/Scanning/ScannerReader.cs`
- Test: `tests/CCDTrace.Tests/FakeSerialPort.cs`
- Test: `tests/CCDTrace.Tests/ModbusSnifferTests.cs`
- Test: `tests/CCDTrace.Tests/ScannerReaderTests.cs`

**Interfaces:**
- Consumes: `ModbusRtuParser`, `ResultInterpreter`, `ISerialPort`
- Produces:
  - `interface ISerialPort { void Open(); void Close(); event Action<byte[]> DataReceived; }`
  - `class ModbusSniffer(ISerialPort port, ResultInterpreter interpreter)`：`event Action<ResultEvent> ResultReceived;`、`void Start()`（`OnData` 同步解析，无 timer）
  - `class ScannerReader(ISerialPort port)`：`event Action<ScannerEvent> QrReceived;`、`void Start()`

- [ ] **Step 1: 写 Fake 与失败测试**

`FakeSerialPort.cs`:
```csharp
using CCDTrace.Serial;

namespace CCDTrace.Tests;

public sealed class FakeSerialPort : ISerialPort
{
    public void Open() { }
    public void Close() { }
    public event Action<byte[]>? DataReceived;
    public void Emit(byte[] data) => DataReceived?.Invoke(data);
}
```

`ModbusSnifferTests.cs`:
```csharp
using CCDTrace.Config;
using CCDTrace.Events;
using CCDTrace.Modbus;
using CCDTrace.Serial;

namespace CCDTrace.Tests;

public class ModbusSnifferTests
{
    [Fact]
    public void Start_WriteValveCoil_EmitsResult()
    {
        var port = new FakeSerialPort();
        var cfg = new SnifferConfig { SlaveId = 1, ValveCoilAddress = 5, SensorCoilAddress = 6 };
        var sniffer = new ModbusSniffer(port, new ResultInterpreter(cfg));

        ResultEvent? got = null;
        sniffer.ResultReceived += e => got = e;
        sniffer.Start();

        // 构造 0x05 写线圈 5=ON 的完整帧
        var body = new byte[] { 0x01, 0x05, 0x00, 0x05, 0xFF, 0x00 };
        var crc = ModbusCrc16.Compute(body);
        port.Emit(body.Concat(new byte[] { (byte)(crc & 0xFF), (byte)(crc >> 8) }).ToArray());

        Assert.NotNull(got);
        Assert.Equal(InspectionResult.NG, got!.Result);
    }
}
```

`ScannerReaderTests.cs`:
```csharp
using CCDTrace.Scanning;
using CCDTrace.Serial;

namespace CCDTrace.Tests;

public class ScannerReaderTests
{
    [Fact]
    public void Start_AsciiQrWithCrLf_EmitsTrimmedQr()
    {
        var port = new FakeSerialPort();
        var reader = new ScannerReader(port);

        ScannerEvent? got = null;
        reader.QrReceived += e => got = e;
        reader.Start();

        port.Emit(System.Text.Encoding.ASCII.GetBytes("SN202609120001\r\n"));

        Assert.NotNull(got);
        Assert.Equal("SN202609120001", got!.QrCode);
    }
}
```

- [ ] **Step 2: 运行确认失败**

Run: `dotnet test --filter "ModbusSnifferTests|ScannerReaderTests"`
Expected: FAIL

- [ ] **Step 3: 实现**

`Serial/ISerialPort.cs`:
```csharp
namespace CCDTrace.Serial;

public interface ISerialPort
{
    void Open();
    void Close();
    event Action<byte[]> DataReceived;
}
```

`Serial/SystemSerialPort.cs`:
```csharp
using System.IO.Ports;

namespace CCDTrace.Serial;

public sealed class SystemSerialPort : ISerialPort
{
    private readonly SerialPort _port = new();

    public SystemSerialPort(string portName, int baudRate)
    {
        _port.PortName = portName;
        _port.BaudRate = baudRate;
        _port.DataBits = 8;
        _port.StopBits = StopBits.One;
        _port.Parity = Parity.None;
        _port.DataReceived += (_, _) =>
        {
            var n = _port.BytesToRead;
            if (n <= 0) return;
            var buf = new byte[n];
            _port.Read(buf, 0, n);
            DataReceived?.Invoke(buf);
        };
    }

    public void Open() => _port.Open();
    public void Close() => _port.Close();
    public event Action<byte[]>? DataReceived;
}
```

`Modbus/ModbusSniffer.cs`:
```csharp
using CCDTrace.Events;
using CCDTrace.Serial;

namespace CCDTrace.Modbus;

public sealed class ModbusSniffer
{
    private readonly ISerialPort _port;
    private readonly ResultInterpreter _interpreter;
    private readonly MemoryStream _buffer = new();

    public event Action<ResultEvent>? ResultReceived;

    public ModbusSniffer(ISerialPort port, ResultInterpreter interpreter)
    {
        _port = port;
        _interpreter = interpreter;
    }

    public void Start()
    {
        _port.DataReceived += OnData;
        _port.Open();
    }

    private void OnData(byte[] chunk)
    {
        lock (_buffer)
        {
            _buffer.Write(chunk, 0, chunk.Length);
            FlushLocked();
        }
    }

    private void FlushLocked()
    {
        var bytes = _buffer.ToArray();
        var i = 0;
        while (i < bytes.Length)
        {
            var frame = ModbusRtuParser.TryParseFrame(bytes.AsSpan(i), out var consumed);
            if (frame is null) break; // 尾部可能是半帧，等更多字节
            var result = _interpreter.TryGetResult(frame);
            if (result is not null)
            {
                ResultReceived?.Invoke(new ResultEvent(result.Value, DateTimeOffset.Now));
            }
            i += consumed;
        }
        _buffer.SetLength(0);
        _buffer.Write(bytes, i, bytes.Length - i); // 保留未解析尾部
    }
}
```

> 说明：`OnData` 同步解析，完整帧被消费、半帧尾部保留等后续字节；帧边界靠 CRC 校验保证，从站响应帧因 `TryGetResult` 返回 null 被自然忽略。

`Scanning/ScannerReader.cs`:
```csharp
using System.Text;
using CCDTrace.Events;
using CCDTrace.Serial;

namespace CCDTrace.Scanning;

public sealed class ScannerReader
{
    private readonly ISerialPort _port;
    private readonly StringBuilder _buf = new();

    public event Action<ScannerEvent>? QrReceived;

    public ScannerReader(ISerialPort port) => _port = port;

    public void Start()
    {
        _port.DataReceived += OnData;
        _port.Open();
    }

    private void OnData(byte[] chunk)
    {
        _buf.Append(Encoding.ASCII.GetString(chunk));
        var s = _buf.ToString();
        int idx;
        while ((idx = s.IndexOfAny(new[] { '\r', '\n' })) >= 0)
        {
            var qr = s[..idx].Trim();
            s = s[(idx + 1)..];
            if (qr.Length > 0) QrReceived?.Invoke(new ScannerEvent(qr, DateTimeOffset.Now));
        }
        _buf.Clear();
        if (s.Length > 0) _buf.Append(s);
    }
}
```

- [ ] **Step 4: 运行确认通过**

Run: `dotnet test --filter "ModbusSnifferTests|ScannerReaderTests"`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git add src/CCDTrace.Core/Serial src/CCDTrace.Core/Modbus/ModbusSniffer.cs src/CCDTrace.Core/Scanning/ScannerReader.cs tests/CCDTrace.Tests/FakeSerialPort.cs tests/CCDTrace.Tests/ModbusSnifferTests.cs tests/CCDTrace.Tests/ScannerReaderTests.cs
git commit -m "feat: add serial abstraction, modbus sniffer, scanner reader"
```

---

### Task 11: 组合根 AppRuntime + WinForms 外壳

**Files:**
- Create: `src/CCDTrace.Edge/Program.cs`
- Create: `src/CCDTrace.Edge/AppRuntime.cs`
- Create: `src/CCDTrace.Edge/MainForm.cs`
- Create: `src/CCDTrace.Edge/MainForm.Designer.cs`

**Interfaces:**
- Consumes: `AppConfigLoader`, `CorrelationQueue`, `SummaryCalculator`, `SqliteTraceStore`, `CloudSyncService`, `ModbusSniffer`, `ScannerReader`, `SystemSerialPort`, `ResultInterpreter`
- Produces: 可运行的桌面程序骨架（先不含 WebView2，窗口含一个状态 Label，后续任务替换为看板）。

- [ ] **Step 1: 实现 AppRuntime（组合根，串联全部组件）**

```csharp
using CCDTrace.Config;
using CCDTrace.Correlation;
using CCDTrace.Events;
using CCDTrace.Models;
using CCDTrace.Modbus;
using CCDTrace.Scanning;
using CCDTrace.Serial;
using CCDTrace.Storage;
using CCDTrace.Summary;
using CCDTrace.Sync;

namespace CCDTrace.Edge;

public sealed class AppRuntime
{
    private readonly AppConfig _cfg;
    private readonly SummaryCalculator _summary = new();
    private readonly CorrelationQueue _queue;
    private readonly SqliteTraceStore _local;
    private readonly ModbusSniffer? _sniffer;
    private readonly ScannerReader? _scanner;
    private readonly CloudSyncService? _sync;

    public event Action<SummaryStats>? SummaryChanged;
    public event Action<TraceRecord>? RecordBound;

    public AppRuntime(AppConfig cfg)
    {
        _cfg = cfg;
        _queue = new CorrelationQueue(cfg.Correlation.MaxQueueLength);
        _local = new SqliteTraceStore($"Data Source={cfg.LocalDbPath}");
        _local.Init();

        if (cfg.CloudConnectionString is not null)
        {
            _sync = new CloudSyncService(_local, new MySqlCloudStore(cfg.CloudConnectionString));
        }

        var snifferPort = new SystemSerialPort(cfg.Sniffer.Port, cfg.Sniffer.BaudRate);
        _sniffer = new ModbusSniffer(snifferPort, new ResultInterpreter(cfg.Sniffer));
        _sniffer.ResultReceived += OnResult;

        var scannerPort = new SystemSerialPort(cfg.Scanner.Port, cfg.Scanner.BaudRate);
        _scanner = new ScannerReader(scannerPort);
        _scanner.QrReceived += OnQr;
    }

    private void OnResult(ResultEvent e)
    {
        _summary.Add(e.Result);
        SummaryChanged?.Invoke(_summary.Snapshot());
        _queue.EnqueueResult(e);
    }

    private void OnQr(ScannerEvent e)
    {
        var rec = _queue.EnqueueScanner(e, qr => new TraceRecord(qr, InspectionResult.NG, e.Timestamp, 0, _cfg.ProductionSite, "M1", _cfg.MachineId));
        _local.Upsert(rec);
        RecordBound?.Invoke(rec);
        _ = _sync?.RunOnceAsync();
    }

    public void Start()
    {
        _sniffer?.Start();
        _scanner?.Start();
    }

    public SummaryStats Snapshot() => _summary.Snapshot();
}
```

- [ ] **Step 2: 实现 Program 与 MainForm（暂以 Label 展示状态）**

`Program.cs`:
```csharp
namespace CCDTrace.Edge;

internal static class Program
{
    [STAThread]
    static void Main()
    {
        ApplicationConfiguration.Initialize();
        Application.Run(new MainForm());
    }
}
```

`MainForm.cs`:
```csharp
using CCDTrace.Config;
using CCDTrace.Edge;
using CCDTrace.Models;

namespace CCDTrace.Edge;

public partial class MainForm : Form
{
    private AppRuntime? _runtime;

    public MainForm()
    {
        InitializeComponent();
        LoadRuntime();
    }

    private void LoadRuntime()
    {
        try
        {
            var cfg = AppConfigLoader.Load("config.json");
            _runtime = new AppRuntime(cfg);
            _runtime.SummaryChanged += s => statusLabel.Text = $"总量 {s.TotalCount} / 合格 {s.OkCount} / 合格率 {s.OkRatePercent}%";
            _runtime.Start();
        }
        catch (Exception ex)
        {
            statusLabel.Text = "启动失败: " + ex.Message;
        }
    }
}
```

`MainForm.Designer.cs`:
```csharp
namespace CCDTrace.Edge;

partial class MainForm
{
    private Label statusLabel = null!;

    private void InitializeComponent()
    {
        statusLabel = new Label
        {
            Text = "正在初始化…",
            Dock = DockStyle.Top,
            Height = 40,
            Font = new Font("Segoe UI", 14F),
            TextAlign = ContentAlignment.MiddleCenter
        };
        ClientSize = new Size(1100, 720);
        Controls.Add(statusLabel);
        Text = "CCD 溯源 · 边缘采集";
    }
}
```

- [ ] **Step 3: 构建通过**

Run: `dotnet build src/CCDTrace.Edge/CCDTrace.Edge.csproj`
Expected: `Build succeeded.`（不实际运行 GUI，仅编译）

- [ ] **Step 4: Commit**

```bash
git add src/CCDTrace.Edge/Program.cs src/CCDTrace.Edge/AppRuntime.cs src/CCDTrace.Edge/MainForm.cs src/CCDTrace.Edge/MainForm.Designer.cs
git commit -m "feat: add WinForms shell and composition root"
```

---

### Task 12: WebView2 内嵌 HTML 看板

> 本任务的前端视觉方向遵循 frontend-design 技能：明确的配色/字体/结构，界面文案用真实信息（串口名、产量、合格率、同步状态），不用占位假数据。

**Files:**
- Create: `src/CCDTrace.Edge/Dashboard/index.html`
- Create: `src/CCDTrace.Edge/Dashboard/app.css`
- Create: `src/CCDTrace.Edge/Dashboard/app.js`
- Modify: `src/CCDTrace.Edge/MainForm.cs`（加载 WebView2 并桥接）
- Modify: `src/CCDTrace.Edge/AppRuntime.cs`（暴露状态快照与事件）

**Interfaces:**
- Consumes: `AppRuntime.SummaryChanged`, `RecordBound`
- Produces: 看板通过 `window.chrome.webview.postMessage` 请求状态，宿主用 `CoreWebView2.PostWebMessageAsJson` 推送。

- [ ] **Step 1: 写看板 HTML**

`Dashboard/index.html`:
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>CCD 溯源 · 边缘看板</title>
  <link rel="stylesheet" href="app.css" />
</head>
<body>
  <header class="topbar">
    <h1>CCD 溯源 · 边缘采集看板</h1>
    <span id="conn" class="pill">未连接</span>
  </header>

  <main class="grid">
    <section class="card kpi">
      <p class="kpi-label">总产量</p>
      <p id="total" class="kpi-value">0</p>
    </section>
    <section class="card kpi">
      <p class="kpi-label">合格数量</p>
      <p id="ok" class="kpi-value">0</p>
    </section>
    <section class="card kpi">
      <p class="kpi-label">合格率</p>
      <p id="rate" class="kpi-value">0%</p>
    </section>

    <section class="card wide">
      <h2>最近绑定记录</h2>
      <table>
        <thead><tr><th>QR 码</th><th>结果</th><th>时间</th></tr></thead>
        <tbody id="records"></tbody>
      </table>
    </section>

    <section class="card wide">
      <h2>状态</h2>
      <ul id="status"></ul>
    </section>
  </main>

  <script src="app.js"></script>
</body>
</html>
```

`Dashboard/app.css`:
```css
:root {
  --bg: #0f172a;
  --card: #1e293b;
  --ink: #e2e8f0;
  --muted: #94a3b8;
  --accent: #22d3ee;
  --ok: #22c55e;
  --ng: #ef4444;
  font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}
* { box-sizing: border-box; margin: 0; }
body { background: var(--bg); color: var(--ink); padding: 24px; }
.topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
h1 { font-size: 20px; font-weight: 600; }
.pill { padding: 4px 12px; border-radius: 999px; background: #334155; color: var(--muted); font-size: 13px; }
.pill.on { background: #134e4a; color: var(--accent); }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.card { background: var(--card); border-radius: 12px; padding: 20px; }
.card.wide { grid-column: span 3; }
.kpi-label { color: var(--muted); font-size: 13px; }
.kpi-value { font-size: 40px; font-weight: 700; margin-top: 6px; font-variant-numeric: tabular-nums; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid #334155; }
th { color: var(--muted); font-weight: 500; }
.tag { padding: 2px 10px; border-radius: 6px; font-weight: 600; }
.tag.ok { background: #14532d; color: var(--ok); }
.tag.ng { background: #7f1d1d; color: var(--ng); }
ul { list-style: none; }
li { padding: 6px 0; color: var(--muted); font-size: 14px; border-bottom: 1px solid #334155; }
```

`Dashboard/app.js`:
```js
const $ = (id) => document.getElementById(id);

function update(data) {
  $("conn").textContent = "已连接";
  $("conn").classList.add("on");
  $("total").textContent = data.total;
  $("ok").textContent = data.ok;
  $("rate").textContent = data.rate + "%";

  const rows = (data.recent || []).map(r =>
    `<tr><td>${r.qr}</td><td><span class="tag ${r.result.toLowerCase()}">${r.result}</span></td><td>${r.time}</td></tr>`
  ).join("");
  $("records").innerHTML = rows;

  $("status").innerHTML = (data.status || []).map(s => `<li>${s}</li>`).join("");
}

window.chrome.webview.addEventListener("message", (e) => update(e.data));
window.chrome.webview.postMessage({ type: "hello" });
```

- [ ] **Step 2: 改 MainForm 加载 WebView2 并桥接**

`MainForm.cs`（替换 `statusLabel` 逻辑）:
```csharp
using Microsoft.Web.WebView2.WinForms;
using Microsoft.Web.WebView2.Core;
using System.Text.Json;
using CCDTrace.Config;
using CCDTrace.Models;

namespace CCDTrace.Edge;

public partial class MainForm : Form
{
    private AppRuntime? _runtime;
    private WebView2 webView = null!;

    public MainForm()
    {
        InitializeComponent();
        _ = InitAsync();
    }

    private async Task InitAsync()
    {
        var htmlPath = Path.Combine(AppContext.BaseDirectory, "Dashboard", "index.html");
        await webView.EnsureCoreWebView2Async();
        webView.CoreWebView2.SetVirtualHostNameToFolderMapping("app.local", Path.GetDirectoryName(htmlPath)!, CoreWebView2HostResourceAccessKind.Allow);
        webView.CoreWebView2.WebMessageReceived += (_, e) =>
        {
            if (e.WebMessageAsJson.Contains("hello")) PushState();
        };

        try
        {
            var cfg = AppConfigLoader.Load("config.json");
            _runtime = new AppRuntime(cfg);
            _runtime.SummaryChanged += _ => PushState();
            _runtime.RecordBound += _ => PushState();
            _runtime.Start();
        }
        catch (Exception ex)
        {
            webView.CoreWebView2.ExecuteScriptAsync($"document.getElementById('conn').textContent='{ex.Message}'");
        }

        webView.CoreWebView2.Navigate("https://app.local/index.html");
    }

    private void PushState()
    {
        if (_runtime is null) return;
        var s = _runtime.Snapshot();
        var data = new
        {
            total = s.TotalCount,
            ok = s.OkCount,
            rate = s.OkRatePercent,
            recent = _runtime.RecentRecords().Select(r => new
            {
                qr = r.QrCode,
                result = r.Result == Events.InspectionResult.OK ? "OK" : "NG",
                time = r.InspectTime.ToString("HH:mm:ss")
            }),
            status = new[]
            {
                $"本地库: {_runtime.LocalDbPath}",
                $"旁听串口: {_runtime.SnifferPort}",
                $"扫码串口: {_runtime.ScannerPort}"
            }
        };
        webView.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(data));
    }
}
```

- [ ] **Step 3: AppRuntime 暴露看板所需只读属性**

在 `AppRuntime.cs` 增加：
```csharp
public string LocalDbPath => _cfg.LocalDbPath;
public string SnifferPort => _cfg.Sniffer.Port;
public string ScannerPort => _cfg.Scanner.Port;
public IReadOnlyList<TraceRecord> RecentRecords()
{
    var all = _local.GetUnsynced(0);
    return all.Take(20).ToList();
}
```

> 说明：`GetUnsynced(0)` 表示不限条数（Task 8 已支持 `limit <= 0` 时不加 LIMIT）。

- [ ] **Step 4: 确保 Dashboard 文件随输出复制**

在 `CCDTrace.Edge.csproj` 加：
```xml
<ItemGroup>
  <None Update="Dashboard\**\*" CopyToOutputDirectory="PreserveNewest" />
</ItemGroup>
```

- [ ] **Step 5: 构建通过**

Run: `dotnet build src/CCDTrace.Edge/CCDTrace.Edge.csproj`
Expected: `Build succeeded.`

- [ ] **Step 6: Commit**

```bash
git add src/CCDTrace.Edge/Dashboard src/CCDTrace.Edge/MainForm.cs src/CCDTrace.Edge/AppRuntime.cs src/CCDTrace.Edge/CCDTrace.Edge.csproj
git commit -m "feat: add WebView2 HTML dashboard"
```

---

### Task 13: 端到端模拟验证 + README 完善

**Files:**
- Create: `tools/modbus_slave_sim.py`（Modbus RTU 从站模拟器，扮演 MCU + 吹阀线圈）
- Modify: `README.md`

**Interfaces:**
- Consumes: 全部已实现组件
- Produces: 无需真实硬件的端到端联调手段。

- [ ] **Step 1: 写 Modbus 从站模拟脚本**

`tools/modbus_slave_sim.py`:
```python
"""Modbus RTU 从站模拟器：扮演 MCU，配合旁听器做端到端联调。
用法: python modbus_slave_sim.py
帧: 主站写单线圈 0x05 → 回显相同帧（从站正常应答）。
"""
import serial, threading, time

PORT = "COM5"   # 与 config.json 的 Sniffer.Port 一致（用虚拟串口对）
BAUD = 9600

def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc

def main():
    s = serial.Serial(PORT, BAUD, timeout=1)
    print(f"slave listening on {PORT}")
    while True:
        head = s.read(2)
        if len(head) < 2:
            continue
        func = head[1]
        n = {0x05: 6, 0x06: 6, 0x0F: 0, 0x10: 0}.get(func, 6)
        body = head + s.read(n)
        if crc16(body[:-2]) != (body[-2] | body[-1] << 8):
            continue
        s.write(body)  # 回显 = 从站应答
        print("frame:", body.hex())

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 完善 README 联调说明**

在 `README.md` 追加：
```markdown
## 端到端联调（无需真实 MCU）
1. 用虚拟串口工具(如 com0com)建一对互连串口 COM5<->COM6。
2. 把 config.json 的 Sniffer.Port 设为 COM5，Scanner.Port 设为扫码枪串口。
3. python tools/modbus_slave_sim.py（监听 COM5）
4. 运行边缘采集程序，向 COM6 发写线圈帧，观察看板产量/合格率变化。
```

- [ ] **Step 3: 全量测试 + 构建**

Run: `dotnet test && dotnet build`
Expected: 全部测试通过，`Build succeeded.`

- [ ] **Step 4: Commit**

```bash
git add tools/modbus_slave_sim.py README.md
git commit -m "docs: add modbus slave simulator and e2e runbook"
```

---

## Self-Review 结果

- **Spec 覆盖**：设计文档的组件 A–F、H 均有对应任务（A=Task10 扫码、B=Task3/4/10 旁听、C=Task5 绑定、D=Task8/9 入库、E=Task6 汇总、F=Task9 同步、H=Task12 看板）；组件 G（工控机2 展示端）属独立子项目，不在本计划内。
- **占位符**：无 TBD/TODO；每个代码步骤含完整实现。
- **类型一致性**：`TraceRecord`、`ResultEvent`、`ScannerEvent`、`SummaryStats`、`ITraceStore`、`ICloudStore` 签名跨任务一致；`CorrelationQueue` 构造函数参数已统一为 `int maxQueueLength`。
- **已知风险（对应设计文档 R1/R2/R3）**：地址表/串口参数/RS-232vs485 仍待现场确认——已全部收敛到 `config.json` 的 `SnifferConfig`，实现不写死；`ResultInterpreter` 当前按「吹阀线圈写=NG」建模，若现场协议含独立「产品到位」触发位，需在 `ResultInterpreter` 增补（届时新增任务，不影响已交付任务）。
