using CCDTrace.Events;
using CCDTrace.Models;

namespace CCDTrace.Summary;

public sealed class SummaryCalculator
{
    private int _total;
    private int _ok;

    public void Add(InspectionResult r)
    {
        _total++;
        if (r == InspectionResult.OK) _ok++;
    }

    public SummaryStats Snapshot()
    {
        var rate = _total == 0 ? 0.0 : _ok * 100.0 / _total;
        return new SummaryStats(_total, _ok, _total - _ok, Math.Round(rate, 2));
    }

    public void Reset() { _total = 0; _ok = 0; }
}
