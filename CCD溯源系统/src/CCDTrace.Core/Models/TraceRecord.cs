using CCDTrace.Events;

namespace CCDTrace.Models;

public sealed record TraceRecord(
    string QrCode,
    InspectionResult Result,
    DateTimeOffset InspectTime,
    int Station,
    string ProductionSite,
    string Model,
    string MachineId);
