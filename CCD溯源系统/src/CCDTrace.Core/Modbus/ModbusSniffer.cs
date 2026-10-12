using CCDTrace.Events;
using CCDTrace.Serial;

namespace CCDTrace.Modbus;

public sealed class ModbusSniffer
{
    private readonly ISerialPort _port;
    private readonly ResultInterpreter _interpreter;
    private readonly MemoryStream _buffer = new();

    public event Action<ResultEvent>? ResultReceived;

    public ModbusSniffer(ISerialPort port, ResultInterpreter interpreter)
    {
        _port = port;
        _interpreter = interpreter;
    }

    public void Start()
    {
        _port.DataReceived += OnData;
        _port.Open();
    }

    private void OnData(byte[] chunk)
    {
        lock (_buffer)
        {
            _buffer.Write(chunk, 0, chunk.Length);
            FlushLocked();
        }
    }

    private const int MaxFrameLen = 256;   // Modbus RTU ADU 上限
    private const int MaxBufferLen = 4096;

    private void FlushLocked()
    {
        var bytes = _buffer.ToArray();
        var i = 0;
        while (i < bytes.Length)
        {
            var frame = ModbusRtuParser.TryParseFrame(bytes.AsSpan(i), out var consumed);
            if (frame is not null)
            {
                var result = _interpreter.TryGetResult(frame);
                if (result is not null)
                {
                    ResultReceived?.Invoke(new ResultEvent(result.Value, DateTimeOffset.Now));
                }
                i += consumed;
                continue;
            }
            // null = 半帧(数据不足) 或 corrupt(CRC 失败)。
            // 剩余字节已达到最大帧长仍无法解析 → 视为 corrupt，丢弃 1 字节向前 resync；
            // 否则视为半帧，break 保留等更多字节。
            if (bytes.Length - i >= MaxFrameLen) { i++; continue; }
            break;
        }
        var remaining = bytes.Length - i;
        _buffer.SetLength(0);
        if (remaining > 0 && remaining <= MaxBufferLen)
        {
            _buffer.Write(bytes, i, remaining);
        }
        // remaining > MaxBufferLen 时清空，防止 corrupt 流无界增长
    }
}
