#!/usr/bin/env python3
"""
AIR Research — Oracle ローカル接続クライアント
python-oracledb の thin モード (クライアント不要) で接続。
"""
import os
import oracledb

DSN = os.environ.get("DB_DSN", "localhost:1521/FREEPDB1")
USER = os.environ.get("DB_USER", "air_app")
PASS = os.environ.get("DB_PASS", "air_pass")

def connect():
    return oracledb.connect(user=USER, password=PASS, dsn=DSN)

def query(sql: str, **kw):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, **kw)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return rows

if __name__ == "__main__":
    rows = query("SELECT table_name FROM user_tables ORDER BY table_name")
    print(f"Tables ({len(rows)}):")
    for r in rows:
        print(f"  {r['TABLE_NAME']}")

    rows = query("SELECT * FROM v_room_comfort_summary")
    print(f"\nRoom summary ({len(rows)}):")
    for r in rows:
        print(f"  {r['NAME']:20s} IAQ={r['AVG_IAQ']:3d}  comfort={r['AVG_COMFORT']:5.1f}  complaints={r['COMPLAINT_COUNT']}")
