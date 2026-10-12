#!/usr/bin/env python3
"""
Modbus TCP 服务器 + Web界面，工件计数功能 + 环境传感器数据监控。
"""

import logging
import threading
import time
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import werkzeug.serving
import requests
import json

from pymodbus.datastore import ModbusSequentialDataBlock, ModbusDeviceContext, ModbusServerContext
from pymodbus.server import StartTcpServer

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.INFO)

REG_ADDR = 1001
REG_MATERIAL_ADDR = 1002
POLL_INTERVAL = 0.1
REG_INITIAL_VALUE = 10

# 传感器配置
SENSOR_URL = "http://192.168.1.233:8000/" # 网关IP地址
SENSOR_POLL_INTERVAL = 1  # 每秒获取一次传感器数据
SENSOR_TIMEOUT = 5  # 请求超时时间


class WorkpieceCounter:
    def __init__(self):
        self.circle_total = 0
        self.circle_qualified = 0
        self.square_total = 0
        self.square_qualified = 0
        self.current_material = 0
        self.lock = threading.Lock()

    def set_material(self, material_type):
        with self.lock:
            if self.current_material != material_type:
                self.current_material = material_type
                log.info(f"物料种类变更: {material_type}")

    def add_qualified(self, material_type):
        with self.lock:
            if material_type == 1:
                self.circle_total += 1
                self.circle_qualified += 1
                rate = (self.circle_qualified / self.circle_total * 100) if self.circle_total > 0 else 0.0
                log.info(f"圆形工件合格 - 总数:{self.circle_total}, 合格:{self.circle_qualified}, 合格率:{rate:.2f}%")
            elif material_type == 2:
                self.square_total += 1
                self.square_qualified += 1
                rate = (self.square_qualified / self.square_total * 100) if self.square_total > 0 else 0.0
                log.info(f"方形工件合格 - 总数:{self.square_total}, 合格:{self.square_qualified}, 合格率:{rate:.2f}%")

    def add_unqualified(self, material_type):
        with self.lock:
            if material_type == 1:
                self.circle_total += 1
                rate = (self.circle_qualified / self.circle_total * 100) if self.circle_total > 0 else 0.0
                log.info(f"圆形工件不合格 - 总数:{self.circle_total}, 合格:{self.circle_qualified}, 合格率:{rate:.2f}%")
            elif material_type == 2:
                self.square_total += 1
                rate = (self.square_qualified / self.square_total * 100) if self.square_total > 0 else 0.0
                log.info(f"方形工件不合格 - 总数:{self.square_total}, 合格:{self.square_qualified}, 合格率:{rate:.2f}%")

    def get_stats(self):
        with self.lock:
            circle_rate = (self.circle_qualified / self.circle_total * 100) if self.circle_total > 0 else 0.0
            square_rate = (self.square_qualified / self.square_total * 100) if self.square_total > 0 else 0.0
            return {
                'current_material': self.current_material,
                'circle_total': self.circle_total,
                'circle_qualified': self.circle_qualified,
                'circle_rate': round(circle_rate, 2),
                'square_total': self.square_total,
                'square_qualified': self.square_qualified,
                'square_rate': round(square_rate, 2)
            }


#  传感器数据管理类
class SensorData:
    def __init__(self):
        self.data = {
            'Illuminance': 0,  # 照度
            'PM2_5': 0,  # PM2.5
            'PM10': 0,  # PM10
            'PM1': 0,  # PM1
            'flooding': 0,  # 浸水状态
            'wendu': 0.0,  # 温度（转换后）
            'shidu': 0.0,  # 湿度（转换后）
            'raw_wendu': 0,  # 原始温度值
            'raw_shidu': 0,  # 原始湿度值
            'wd_auto': 0,  # 温度自动化开关
            'sd_auto': 0,  # 湿度自动化开关
            'RGB': 0,  # RGB灯带开关
            'RGB_mode': 0,  # RGB灯带模式
            'RGB_color_red': 0,  # 红色值
            'RGB_color_green': 0,  # 绿色值
            'RGB_color_blue': 255  # 蓝色值
        }
        self.lock = threading.Lock()

    def update_data(self, new_data):
        """更新传感器数据"""
        with self.lock:
            # 解析并更新指定字段
            for key in ['Illuminance', 'PM2_5', 'PM10', 'PM1', 'flooding', 'wd_auto', 'sd_auto',
                       'RGB', 'RGB_mode', 'RGB_color_red', 'RGB_color_green', 'RGB_color_blue']:
                if key in new_data:
                    self.data[key] = new_data[key]

            # 温度/湿度原始值转换（根据示例值291→29.1℃，608→60.8%）
            if 'wendu' in new_data:
                self.data['raw_wendu'] = new_data['wendu']
                self.data['wendu'] = round(new_data['wendu'] / 10, 1)
            if 'shidu' in new_data:
                self.data['raw_shidu'] = new_data['shidu']
                self.data['shidu'] = round(new_data['shidu'] / 10, 1)

    def get_data(self):
        """获取传感器数据"""
        with self.lock:
            return self.data.copy()

    def toggle_auto(self, auto_type):
        """切换自动化开关状态"""
        with self.lock:
            if auto_type == 'wd_auto':
                self.data['wd_auto'] = 1 if self.data['wd_auto'] == 0 else 0
                return self.data['wd_auto']
            elif auto_type == 'sd_auto':
                self.data['sd_auto'] = 1 if self.data['sd_auto'] == 0 else 0
                return self.data['sd_auto']
        return None
    
    def set_rgb_value(self, param_name, value):
        """设置RGB参数值"""
        with self.lock:
            if param_name in ['RGB', 'RGB_mode', 'RGB_color_red', 'RGB_color_green', 'RGB_color_blue']:
                self.data[param_name] = value
                return value
        return None


# 初始化实例
counter = WorkpieceCounter()
sensor_data = SensorData()  # 传感器数据实例

app = Flask(__name__)
CORS(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/stats')
def get_stats():
    return jsonify(counter.get_stats())


#  传感器数据API
@app.route('/api/sensor_stats')
def get_sensor_stats():
    return jsonify(sensor_data.get_data())


#  自动化控制API
@app.route('/api/toggle_auto/<auto_type>', methods=['POST'])
def toggle_auto(auto_type):
    """切换自动化开关"""
    if auto_type not in ['wd_auto', 'sd_auto']:
        return jsonify({'status': 'error', 'message': '无效的自动化类型'}), 400

    try:
        # 切换本地状态
        new_value = sensor_data.toggle_auto(auto_type)

        # 发送POST请求到传感器URL（使用表单数据格式）
        post_data = {auto_type: new_value}

        log.info(f"正在发送POST请求到 {SENSOR_URL}: {post_data}")
        response = requests.post(SENSOR_URL, data=post_data, timeout=SENSOR_TIMEOUT)

        log.info(f"传感器URL响应: 状态码={response.status_code}, 内容={response.text[:200]}")

        if response.status_code == 200:
            log.info(f"成功切换{auto_type}状态为: {new_value}")
            return jsonify({
                'status': 'ok',
                'auto_type': auto_type,
                'value': new_value,
                'message': f'{auto_type}已切换为{new_value}'
            })
        else:
            log.warning(f"传感器URL返回错误: {response.status_code} - {response.text}")
            return jsonify({
                'status': 'warning',
                'auto_type': auto_type,
                'value': new_value,
                'message': f'本地已切换，但传感器URL返回错误: {response.status_code}'
            })

    except requests.exceptions.RequestException as e:
        log.error(f"发送POST请求失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'无法连接到传感器URL: {str(e)}'
        }), 500
    except Exception as e:
        log.error(f"切换自动化开关异常: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# RGB灯带控制API
@app.route('/api/rgb_control/<param_name>', methods=['POST'])
def rgb_control(param_name):
    """控制RGB灯带参数"""
    if param_name not in ['RGB', 'RGB_mode', 'RGB_color_red', 'RGB_color_green', 'RGB_color_blue']:
        return jsonify({'status': 'error', 'message': '无效的RGB参数'}), 400
    
    try:
        # 获取请求中的值
        data = request.get_json()
        
        if 'value' not in data:
            return jsonify({'status': 'error', 'message': '缺少value参数'}), 400
        
        value = int(data['value'])
        
        # 验证值范围
        if param_name == 'RGB':
            value = 1 if value else 0  # 只能是0或1
        elif param_name == 'RGB_mode':
            if not (0 <= value <= 3):
                return jsonify({'status': 'error', 'message': '模式值必须在0-3之间'}), 400
        elif param_name.startswith('RGB_color_'):
            if not (0 <= value <= 255):
                return jsonify({'status': 'error', 'message': '颜色值必须在0-255之间'}), 400
        
        # 更新本地状态
        sensor_data.set_rgb_value(param_name, value)
        
        # 发送POST请求到传感器URL
        post_data = {param_name: value}
        
        log.info(f"正在发送RGB控制命令: {param_name}={value}")
        response = requests.post(SENSOR_URL, data=post_data, timeout=SENSOR_TIMEOUT)
        
        log.info(f"传感器URL响应: 状态码={response.status_code}, 内容={response.text[:200]}")
        
        if response.status_code == 200:
            log.info(f"成功设置{param_name}为: {value}")
            return jsonify({
                'status': 'ok',
                'param_name': param_name,
                'value': value,
                'message': f'{param_name}已设置为{value}'
            })
        else:
            log.warning(f"传感器URL返回错误: {response.status_code} - {response.text}")
            return jsonify({
                'status': 'warning',
                'param_name': param_name,
                'value': value,
                'message': f'本地已设置，但传感器URL返回错误'
            })
    
    except ValueError as e:
        log.error(f"数值转换失败: {e}")
        return jsonify({'status': 'error', 'message': '无效的数值格式'}), 400
    except requests.exceptions.RequestException as e:
        log.error(f"发送POST请求失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'无法连接到传感器URL: {str(e)}'
        }), 500
    except Exception as e:
        log.error(f"RGB控制异常: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/test')
def test():
    return jsonify({'status': 'ok', 'message': 'Flask服务器运行正常'})


def run_flask():
    try:
        log.info("Flask Web服务器正在启动...")
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        log.error(f"Flask服务器启动失败: {e}")


def poll_register(context, device_id=1):
    """
    后台线程函数：定时读取寄存器值，检测变化并更新计数。
    """
    last_value = REG_INITIAL_VALUE
    last_material = 0
    log.info(f"寄存器监控线程已启动，监控地址: {REG_ADDR}, 物料地址: {REG_MATERIAL_ADDR}, 初始值: {REG_INITIAL_VALUE}")

    while True:
        try:
            current = context[device_id].getValues(3, REG_ADDR, 1)[0]
            material_type = context[device_id].getValues(3, REG_MATERIAL_ADDR, 1)[0]

            if material_type != last_material:
                log.info(f"物料种类变化: {last_material} → {material_type}")
                counter.set_material(material_type)
                last_material = material_type

            if last_value != current:
                log.info(f"寄存器值变化: {last_value} → {current}")

            if last_value == REG_INITIAL_VALUE:
                if current == 1:
                    if material_type in [1, 2]:
                        log.info(f"检测到工件合格信号 (10 → 1), 物料类型: {material_type}")
                        counter.add_qualified(material_type)
                        context[device_id].setValues(3, REG_ADDR, [REG_INITIAL_VALUE])
                        log.info(f"寄存器已重置为 {REG_INITIAL_VALUE}")
                        current = REG_INITIAL_VALUE
                    else:
                        log.warning(f"物料类型无效: {material_type}，忽略合格信号")
                elif current == 0:
                    if material_type in [1, 2]:
                        log.info(f"检测到工件不合格信号 (10 → 0), 物料类型: {material_type}")
                        counter.add_unqualified(material_type)
                        context[device_id].setValues(3, REG_ADDR, [REG_INITIAL_VALUE])
                        log.info(f"寄存器已重置为 {REG_INITIAL_VALUE}")
                        current = REG_INITIAL_VALUE
                    else:
                        log.warning(f"物料类型无效: {material_type}，忽略不合格信号")

            last_value = current
        except Exception as e:
            log.error(f"轮询过程中发生异常: {e}")
        time.sleep(POLL_INTERVAL)


# 传感器数据获取线程
def poll_sensor_data():
    """定时获取传感器数据"""
    log.info(f"传感器监控线程已启动，监控地址: {SENSOR_URL}, 轮询间隔: {SENSOR_POLL_INTERVAL}s")

    while True:
        try:
            # 发送HTTP请求获取传感器数据
            response = requests.get(SENSOR_URL, timeout=SENSOR_TIMEOUT)
            response.raise_for_status()  # 抛出HTTP错误

            # 解析JSON数据
            data = response.json()
            sensor_values = {}

            # 提取需要的字段
            if 'datastreams' in data:
                for stream in data['datastreams']:
                    stream_id = stream.get('id')
                    value = stream.get('value')
                    if stream_id in ['Illuminance', 'PM2_5', 'PM10', 'PM1', 'flooding', 'wendu', 'shidu',
                                   'wd_auto', 'sd_auto', 'RGB', 'RGB_mode',
                                   'RGB_color_red', 'RGB_color_green', 'RGB_color_blue']:
                        sensor_values[stream_id] = value

            # 更新传感器数据
            sensor_data.update_data(sensor_values)
            log.debug(f"传感器数据更新: {sensor_values}")

        except requests.exceptions.RequestException as e:
            log.error(f"获取传感器数据失败: {e}")
        except json.JSONDecodeError as e:
            log.error(f"解析传感器数据失败: {e}")
        except Exception as e:
            log.error(f"传感器轮询异常: {e}")

        time.sleep(SENSOR_POLL_INTERVAL)


def main():
    log.info("=" * 60)
    log.info("工件计数+环境监控系统正在启动...")
    log.info("=" * 60)

    initial_values = [0] * 2000
    initial_values[REG_ADDR + 1] = REG_INITIAL_VALUE
    initial_values[REG_MATERIAL_ADDR + 1] = 0

    data_block = ModbusSequentialDataBlock(0, initial_values)
    log.info(f"✓ 寄存器 {REG_ADDR} 初始化为 {REG_INITIAL_VALUE}")
    log.info(f"✓ 寄存器 {REG_MATERIAL_ADDR} 初始化为 0")

    device_context = ModbusDeviceContext(hr=data_block)
    server_context = ModbusServerContext(devices={1: device_context}, single=False)

    # 启动寄存器监控线程
    poll_thread = threading.Thread(target=poll_register, args=(server_context, 1), daemon=True)
    poll_thread.start()
    log.info("✓ Modbus监控线程已启动")

    #  启动传感器监控线程
    sensor_thread = threading.Thread(target=poll_sensor_data, daemon=True)
    sensor_thread.start()
    log.info("✓ 传感器监控线程已启动")

    # 启动Flask线程
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    log.info("✓ Flask Web服务器线程已启动")

    time.sleep(1)

    log.info("=" * 60)
    log.info(f"Modbus TCP 服务器启动，监听端口 502")
    log.info(f"监控寄存器: {REG_ADDR} (初始值: {REG_INITIAL_VALUE})")
    log.info(f"物料寄存器: {REG_MATERIAL_ADDR} (初始值: 0)")
    log.info(f"传感器监控地址: {SENSOR_URL}")
    log.info("Web界面访问地址:")
    log.info("  - http://localhost:5000")
    log.info("  - http://192.168.1.7:5000")
    log.info("测试API地址: http://192.168.1.7:5000/api/test")
    log.info("传感器API地址: http://192.168.1.7:5000/api/sensor_stats")
    log.info("=" * 60)
#提示：我们来看云平台上的数据
    try:
        StartTcpServer(context=server_context, address=("0.0.0.0", 502))
    except KeyboardInterrupt:
        log.info("收到中断信号，服务器正在关闭...")
    except Exception as e:
        log.error(f"服务器启动失败: {e}")
 #我是AI算法工程师负责识别算法训练，数据行为分析和网关脚本的搭建
if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        log.warning("未安装requests库，正在自动安装...")
        import subprocess
        import sys
   
 #接下来带大家了解一下我们的AI视频识别系统
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        import requests

    main()
    #本系统基于AI大模型，自动识别人员特征与行为的关键因素

    log.info("=" * 60)
    log.info(f"Modbus TCP 服务器启动，监听端口 502")
    log.info(f"监控寄存器: {REG_ADDR} (初始值: {REG_INITIAL_VALUE})")
    log.info(f"物料寄存器: {REG_MATERIAL_ADDR} (初始值: 0)")
    log.info(f"传感器监控地址: {SENSOR_URL}")
    log.info("Web界面访问地址:")
    log.info("  - http://localhost:5000")
    log.info("  - http://192.168.1.7:5000")
    log.info("测试API地址: http://192.168.1.7:5000/api/test")
    log.info("传感器API地址: http://192.168.1.7:5000/api/sensor_stats")
    log.info("=" * 60)
    #深度识别工作人员是否正确穿戴反光衣，安全帽等必要安全设备还可以检测工作人员是否违规作业或在岗睡觉等安全问题
def main():
    log.info("=" * 60)
    log.info("工件计数+环境监控系统正在启动...")
    log.info("=" * 60)
    #依托标记图片与视频素材开展模型训练，让AI自主研判场景中是否存在安全隐患
    initial_values = [0] * 2000
    initial_values[REG_ADDR + 1] = REG_INITIAL_VALUE
    initial_values[REG_MATERIAL_ADDR + 1] = 0
    #最终接入智能网关，完成对现场的自动化控制
    data_block = ModbusSequentialDataBlock(0, initial_values)
    log.info(f"✓ 寄存器 {REG_ADDR} 初始化为 {REG_INITIAL_VALUE}")
    log.info(f"✓ 寄存器 {REG_MATERIAL_ADDR} 初始化为 0")

    device_context = ModbusDeviceContext(hr=data_block)
    server_context = ModbusServerContext(devices={1: device_context}, single=False)

    # 启动寄存器监控线程
    poll_thread = threading.Thread(target=poll_register, args=(server_context, 1), daemon=True)
    poll_thread.start()
    log.info("✓ Modbus监控线程已启动")

    #  我们通过AI智能分析系统，可精准识别，安全设备是否穿戴，人员是否出现不安全行为等问题
    sensor_thread = threading.Thread(target=poll_sensor_data, daemon=True)
    sensor_thread.start()
    log.info("✓ 传感器监控线程已启动")

    # 为生产安全提供关键保障，筑牢安全防线
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    log.info("✓ Flask Web服务器线程已启动")

    time.sleep(1)