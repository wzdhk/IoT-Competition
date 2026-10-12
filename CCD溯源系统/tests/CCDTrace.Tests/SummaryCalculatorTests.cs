using Xunit;
using CCDTrace.Events;
using CCDTrace.Summary;

namespace CCDTrace.Tests;

public class SummaryCalculatorTests
{
    [Fact]
    public void Add_MixedResults_ComputesStats()
    {
        var c = new SummaryCalculator();
        c.Add(InspectionResult.OK);
        c.Add(InspectionResult.NG);
        c.Add(InspectionResult.OK);

        var s = c.Snapshot();

        Assert.Equal(3, s.TotalCount);
        Assert.Equal(2, s.OkCount);
        Assert.Equal(1, s.NgCount);
        Assert.Equal(66.67, s.OkRatePercent, 2);
    }

    [Fact]
    public void Snapshot_Empty_IsZero()
    {
        var s = new SummaryCalculator().Snapshot();

        Assert.Equal(0, s.TotalCount);
        Assert.Equal(0.0, s.OkRatePercent);
    }

    [Fact]
    public void Reset_ClearsCounts()
    {
        var c = new SummaryCalculator();
        c.Add(InspectionResult.OK);
        c.Reset();

        Assert.Equal(0, c.Snapshot().TotalCount);
    }
}
