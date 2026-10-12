using Microsoft.Web.WebView2.WinForms;

namespace CCDTrace.Edge;

partial class MainForm
{
    private void InitializeComponent()
    {
        webView = new WebView2
        {
            Dock = DockStyle.Fill
        };
        ClientSize = new Size(1100, 720);
        Controls.Add(webView);
        Text = "CCD 溯源 · 边缘采集";
    }
}
