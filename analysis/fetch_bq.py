#!/usr/bin/env python3
"""
BigQuery から最新センサーデータを取得して JSON に書き出す
CI/CD (GitHub Actions) から呼ばれる想定
"""

import os
import json
import argparse
from pathlib import Path
from google.cloud import bigquery

GCP_PROJECT = os.environ["GCP_PROJECT"]
BQ_DATASET  = os.environ.get("BQ_DATASET", "air_research")
BQ_TABLE    = os.environ.get("BQ_TABLE",   "sensor_log")

QUERY = f"""
SELECT
  sensor_id, timestamp, received_at,
  temperature, humidity, pressure,
  gas_resistance, iaq, turbulence, discomfort
FROM `{GCP_PROJECT}.{BQ_DATASET}.{BQ_TABLE}`
WHERE DATE(received_at) = CURRENT_DATE('Asia/Tokyo')
ORDER BY received_at ASC
LIMIT 2000
"""

def main(out: str):
    client = bigquery.Client(project=GCP_PROJECT)
    rows = list(client.query(QUERY).result())

    if not rows:
        # BQにデータがない場合はサンプルデータで代替
        sample = Path(__file__).parent / "../data/sample/sensor_log.json"
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(sample.read_text())
        print(f"[WARN] No BQ data today. Using sample. -> {out}")
        return

    records = [dict(r) for r in rows]
    # received_at は datetime → str に変換
    for rec in records:
        if hasattr(rec.get("received_at"), "isoformat"):
            rec["received_at"] = rec["received_at"].isoformat()

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Fetched {len(records)} rows -> {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="../data/latest.json")
    main(parser.parse_args().out)
