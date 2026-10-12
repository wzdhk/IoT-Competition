using CCDTrace.Modbus;
using Xunit;

namespace CCDTrace.Tests;

public class ModbusCrc16Tests
{
    [Fact]
    public void Compute_KnownVector_MatchesSpec()
    {
        // Modbus 规范示例：0x02 0x07 → CRC 0x1241
        Assert.Equal(0x1241, ModbusCrc16.Compute(new byte[] { 0x02, 0x07 }));
    }

    [Fact]
    public void Compute_ReadHoldingRegisterFrame_MatchesSpec()
    {
        // 0x01 0x03 0x00 0x00 0x00 0x0A → CRC 0xCDC5（线上字节序 C5 CD）
        Assert.Equal(0xCDC5, ModbusCrc16.Compute(
            new byte[] { 0x01, 0x03, 0x00, 0x00, 0x00, 0x0A }));
    }

    [Fact]
    public void Compute_Empty_ReturnsInitialValue()
    {
        // 无字节处理 → 返回初值 0xFFFF
        Assert.Equal(0xFFFF, ModbusCrc16.Compute(Array.Empty<byte>()));
    }

    [Fact]
    public void Compute_StandardCheckValue_Matches()
    {
        // CRC-16/MODBUS 官方校验值："123456789" → 0x4B37
        Assert.Equal(0x4B37, ModbusCrc16.Compute("123456789"u8));
    }
}
