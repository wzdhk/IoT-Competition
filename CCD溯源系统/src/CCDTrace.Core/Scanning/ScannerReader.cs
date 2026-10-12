using System.Text;
using CCDTrace.Events;
using CCDTrace.Serial;

namespace CCDTrace.Scanning;

public sealed class ScannerReader
{
    private readonly ISerialPort _port;
    private readonly StringBuilder _buf = new();

    public event Action<ScannerEvent>? QrReceived;

    public ScannerReader(ISerialPort port) => _port = port;

    public void Start()
    {
        _port.DataReceived += OnData;
        _port.Open();
    }

    private void OnData(byte[] chunk)
    {
        _buf.Append(Encoding.ASCII.GetString(chunk));
        var s = _buf.ToString();
        int idx;
        while ((idx = s.IndexOfAny(new[] { '\r', '\n' })) >= 0)
        {
            var qr = s[..idx].Trim();
            s = s[(idx + 1)..];
            if (qr.Length > 0) QrReceived?.Invoke(new ScannerEvent(qr, DateTimeOffset.Now));
        }
        _buf.Clear();
        if (s.Length > 0) _buf.Append(s);
    }
}
