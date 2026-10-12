using CCDTrace.Config;
using CCDTrace.Events;

namespace CCDTrace.Modbus;

public sealed class ResultInterpreter
{
    private readonly byte _slaveId;
    private readonly ushort _valveCoil;
    private readonly ushort _sensorCoil;

    public ResultInterpreter(SnifferConfig cfg)
    {
        _slaveId = cfg.SlaveId;
        _valveCoil = cfg.ValveCoilAddress;
        _sensorCoil = cfg.SensorCoilAddress;
    }

    public InspectionResult? TryGetResult(ModbusRtuFrame frame)
    {
        if (frame.SlaveId != _slaveId) return null;
        if (!ModbusRtuParser.TryParseWriteSingleCoil(frame, out var addr, out var value)) return null;
        if (addr != _valveCoil) return null;
        // 注意：value=false → OK 是「阀线圈=NG」模型下的推断，待现场协议确认（若阀为脉冲，OFF 是同一 reject 的下降沿而非 OK 件；真 OK 件可能无阀动作）。
        return value ? InspectionResult.NG : InspectionResult.OK;
    }

    public bool IsSensorTrigger(ModbusRtuFrame frame)
    {
        if (frame.SlaveId != _slaveId) return false;
        if (!ModbusRtuParser.TryParseWriteSingleCoil(frame, out var addr, out _)) return false;
        return addr == _sensorCoil;
    }
}
