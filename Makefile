.PHONY: all report clean server bq-setup

GCP_PROJECT ?= your-project-id
BQ_DATASET  ?= air_research
BQ_TABLE    ?= sensor_log

all: report

report:
	cd analysis && python3 analyze.py \
		../data/sample/sensor_log.json \
		--out ../report/index.html \
		--json ../report/analysis_result.json

server:
	cd server && GCP_PROJECT=$(GCP_PROJECT) uvicorn ingest:app --host 0.0.0.0 --port 8000

bq-setup:
	bq mk --dataset $(GCP_PROJECT):$(BQ_DATASET) || true
	bq mk --table $(GCP_PROJECT):$(BQ_DATASET).$(BQ_TABLE) server/bq_schema.json

clean:
	rm -f report/index.html report/analysis_result.json
