#!/usr/bin/env python3
"""
AIR Research - 不快空間分析エンジン
入力: センサーJSONログ
出力: analysis_result.json + report/index.html
"""

import json
import math
import argparse
from pathlib import Path
from datetime import datetime


# ── 閾値定義 ─────────────────────────────────────────────────────────────────

THRESHOLDS = {
    "temperature": {"ok": (22, 26), "warn": (20, 28), "unit": "°C"},
    "humidity":    {"ok": (40, 60), "warn": (35, 65), "unit": "%RH"},
    "iaq":         {"ok": (0, 100), "warn": (0, 150), "unit": ""},
    "turbulence":  {"ok": (0, 0.05), "warn": (0, 0.12), "unit": "m/s²"},
    "discomfort":  {"ok": (0, 30), "warn": (0, 50), "unit": "pt"},
}

FACTOR_LABELS = {
    "temperature": "温度",
    "humidity":    "湿度",
    "iaq":         "空気質(IAQ)",
    "turbulence":  "気流乱流",
    "discomfort":  "体感不快指数",
}


# ── 分析関数 ─────────────────────────────────────────────────────────────────

def load_data(path: str) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def stats(values: list[float]) -> dict:
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    return {
        "mean":   round(mean, 2),
        "min":    round(min(values), 2),
        "max":    round(max(values), 2),
        "std":    round(math.sqrt(variance), 2),
        "p95":    round(sorted(values)[int(n * 0.95)], 2),
    }


def rate_factor(key: str, mean: float) -> str:
    t = THRESHOLDS[key]
    lo_ok, hi_ok   = t["ok"]
    lo_warn, hi_warn = t["warn"]
    if lo_ok <= mean <= hi_ok:
        return "good"
    if lo_warn <= mean <= hi_warn:
        return "warn"
    return "bad"


def detect_events(records: list[dict]) -> list[dict]:
    """不快スコアが閾値を超えた区間を検出"""
    events = []
    in_event = False
    start = None
    for r in records:
        if r["discomfort"] > 50 and not in_event:
            in_event = True
            start = r["timestamp"]
        elif r["discomfort"] <= 50 and in_event:
            in_event = False
            events.append({
                "start_ms": start,
                "end_ms":   r["timestamp"],
                "duration_s": round((r["timestamp"] - start) / 1000),
                "type": "high_discomfort",
            })
    if in_event:
        events.append({
            "start_ms": start,
            "end_ms":   records[-1]["timestamp"],
            "duration_s": round((records[-1]["timestamp"] - start) / 1000),
            "type": "high_discomfort",
        })
    return events


def find_root_causes(factor_ratings: dict, factor_stats: dict) -> list[str]:
    causes = []
    if factor_ratings["temperature"] != "good":
        mean = factor_stats["temperature"]["mean"]
        if mean > 26:
            causes.append(f"室温が高め ({mean}°C) — 冷房設定または日射遮蔽を確認")
        else:
            causes.append(f"室温が低め ({mean}°C) — 暖房または断熱を確認")
    if factor_ratings["humidity"] != "good":
        mean = factor_stats["humidity"]["mean"]
        if mean > 60:
            causes.append(f"湿度過多 ({mean}%RH) — 換気または除湿を推奨")
        else:
            causes.append(f"湿度不足 ({mean}%RH) — 加湿を推奨")
    if factor_ratings["iaq"] != "good":
        causes.append(f"IAQ悪化 (平均{factor_stats['iaq']['mean']}) — CO₂蓄積またはVOC発生源を調査")
    if factor_ratings["turbulence"] != "good":
        causes.append(f"気流乱流あり (平均{factor_stats['turbulence']['mean']}m/s²) — 吹き出し口・障害物の配置を確認")
    if not causes:
        causes.append("測定値は概ね快適範囲内")
    return causes


def analyze(data_path: str) -> dict:
    records = load_data(data_path)
    keys = ["temperature", "humidity", "pressure", "gas_resistance", "iaq", "turbulence", "discomfort"]

    factor_stats = {k: stats([r[k] for r in records]) for k in keys}
    factor_ratings = {
        k: rate_factor(k, factor_stats[k]["mean"])
        for k in THRESHOLDS
    }

    events = detect_events(records)
    causes = find_root_causes(factor_ratings, factor_stats)

    # 総合スコア (0〜100, 高いほど良好)
    bad_count  = sum(1 for r in factor_ratings.values() if r == "bad")
    warn_count = sum(1 for r in factor_ratings.values() if r == "warn")
    overall = max(0, 100 - bad_count * 30 - warn_count * 15)

    return {
        "generated_at":   datetime.now().isoformat(),
        "sensor_id":      records[0]["sensor_id"],
        "sample_count":   len(records),
        "duration_s":     round((records[-1]["timestamp"] - records[0]["timestamp"]) / 1000),
        "overall_score":  overall,
        "factor_stats":   factor_stats,
        "factor_ratings": factor_ratings,
        "events":         events,
        "root_causes":    causes,
        "raw":            records,
    }


# ── HTMLレポート生成 ──────────────────────────────────────────────────────────

def render_html(result: dict, out_path: str):
    r = result
    rating_badge = {
        "good": '<span class="badge good">良好</span>',
        "warn": '<span class="badge warn">注意</span>',
        "bad":  '<span class="badge bad">要改善</span>',
    }
    score_color = "#2ecc71" if r["overall_score"] >= 70 else "#e67e22" if r["overall_score"] >= 40 else "#e74c3c"

    # 時系列データをJSに渡す
    labels     = [str(d["timestamp"] // 1000) + "s" for d in r["raw"]]
    discomfort = [d["discomfort"] for d in r["raw"]]
    temperature = [d["temperature"] for d in r["raw"]]
    humidity   = [d["humidity"] for d in r["raw"]]
    iaq        = [d["iaq"] for d in r["raw"]]

    factor_rows = ""
    for key, label in FACTOR_LABELS.items():
        st = r["factor_stats"][key]
        badge = rating_badge[r["factor_ratings"][key]]
        unit = THRESHOLDS[key]["unit"]
        factor_rows += f"""
        <tr>
          <td>{label}</td>
          <td>{st['mean']}{unit}</td>
          <td>{st['min']} – {st['max']}{unit}</td>
          <td>{st['p95']}{unit}</td>
          <td>{badge}</td>
        </tr>"""

    cause_items = "".join(f"<li>{c}</li>" for c in r["root_causes"])
    event_section = ""
    if r["events"]:
        event_rows = "".join(
            f"<tr><td>{e['start_ms']//1000}s</td><td>{e['end_ms']//1000}s</td>"
            f"<td>{e['duration_s']}秒</td><td>高不快ゾーン</td></tr>"
            for e in r["events"]
        )
        event_section = f"""
        <h2>検出イベント</h2>
        <table>
          <tr><th>開始</th><th>終了</th><th>継続時間</th><th>種別</th></tr>
          {event_rows}
        </table>"""

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>AIR Research — 空間環境レポート</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Hiragino Sans','Noto Sans JP',sans-serif;background:#f4f6f9;color:#2c3e50;font-size:14px}}
    .page{{max-width:900px;margin:0 auto;padding:24px}}
    header{{background:#1a252f;color:#fff;padding:24px 32px;border-radius:12px;margin-bottom:24px;display:flex;justify-content:space-between;align-items:center}}
    header h1{{font-size:22px;font-weight:700;letter-spacing:.05em}}
    header .meta{{font-size:12px;opacity:.7;text-align:right;line-height:1.8}}
    .score-card{{background:#fff;border-radius:12px;padding:24px;margin-bottom:20px;display:flex;align-items:center;gap:32px;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
    .score-ring{{width:100px;height:100px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:700;color:#fff;background:{score_color};flex-shrink:0}}
    .score-desc h2{{font-size:18px;margin-bottom:8px}}
    .score-desc p{{color:#666;line-height:1.7}}
    h2{{font-size:16px;font-weight:700;margin:0 0 12px;padding-bottom:8px;border-bottom:2px solid #eee}}
    .card{{background:#fff;border-radius:12px;padding:20px;margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
    table{{width:100%;border-collapse:collapse}}
    th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid #eee}}
    th{{background:#f8f9fa;font-weight:600;font-size:13px}}
    .badge{{display:inline-block;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:600}}
    .badge.good{{background:#d5f5e3;color:#1e8449}}
    .badge.warn{{background:#fef9e7;color:#b7770d}}
    .badge.bad{{background:#fde8e8;color:#c0392b}}
    .causes{{padding-left:20px}}
    .causes li{{margin-bottom:8px;line-height:1.6}}
    .chart-wrap{{position:relative;height:220px;margin-top:8px}}
    .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
    footer{{text-align:center;color:#999;font-size:12px;margin-top:32px;padding-top:16px;border-top:1px solid #eee}}
    @media(max-width:600px){{.grid2{{grid-template-columns:1fr}}.score-card{{flex-direction:column}}}}
  </style>
</head>
<body>
<div class="page">
  <header>
    <div>
      <h1>空間環境レポート</h1>
      <div style="font-size:13px;opacity:.8;margin-top:4px">AIR Research PoC</div>
    </div>
    <div class="meta">
      センサー: {r['sensor_id']}<br>
      測定時間: {r['duration_s']}秒 / {r['sample_count']}サンプル<br>
      生成: {r['generated_at'][:16].replace('T',' ')}
    </div>
  </header>

  <div class="score-card">
    <div class="score-ring">{r['overall_score']}</div>
    <div class="score-desc">
      <h2>総合快適スコア</h2>
      <p>{"この空間は概ね快適な環境です。" if r['overall_score']>=70 else "一部の指標に改善余地があります。" if r['overall_score']>=40 else "複数の要因で不快感が生じています。改善を推奨します。"}</p>
    </div>
  </div>

  <div class="card">
    <h2>各指標サマリー</h2>
    <table>
      <tr><th>指標</th><th>平均値</th><th>範囲</th><th>P95</th><th>評価</th></tr>
      {factor_rows}
    </table>
  </div>

  <div class="card">
    <h2>体感不快指数 推移</h2>
    <div class="chart-wrap">
      <canvas id="mainChart"></canvas>
    </div>
  </div>

  <div class="grid2">
    <div class="card">
      <h2>温度 / 湿度</h2>
      <div class="chart-wrap">
        <canvas id="thChart"></canvas>
      </div>
    </div>
    <div class="card">
      <h2>空気質 (IAQ)</h2>
      <div class="chart-wrap">
        <canvas id="iaqChart"></canvas>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>原因分析・改善提言</h2>
    <ul class="causes">
      {cause_items}
    </ul>
  </div>

  {event_section}

  <footer>AIR Research PoC — 測定データは参考値です。詳細は専門家による現地調査をご依頼ください。</footer>
</div>

<script>
const labels = {json.dumps(labels, ensure_ascii=False)};
const discomfort = {json.dumps(discomfort)};
const temperature = {json.dumps(temperature)};
const humidity = {json.dumps(humidity)};
const iaq = {json.dumps(iaq)};

const defaults = {{
  pointRadius: 3,
  borderWidth: 2,
  tension: 0.3,
  fill: false,
}};

new Chart(document.getElementById('mainChart'), {{
  type: 'line',
  data: {{
    labels,
    datasets: [{{
      ...defaults,
      label: '体感不快指数',
      data: discomfort,
      borderColor: '#e74c3c',
      backgroundColor: 'rgba(231,76,60,.08)',
      fill: true,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    scales: {{
      y: {{ min: 0, max: 100, title: {{ display: true, text: 'discomfort score' }} }},
      x: {{ ticks: {{ maxTicksLimit: 8 }} }}
    }},
    plugins: {{
      annotation: {{ annotations: {{
        warnLine: {{ type: 'line', yMin: 50, yMax: 50, borderColor: '#e67e22', borderDash: [4,4] }},
      }} }}
    }}
  }}
}});

new Chart(document.getElementById('thChart'), {{
  type: 'line',
  data: {{
    labels,
    datasets: [
      {{ ...defaults, label: '温度(°C)', data: temperature, borderColor: '#e67e22', yAxisID: 'yT' }},
      {{ ...defaults, label: '湿度(%)', data: humidity, borderColor: '#3498db', yAxisID: 'yH' }},
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    scales: {{
      yT: {{ position: 'left',  min: 15, max: 35, title: {{ display: true, text: '°C' }} }},
      yH: {{ position: 'right', min: 30, max: 80, title: {{ display: true, text: '%' }}, grid: {{ drawOnChartArea: false }} }},
      x:  {{ ticks: {{ maxTicksLimit: 6 }} }}
    }}
  }}
}});

new Chart(document.getElementById('iaqChart'), {{
  type: 'line',
  data: {{
    labels,
    datasets: [{{
      ...defaults,
      label: 'IAQ',
      data: iaq,
      borderColor: '#9b59b6',
      backgroundColor: 'rgba(155,89,182,.08)',
      fill: true,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    scales: {{
      y: {{ min: 0, title: {{ display: true, text: 'IAQ' }} }},
      x: {{ ticks: {{ maxTicksLimit: 6 }} }}
    }}
  }}
}});
</script>
</body>
</html>"""

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        f.write(html)
    print(f"[INFO] Report saved: {out_path}")


# ── エントリポイント ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIR Research 不快空間分析")
    parser.add_argument("data", nargs="?", default="../data/sample/sensor_log.json",
                        help="センサーJSONファイルパス")
    parser.add_argument("--out", default="../report/index.html",
                        help="レポートHTML出力先")
    parser.add_argument("--json", default="../report/analysis_result.json",
                        help="分析結果JSON出力先")
    args = parser.parse_args()

    result = analyze(args.data)

    # JSON結果保存
    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    with open(args.json, "w") as f:
        json.dump({k: v for k, v in result.items() if k != "raw"}, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Analysis saved: {args.json}")

    render_html(result, args.out)
    print("[DONE]")
