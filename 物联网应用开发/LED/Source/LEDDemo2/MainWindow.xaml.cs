using LEDLibrary;
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

namespace LEDDemo2
{
    /// <summary>
    /// 应用程序主窗体
    /// </summary>
    public partial class MainWindow : Window
    {
        private LEDPlayer player;

        /// <summary>
        /// 窗体构造函数
        /// </summary>
        public MainWindow()
        {
            InitializeComponent();
        }

        /// <summary>
        /// 窗体加载
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void Window_Loaded(object sender, RoutedEventArgs e)
        {
            //加载接入到电脑的所有串口号，并添加到下拉菜单
            string[] arrPort = SerialPort.GetPortNames();
            foreach (var item in arrPort)
            {
                ddlPort.Items.Add(item);
            }
        }

        /// <summary>
        /// 发送信息
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void btnSend_Click(object sender, RoutedEventArgs e)
        {
            //判断是否选择了串口
            if (ddlPort.SelectedIndex < 0)
            {
                MessageBox.Show("请选择正确的串口");
                return;
            }

            //开始根据串口实例LED对象
            player = new LEDPlayer(ddlPort.SelectedValue.ToString());

            string mes = this.txtMessage.Text.Trim();
            if (mes == "")
            {
                MessageBox.Show("请填写需要发送的信息！");
                return;
            }

            string result = player.DisplayText(mes);
            if (result != "")
                MessageBox.Show(result);
        }
        
    }
}
