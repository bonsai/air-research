# Ingest Server

ESP32 → `POST /ingest` → BigQuery streaming insert

## セットアップ

### 1. BQテーブル作成

```bash
export GCP_PROJECT=your-project-id

bq mk --dataset ${GCP_PROJECT}:air_research

bq mk --table \
  ${GCP_PROJECT}:air_research.sensor_log \
  bq_schema.json
```

### 2. 認証

```bash
# 開発環境
gcloud auth application-default login

# 本番 (サービスアカウント)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

### 3. サーバー起動

```bash
pip install -r requirements.txt

export GCP_PROJECT=your-project-id
uvicorn ingest:app --host 0.0.0.0 --port 8000
```

### 4. 動作確認

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_id":"poc-001","timestamp":1000,
    "temperature":25.0,"humidity":55.0,"pressure":1013.0,
    "gas_resistance":38.0,"iaq":95.0,"turbulence":0.03,"discomfort":28.5
  }'
# → 204 No Content
```

### 5. BQで確認

```sql
SELECT * FROM `your-project.air_research.sensor_log`
ORDER BY received_at DESC
LIMIT 20;
```

## ESP32側の設定

`firmware/air_sensor.ino` の `SERVER_URL` をPCのIPに合わせる:

```cpp
#define SERVER_URL "http://192.168.1.100:8000/ingest"
```
