using CCDTrace.Events;
using CCDTrace.Models;
using MySqlConnector;

namespace CCDTrace.Storage;

public sealed class MySqlCloudStore : ICloudStore
{
    private readonly string _connStr;

    public MySqlCloudStore(string connectionString) => _connStr = connectionString;

    public async Task<bool> PushAsync(TraceRecord r)
    {
        try
        {
            await using var conn = new MySqlConnection(_connStr);
            await conn.OpenAsync();
            await using var cmd = conn.CreateCommand();
            cmd.CommandText = """
                INSERT INTO trace_records
                    (machine_id, qr_code, result, inspect_time, station, production_site, model)
                VALUES
                    (@machine, @qr, @result, @time, @station, @site, @model) AS new
                ON DUPLICATE KEY UPDATE
                    result = new.result,
                    inspect_time = new.inspect_time,
                    station = new.station,
                    production_site = new.production_site,
                    model = new.model;
                """;
            cmd.Parameters.AddWithValue("@machine", r.MachineId);
            cmd.Parameters.AddWithValue("@qr", r.QrCode);
            cmd.Parameters.AddWithValue("@result", r.Result == InspectionResult.OK ? "OK" : "NG");
            cmd.Parameters.AddWithValue("@time", r.InspectTime.UtcDateTime);
            cmd.Parameters.AddWithValue("@station", r.Station);
            cmd.Parameters.AddWithValue("@site", r.ProductionSite);
            cmd.Parameters.AddWithValue("@model", r.Model);
            await cmd.ExecuteNonQueryAsync();
            return true;
        }
        catch (MySqlException)
        {
            return false;
        }
    }
}
