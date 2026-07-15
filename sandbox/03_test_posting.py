"""
Ozon API — 测试 Posting API：追踪订单完整生命周期
接口: /v2/posting/fbo/get (FBO) 和 /v3/posting/fbs/get (FBS)
用途: 查看一个 posting 从创建到退货/完成的完整状态流转
"""
import json, os, httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

client = httpx.Client(
    base_url="https://api-seller.ozon.ru",
    headers={
        "Client-Id": os.getenv("OZON_CLIENT_ID"),
        "Api-Key": os.getenv("OZON_API_KEY"),
        "Content-Type": "application/json",
    },
    timeout=30.0,
)

# 从数据库取几个 posting_number 作为测试样本
import psycopg2
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)
cur = conn.cursor()

# 取非空的 posting_number，优先选有 delivery_schema 的
cur.execute("""
    SELECT DISTINCT posting_number, delivery_schema, operation_type_name, operation_date
    FROM ozon.finance_transactions
    WHERE posting_number IS NOT NULL
      AND delivery_schema = 'FBO'
    ORDER BY operation_date DESC
    LIMIT 5
""")
samples = cur.fetchall()
conn.close()

print("=" * 60)
print("Ozon Posting API — 订单生命周期追踪")
print("=" * 60)

all_results = []

for posting_number, schema, type_name, op_date in samples:
    print(f"\n--- posting_number: {posting_number}")
    print(("  delivery_schema: " + (schema or "N/A") + " | operation: " + (type_name or "N/A"))[:100])

    # 根据 delivery_schema 选接口，如果没有 schema 也尝试 FBO
    if schema == "FBO" or not schema:
        endpoint = "/v2/posting/fbo/get"
    else:
        endpoint = "/v3/posting/fbs/get"

    resp = client.post(endpoint, json={"posting_number": posting_number})

    if resp.status_code == 200:
        data = resp.json()
        result = data.get("result", {})
        status = result.get("status", "N/A")
        status_name = result.get("status_name", "")
        created = result.get("created_at", "")
        in_process = result.get("in_process_at", "")
        shipped = result.get("shipment_date", "")
        delivered = result.get("delivered_date", "")
        cancelled = result.get("cancel_date", "")

        # 状态时间线
        timeline = []
        for s in result.get("analytics_data", []) or []:
            timeline.append(f"{s.get('operation_date', '?')}  {s.get('operation_type_name', '?')}")

        print(f"  status: {status}")
        print(f"  status_name: {status_name}")
        print(f"  created: {created}  →  shipped: {shipped}  →  delivered: {delivered}  →  cancelled: {cancelled}")

        if timeline:
            print(f"  timeline:")
            for t in timeline[-10:]:
                print(f"    {t}")

        all_results.append({
            "posting_number": posting_number,
            "status": status,
            "status_name": status_name,
            "timeline": timeline,
        })
    elif resp.status_code == 404:
        print(f"  [404] posting might be FBS, trying alternate endpoint")
        # 尝试另一个接口
        alt_endpoint = "/v3/posting/fbs/get" if endpoint == "/v2/posting/fbo/get" else "/v2/posting/fbo/get"
        resp2 = client.post(alt_endpoint, json={"posting_number": posting_number})
        if resp2.status_code == 200:
            data = resp2.json()
            result = data.get("result", {})
            print(f"  [OK] {alt_endpoint} success: status={result.get('status')}")
            all_results.append({
                "posting_number": posting_number,
                "status": result.get("status"),
                "endpoint": alt_endpoint,
            })
        else:
            print(f"  [FAIL] both endpoints failed: {resp2.status_code}")
    else:
        print(f"  [FAIL] HTTP {resp.status_code}: {resp.text[:200]}")

# 保存结果
path = os.path.join(OUTPUT_DIR, "03_posting_sample.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

print(f"\nResults saved: {path}")
print(f"Tested {len(samples)} postings, {len(all_results)} succeeded")

client.close()
