using System.IO.Ports;

namespace CCDTrace.Serial;

public sealed class SystemSerialPort : ISerialPort
{
    private readonly SerialPort _port = new();

    public SystemSerialPort(string portName, int baudRate)
    {
        _port.PortName = portName;
        _port.BaudRate = baudRate;
        _port.DataBits = 8;
        _port.StopBits = StopBits.One;
        _port.Parity = Parity.None;
        _port.DataReceived += (_, _) =>
        {
            var n = _port.BytesToRead;
            if (n <= 0) return;
            var buf = new byte[n];
            _port.Read(buf, 0, n);
            DataReceived?.Invoke(buf);
        };
    }

    public void Open() => _port.Open();
    public void Close() => _port.Close();
    public event Action<byte[]>? DataReceived;
}
