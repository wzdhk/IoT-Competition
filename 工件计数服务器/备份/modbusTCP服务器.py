#!/usr/bin/env python3
"""
Modbus TCP 服务器，实现寄存器 1001 的上升沿检测与自动复位。
适用于 pymodbus 3.x 版本。
"""

import logging
import threading
import time

from pymodbus.datastore import ModbusSequentialDataBlock, ModbusDeviceContext, ModbusServerContext
from pymodbus.server import StartTcpServer

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

REG_ADDR = 1001
POLL_INTERVAL = 0.5


def poll_register(context, device_id=1):
    """
    后台线程函数：定时读取寄存器值，检测 0 -> 1 上升沿并复位。
    """
    last_value = 0

    while True:
        try:
            current = context[device_id].getValues(3, REG_ADDR, 1)[0]
            if last_value == 0 and current == 1:
                log.info("接收到数据")
                context[device_id].setValues(3, REG_ADDR, [0])
                current = 0
            last_value = current
        except Exception as e:
            log.error(f"轮询过程中发生异常: {e}")
        time.sleep(POLL_INTERVAL)


def main():
    # 创建保持寄存器数据块：地址范围 0～2000，初始值全为 0
    data_block = ModbusSequentialDataBlock(0, [0] * 2000)

    # 创建设备上下文，只使用保持寄存器
    device_context = ModbusDeviceContext(hr=data_block)

    # 创建服务器上下文，从机 ID 为 1
    server_context = ModbusServerContext(devices={1: device_context}, single=False)

    # 启动后台轮询线程
    poll_thread = threading.Thread(target=poll_register, args=(server_context, 1), daemon=True)
    poll_thread.start()

    log.info("Modbus TCP 服务器启动，监听端口 502，寄存器 1001 初始值为 0")
    try:
        StartTcpServer(context=server_context, address=("0.0.0.0", 502))
    except KeyboardInterrupt:
        log.info("收到中断信号，服务器正在关闭...")
    except Exception as e:
        log.error(f"服务器启动失败: {e}")


if __name__ == "__main__":
    main()