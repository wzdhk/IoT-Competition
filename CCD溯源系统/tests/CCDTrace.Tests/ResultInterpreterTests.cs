using CCDTrace.Config;
using CCDTrace.Events;
using CCDTrace.Modbus;
using Xunit;

namespace CCDTrace.Tests;

public class ResultInterpreterTests
{
    private static ModbusRtuFrame CoilWrite(byte slave, ushort addr, bool value)
        => new(slave, 0x05, new byte[]
        {
            (byte)(addr >> 8), (byte)(addr & 0xFF),
            value ? (byte)0xFF : (byte)0x00, 0x00,
        });

    [Fact]
    public void TryGetResult_ValveCoilOn_ReturnsNG()
    {
        var cfg = new SnifferConfig { SlaveId = 1, ValveCoilAddress = 5, SensorCoilAddress = 6 };
        var it = new ResultInterpreter(cfg);

        Assert.Equal(InspectionResult.NG, it.TryGetResult(CoilWrite(1, 5, true)));
    }

    [Fact]
    public void TryGetResult_ValveCoilOff_ReturnsOK()
    {
        var cfg = new SnifferConfig { SlaveId = 1, ValveCoilAddress = 5, SensorCoilAddress = 6 };
        var it = new ResultInterpreter(cfg);

        Assert.Equal(InspectionResult.OK, it.TryGetResult(CoilWrite(1, 5, false)));
    }

    [Fact]
    public void TryGetResult_WrongSlave_ReturnsNull()
    {
        var cfg = new SnifferConfig { SlaveId = 1, ValveCoilAddress = 5 };
        var it = new ResultInterpreter(cfg);

        Assert.Null(it.TryGetResult(CoilWrite(2, 5, true)));
    }

    [Fact]
    public void TryGetResult_NonValveCoil_ReturnsNull()
    {
        var cfg = new SnifferConfig { SlaveId = 1, ValveCoilAddress = 5, SensorCoilAddress = 6 };
        var it = new ResultInterpreter(cfg);

        Assert.Null(it.TryGetResult(CoilWrite(1, 6, true)));
    }

    [Fact]
    public void IsSensorTrigger_MatchesConfiguredCoil()
    {
        var cfg = new SnifferConfig { SlaveId = 1, ValveCoilAddress = 5, SensorCoilAddress = 6 };
        var it = new ResultInterpreter(cfg);

        Assert.True(it.IsSensorTrigger(CoilWrite(1, 6, true)));
        Assert.False(it.IsSensorTrigger(CoilWrite(1, 5, true)));
    }
}
