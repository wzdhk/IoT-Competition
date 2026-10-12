using System;
using System.Collections.Generic;
using System.IO.Ports;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Shapes;
using ZigBeeLibrary;

namespace FourAnalogDemo
{
    /// <summary>
    /// MainWindow.xaml 的交互逻辑
    /// </summary>
    public partial class MainWindow : Window
    {
        private Dictionary<string, ZigBee> mDic = new Dictionary<string, ZigBee>();
        public MainWindow()
        {
            InitializeComponent();
        }

        private void Window_Loaded(object sender, RoutedEventArgs e)
        {
            GetPortList();
        }

        private void GetPortList()
        {
            //SerialPort.GetPortNames()获取当前计算机的串口名称数组
            //遍历串口名称数组，并将其添加到ComboBox控件中
            foreach (string item in SerialPort.GetPortNames())
            {
                cmbPortList.Items.Add(item);
            }

            //若ComboBox控件记录数大于0，即有选项，则将当前选择的第一个项索引设置为索引0
            //否则添加一个“未找到串口”的项，并禁用“发送按钮”
            if (cmbPortList.Items.Count > 0)
            {
                cmbPortList.SelectedIndex = 0;
            }
            else
            {
                MessageBox.Show("未找到串口");
            }
        }

        private void btnGet_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                if (cmbPortList.SelectedIndex == -1)
                {
                    MessageBox.Show("请选择串口号");
                    return;
                }

                //获取传感器数据
                ComSettingModel model = new ComSettingModel();
                model.ZigbeeCom = cmbPortList.SelectedValue.ToString();
                ZigBee zigbee = null;
                if (!mDic.TryGetValue(model.ZigbeeCom, out zigbee))
                {
                    zigbee = new ZigBee(model); zigbee.InitSerialPort();
                }
                zigbee.GetSet();
                zigbee.Close();

                lblLight.Content = zigbee.lightValue;
                lblTemperature.Content = zigbee.temperatureValue;
                lblHumidity.Content = zigbee.humidityValue;
            }
            catch (Exception ex)
            {
                WriteLog(ex.ToString());
            }
        }

        #region 日志记录
        /// <summary>
        /// 日志记录
        /// </summary>
        /// <param name="logContent"></param>
        public static void WriteLog(string logContent)
        {
            try
            {
                string appDomainPath = AppDomain.CurrentDomain.BaseDirectory;

                string logDiretoryPath = appDomainPath + "\\log";

                string logFileName = DateTime.Now.ToString("yyyyMMdd") + ".log";

                string logFilePath = logDiretoryPath + "\\" + logFileName;

                if (!System.IO.Directory.Exists(logDiretoryPath))
                    System.IO.Directory.CreateDirectory(logDiretoryPath);

                if (!System.IO.File.Exists(logFilePath))
                {
                    System.IO.FileStream fs1 = System.IO.File.Create(logFilePath);
                    fs1.Close();
                }

                using (System.IO.FileStream fs = new System.IO.FileStream(logFilePath, System.IO.FileMode.Append, System.IO.FileAccess.Write, System.IO.FileShare.ReadWrite))
                {
                    using (System.IO.StreamWriter sw = new System.IO.StreamWriter(fs, System.Text.Encoding.Default))
                    {
                        sw.WriteLine("[" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "]");
                        sw.WriteLine(logContent);
                    }
                }
            }
            catch (Exception ex)
            {
                using (System.IO.StreamWriter sw = new System.IO.StreamWriter("C:\\log.txt", true))
                {
                    sw.WriteLine("[" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss ") + "]");
                    sw.WriteLine(ex.Message);
                }
            }
        }
        #endregion
    }
}
