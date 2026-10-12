# CCD 溯源系统 · 边缘采集层

工控机（1）上的非侵入式溯源采集程序：旁听 Modbus RTU 逐件结果 + 扫码枪 QR，
绑定后写入本地 SQLite 与云端 MySQL，WebView2 看板实时展示。

## 构建
dotnet build

## 测试
dotnet test

## 运行
配置 config.json 后：dotnet run --project src/CCDTrace.Edge

## 打开即用（一键启动）
双击 `setup.bat`（或 `setup.ps1`）：自动检测本地 .NET SDK（缺失则下载安装），构建并运行。

## 端到端联调（无需真实 MCU）

> 拓扑说明：旁听器（`ModbusSniffer`）是被动只读监听——只 `Open()` 串口解析收到的帧、从不回发。点对点串口（含 com0com 虚拟串口对）只有两个端点，一个串口对无法同时容纳「主站 + MCU 从站 + 旁听器」三方，因此**单个 com0com 串口对无法直接模拟**端到端链路，需借助串口集线器或硬件分线。

**方案 A（纯软件，需 hub4com）**：用 hub4com 把三个虚拟端口桥接成一条共享总线，主站脚本开一端发写线圈帧、`tools/modbus_slave_sim.py`（从站）开一端回显、伴生程序旁听器开一端只读监听；`config.json` 的 `Sniffer.Port` 指向旁听器所开端口，`Scanner.Port` 指向扫码枪串口，运行边缘采集程序观察看板产量/合格率变化。

**方案 B（硬件）**：在 RS-485 总线上多挂载旁听器，或用 RS-232 TX 分线 + 独立 USB 转串口供旁听器监听；`Sniffer.Port` 指向旁听器串口即可。

无 hub4com / 硬件时，旁听器的帧解析与扫码读取逻辑已由单元测试覆盖：`./.dotnet/dotnet test --filter ModbusSnifferTests`、`./.dotnet/dotnet test --filter ScannerReaderTests`。
