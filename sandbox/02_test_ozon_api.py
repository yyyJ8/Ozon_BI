"""
验证 2: Ozon Seller API 连接 + 数据采样
依次测试:
  1. GET /v3/product/list — 商品列表（分页）
  2. GET /v3/product/info/list — 商品详情（批量）
  3. GET /v1/analytics/data — 销售分析（核心）
  4. GET /v3/finance/transaction/list — 财务流水

重点关注: 实际返回字段、分页方式、日期范围限制
"""
import json
import os
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("OZON_CLIENT_ID")
API_KEY = os.getenv("OZON_API_KEY")
BASE_URL = "https://api-seller.ozon.ru"

headers = {
    "Client-Id": CLIENT_ID,
    "Api-Key": API_KEY,
    "Content-Type": "application/json",
}

client = httpx.Client(base_url=BASE_URL, headers=headers, timeout=30.0)


def print_section(title):
    print()
    print("=" * 60)
    print("  %s" % title)
    print("=" * 60)


def dump(data, max_len=1500):
    """格式化打印 JSON，截断过长内容"""
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if len(text) > max_len:
        print(text[:max_len] + "\n  ... (truncated, %d chars total)" % len(text))
    else:
        print(text)


# ============================================================
print()
print("  Ozon Seller API 验证")
print("  Client-ID: %s" % CLIENT_ID)
print("  Base URL : %s" % BASE_URL)
print()

# ============================================================
# 1. 商品列表
# ============================================================
print_section("1. GET /v3/product/list — 商品列表")

payload = {"filter": {"visibility": "ALL"}, "limit": 5, "last_id": ""}
resp = client.post("/v3/product/list", json=payload)
print("  Status: %d" % resp.status_code)

if resp.status_code == 200:
    data = resp.json()
    total = data.get("total", 0)
    items = data.get("result", {}).get("items", [])
    print("  商品总数: %d" % total)
    print("  本页返回: %d 条" % len(items))
    if items:
        print("  字段列表: %s" % list(items[0].keys()))
        print("  第一条:")
        dump(items[0], max_len=800)
else:
    print("  Error: %s" % resp.text[:500])

# ============================================================
# 2. 商品详情（要有 product_id 才能调）
# ============================================================
print_section("2. GET /v3/product/info/list — 商品详情")

# 拿上一步的 product_id
product_ids = []
if resp.status_code == 200 and items:
    product_ids = [item["product_id"] for item in items if item.get("product_id")]
    print("  获取 %d 个商品详情 ..." % len(product_ids))

    payload = {
        "product_id": product_ids,
        "sku": None  # 用 None 表示取所有 SKU
    }
    resp2 = client.post("/v3/product/info/list", json=payload)
    print("  Status: %d" % resp2.status_code)

    if resp2.status_code == 200:
        info_data = resp2.json()
        products = info_data.get("items", [])
        print("  返回商品数: %d" % len(products))
        if products:
            # Ozon info/list 返回较复杂，看看结构
            p = products[0]
            print("  顶级字段: %s" % list(p.keys()))
            # 提取关键信息
            skus = p.get("skus", [])
            print("  SKU 数量: %d" % len(skus))
            print("  商品名称: %s" % p.get("name", ""))
            print("  Offer ID: %s" % p.get("offer_id", ""))
            print("  价格信息: price=%s, old_price=%s" % (p.get("price"), p.get("old_price")))
            print("  分类 ID : %s" % p.get("category_id"))
            print("  状态    : %s" % p.get("status", {}).get("name", "") if isinstance(p.get("status"), dict) else p.get("status"))
            if skus:
                print("  SKU 示例: %s" % json.dumps(skus[0], ensure_ascii=False, indent=2)[:500])
    else:
        print("  Error: %s" % resp2.text[:500])

# ============================================================
# 3. 销售分析 — 核心！
# ============================================================
print_section("3. GET /v1/analytics/data — 销售分析（核心）")

# 取最近 7 天数据
date_to = datetime.now().strftime("%Y-%m-%d")
date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
print("  日期范围: %s ~ %s" % (date_from, date_to))

# Ozon analytics/data 的已知参数格式
payload = {
    "date_from": date_from,
    "date_to": date_to,
    "metrics": [
        "ordered_units",
        "revenue",
        "returns",
        "cancellations",
        "session_view",
        "session_visit",
        "conversion",
        "avg_order_price",
    ],
    "dimension": ["sku", "day"],
    "limit": 10,
    "offset": 0,
}
resp3 = client.post("/v1/analytics/data", json=payload)
print("  Status: %d" % resp3.status_code)

if resp3.status_code == 200:
    adata = resp3.json()
    result = adata.get("result", {})
    print("  结果 keys: %s" % list(result.keys()))
    rows = result.get("rows", [])
    print("  数据行数: %d" % len(rows))
    if rows:
        print("  行字段: %s" % list(rows[0].keys()))
        # 看 metrics 和 dimensions 的结构
        r = rows[0]
        print("  dimensions: %s" % json.dumps(r.get("dimensions", []), ensure_ascii=False))
        print("  metrics: %s" % json.dumps(r.get("metrics", []), ensure_ascii=False)[:500])
else:
    # 可能需要其他格式
    print("  Status: %d, Body: %s" % (resp3.status_code, resp3.text[:500]))
    # 尝试另一种参数格式（不带 offset）
    print("  尝试备用参数格式...")
    payload2 = {
        "date_from": date_from,
        "date_to": date_to,
        "metrics": ["ordered_units", "revenue"],
        "dimension": ["sku"],
        "limit": 10,
    }
    resp3b = client.post("/v1/analytics/data", json=payload2)
    print("  Status: %d, Body: %s" % (resp3b.status_code, resp3b.text[:500]))

# ============================================================
# 4. 财务流水
# ============================================================
print_section("4. GET /v3/finance/transaction/list — 财务流水")

date_from_fin = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
print("  日期范围: %s ~ %s" % (date_from_fin, date_to))

payload = {
    "filter": {"date": {"from": date_from_fin, "to": date_to}},
    "page": 1,
    "page_size": 10,
}
resp4 = client.post("/v3/finance/transaction/list", json=payload)
print("  Status: %d" % resp4.status_code)

if resp4.status_code == 200:
    fdata = resp4.json()
    print("  Top keys: %s" % list(fdata.keys()))
    result = fdata.get("result", {})
    if result:
        print("  Result keys: %s" % list(result.keys()))
        txns = result.get("operations", []) or result.get("transactions", [])
        print("  交易数: %d" % len(txns))
        if txns:
            print("  字段: %s" % list(txns[0].keys()))
            print("  第一条:")
            dump(txns[0], max_len=800)
    else:
        print("  Body: %s" % fdata)
else:
    print("  Error: %s" % resp4.text[:500])

client.close()
print()
print("=" * 60)
print("  验证完成")
print("=" * 60)
