namespace CCDTrace.Events;

public sealed record ResultEvent(InspectionResult Result, DateTimeOffset Timestamp, int Station = 0);
