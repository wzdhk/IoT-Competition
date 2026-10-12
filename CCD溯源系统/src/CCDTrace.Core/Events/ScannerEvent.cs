namespace CCDTrace.Events;

public sealed record ScannerEvent(string QrCode, DateTimeOffset Timestamp);
