using Microsoft.Web.WebView2.WinForms;
using Microsoft.Web.WebView2.Core;
using System.Text.Json;
using CCDTrace.Config;
using CCDTrace.Models;

namespace CCDTrace.Edge;

public partial class MainForm : Form
{
    private AppRuntime? _runtime;
    private string? _startupError;
    private WebView2 webView = null!;

    public MainForm()
    {
        InitializeComponent();
        _ = InitAsync();
    }

    private async Task InitAsync()
    {
        var htmlPath = Path.Combine(AppContext.BaseDirectory, "Dashboard", "index.html");
        await webView.EnsureCoreWebView2Async();
        webView.CoreWebView2.SetVirtualHostNameToFolderMapping("app.local", Path.GetDirectoryName(htmlPath)!, CoreWebView2HostResourceAccessKind.Allow);
        webView.CoreWebView2.WebMessageReceived += (_, e) =>
        {
            if (e.WebMessageAsJson.Contains("hello")) PushState();
        };

        try
        {
            var cfg = AppConfigLoader.Load("config.json");
            _runtime = new AppRuntime(cfg);
            _runtime.SummaryChanged += _ => PushState();
            _runtime.RecordBound += _ => PushState();
            _runtime.Start();
        }
        catch (Exception ex)
        {
            _startupError = ex.Message;
        }

        webView.CoreWebView2.Navigate("https://app.local/index.html");
    }

    private void PushState()
    {
        if (_runtime is null)
        {
            var err = new
            {
                conn = "启动失败",
                error = true,
                total = 0,
                ok = 0,
                rate = 0,
                recent = new object[0],
                status = new[] { $"启动失败: {_startupError}" }
            };
            webView.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(err));
            return;
        }
        var s = _runtime.Snapshot();
        var data = new
        {
            total = s.TotalCount,
            ok = s.OkCount,
            rate = s.OkRatePercent,
            recent = _runtime.RecentRecords().Select(r => new
            {
                qr = r.QrCode,
                result = r.Result == CCDTrace.Events.InspectionResult.OK ? "OK" : "NG",
                time = r.InspectTime.ToString("HH:mm:ss")
            }),
            status = new[]
            {
                $"本地库: {_runtime.LocalDbPath}",
                $"旁听串口: {_runtime.SnifferPort}",
                $"扫码串口: {_runtime.ScannerPort}"
            }
        };
        webView.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(data));
    }
}
