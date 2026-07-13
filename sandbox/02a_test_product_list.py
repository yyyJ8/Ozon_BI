"""
Ozon API - 验证 2a: 商品列表
接口: POST /v3/product/list
用途: 获取店铺所有商品 ID，给 info/list 用
输出: sandbox/output/02a_product_list.json
"""
import json, os, httpx
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

client = httpx.Client(
    base_url="https://api-seller.ozon.ru",
    headers={"Client-Id": os.getenv("OZON_CLIENT_ID"), "Api-Key": os.getenv("OZON_API_KEY"), "Content-Type": "application/json"},
    timeout=30.0,
)

print("=== 2a: 商品列表 /v3/product/list ===")
print("获取所有商品 product_id（分页游标）")

all_items, last_id = [], ""
while True:
    resp = client.post("/v3/product/list", json={"filter": {"visibility": "ALL"}, "limit": 1000, "last_id": last_id})
    if resp.status_code != 200:
        print("出错: %d %s" % (resp.status_code, resp.text[:200]))
        break
    data = resp.json()
    items = data.get("result", {}).get("items", [])
    all_items.extend(items)
    print("  页... %d 条 (累计 %d / 总量 %s)" % (len(items), len(all_items), data.get("total", "?")))
    if not items:
        break
    last_id = items[-1].get("id", "")
    if len(items) < 1000:
        break

output = {"total": len(all_items), "fields": list(all_items[0].keys()) if all_items else [], "items": all_items}
path = os.path.join(OUTPUT_DIR, "02a_product_list.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print("\n共 %d 个商品" % len(all_items))
print("字段: %s" % output["fields"])
print("已保存: %s" % path)
client.close()
