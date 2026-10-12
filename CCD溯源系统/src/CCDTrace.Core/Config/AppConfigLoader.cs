using System.Text.Json;

namespace CCDTrace.Config;

public static class AppConfigLoader
{
    private static readonly JsonSerializerOptions Options = new() { PropertyNameCaseInsensitive = true };

    public static AppConfig Load(string path)
    {
        if (!File.Exists(path)) throw new FileNotFoundException("配置文件不存在", path);
        var json = File.ReadAllText(path);
        return JsonSerializer.Deserialize<AppConfig>(json, Options) ?? new AppConfig();
    }
}
