# AIR Research

「なんとなく不快な空間」を数値化・可視化するシステム。

## 構成

```
firmware/     ESP32+BME680 センサーファームウェア
server/       FastAPI 受信サーバー (本番: BigQuery)
analysis/     分析エンジン + HTMLレポート生成
data/         データ・サンプル
db/           Oracle 23c Free スキーマ定義 (ローカル実験用)
report/       生成レポート出力
```

## クイックスタート

```bash
# サンプルデータでレポート生成
make report

# 出力: report/index.html
```

## ローカルで Oracle で遊ぶ

```bash
docker compose up -d oracle
python3 db/query.py
```

## 測定指標

| 指標 | センサー | 快適範囲 |
|------|----------|---------|
| 温度 | BME680 | 22〜26°C |
| 湿度 | BME680 | 40〜60%RH |
| VOC/IAQ | BME680 | < 100 |
| 気流乱流 | MPU6050 | < 0.05 m/s² |
| 体感不快指数 | 合成 | < 30 |
