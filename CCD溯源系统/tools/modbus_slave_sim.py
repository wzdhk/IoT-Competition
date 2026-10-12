"""Modbus RTU 从站模拟器：扮演 MCU，配合旁听器做端到端联调。
用法: python modbus_slave_sim.py
帧: 主站写单线圈 0x05 → 回显相同帧（从站正常应答）。
"""
import serial, threading, time

PORT = "COM5"   # 与 config.json 的 Sniffer.Port 一致（用虚拟串口对）
BAUD = 9600

def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc

def main():
    s = serial.Serial(PORT, BAUD, timeout=1)
    print(f"slave listening on {PORT}")
    while True:
        head = s.read(2)
        if len(head) < 2:
            continue
        func = head[1]
        n = {0x05: 6, 0x06: 6, 0x0F: 0, 0x10: 0}.get(func, 6)
        body = head + s.read(n)
        if crc16(body[:-2]) != (body[-2] | body[-1] << 8):
            continue
        s.write(body)  # 回显 = 从站应答
        print("frame:", body.hex())

if __name__ == "__main__":
    main()
