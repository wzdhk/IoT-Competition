# CCD 溯源系统 设计文档

- 日期：2026-09-11
- 状态：待评审
- 关联设备：CCD 光学影像筛选机（皮带式视觉分选机，1–4 工位）

## 1. 目标

在工控机（1）上，与现有 CCD 质检软件**并行**运行一个独立的溯源程序，实现：

1. 溯源扫码枪读取完成质检的电子元件 QR 码；
2. 将单件质检结果（合格/不合格）与对应 QR 码绑定；
3. 逐件记录存入**本地数据库**与**云端数据库（公网 RDS MySQL）**；
4. 汇总数据（合格数量、总数量、合格率、质检时间、生产地）经云端中转，供工控机（2）展示。

## 2. 约束（不可违反）

- **不能修改现有 CCD 质检软件**：无源码，是编译好的 .NET EXE。
- **不能修改 PLC/MCU 固件**：不得改 PLC 程序或 MCU 程序。
- **只能被动观测**：通过非侵入式串口旁听获取逐件结果，不向原链路发送任何数据。

## 3. 架构

### 3.1 组件

| 组件 | 职责 | 输入 → 输出 |
|---|---|---|
| A. 扫码读取器 ScannerReader | 从串口(RS-232)或网口主动读扫码枪的 QR 字符串 | 扫码枪 → `QR事件{码值,时间}` |
| B. Modbus 旁听器 ModbusSniffer | 打开转接来的监听串口，**只读**，按 Modbus RTU 帧解析 | COM3 报文 → `结果事件{OK/NG,时间}` |
| C. 时序绑定队列 CorrelationQueue | FIFO 把结果事件与 QR 事件按先后+物理延时对齐 | 两路事件 → `绑定记录{QR,结果,时间}` |
| D. 溯源入库 TraceService | 绑定记录写本地 SQLite + 云端 RDS | 绑定记录 → 逐件记录 |
| E. 汇总服务 SummaryService | 实时算合格数量/总数量/合格率，写云端汇总表 | 结果流 → 汇总 → 云端 |
| F. 云同步 CloudSync | 断网 SQLite 缓存 + 恢复重传 + 按 QR 幂等去重 | 本地库 → 云端 |
| G. 工控机2 展示端 Display | 读云端汇总表展示 KPI | 云端 → 界面 |
| H. 本地 HTML 看板 LocalDashboard | 工控机1 内嵌 WebView2 显示：串口/旁听状态、实时产量/合格率、最近绑定记录、同步状态、告警 | 各组件状态 → HTML 界面 |

### 3.2 数据流

```
扫码枪 ──QR──┐
             ├─→ 绑定队列 ─→ 溯源入库 ─→ SQLite + 云端RDS(逐件)
Modbus旁听─结果┘               └→ 汇总服务 ─→ 云端RDS(汇总) ─→ 工控机2展示
```

### 3.3 关键技术事实（已通过只读反查确认）

- 现有软件与 MCU 之间为 **Modbus RTU（串口 COM3）**，引用 `HslCommunication.ModBus → ModbusRtu`，含 `ReadCoil`、`set_BaudRate`、`set_Station`、`set_Parity`、`set_DataBits`、`set_StopBits` 等接口。
- 现有软件为 Modbus **主站**，MCU 为**从站**。
- 吹气阀（`Btn_OKValve`，含 MouseDown/MouseUp）为线圈写控制；配方读写为 `readModel`/`writeModel`。
- 逐件结果**没有文件输出**；汇总导出为 `statistics\*.xlsx`（表头：`工位/OK数量/总数量/合格率`）。

## 4. 数据模型

### 4.1 本地库（SQLite）

表 `trace_records`：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| qr_code | TEXT UNIQUE | 二维码值，唯一约束用于幂等 |
| result | TEXT | `OK` / `NG` |
| inspect_time | TEXT | 质检时间（本地） |
| station | INTEGER | 工位（1–4） |
| production_site | TEXT | 生产地（每机固定配置值） |
| model | TEXT | 当前型号 |
| synced | INTEGER | 是否已同步云端（0/1） |
| created_at | TEXT | 入库时间 |

### 4.2 云端库（RDS MySQL）

表 `trace_records`（字段同本地，另加）：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK AUTO_INCREMENT | |
| machine_id | VARCHAR | 设备编号（溯源用） |
| qr_code | VARCHAR UNIQUE | 幂等键 |
| result | VARCHAR | `OK`/`NG` |
| inspect_time | DATETIME | |
| station | INT | |
| production_site | VARCHAR | |
| model | VARCHAR | |
| created_at | DATETIME | |

表 `summary`（供工控机2 展示）：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | |
| machine_id | VARCHAR | |
| stat_date | DATE | 统计日期 |
| total_count | INT | 总数量 |
| ok_count | INT | 合格数量 |
| ng_count | INT | 不合格数量 |
| ok_rate | DECIMAL(5,2) | 合格率(%) = ok/total×100 |
| last_inspect_time | DATETIME | 最近一次质检时间 |
| production_site | VARCHAR | 生产地 |
| updated_at | DATETIME | 更新时间 |

表 `machines`（设备注册）：

| 字段 | 类型 | 说明 |
|---|---|---|
| machine_id | VARCHAR PK | 设备编号 |
| production_site | VARCHAR | 生产地 |
| name | VARCHAR | 设备名 |

## 5. 通信与协议

### 5.1 扫码枪

- 接口：串口(RS-232)或网口(TCP)，**实现时以串口为主、TCP 为可选项**（最终以实际设备为准，配置化）。
- 数据格式：QR 码字符串，通常以 CR/LF 结尾（解析时兼容无结尾符）。

### 5.2 Modbus 旁听

- 旁听串口以**只读**方式打开转接端口，逐字节收流，按 Modbus RTU 帧（站号 + 功能码 + 数据 + CRC16）切帧与校验。
- 需识别两类信号：
  1. **吹阀线圈写**（功能码 0x05 写单线圈，或 0x0F 写多线圈）→ 判定为 NG；
  2. **传感器/触发读取**（`ReadCoil` 结果里产品到位位）→ 判定为「一件已检测」，用于计数总数。
- 若协议中无可见触发位，则「总数量」退化为由 NG 事件 + 外部触发信号补齐（见风险 R1）。

### 5.3 时序绑定

- 相机检测 → 吹阀 → 扫码枪三者之间是**固定物理间距**，等价于固定时间差（与皮带速度相关）。
- 绑定队列维护 FIFO；每条结果事件入队，每条 QR 事件出队队首并绑定。
- 队列配置项：`correlation_delay_ms`（结果→扫码的时间差）、`bind_timeout_ms`（超时未出队则挂起标记「未绑定」）。

## 6. 配置（每台机器一个文件，`config.json`）

| 键 | 说明 |
|---|---|
| scanner.port / scanner.baud / scanner.protocol | 扫码枪接口（serial/tcp） |
| sniffer.port / sniffer.baud | 旁听串口 |
| modbus.slave_id / modbus.address_map | 从站号 + 线圈/寄存器地址表（见风险 R2） |
| correlation.delay_ms / bind_timeout_ms | 时序绑定参数 |
| production_site | 生产地（**每台机器固定值**） |
| machine_id | 设备编号 |
| local_db.path | SQLite 文件路径 |
| cloud.connection_string | RDS 连接串 |
| station_count | 工位数 |

## 7. 错误处理

- **扫码枪/旁听串口断线**：告警 + 本地缓冲 + 自动重连（指数退避）。
- **云端断网**：记录写入 SQLite，`synced=0`；恢复后重传，按 `qr_code` 幂等去重。
- **绑定错位/漏码**：超时挂起，标记「未绑定」，进入人工补录队列。
- **Modbus 帧校验失败**：丢弃该帧并计数，连续 N 次告警（串口参数或地址表可能配错）。

## 8. 技术选型

- 语言/运行时：**C# / .NET**（与现有一致，可复用 `HslCommunication` 解析 Modbus；串口用 `System.IO.Ports`）。
- 本地库：**SQLite**（`Microsoft.Data.Sqlite`）。
- 云端：**MySQL**（`MySqlConnector`）。
- 程序形态：工控机1 为 **桌面程序（WinForms）+ WebView2 内嵌 HTML 本地看板**（组件 H）；工控机2 为轻量展示端（WinForms/网页可选，实施时定）。

## 9. 测试

- **单测**：Modbus RTU 帧解析器（用抓取的真实样本帧）；时序绑定队列（模拟 OK/NG 与 QR 序列）。
- **集成**：用脚本写一个 Modbus RTU 从站模拟器（扮演 MCU + 吹阀线圈 + 传感器位），端到端跑「模拟检测 → 旁听 → 绑定 → 入库 → 汇总」。
- **云端**：本地起 MySQL 替身（或测试库）验证幂等与断网重传。

## 10. 部署

- **工控机1**：现有质检软件（不动）+ 溯源程序 + 扫码枪 + 串口旁听转接。
- **工控机2**：展示端，读云端 `summary` 表。
- 两台均需可访问公网 RDS。

## 11. 风险与待定项

| 编号 | 风险 | 影响 | 处置 |
|---|---|---|---|
| R1 | Modbus 协议中可能无「产品到位」触发位 | 总数无法从旁听直接获得 | 实施第一步先确认；缺失则用外部触发信号（传感器线光耦采集）补齐 |
| R2 | 精确的线圈/寄存器地址表 + 串口参数（波特率/校验/站号）未知 | 旁听器无法定位 NG/触发信号 | **实施第一步**：只读反编译现有 EXE 的 IL 抠出地址表；或用 MCU 协议文档 |
| R3 | COM3 物理层是 RS-232 还是 RS-485 未确认 | 决定旁听转接硬件 | 现场确认接线；RS-485 直接并联，RS-232 用分线 |
| R4 | 扫码枪具体接口（串口 vs 网口）未最终锁定 | 影响读取器实现 | 配置化支持两者，串口优先 |

## 12. 里程碑（建议实施顺序）

1. **前置**：反编译确认 Modbus 地址表 + 串口参数 + RS-232/485（风险 R2/R3）。
2. 单测就绪的 Modbus 帧解析器 + 旁听器骨架。
3. 扫码读取器 + 时序绑定队列。
4. 本地 SQLite + 云同步 + 汇总服务。
5. 集成测试（Modbus 从站模拟器全链路）。
6. 工控机2 展示端。
7. 现场联调。
