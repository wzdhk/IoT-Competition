using CCDTrace.Events;
using CCDTrace.Models;
using Microsoft.Data.Sqlite;

namespace CCDTrace.Storage;

public sealed class SqliteTraceStore : ITraceStore, IDisposable
{
    private readonly object _gate = new();
    private readonly SqliteConnection _conn;

    public SqliteTraceStore(string connectionString) => _conn = new SqliteConnection(connectionString);

    public void Init()
    {
        lock (_gate)
        {
            _conn.Open();
            using var cmd = _conn.CreateCommand();
            cmd.CommandText = """
                CREATE TABLE IF NOT EXISTS trace_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    qr_code TEXT UNIQUE NOT NULL,
                    result TEXT NOT NULL,
                    inspect_time TEXT NOT NULL,
                    station INTEGER NOT NULL,
                    production_site TEXT NOT NULL,
                    model TEXT NOT NULL,
                    machine_id TEXT NOT NULL,
                    synced INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                """;
            cmd.ExecuteNonQuery();
        }
    }

    public void Upsert(TraceRecord r)
    {
        lock (_gate)
        {
            using var cmd = _conn.CreateCommand();
            cmd.CommandText = """
                INSERT INTO trace_records
                    (qr_code, result, inspect_time, station, production_site, model, machine_id, synced, created_at)
                VALUES
                    ($qr, $result, $time, $station, $site, $model, $machine, 0, $created)
                ON CONFLICT(qr_code) DO UPDATE SET
                    result = excluded.result,
                    inspect_time = excluded.inspect_time,
                    station = excluded.station,
                    production_site = excluded.production_site,
                    model = excluded.model,
                    machine_id = excluded.machine_id,
                    synced = excluded.synced;
                """;
            cmd.Parameters.AddWithValue("$qr", r.QrCode);
            cmd.Parameters.AddWithValue("$result", r.Result == InspectionResult.OK ? "OK" : "NG");
            cmd.Parameters.AddWithValue("$time", r.InspectTime.ToString("O"));
            cmd.Parameters.AddWithValue("$station", r.Station);
            cmd.Parameters.AddWithValue("$site", r.ProductionSite);
            cmd.Parameters.AddWithValue("$model", r.Model);
            cmd.Parameters.AddWithValue("$machine", r.MachineId);
            cmd.Parameters.AddWithValue("$created", DateTimeOffset.UtcNow.ToString("O"));
            cmd.ExecuteNonQuery();
        }
    }

    public IReadOnlyList<TraceRecord> GetUnsynced(int limit = 100)
    {
        lock (_gate)
        {
            var list = new List<TraceRecord>();
            using var cmd = _conn.CreateCommand();
            cmd.CommandText = limit > 0
                ? "SELECT qr_code, result, inspect_time, station, production_site, model, machine_id FROM trace_records WHERE synced = 0 ORDER BY id LIMIT $limit;"
                : "SELECT qr_code, result, inspect_time, station, production_site, model, machine_id FROM trace_records WHERE synced = 0 ORDER BY id;";
            if (limit > 0) cmd.Parameters.AddWithValue("$limit", limit);
            using var reader = cmd.ExecuteReader();
            while (reader.Read())
            {
                list.Add(new TraceRecord(
                    reader.GetString(0),
                    reader.GetString(1) == "OK" ? InspectionResult.OK : InspectionResult.NG,
                    DateTimeOffset.Parse(reader.GetString(2)),
                    reader.GetInt32(3),
                    reader.GetString(4),
                    reader.GetString(5),
                    reader.GetString(6)));
            }
            return list;
        }
    }

    public void MarkSynced(string qrCode)
    {
        lock (_gate)
        {
            using var cmd = _conn.CreateCommand();
            cmd.CommandText = "UPDATE trace_records SET synced = 1 WHERE qr_code = $qr;";
            cmd.Parameters.AddWithValue("$qr", qrCode);
            cmd.ExecuteNonQuery();
        }
    }

    public void Dispose() => _conn.Dispose();
}
