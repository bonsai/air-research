#!/usr/bin/env python3
"""
AIR Research — Ingest Server
ESP32 → POST /ingest → BigQuery streaming insert
"""

import os
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── 設定 ──────────────────────────────────────────────────────────────────────
GCP_PROJECT = os.environ["GCP_PROJECT"]          # 例: my-project-123
BQ_DATASET  = os.environ.get("BQ_DATASET", "air_research")
BQ_TABLE    = os.environ.get("BQ_TABLE",   "sensor_log")

bq = bigquery.Client(project=GCP_PROJECT)
table_ref = f"{GCP_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"

app = FastAPI(title="AIR Research Ingest")


# ── スキーマ ──────────────────────────────────────────────────────────────────
class SensorPayload(BaseModel):
    sensor_id:      str
    timestamp:      int              # ESP32 millis()
    temperature:    float
    humidity:       float
    pressure:       float
    gas_resistance: float
    iaq:            float
    turbulence:     float
    discomfort:     float = Field(ge=0, le=100)


# ── エンドポイント ─────────────────────────────────────────────────────────────
@app.post("/ingest", status_code=204)
async def ingest(payload: SensorPayload):
    row = payload.model_dump()
    row["received_at"] = datetime.now(timezone.utc).isoformat()

    errors = bq.insert_rows_json(table_ref, [row])
    if errors:
        log.error("BQ insert error: %s", errors)
        raise HTTPException(status_code=500, detail="BigQuery insert failed")

    log.info("ok sensor=%s discomfort=%.1f", payload.sensor_id, payload.discomfort)
    return


@app.get("/health")
async def health():
    return {"status": "ok"}
