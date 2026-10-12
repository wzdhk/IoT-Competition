using Xunit;
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

    [Fact]
    public void Upsert_MarkedSyncedQr_ResetsSyncedToZero()
    {
        using var store = new SqliteTraceStore("Data Source=:memory:");
        store.Init();
        store.Upsert(Rec("QR-1"));
        store.MarkSynced("QR-1");
        store.Upsert(Rec("QR-1"));

        var unsynced = store.GetUnsynced();
        Assert.Single(unsynced);
        Assert.Equal("QR-1", unsynced[0].QrCode);
    }
}
