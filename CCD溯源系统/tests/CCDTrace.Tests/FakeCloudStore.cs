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
