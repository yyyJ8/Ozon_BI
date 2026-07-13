"""
Ozon API - 验证 2c: 销售分析（核心！）
接口: POST /v1/analytics/data
用途: 按 SKU × 日维度获取销量、收入、退货、曝光、转化率
      这是看板最核心的数据来源

API 实际返回格式:
  result.data[].dimensions = [{"id": "sku_id", "name": "商品名"}, {"id": "date", "name": ""}]
  result.data[].metrics = [val1, val2, ...]  (按请求 metrics 顺序)

本次测试: 不同 metrics 组合，看哪些字段有实际数据
输出: sandbox/output/02c_analytics_sample.json
"""
import json, os
from datetime import datetime, timedelta
import httpx
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

client = httpx.Client(
    base_url="https://api-seller.ozon.ru",
    headers={"Client-Id": os.getenv("OZON_CLIENT_ID"), "Api-Key": os.getenv("OZON_API_KEY"), "Content-Type": "application/json"},
    timeout=30.0,
)

date_to = datetime.now().strftime("%Y-%m-%d")
date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

# ── 测试不同维度组合 ──────────────────────────────────

tests = [
    # (name, dimension, metrics)
    ("sku + day 维度", ["sku", "day"],
     ["ordered_units", "revenue", "returns", "cancellations",
      "session_view", "session_visit", "conversion", "hits_tocart"]),
    ("仅 sku 维度", ["sku"],
     ["ordered_units", "revenue", "returns", "cancellations",
      "session_view", "session_visit", "conversion", "hits_tocart"]),
]

all_results = {}
for test_name, dimension, metrics in tests:
    print("\n=== %s ===" % test_name)
    print("维度: %s" % dimension)
    print("指标: %s" % metrics)

    resp = client.post("/v1/analytics/data", json={
        "date_from": date_from,
        "date_to": date_to,
        "metrics": metrics,
        "dimension": dimension,
        "limit": 500,
        "offset": 0,
    })

    if resp.status_code != 200:
        print("状态: %d, 错误: %s" % (resp.status_code, resp.text[:300]))
        all_results[test_name] = {"_error": resp.text[:300]}
        continue

    data = resp.json()
    rows = data.get("result", {}).get("data", [])
    total = data.get("result", {}).get("total", len(rows))
    print("状态: %d, 返回 %d 行 (总计 %s)" % (resp.status_code, len(rows), total))

    if rows:
        r0 = rows[0]
        dims = r0.get("dimensions", [])
        vals = r0.get("metrics", [])
        print("\n--- 第 1 行样例 ---")
        for d in dims:
            print("  dimension: id=%s  name=%s" % (d.get("id",""), d.get("name","")[:40]))
        print("  metrics 数组: %s" % vals)
        print("  字段映射:")
        for i, m in enumerate(metrics):
            print("    [%d] %s = %s" % (i, m, vals[i] if i < len(vals) else "N/A"))

        # 统计哪些指标有非零数据
        nonzero = {metrics[i]: 0 for i in range(len(metrics))}
        for row in rows:
            for i, m in enumerate(metrics):
                if i < len(row.get("metrics", [])) and row["metrics"][i] != 0:
                    nonzero[m] = nonzero.get(m, 0) + 1
        print("\n  非零指标统计 (有数据的行数):")
        for m, c in sorted(nonzero.items(), key=lambda x: -x[1]):
            print("    %s: %d/%d 行有数据" % (m, c, len(rows)))

    all_results[test_name] = data

# ── 详情页用: 单 SKU 的日趋势 ─────────────────────
# 取第一个有数据的 SKU 看看
print("\n=== 单 SKU 日趋势验证 ===")
# 从 sku-only 结果里找一个 sku_id
sku_only = all_results.get("仅 sku 维度", {})
sku_rows = sku_only.get("result", {}).get("data", [])
if sku_rows and len(sku_rows) > 0:
    first_sku = sku_rows[0]["dimensions"][0]["id"]
    first_name = sku_rows[0]["dimensions"][0].get("name", "")[:30]
    print("取 SKU: %s (%s)" % (first_sku, first_name))

    resp = client.post("/v1/analytics/data", json={
        "date_from": date_from,
        "date_to": date_to,
        "metrics": ["ordered_units", "revenue", "returns", "session_view", "session_visit", "conversion"],
        "dimension": ["sku", "day"],
        "limit": 100,
        "offset": 0,
    })
    data = resp.json()
    rows = data.get("result", {}).get("data", [])
    print("返回 %d 行" % len(rows))
    if rows:
        for row in rows[:5]:
            dims = row["dimensions"]
            vals = row["metrics"]
            print("  %s | %s -> %s" % (dims[0].get("id",""), dims[1].get("id",""), vals))
    all_results["单 SKU 日趋势"] = data

# 保存全部
path = os.path.join(OUTPUT_DIR, "02c_analytics_sample.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)
print("\n全部结果已保存: %s" % path)
client.close()
