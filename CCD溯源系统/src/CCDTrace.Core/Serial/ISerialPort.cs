namespace CCDTrace.Serial;

public interface ISerialPort
{
    void Open();
    void Close();
    event Action<byte[]> DataReceived;
}
