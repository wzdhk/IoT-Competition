using CCDTrace.Modbus;
using Xunit;

namespace CCDTrace.Tests;

public class ModbusRtuParserTests
{
    private static byte[] Frame(params byte[] body)
    {
        var crc = ModbusCrc16.Compute(body);
        return body.Concat(new byte[] { (byte)(crc & 0xFF), (byte)(crc >> 8) }).ToArray();
    }

    [Fact]
    public void TryParseFrame_WriteSingleCoil_ExtractsAddressAndValue()
    {
        var buf = Frame(0x01, 0x05, 0x00, 0x00, 0xFF, 0x00);

        var frame = ModbusRtuParser.TryParseFrame(buf, out var consumed);

        Assert.NotNull(frame);
        Assert.Equal(buf.Length, consumed);
        Assert.Equal(0x01, frame!.SlaveId);
        Assert.Equal(0x05, frame.FunctionCode);
        Assert.True(ModbusRtuParser.TryParseWriteSingleCoil(frame, out var addr, out var val));
        Assert.Equal((ushort)0, addr);
        Assert.True(val);
    }

    [Fact]
    public void TryParseFrame_WriteSingleCoilOff_SetsValueFalse()
    {
        var buf = Frame(0x01, 0x05, 0x00, 0x02, 0x00, 0x00);

        var frame = ModbusRtuParser.TryParseFrame(buf, out _);

        Assert.NotNull(frame);
        Assert.True(ModbusRtuParser.TryParseWriteSingleCoil(frame!, out _, out var val));
        Assert.False(val);
    }

    [Fact]
    public void TryParseFrame_ReadCoilsResponse_ExtractsBits()
    {
        var buf = Frame(0x01, 0x01, 0x01, 0x03);

        var frame = ModbusRtuParser.TryParseFrame(buf, out _);

        Assert.NotNull(frame);
        Assert.True(ModbusRtuParser.TryParseReadCoilsResponse(frame!, out var bits));
        Assert.Equal(new byte[] { 0x03 }, bits.ToArray());
    }

    [Fact]
    public void TryParseFrame_CorruptedCrc_ReturnsNull()
    {
        var buf = Frame(0x01, 0x05, 0x00, 0x00, 0xFF, 0x00);
        buf[^1] ^= 0xFF; // 破坏最后一个 CRC 字节

        var frame = ModbusRtuParser.TryParseFrame(buf, out _);

        Assert.Null(frame);
    }

    [Fact]
    public void TryParseFrame_IncompleteBuffer_ReturnsNull()
    {
        var full = Frame(0x01, 0x05, 0x00, 0x00, 0xFF, 0x00);
        var partial = full[..^2]; // 去掉 CRC

        Assert.Null(ModbusRtuParser.TryParseFrame(partial, out _));
    }
}
