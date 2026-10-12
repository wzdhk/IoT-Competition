/**
 * ESP32-S3 主站 - 继电器控制接收端
 *
 * 通过 ESP-NOW 接收指令（发送端为 ESP8266）：
 *   "1" → GPIO4 低2秒→高
 *   "2" → GPIO5 低2秒→高
 *   "3" → GPIO6 低2秒→高
 */

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

#define RELAY1_PIN  4    // GPIO4
#define RELAY2_PIN  5    // GPIO5
#define RELAY3_PIN  6    // GPIO6

#define RELAY_ON    LOW    // 低电平触发: 0V = 吸合
#define RELAY_OFF   HIGH   // 3.3V = 断开

#define TRIGGER_COOLDOWN_MS  10000   // 同一路继电器 10 秒内只触发一次

// ==================== 继电器状态 ====================
struct RelayState {
  bool active = false;
  unsigned long timer = 0;         // 下一次动作的时间点
  unsigned long lastTrigger = 0;   // 上次触发时间(用于10秒冷却)
  bool triggered = false;          // 是否触发过(首次触发不受冷却限制)
};

RelayState relay1;
RelayState relay2;
RelayState relay3;

// ==================== 启动继电器脉冲 ====================
// 启动继电器脉冲; 返回 false 表示处于 10 秒冷却中未触发
bool startPulse(RelayState &relay, int pin) {
  unsigned long now = millis();
  if (relay.triggered && (long)(now - relay.lastTrigger) < TRIGGER_COOLDOWN_MS) {
    return false;   // 10 秒内已触发过, 忽略
  }
  relay.triggered = true;
  relay.lastTrigger = now;

  relay.active = true;
  relay.timer  = now + 2000;              // 吸合2秒后断开
  digitalWrite(pin, RELAY_ON);
  return true;
}

// ==================== 状态机更新 ====================
void updateRelay(RelayState &relay, int pin) {
  if (!relay.active) return;

  unsigned long now = millis();
  if ((long)(now - relay.timer) < 0) return;  // 还没到时间

  // 吸合2秒完成 → 断开并结束
  digitalWrite(pin, RELAY_OFF);
  relay.active = false;
}

// ==================== ESP-NOW 接收回调 ====================
// arduino-esp32 core 3.x 用新签名(info), 2.x 用旧签名(mac 指针), 这里做兼容
#if ESP_ARDUINO_VERSION_MAJOR >= 3
void onDataRecv(const esp_now_recv_info_t *info, const uint8_t *incomingData, int len) {
  const uint8_t *mac = info->src_addr;
#else
void onDataRecv(const uint8_t *mac, const uint8_t *incomingData, int len) {
#endif
  char received[32] = {0};
  int copyLen = len < 31 ? len : 31;
  memcpy(received, incomingData, copyLen);

  Serial.print("收到: \"");
  Serial.print(received);
  Serial.print("\" 来自 ");
  for (int i = 0; i < 6; i++) {
    Serial.printf("%02X", mac[i]);
    if (i < 5) Serial.print(":");
  }
  Serial.println();

  if (strcmp(received, "1") == 0) {
    if (startPulse(relay1, RELAY1_PIN))
      Serial.println("→ GPIO4 低高");
    else
      Serial.println("→ GPIO4 10秒冷却中, 忽略");
  }
  else if (strcmp(received, "2") == 0) {
    if (startPulse(relay2, RELAY2_PIN))
      Serial.println("→ GPIO5 低高");
    else
      Serial.println("→ GPIO5 10秒冷却中, 忽略");
  }
  else if (strcmp(received, "3") == 0) {
    if (startPulse(relay3, RELAY3_PIN))
      Serial.println("→ GPIO6 低高");
    else
      Serial.println("→ GPIO6 10秒冷却中, 忽略");
  }
  else {
    Serial.print("→ 未知指令: ");
    Serial.println(received);
  }
}

// ==================== 初始化 ====================
void setup() {
  Serial.begin(115200);

  pinMode(RELAY1_PIN, OUTPUT);
  pinMode(RELAY2_PIN, OUTPUT);
  pinMode(RELAY3_PIN, OUTPUT);
  digitalWrite(RELAY1_PIN, RELAY_OFF);
  digitalWrite(RELAY2_PIN, RELAY_OFF);
  digitalWrite(RELAY3_PIN, RELAY_OFF);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);   // 信道1, 与 ESP8266 发送端一致

  Serial.print("本机MAC: ");
  Serial.println(WiFi.macAddress());

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW 初始化失败!");
    return;
  }
  esp_now_register_recv_cb(onDataRecv);

  Serial.println("ESP-NOW 就绪");
}

// ==================== 主循环 ====================
void loop() {
  updateRelay(relay1, RELAY1_PIN);
  updateRelay(relay2, RELAY2_PIN);
  updateRelay(relay3, RELAY3_PIN);
}
