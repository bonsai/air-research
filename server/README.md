# AIR Research Server

## 本番 (BigQuery)

```bash
export GCP_PROJECT=my-project
make server
```

## ローカル実験 (Oracle 23c Free)

```bash
# 起動
docker compose up -d oracle

# DDL + サンプルデータ自動投入 (初回のみ60〜90秒)
# 確認
python3 db/query.py
```

## エンドポイント

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ingest` | センサーデータ受信 → BQ |
| GET  | `/health` | ヘルスチェック |
