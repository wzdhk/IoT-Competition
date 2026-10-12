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
        try
        {
            _summary.Add(e.Result);
            SummaryChanged?.Invoke(_summary.Snapshot());
            _queue.EnqueueResult(e);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"[AppRuntime] {ex}");
        }
    }

    private void OnQr(ScannerEvent e)
    {
        try
        {
            var rec = _queue.EnqueueScanner(e, qr => new TraceRecord(qr, InspectionResult.NG, e.Timestamp, 0, _cfg.ProductionSite, "M1", _cfg.MachineId));
            _local.Upsert(rec);
            RecordBound?.Invoke(rec);
            _ = _sync?.RunOnceAsync();
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"[AppRuntime] {ex}");
        }
    }

    public void Start()
    {
        _sniffer?.Start();
        _scanner?.Start();
    }

    public SummaryStats Snapshot() => _summary.Snapshot();

    public string LocalDbPath => _cfg.LocalDbPath;
    public string SnifferPort => _cfg.Sniffer.Port;
    public string ScannerPort => _cfg.Scanner.Port;
    public IReadOnlyList<TraceRecord> RecentRecords()
    {
        var all = _local.GetUnsynced(0);
        return all.Take(20).ToList();
    }
}
