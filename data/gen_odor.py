#!/usr/bin/env python3
"""
臭気ダミーデータ生成
10物質 × 10分間隔 × 3日分
シナリオ: トイレ / 調理 / 香水 / 柔軟剤
"""

import json, math, random
from datetime import datetime, timedelta, timezone

random.seed(42)

JST = timezone(timedelta(hours=9))
START = datetime(2026, 6, 21, 0, 0, tzinfo=JST)
DAYS  = 3
STEP  = timedelta(minutes=10)

# ── 10物質定義 ────────────────────────────────────────────────
# name, unit, baseline_ppb, scenario
SUBSTANCES = [
    # --- トイレ系 ---
    {"id": "NH3",    "name": "アンモニア",         "unit": "ppb", "baseline": 8.0,  "scenario": "toilet"},
    {"id": "H2S",    "name": "硫化水素",           "unit": "ppb", "baseline": 0.5,  "scenario": "toilet"},
    {"id": "MeSH",   "name": "メチルメルカプタン", "unit": "ppb", "baseline": 0.08, "scenario": "toilet"},
    # --- 調理系 ---
    {"id": "AcH",    "name": "アセトアルデヒド",   "unit": "ppb", "baseline": 3.0,  "scenario": "cooking"},
    {"id": "TMA",    "name": "トリメチルアミン",   "unit": "ppb", "baseline": 0.3,  "scenario": "cooking"},
    {"id": "AcOH",   "name": "酢酸",               "unit": "ppb", "baseline": 5.0,  "scenario": "cooking"},
    # --- 香水系 ---
    {"id": "LinOH",  "name": "リナロール",         "unit": "ppb", "baseline": 0.5,  "scenario": "perfume"},
    {"id": "EtBenz", "name": "安息香酸エチル",     "unit": "ppb", "baseline": 0.2,  "scenario": "perfume"},
    # --- 柔軟剤系 ---
    {"id": "Lim",    "name": "リモネン",           "unit": "ppb", "baseline": 1.2,  "scenario": "softener"},
    {"id": "Pin",    "name": "α-ピネン",           "unit": "ppb", "baseline": 0.8,  "scenario": "softener"},
]

# ── シナリオ別ピーク時間帯 (hour, 強度倍率, 幅h) ──────────────
PEAKS = {
    "toilet":   [(7.0, 18, 0.5), (8.5, 12, 0.4), (12.5, 8, 0.3),
                 (13.5, 6, 0.3), (18.5, 14, 0.5), (22.0, 5, 0.4)],
    "cooking":  [(7.5, 10, 0.6), (12.0, 22, 0.8), (12.5, 18, 0.6),
                 (18.0, 28, 1.0), (18.5, 24, 0.9), (19.0, 15, 0.7)],
    "perfume":  [(8.5, 30, 0.3), (13.0, 15, 0.2), (17.5, 12, 0.2)],
    "softener": [(7.0, 25, 0.8), (8.0, 18, 0.6), (20.0, 12, 0.5)],
}

def gaussian_peak(hour_now, peak_hour, amplitude, width_h):
    return amplitude * math.exp(-0.5 * ((hour_now - peak_hour) / width_h) ** 2)

def odor_level(substance, dt: datetime) -> float:
    h = dt.hour + dt.minute / 60.0
    base = substance["baseline"]
    scenario = substance["scenario"]

    spike = sum(
        gaussian_peak(h, ph, base * mult, width)
        for ph, mult, width in PEAKS[scenario]
    )

    # 曜日補正: 週末は調理↑, 通勤香水↓
    if dt.weekday() >= 5:
        if scenario == "cooking":  spike *= 1.3
        if scenario == "perfume":  spike *= 0.4
        if scenario == "softener": spike *= 1.5  # 洗濯デー

    noise = random.gauss(0, base * 0.08)
    return max(0.0, round(base + spike + noise, 4))

# ── 生成 ──────────────────────────────────────────────────────
records = []
t = START
total = int(DAYS * 24 * 60 / 10)

for _ in range(total):
    row = {
        "timestamp": t.isoformat(),
        "sensor_id": "poc-001",
    }
    for s in SUBSTANCES:
        row[s["id"]] = odor_level(s, t)
    records.append(row)
    t += STEP

out = "sample/odor_log.json"
import pathlib; pathlib.Path("sample").mkdir(exist_ok=True)
with open(out, "w") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

print(f"Generated {len(records)} records -> {out}")
print(f"Substances: {[s['id'] for s in SUBSTANCES]}")

# メタデータも出力
meta = {"substances": SUBSTANCES, "peaks": PEAKS}
with open("sample/odor_meta.json", "w") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)
print("Meta -> sample/odor_meta.json")
