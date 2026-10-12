using CCDTrace.Serial;

namespace CCDTrace.Tests;

public sealed class FakeSerialPort : ISerialPort
{
    public void Open() { }
    public void Close() { }
    public event Action<byte[]>? DataReceived;
    public void Emit(byte[] data) => DataReceived?.Invoke(data);
}
