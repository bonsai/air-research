/*
 * AIR Research PoC Firmware
 * Hardware: ESP32 + BME680 (I2C) + MPU6050 (気流振動補助)
 *
 * 測定項目:
 *   - 温度 / 湿度 / 気圧 (BME680)
 *   - VOC ガス抵抗値 → IAQ推定 (BME680)
 *   - 微振動 (MPU6050) → 気流乱流指標
 *
 * 出力: UART JSON + WiFi → HTTP POST (analysis server)
 */

#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Adafruit_BME680.h>
#include <Adafruit_MPU6050.h>

// ── 設定 ──────────────────────────────────────────────
#define SENSOR_ID       "poc-001"
#define WIFI_SSID       "YOUR_SSID"
#define WIFI_PASS       "YOUR_PASSWORD"
#define SERVER_URL      "http://192.168.1.100:8000/ingest"
#define SAMPLE_INTERVAL 5000  // ms

// ── センサーインスタンス ───────────────────────────────
Adafruit_BME680 bme;
Adafruit_MPU6050 mpu;

// IAQ計算用の基準値（初回10サンプルで自動キャリブレーション）
float gasResistanceBaseline = 0;
int calibrationCount = 0;

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);  // SDA=21, SCL=22

  // BME680 初期化
  if (!bme.begin(0x77)) {
    Serial.println("[ERROR] BME680 not found. Check wiring.");
    while (1) delay(100);
  }
  bme.setTemperatureOversampling(BME680_OS_8X);
  bme.setHumidityOversampling(BME680_OS_2X);
  bme.setPressureOversampling(BME680_OS_4X);
  bme.setIIRFilterSize(BME680_FILTER_SIZE_3);
  bme.setGasHeater(320, 150);  // 320°C, 150ms

  // MPU6050 初期化
  if (!mpu.begin()) {
    Serial.println("[WARN] MPU6050 not found. Turbulence disabled.");
  } else {
    mpu.setAccelerometerRange(MPU6050_RANGE_2_G);
    mpu.setGyroRange(MPU6050_RANGE_250_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  }

  // WiFi接続
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting WiFi");
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nConnected: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n[WARN] WiFi failed. Serial-only mode.");
  }

  Serial.println("[INFO] AIR Research sensor ready.");
}

// 気流乱流スコア: 加速度の標準偏差（16サンプル）
float measureTurbulence() {
  const int N = 16;
  float ax_buf[N];
  float sum = 0;
  sensors_event_t a, g, temp;

  for (int i = 0; i < N; i++) {
    mpu.getEvent(&a, &g, &temp);
    ax_buf[i] = a.acceleration.x;
    sum += ax_buf[i];
    delay(10);
  }
  float mean = sum / N;
  float variance = 0;
  for (int i = 0; i < N; i++) {
    variance += (ax_buf[i] - mean) * (ax_buf[i] - mean);
  }
  return sqrt(variance / N);  // m/s² 単位の振動強度
}

// IAQスコア計算 (0〜500, 低いほど良好)
// BME680のガス抵抗値をベースラインと比較
float calcIAQ(float gasResistance, float humidity) {
  if (gasResistanceBaseline == 0) return -1;  // キャリブ中

  // 湿度補正 (40%RH を最適とする)
  float humidityScore = 25.0 * (0.25 / 0.40) * (humidity / 100.0);
  if (humidity >= 38 && humidity <= 42) humidityScore = 25.0;
  else if (humidity < 38) humidityScore = 25.0 * (humidity / 40.0);
  else humidityScore = 25.0 * (80.0 / humidity) / 100.0 * 25.0;

  // ガス抵抗スコア
  float gasScore = (gasResistance / gasResistanceBaseline) * 75.0;
  gasScore = constrain(gasScore, 0, 75);

  float iaqPercent = humidityScore + gasScore;
  return (100.0 - iaqPercent) * 5.0;  // 0〜500にスケール
}

void loop() {
  if (!bme.performReading()) {
    Serial.println("[ERROR] BME680 read failed.");
    delay(SAMPLE_INTERVAL);
    return;
  }

  float temperature   = bme.temperature;
  float humidity      = bme.humidity;
  float pressure      = bme.pressure / 100.0;  // hPa
  float gasResistance = bme.gas_resistance / 1000.0;  // kΩ

  // キャリブレーション（初期10サンプルの移動平均）
  if (calibrationCount < 10) {
    gasResistanceBaseline = (gasResistanceBaseline * calibrationCount + gasResistance)
                            / (calibrationCount + 1);
    calibrationCount++;
  }

  float iaq        = calcIAQ(gasResistance, humidity);
  float turbulence = measureTurbulence();

  // 体感不快指数 (独自): 温度・湿度・IAQ・乱流の重み付け合成
  // PMV的な簡易計算: 26℃/50%RHを快適基準
  float tempDev  = abs(temperature - 26.0);
  float humDev   = abs(humidity - 50.0) / 2.0;
  float iaqNorm  = (iaq > 0) ? min(iaq / 200.0, 1.0) : 0;
  float turbNorm = min(turbulence * 20.0, 1.0);
  float discomfortScore = (tempDev * 2.5 + humDev * 1.5 + iaqNorm * 30.0 + turbNorm * 20.0);
  discomfortScore = constrain(discomfortScore, 0, 100);

  // JSON組み立て
  StaticJsonDocument<256> doc;
  doc["sensor_id"]       = SENSOR_ID;
  doc["timestamp"]       = millis();
  doc["temperature"]     = round(temperature * 10) / 10.0;
  doc["humidity"]        = round(humidity * 10) / 10.0;
  doc["pressure"]        = round(pressure * 10) / 10.0;
  doc["gas_resistance"]  = round(gasResistance * 10) / 10.0;
  doc["iaq"]             = round(iaq);
  doc["turbulence"]      = round(turbulence * 1000) / 1000.0;
  doc["discomfort"]      = round(discomfortScore * 10) / 10.0;

  String json;
  serializeJson(doc, json);
  Serial.println(json);

  // WiFi送信
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    int code = http.POST(json);
    if (code != 200) {
      Serial.printf("[WARN] POST failed: %d\n", code);
    }
    http.end();
  }

  delay(SAMPLE_INTERVAL);
}
