namespace CCDTrace.Modbus;

public static class ModbusRtuParser
{
    public static ModbusRtuFrame? TryParseFrame(ReadOnlySpan<byte> buf, out int consumed)
    {
        consumed = 0;
        if (buf.Length < 4) return null;

        var slave = buf[0];
        var func = buf[1];
        var len = ExpectedLength(func, buf);
        if (len < 0 || buf.Length < len) return null;

        var crcExpected = (ushort)(buf[len - 2] | (buf[len - 1] << 8));
        var crcActual = ModbusCrc16.Compute(buf[..(len - 2)]);
        if (crcExpected != crcActual) return null;

        consumed = len;
        return new ModbusRtuFrame(slave, func, buf[2..(len - 2)].ToArray());
    }

    private static int ExpectedLength(byte func, ReadOnlySpan<byte> buf)
    {
        // 请求帧固定长度；带字节计数的帧(0x0F/0x10/读响应)按第7字节扩展
        return func switch
        {
            0x05 or 0x06 => 8,
            0x0F or 0x10 => buf.Length >= 7 ? 9 + buf[6] : -1,
            >= 0x01 and <= 0x04 => buf.Length >= 3 && LooksLikeReadResponse(buf) ? 5 + buf[2] : 8,
            _ => -1,
        };
    }

    private static bool LooksLikeReadResponse(ReadOnlySpan<byte> buf)
    {
        // 请求帧第3字节是起始地址高字节(通常为0)，响应帧第3字节是字节计数(通常≤8)
        return buf.Length >= 3 && buf[2] is >= 1 and <= 8 && buf[1] is >= 0x01 and <= 0x04;
    }

    public static bool TryParseWriteSingleCoil(ModbusRtuFrame frame, out ushort address, out bool value)
    {
        address = 0; value = false;
        if (frame.FunctionCode != 0x05 || frame.Data.Length < 4) return false;
        address = (ushort)((frame.Data.Span[0] << 8) | frame.Data.Span[1]);
        value = frame.Data.Span[2] == 0xFF && frame.Data.Span[3] == 0x00;
        return true;
    }

    public static bool TryParseReadCoilsResponse(ModbusRtuFrame frame, out ReadOnlySpan<byte> bits)
    {
        bits = default;
        if (frame.FunctionCode != 0x01 || frame.Data.Length < 1) return false;
        var count = frame.Data.Span[0];
        if (frame.Data.Length < 1 + count) return false;
        bits = frame.Data.Span.Slice(1, count);
        return true;
    }
}
