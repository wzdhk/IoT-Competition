using Xunit;
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
