"""
Ozon API - 验证 2b: 商品详情
接口: POST /v3/product/info/list
用途: 获取 sku_id（建表主键）、名称、价格、分类、佣金比例
前置: 需要先跑 2a 拿到 product_ids
输出: sandbox/output/02b_product_info.json
"""
import json, os, sys, httpx
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
PRODUCT_LIST_PATH = os.path.join(OUTPUT_DIR, "02a_product_list.json")

# 从 2a 产出读 product_id
if not os.path.exists(PRODUCT_LIST_PATH):
    print("请先运行 02a_test_product_list.py")
    sys.exit(1)
with open(PRODUCT_LIST_PATH, encoding="utf-8") as f:
    product_data = json.load(f)
product_ids = list(set(p["product_id"] for p in product_data.get("items", []) if p.get("product_id")))

client = httpx.Client(
    base_url="https://api-seller.ozon.ru",
    headers={"Client-Id": os.getenv("OZON_CLIENT_ID"), "Api-Key": os.getenv("OZON_API_KEY"), "Content-Type": "application/json"},
    timeout=30.0,
)

print("=== 2b: 商品详情 /v3/product/info/list ===")
print("共 %d 个 product_id，分批获取（每批最多 100 个）" % len(product_ids))

all_products = []
for i in range(0, len(product_ids), 100):
    batch = product_ids[i : i + 100]
    resp = client.post("/v3/product/info/list", json={"product_id": batch})
    if resp.status_code != 200:
        print("批次 %d 出错: %s" % (i // 100 + 1, resp.text[:200]))
        continue
    items = resp.json().get("items", [])
    all_products.extend(items)
    print("  批 %d: -> %d 条商品详情" % (i // 100 + 1, len(items)))

# 整理关键字段预览
first = all_products[0] if all_products else {}
skus = first.get("skus", [])
output = {
    "total": len(all_products),
    "top_level_fields": list(first.keys()) if first else [],
    "sku_fields": list(skus[0].keys()) if skus else [],
    "sample_item": first,
    "all_items": all_products,
}
path = os.path.join(OUTPUT_DIR, "02b_product_info.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("\n共 %d 个商品详情" % len(all_products))
print("顶级字段: %s" % list(first.keys())[:20])
if skus:
    print("SKU 字段: %s" % list(skus[0].keys()))
print("已保存: %s" % path)
client.close()
