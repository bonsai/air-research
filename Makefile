.PHONY: all report clean server bq-setup oracle oracle-shell oracle-query

GCP_PROJECT ?= your-project-id
BQ_DATASET  ?= air_research
BQ_TABLE    ?= sensor_log

all: report

# ── ローカル分析 ────────────────────────────────────────────────
report:
	cd analysis && python3 analyze.py \
		../data/sample/sensor_log.json \
		--out ../report/index.html \
		--json ../report/analysis_result.json

# ── BQ 本番サーバー ──────────────────────────────────────────────
server:
	cd server && GCP_PROJECT=$(GCP_PROJECT) uvicorn ingest:app --host 0.0.0.0 --port 8000

bq-setup:
	bq mk --dataset $(GCP_PROJECT):$(BQ_DATASET) || true
	bq mk --table $(GCP_PROJECT):$(BQ_DATASET).$(BQ_TABLE) server/bq_schema.json

# ── Oracle ローカル ─────────────────────────────────────────────
oracle:
	docker compose up -d oracle
	@echo "Waiting for Oracle to start (60-90s first time)..."
	@sleep 5
	@docker compose logs --tail=5 oracle

oracle-shell:
	docker compose exec oracle sqlplus air_app/air_pass@FREEPDB1

oracle-query:
	python3 db/query.py

clean:
	rm -f report/index.html report/analysis_result.json

oracle-down:
	docker compose down
