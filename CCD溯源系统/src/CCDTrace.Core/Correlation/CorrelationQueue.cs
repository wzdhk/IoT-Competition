using CCDTrace.Events;
using CCDTrace.Models;

namespace CCDTrace.Correlation;

public sealed class CorrelationQueue
{
    private readonly object _gate = new();
    private readonly int _max;
    private readonly Queue<ResultEvent> _results = new();
    private int _qrBacklog;

    public CorrelationQueue(int maxQueueLength) => _max = maxQueueLength;

    public int ResultBacklog { get { lock (_gate) return _results.Count; } }
    public int QrBacklog { get { lock (_gate) return _qrBacklog; } }

    public void EnqueueResult(ResultEvent e)
    {
        lock (_gate)
        {
            _results.Enqueue(e);
            while (_results.Count > _max) _results.Dequeue();
        }
    }

    public TraceRecord EnqueueScanner(ScannerEvent e, Func<string, TraceRecord> fallback)
    {
        lock (_gate)
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

            _qrBacklog++;
            return fallback(e.QrCode); // 结果缺失，保持 fallback 默认（调用方约定 NG=待复核）
        }
    }
}
