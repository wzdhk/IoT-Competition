using Xunit;
using System.Text.Json;
using CCDTrace.Config;

namespace CCDTrace.Tests;

public class AppConfigLoaderTests
{
    [Fact]
    public void Load_ValidJson_ParsesFields()
    {
        var path = Path.GetTempFileName();
        var json = JsonSerializer.Serialize(new AppConfig
        {
            MachineId = "MC-9",
            ProductionSite = "苏州工厂",
            Sniffer = new SnifferConfig { Port = "COM7", ValveCoilAddress = 12 }
        });
        File.WriteAllText(path, json);

        var cfg = AppConfigLoader.Load(path);

        Assert.Equal("MC-9", cfg.MachineId);
        Assert.Equal("苏州工厂", cfg.ProductionSite);
        Assert.Equal("COM7", cfg.Sniffer.Port);
        Assert.Equal((ushort)12, cfg.Sniffer.ValveCoilAddress);

        File.Delete(path);
    }

    [Fact]
    public void Load_MissingFile_Throws()
    {
        Assert.Throws<FileNotFoundException>(() => AppConfigLoader.Load("no-such-file.json"));
    }
}
