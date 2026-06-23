# AIR Research PoC

「なんとなく不快な空間」を数値化・可視化するシステムのプロトタイプ。

```
firmware/   ESP32+BME680 センサーファームウェア (Arduino)
analysis/   Pythonデータ解析・レポート生成
data/       センサーログ (JSON)
report/     生成済みHTMLレポート
```

## クイックスタート

```bash
# サンプルデータでレポート生成
cd analysis
python3 analyze.py

# 出力: report/index.html をブラウザで開く
```

## 測定指標

| 指標 | センサー | 快適範囲 |
|------|----------|---------|
| 温度 | BME680 | 22〜26°C |
| 湿度 | BME680 | 40〜60%RH |
| VOC/IAQ | BME680 | < 100 |
| 気流乱流 | MPU6050 | < 0.05 m/s² |
| **体感不快指数** | 合成 | **< 30** |

## ハードウェア (1台 約¥3,000)

ESP32 + BME680 + MPU6050 で構成。
WiFiでデータをリアルタイム送信 or シリアルでローカル取得。

詳細 → `firmware/README.md`
