#!/usr/bin/env python3
"""
Modbus TCP 服务器 + Web 界面，工件计数功能 + 环境传感器数据监控。

主要功能：
1. 作为 Modbus TCP 服务器监听端口 502，接收 PLC 或其他设备的寄存器读写请求。
2. 监控特定寄存器变化以统计圆形/方形工件的合格/不合格数量。
3. 提供 Flask Web 服务展示统计数据及传感器实时数据。
4. 定时从外部传感器 API 获取环境数据（温度、湿度、PM2.5等）。
5. 支持通过 Web 接口反向控制传感器的自动化开关与 RGB 灯带。
"""

import logging
import threading
import time
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import werkzeug.serving
import requests
import json

# Modbus 相关库导入
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusDeviceContext, ModbusServerContext
from pymodbus.server import StartTcpServer

# 配置基础日志记录器，级别设置为 INFO
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# 单独配置 Werkzeug (Flask底层服务器) 的日志级别，避免输出过多调试信息
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.INFO)

# ================= 常量配置 =================
REG_ADDR = 1001           # Modbus 保持寄存器地址：用于接收工件检测信号 (1:合格, 0:不合格, 10:初始/空闲)
REG_MATERIAL_ADDR = 1002  # Modbus 保持寄存器地址：用于接收当前物料类型 (1:圆形, 2:方形)
POLL_INTERVAL = 0.1       # Modbus 寄存器轮询间隔（秒），越短响应越快但占用CPU越高
REG_INITIAL_VALUE = 10    # 寄存器的初始状态值，表示无新信号

# 传感器配置
SENSOR_URL = "http://192.168.1.233:8000/"  # 外部传感器数据接口的 URL（网关IP地址）
SENSOR_POLL_INTERVAL = 1  # 传感器数据获取间隔（秒）
SENSOR_TIMEOUT = 5        # HTTP 请求超时时间（秒）


class WorkpieceCounter:
    """
    工件计数器类
    负责维护圆形和方形工件的总数、合格数，并计算合格率。
    使用线程锁保证多线程环境下的数据安全。
    """
    def __init__(self):
        self.circle_total = 0       # 圆形工件总数
        self.circle_qualified = 0   # 圆形工件合格数
        self.square_total = 0       # 方形工件总数
        self.square_qualified = 0   # 方形工件合格数
        self.current_material = 0   # 当前正在处理的物料类型
        self.lock = threading.Lock()  # 线程锁，防止并发修改数据导致错误

    def set_material(self, material_type):
        """
        设置当前物料类型
        :param material_type: 1代表圆形，2代表方形
        """
        with self.lock:
            # 仅在物料类型发生变化时更新，避免重复日志
            if self.current_material != material_type:
                self.current_material = material_type
                log.info(f"物料种类变更: {material_type}")

    def add_qualified(self, material_type):
        """
        增加一个合格工件计数
        :param material_type: 物料类型 (1:圆形, 2:方形)
        """
        with self.lock:
            if material_type == 1:
                self.circle_total += 1
                self.circle_qualified += 1
                # 计算合格率，防止除以零
                rate = (self.circle_qualified / self.circle_total * 100) if self.circle_total > 0 else 0.0
                log.info(f"圆形工件合格 - 总数:{self.circle_total}, 合格:{self.circle_qualified}, 合格率:{rate:.2f}%")
            elif material_type == 2:
                self.square_total += 1
                self.square_qualified += 1
                rate = (self.square_qualified / self.square_total * 100) if self.square_total > 0 else 0.0
                log.info(f"方形工件合格 - 总数:{self.square_total}, 合格:{self.square_qualified}, 合格率:{rate:.2f}%")

    def add_unqualified(self, material_type):
        """
        增加一个不合格工件计数（只增加总数，不增加合格数）
        :param material_type: 物料类型 (1:圆形, 2:方形)
        """
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
        """
        获取当前的统计数据结构
        :return: 包含各类统计数据的字典
        """
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


class SensorData:
    """
    传感器数据管理类
    负责存储、更新和获取环境传感器数据，支持原始值到实际值的转换，
    以及自动化开关与 RGB 灯带的控制。
    """
    def __init__(self):
        # 初始化传感器数据字典
        self.data = {
            'Illuminance': 0,      # 照度 (Lux)
            'PM2_5': 0,            # PM2.5 浓度
            'PM10': 0,             # PM10 浓度
            'PM1': 0,              # PM1 浓度
            'flooding': 0,         # 浸水状态 (1:正常, 0:报警) — 网关 mode1: flooding ~= 1 时报警
            'fan': 0,              # 风扇状态 (0:停止, 1:运转)
            'E_stop': 1,           # 急停状态 (0:急停中, 1:正常)
            'wendu': 0.0,          # 温度（转换后，单位℃）
            'shidu': 0.0,          # 湿度（转换后，单位%）
            'raw_wendu': 0,        # 原始温度值（通常为整数，需除以10）
            'raw_shidu': 0,        # 原始湿度值（通常为整数，需除以10）
            'wd_auto': 0,          # 温度自动化控制开关 (0:关, 1:开)
            'sd_auto': 0,          # 湿度自动化控制开关 (0:关, 1:开)
            'RGB': 0,              # RGB灯带开关 (0:关, 1:开)
            'RGB_mode': 0,         # RGB灯带模式 (0:常亮, 1:呼吸, 2:流水灯, 3:跑马灯)
            'RGB_color_red': 0,    # 红色值 (0-255)
            'RGB_color_green': 0,  # 绿色值 (0-255)
            'RGB_color_blue': 255  # 蓝色值 (0-255)
        }
        self.lock = threading.Lock()  # 线程锁

    def update_data(self, new_data):
        """
        更新传感器数据
        :param new_data: 从外部API获取的最新数据字典
        """
        with self.lock:
            # 直接更新普通数值字段
            for key in ['Illuminance', 'PM2_5', 'PM10', 'PM1', 'flooding', 'fan', 'E_stop', 'wd_auto', 'sd_auto',
                        'RGB', 'RGB_mode', 'RGB_color_red', 'RGB_color_green', 'RGB_color_blue']:
                if key in new_data:
                    self.data[key] = new_data[key]

            # 温度原始值转换：原始值 291 代表 29.1℃
            if 'wendu' in new_data:
                self.data['raw_wendu'] = new_data['wendu']
                self.data['wendu'] = round(new_data['wendu'] / 10, 1)

            # 湿度原始值转换：原始值 608 代表 60.8%
            if 'shidu' in new_data:
                self.data['raw_shidu'] = new_data['shidu']
                self.data['shidu'] = round(new_data['shidu'] / 10, 1)

    def get_data(self):
        """
        获取传感器数据的副本
        返回副本以避免外部修改影响内部状态，同时解决线程安全问题
        :return: 传感器数据字典的拷贝
        """
        with self.lock:
            return self.data.copy()

    def toggle_auto(self, auto_type):
        """
        切换自动化开关状态 (取反操作)
        :param auto_type: 'wd_auto' (温度) 或 'sd_auto' (湿度)
        :return: 切换后的新状态值
        """
        with self.lock:
            if auto_type == 'wd_auto':
                # 如果当前是0则变为1，否则变为0
                self.data['wd_auto'] = 1 if self.data['wd_auto'] == 0 else 0
                return self.data['wd_auto']
            elif auto_type == 'sd_auto':
                self.data['sd_auto'] = 1 if self.data['sd_auto'] == 0 else 0
                return self.data['sd_auto']
        return None

    def set_rgb_value(self, param_name, value):
        """
        设置 RGB 灯带参数值
        :param param_name: 参数名 (RGB / RGB_mode / RGB_color_red / ...)
        :param value: 参数值
        :return: 设置成功返回该值，否则返回 None
        """
        with self.lock:
            if param_name in ['RGB', 'RGB_mode', 'RGB_color_red', 'RGB_color_green', 'RGB_color_blue']:
                self.data[param_name] = value
                return value
        return None


# ================= 全局实例初始化 =================
counter = WorkpieceCounter()      # 创建工件计数器实例
sensor_data = SensorData()        # 创建传感器数据管理实例

# 创建 Flask Web 应用
app = Flask(__name__)
CORS(app)  # 启用跨域资源共享，允许前端页面不同源访问 API


# ================= Flask 路由定义 =================

@app.route('/')
def index():
    """
    根路径：渲染主页 HTML 模板
    """
    return render_template('index.html')


@app.route('/api/stats')
def get_stats():
    """
    API: 获取工件计数统计数据
    """
    return jsonify(counter.get_stats())


@app.route('/api/sensor_stats')
def get_sensor_stats():
    """
    API: 获取实时传感器环境数据
    """
    return jsonify(sensor_data.get_data())


@app.route('/api/toggle_auto/<auto_type>', methods=['POST'])
def toggle_auto(auto_type):
    """
    API: 切换传感器自动化控制开关
    1. 更新本地状态
    2. 发送 POST 请求通知物理传感器设备
    :param auto_type: 开关类型 ('wd_auto' 或 'sd_auto')
    """
    # 参数校验
    if auto_type not in ['wd_auto', 'sd_auto']:
        return jsonify({'status': 'error', 'message': '无效的自动化类型'}), 400

    try:
        # 1. 切换本地内存中的状态
        new_value = sensor_data.toggle_auto(auto_type)

        # 2. 准备发送给物理传感器的数据 (表单格式)
        post_data = {auto_type: new_value}

        log.info(f"正在发送POST请求到 {SENSOR_URL}: {post_data}")
        # 3. 发送 HTTP POST 请求到硬件设备
        response = requests.post(SENSOR_URL, data=post_data, timeout=SENSOR_TIMEOUT)

        log.info(f"传感器URL响应: 状态码={response.status_code}, 内容={response.text[:200]}")

        # 根据响应结果返回不同的状态
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
        # 网络请求异常处理
        log.error(f"发送POST请求失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'无法连接到传感器URL: {str(e)}'
        }), 500
    except Exception as e:
        # 其他未知异常处理
        log.error(f"切换自动化开关异常: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/rgb_control/<param_name>', methods=['POST'])
def rgb_control(param_name):
    """
    API: 控制 RGB 灯带参数
    1. 校验参数与取值范围
    2. 更新本地状态
    3. 发送 POST 请求通知物理传感器设备
    :param param_name: RGB 参数名 (RGB / RGB_mode / RGB_color_*)
    """
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
                'message': '本地已设置，但传感器URL返回错误'
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
    """
    API: 测试接口，用于确认 Flask 服务是否正常运行
    """
    return jsonify({'status': 'ok', 'message': 'Flask服务器运行正常'})


# ================= 后台线程函数 =================

def run_flask():
    """
    在独立线程中运行 Flask Web 服务器
    """
    try:
        log.info("Flask Web服务器正在启动...")
        # host='0.0.0.0' 允许局域网访问, threaded=True 支持多请求并发
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        log.error(f"Flask服务器启动失败: {e}")


def poll_register(context, device_id=1):
    """
    后台线程函数：定时读取 Modbus 寄存器值，检测变化并更新计数。
    逻辑：
    - 监测 REG_ADDR (1001) 的值变化。
    - 如果从初始值(10)变为1，视为合格信号。
    - 如果从初始值(10)变为0，视为不合格信号。
    - 处理完后将寄存器重置为初始值，等待下一次触发。
    - 同时监测 REG_MATERIAL_ADDR (1002) 获取物料类型。

    :param context: Modbus 服务器上下文对象
    :param device_id: 设备ID
    """
    last_value = REG_INITIAL_VALUE  # 记录上一次的寄存器值，用于检测边沿触发
    last_material = 0               # 记录上一次的物料类型
    log.info(f"寄存器监控线程已启动，监控地址: {REG_ADDR}, 物料地址: {REG_MATERIAL_ADDR}, 初始值: {REG_INITIAL_VALUE}")

    while True:
        try:
            # 读取保持寄存器 (Function Code 3) 的值
            # getValues(功能码, 起始地址, 数量)】
            current = context[device_id].getValues(3, REG_ADDR, 1)[0]
            material_type = context[device_id].getValues(3, REG_MATERIAL_ADDR, 1)[0]

            # 检测物料类型变化
            if material_type != last_material:
                log.info(f"物料种类变化: {last_material} → {material_type}")
                counter.set_material(material_type)
                last_material = material_type

            # 日志：如果值发生变化，打印调试信息
            if last_value != current:
                log.info(f"寄存器值变化: {last_value} → {current}")

            # 核心计数逻辑：只有当上一次是初始状态，且当前变为有效信号时才计数
            if last_value == REG_INITIAL_VALUE:
                if current == 1:
                    # 检测到合格信号
                    if material_type in [1, 2]:
                        log.info(f"检测到工件合格信号 (10 → 1), 物料类型: {material_type}")
                        counter.add_qualified(material_type)
                        # 重要：处理完后立即将寄存器写回初始值，防止重复计数
                        context[device_id].setValues(3, REG_ADDR, [REG_INITIAL_VALUE])
                        log.info(f"寄存器已重置为 {REG_INITIAL_VALUE}")
                        current = REG_INITIAL_VALUE  # 更新本地缓存
                    else:
                        log.warning(f"物料类型无效: {material_type}，忽略合格信号")

                elif current == 0:
                    # 检测到不合格信号
                    if material_type in [1, 2]:
                        log.info(f"检测到工件不合格信号 (10 → 0), 物料类型: {material_type}")
                        counter.add_unqualified(material_type)
                        # 重要：处理完后立即将寄存器写回初始值
                        context[device_id].setValues(3, REG_ADDR, [REG_INITIAL_VALUE])
                        log.info(f"寄存器已重置为 {REG_INITIAL_VALUE}")
                        current = REG_INITIAL_VALUE  # 更新本地缓存
                    else:
                        log.warning(f"物料类型无效: {material_type}，忽略不合格信号")

            # 更新最后一次的值，用于下一轮比较
            last_value = current
        except Exception as e:
            log.error(f"轮询过程中发生异常: {e}")

        # 短暂休眠，避免 CPU 占用过高
        time.sleep(POLL_INTERVAL)


def poll_sensor_data():
    """
    后台线程函数：定时从外部 HTTP 接口获取传感器数据并更新到本地对象
    """
    log.info(f"传感器监控线程已启动，监控地址: {SENSOR_URL}, 轮询间隔: {SENSOR_POLL_INTERVAL}s")

    while True:
        try:
            # 发送 HTTP GET 请求获取传感器数据
            response = requests.get(SENSOR_URL, timeout=SENSOR_TIMEOUT)
            response.raise_for_status()  # 如果状态码不是 200，抛出异常

            # 解析 JSON 数据
            data = response.json()
            sensor_values = {}

            # 根据特定的 JSON 结构提取数据 (假设数据在 'datastreams' 列表中)
            if 'datastreams' in data:
                for stream in data['datastreams']:
                    stream_id = stream.get('id')
                    value = stream.get('value')
                    # 只提取我们关心的字段
                    if stream_id in ['Illuminance', 'PM2_5', 'PM10', 'PM1', 'flooding', 'fan', 'E_stop', 'wendu', 'shidu',
                                     'wd_auto', 'sd_auto', 'RGB', 'RGB_mode',
                                     'RGB_color_red', 'RGB_color_green', 'RGB_color_blue']:
                        sensor_values[stream_id] = value

            # 将提取的数据更新到 SensorData 对象中
            sensor_data.update_data(sensor_values)
            log.debug(f"传感器数据更新: {sensor_values}")

        except requests.exceptions.RequestException as e:
            log.error(f"获取传感器数据失败: {e}")
        except json.JSONDecodeError as e:
            log.error(f"解析传感器数据失败: {e}")
        except Exception as e:
            log.error(f"传感器轮询异常: {e}")

        # 休眠指定间隔
        time.sleep(SENSOR_POLL_INTERVAL)


def main():
    """
    主函数：初始化 Modbus 服务器，启动所有后台线程，并开始监听 Modbus TCP 端口
    """
    log.info("=" * 60)
    log.info("工件计数+环境监控系统正在启动...")
    log.info("=" * 60)

    # 初始化 Modbus 数据存储块
    # 创建一个大小为 2000 的数组，初始值全为 0
    initial_values = [0] * 2000
    # 设置特定寄存器的初始值
    # 注意：pymodbus 地址映射可能需要偏移，这里根据原代码逻辑保留
    initial_values[REG_ADDR + 1] = REG_INITIAL_VALUE
    initial_values[REG_MATERIAL_ADDR + 1] = 0

    # 创建保持寄存器数据块
    data_block = ModbusSequentialDataBlock(0, initial_values)
    log.info(f"✓ 寄存器 {REG_ADDR} 初始化为 {REG_INITIAL_VALUE}")
    log.info(f"✓ 寄存器 {REG_MATERIAL_ADDR} 初始化为 0")

    # 创建设备上下文，关联数据块
    device_context = ModbusDeviceContext(hr=data_block)
    # 创建服务器上下文，支持多个设备（这里只配置了设备 ID 1）
    server_context = ModbusServerContext(devices={1: device_context}, single=False)

    # 1. 启动 Modbus 寄存器监控线程 (守护线程)
    poll_thread = threading.Thread(target=poll_register, args=(server_context, 1), daemon=True)
    poll_thread.start()
    log.info("✓ Modbus监控线程已启动")

    # 2. 启动传感器数据获取线程 (守护线程)
    sensor_thread = threading.Thread(target=poll_sensor_data, daemon=True)
    sensor_thread.start()
    log.info("✓ 传感器监控线程已启动")

    # 3. 启动 Flask Web 服务线程 (守护线程)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    log.info("✓ Flask Web服务器线程已启动")

    # 等待片刻让子线程初始化
    time.sleep(1)

    log.info("=" * 60)
    log.info("Modbus TCP 服务器启动，监听端口 502")
    log.info(f"监控寄存器: {REG_ADDR} (初始值: {REG_INITIAL_VALUE})")
    log.info(f"物料寄存器: {REG_MATERIAL_ADDR} (初始值: 0)")
    log.info(f"传感器监控地址: {SENSOR_URL}")
    log.info("Web界面访问地址:")
    log.info("  - http://localhost:5000")
    log.info("  - http://192.168.1.32:5000")  # 请根据实际本机IP调整
    log.info("测试API地址: http://192.168.1.32:5000/api/test")
    log.info("传感器API地址: http://192.168.1.32:5000/api/sensor_stats")
    log.info("=" * 60)

    try:
        # 启动 Modbus TCP 服务器，这将阻塞主线程
        StartTcpServer(context=server_context, address=("0.0.0.0", 502))
    except KeyboardInterrupt:
        log.info("收到中断信号，服务器正在关闭...")
    except Exception as e:
        log.error(f"服务器启动失败: {e}")


if __name__ == "__main__":
    # 确保依赖库 requests 已安装，如果没有则自动安装
    try:
        import requests
    except ImportError:
        log.warning("未安装requests库，正在自动安装...")
        import subprocess
        import sys

        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        import requests

    # 执行主程序
    main()
