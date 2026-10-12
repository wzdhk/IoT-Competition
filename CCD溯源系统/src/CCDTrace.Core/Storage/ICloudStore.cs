using CCDTrace.Models;

namespace CCDTrace.Storage;

public interface ICloudStore
{
    Task<bool> PushAsync(TraceRecord r);
}
