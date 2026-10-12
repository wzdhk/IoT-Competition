using CCDTrace.Models;

namespace CCDTrace.Storage;

public interface ITraceStore
{
    void Init();
    void Upsert(TraceRecord r);
    IReadOnlyList<TraceRecord> GetUnsynced(int limit = 100);
    void MarkSynced(string qrCode);
}
