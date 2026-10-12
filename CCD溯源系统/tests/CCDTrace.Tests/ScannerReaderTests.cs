using CCDTrace.Events;
using CCDTrace.Scanning;
using CCDTrace.Serial;
using Xunit;

namespace CCDTrace.Tests;

public class ScannerReaderTests
{
    [Fact]
    public void Start_AsciiQrWithCrLf_EmitsTrimmedQr()
    {
        var port = new FakeSerialPort();
        var reader = new ScannerReader(port);

        ScannerEvent? got = null;
        reader.QrReceived += e => got = e;
        reader.Start();

        port.Emit(System.Text.Encoding.ASCII.GetBytes("SN202609120001\r\n"));

        Assert.NotNull(got);
        Assert.Equal("SN202609120001", got!.QrCode);
    }
}
