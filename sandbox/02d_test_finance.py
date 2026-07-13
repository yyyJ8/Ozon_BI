"""
Ozon API - 验证 2d: 财务流水
接口: POST /v3/finance/transaction/list
用途: 获取佣金、物流费、仓储费、退款等交易明细
      用于净利润计算和费用构成分析

注意: v3/finance 接口的日期需要 protobuf timestamp 格式
输出: sandbox/output/02d_finance_sample.json
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

date_to = datetime.now()
date_from = date_to - timedelta(days=30)

def fmt_dt(dt):
    """protobuf Timestamp: RFC 3339 with T and Z"""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

print("=== 2d: 财务流水 /v3/finance/transaction/list ===")
print("日期范围: %s ~ %s" % (fmt_dt(date_from), fmt_dt(date_to)))

all_ops = []
for page in range(1, 6):
    resp = client.post("/v3/finance/transaction/list", json={
        "filter": {
            "date": {"from": fmt_dt(date_from), "to": fmt_dt(date_to)}
        },
        "page": page,
        "page_size": 100,
    })
    if resp.status_code != 200:
        print("第 %d 页出错: %s" % (page, resp.text[:300]))
        break
    ops = resp.json().get("result", {}).get("operations", [])
    if not ops:
        print("第 %d 页: 无数据，结束" % page)
        break
    all_ops.extend(ops)
    print("第 %d 页: %d 条 (累计 %d)" % (page, len(ops), len(all_ops)))

if not all_ops:
    print("无财务数据返回")
    client.close()
    exit()

# 统计 operation_type 分布（关键：知道有哪些费用类型）
type_dist = {}
for op in all_ops:
    t = op.get("operation_type", "unknown")
    type_dist[t] = type_dist.get(t, 0) + 1

print("\n共 %d 条财务记录" % len(all_ops))
print("字段列表: %s" % list(all_ops[0].keys()))
print("\noperation_type 分布（费用类型）:")
for t, c in sorted(type_dist.items(), key=lambda x: -x[1]):
    # 金额统计
    amounts = [float(op.get("amount", 0)) for op in all_ops if op.get("operation_type") == t]
    total_amt = sum(amounts)
    print("  %s: %d 条, 合计 %.2f RUB" % (t, c, total_amt))

output = {
    "total": len(all_ops),
    "fields": list(all_ops[0].keys()),
    "operation_type_distribution": {t: {"count": c} for t, c in type_dist.items()},
    "first_item": all_ops[0],
    "all_operations": all_ops,
}
path = os.path.join(OUTPUT_DIR, "02d_finance_sample.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print("\n已保存: %s" % path)
client.close()
