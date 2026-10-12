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
