using CCDTrace.Events;
using CCDTrace.Models;
using CCDTrace.Storage;
using CCDTrace.Sync;
using Xunit;

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
