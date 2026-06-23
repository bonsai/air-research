.PHONY: all report clean

all: report

report:
	cd analysis && python3 analyze.py \
		../data/sample/sensor_log.json \
		--out ../report/index.html \
		--json ../report/analysis_result.json

clean:
	rm -f report/index.html report/analysis_result.json
