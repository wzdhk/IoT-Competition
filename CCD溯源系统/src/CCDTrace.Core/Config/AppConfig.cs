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
