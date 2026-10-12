namespace CCDTrace.Modbus;

public sealed record ModbusRtuFrame(byte SlaveId, byte FunctionCode, ReadOnlyMemory<byte> Data);
