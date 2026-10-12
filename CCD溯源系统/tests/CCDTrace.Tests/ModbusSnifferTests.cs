using CCDTrace.Config;
using CCDTrace.Events;
using CCDTrace.Modbus;
using CCDTrace.Serial;
using Xunit;

namespace CCDTrace.Tests;

public class ModbusSnifferTests
{
    [Fact]
    public void Start_WriteValveCoil_EmitsResult()
    {
        var port = new FakeSerialPort();
        var cfg = new SnifferConfig { SlaveId = 1, ValveCoilAddress = 5, SensorCoilAddress = 6 };
        var sniffer = new ModbusSniffer(port, new ResultInterpreter(cfg));

        ResultEvent? got = null;
        sniffer.ResultReceived += e => got = e;
        sniffer.Start();

        // 构造 0x05 写线圈 5=ON 的完整帧
        var body = new byte[] { 0x01, 0x05, 0x00, 0x05, 0xFF, 0x00 };
        var crc = ModbusCrc16.Compute(body);
        port.Emit(body.Concat(new byte[] { (byte)(crc & 0xFF), (byte)(crc >> 8) }).ToArray());

        Assert.NotNull(got);
        Assert.Equal(InspectionResult.NG, got!.Result);
    }
}
