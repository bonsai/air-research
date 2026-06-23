# Firmware

## 必要部品

| 部品 | 型番 | 用途 | 単価目安 |
|------|------|------|---------|
| マイコン | ESP32 DevKit | WiFi + 処理 | ¥800 |
| 環境センサー | BME680 | 温度/湿度/気圧/VOC | ¥1,500 |
| 加速度センサー | MPU6050 | 気流乱流検出 | ¥400 |
| ケース | 適宜 | | ¥300〜 |
| **合計** | | | **約¥3,000/台** |

## 配線 (I2C)

```
ESP32        BME680 / MPU6050
GPIO21 ───── SDA
GPIO22 ───── SCL
3.3V  ───── VCC
GND   ───── GND
```

## 必要ライブラリ (Arduino IDE)

- `Adafruit BME680 Library`
- `Adafruit MPU6050`
- `ArduinoJson`

## セットアップ

1. `air_sensor.ino` の `WIFI_SSID` / `WIFI_PASS` / `SERVER_URL` を書き換える
2. Arduino IDE でボード `ESP32 Dev Module` を選択してフラッシュ
3. シリアルモニタ (115200bps) でJSON出力を確認
