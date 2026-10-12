#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <espnow.h>
#include <string.h>

// ===== ESP-NOW 目标主站 =====
uint8_t masterMac[] = {0xA4, 0xCB, 0x8F, 0xD6, 0x16, 0x70};

void onDataSent(uint8_t *macAddr, uint8_t status) {
  Serial.print("send status=");
  Serial.print(status);
  Serial.println(status == 0 ? "  [对方已ACK]" : "  [无ACK/失败]");
}

// ===== 发送限流: 每 5 秒最多发送 1 次 =====
#define SEND_INTERVAL_MS 5000
uint32_t lastSendMs = 0;
bool     everSent   = false;

// 收到有效数字 1~4 就发一条 1 字节 ESP-NOW 消息 (受 5 秒限流)
void sendDigit(char d) {
  if (d < '1' || d > '4') return;

  uint32_t now = millis();
  if (everSent && now - lastSendMs < SEND_INTERVAL_MS) {
    Serial.print("[冷却中, 忽略 ");
    Serial.print(d);
    Serial.println("]");
    return;
  }
  everSent   = true;
  lastSendMs = now;

  Serial.print("[发送 ");
  Serial.print(d);
  Serial.println("]");
  int ret = esp_now_send(masterMac, (uint8_t *)&d, 1);
  if (ret != 0) {
    Serial.print("esp_now_send 返回错误码 ");
    Serial.println(ret);
  }
}

// ===== SenRayVar 协议帧接收 =====
// 帧结构 (小端): magic=0xAA88(2) msg_id(2) frag_id(2) data_len(2) flags(1) cmd(1) crc(1) + payload
// 线上字节序: 0x88 0xAA | msg_id | frag_id | len_lo len_hi | flags | cmd | crc | payload...
#define HEADER_SIZE 11
#define RX_BUF_SIZE 1024
#define U_CMD_INTERFACE_OUTPUT 40

uint8_t rxBuf[RX_BUF_SIZE];
size_t  rxLen = 0;

// cmd=40 的 payload 就是原始分类结果 (ASCII '1'~'4', 可能带 \r\n)
void handleOutput(const uint8_t* payload, size_t len) {
  for (size_t i = 0; i < len; i++) {
    if (payload[i] >= '1' && payload[i] <= '4') {
      sendDigit((char)payload[i]);
      return;
    }
  }
  // 没找到 1~4, 打印原始 payload 便于排查
  Serial.print("[cmd=40 未识别到1~4] ");
  Serial.write(payload, len);
  Serial.println();
}

// 解析 SenRayVar 帧
void processRx() {
  while (Serial.available()) {
    uint8_t c = Serial.read();
    if (rxLen < RX_BUF_SIZE) {
      rxBuf[rxLen++] = c;
    } else {
      // 缓冲区满, 丢最旧字节防止死锁
      memmove(rxBuf, rxBuf + 1, rxLen - 1);
      rxBuf[rxLen - 1] = c;
    }
  }

  while (rxLen >= HEADER_SIZE) {
    if (rxBuf[0] == 0x88 && rxBuf[1] == 0xAA) {          // 帧头
      uint16_t dataLen = rxBuf[6] | (rxBuf[7] << 8);
      if (dataLen > RX_BUF_SIZE - HEADER_SIZE) {          // 异常帧, 丢 1 字节重同步
        memmove(rxBuf, rxBuf + 1, rxLen - 1);
        rxLen--;
        continue;
      }
      size_t totalLen = HEADER_SIZE + dataLen;
      if (rxLen < totalLen) break;                        // 数据未收齐, 等待

      uint8_t crc = 0;                                    // XOR 校验 (跳过 crc 字段)
      for (size_t i = 0; i < totalLen; i++) {
        if (i == 10) continue;
        crc ^= rxBuf[i];
      }
      if (crc == rxBuf[10]) {
        if (rxBuf[9] == U_CMD_INTERFACE_OUTPUT) {         // cmd=40 识别结果
          handleOutput(rxBuf + HEADER_SIZE, dataLen);
        }
      } else {
        Serial.println("[CRC 校验失败, 丢弃该帧]");
      }

      memmove(rxBuf, rxBuf + totalLen, rxLen - totalLen);
      rxLen -= totalLen;
    } else {
      bool found = false;                                 // 搜索下一个 0x88 0xAA
      for (size_t i = 1; i + 1 < rxLen; i++) {
        if (rxBuf[i] == 0x88 && rxBuf[i + 1] == 0xAA) {
          memmove(rxBuf, rxBuf + i, rxLen - i);
          rxLen -= i;
          found = true;
          break;
        }
      }
      if (!found) {
        if (rxBuf[rxLen - 1] == 0x88) {                   // 保留可能是帧头首字节的 0x88
          rxBuf[0] = 0x88;
          rxLen = 1;
        } else {
          rxLen = 0;
        }
      }
    }
  }
}

void setup() {
  Serial.begin(115200, SERIAL_8N1);
  delay(500);
  Serial.println("[boot] SenRayVar 帧接收 (RX=GPIO3)");

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  if (esp_now_init() != 0) {
    Serial.println("ESP-NOW init FAIL");
    delay(1000);
    ESP.restart();
  }
  esp_now_set_self_role(ESP_NOW_ROLE_CONTROLLER);
  esp_now_register_send_cb(onDataSent);
  esp_now_add_peer(masterMac, ESP_NOW_ROLE_SLAVE, 1, NULL, 0);

  Serial.println("=== SenRayVar 协议 ===");
  Serial.println("解析 88 AA 帧 -> cmd=40 数字 -> ESP-NOW 1~4");
}

void loop() {
  processRx();
  yield();
}
