"""
Ozon API - 验证 2e: 退货数据
接口: POST /v1/returns/list
用途: 获取 FBO/FBS 退货列表，搞清楚返回字段 + visual status 全量值
输出: sandbox/output/02e_returns_sample.json
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
    headers={
        "Client-Id": os.getenv("OZON_CLIENT_ID"),
        "Api-Key": os.getenv("OZON_API_KEY"),
        "Content-Type": "application/json",
    },
    timeout=30.0,
)

date_to = datetime.now()
date_from = date_to - timedelta(days=90)

print("=== 2e: 退货数据 /v1/returns/list ===")
print("schema: fbo, 90 天窗口")

# 拉取 FBO 退货
resp = client.post("/v1/returns/list", json={
    "filter": {"return_schema": "fbo"},
    "last_id": 0,
    "limit": 500,
})
if resp.status_code != 200:
    print("请求失败: %s" % resp.text[:500])
    client.close()
    exit()

data = resp.json()
returns_list = data.get("returns", [])
has_next = data.get("has_next", False)

print("返回 %d 条, has_next=%s" % (len(returns_list), has_next))

if not returns_list:
    print("无退货数据")
    client.close()
    exit()

# visual status 分布
status_dist = {}
type_dist = {}
for r in returns_list:
    sn = r.get("visual", {}).get("status", {}).get("sys_name", "UNKNOWN")
    status_dist[sn] = status_dist.get(sn, 0) + 1
    tp = r.get("type", "UNKNOWN")
    type_dist[tp] = type_dist.get(tp, 0) + 1

# 递归展开字段路径
def collect_paths(obj, prefix="", depth=0):
    """递归收集所有叶子字段路径和示例值"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                collect_paths(v, path, depth + 1)
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                # 展开第一个元素的字段
                collect_paths(v[0], f"{path}[0]", depth + 1)
                # 也记录数组本身的第一个元素类型
            else:
                field_paths.append(path)
                if v is not None:
                    field_examples[path] = v
    elif isinstance(obj, list):
        pass  # 纯值数组

field_paths = []
field_examples = {}

# 每种 status 取一条做结构分析
seen_status = set()
for r in returns_list:
    sn = r.get("visual", {}).get("status", {}).get("sys_name", "UNKNOWN")
    if sn not in seen_status:
        seen_status.add(sn)
        collect_paths(r)

# 输出 1: 终端概览
print("\n--- visual.status.sys_name 分布 ---")
for st, cnt in sorted(status_dist.items(), key=lambda x: -x[1]):
    print("  %s: %d" % (st, cnt))

print("\n--- type 分布 ---")
for tp, cnt in sorted(type_dist.items(), key=lambda x: -x[1]):
    print("  %s: %d" % (tp, cnt))

print("\n--- 所有叶子字段 (%d 个) ---" % len(field_paths))
for p in sorted(field_paths):
    ex = field_examples.get(p, "N/A")
    if not isinstance(ex, str):
        ex = str(ex)
    if len(ex) > 80:
        ex = ex[:77] + "..."
    print("  %s: %s" % (p, ex))

# 输出 2: 完整 JSON
output = {
    "endpoint": "POST /v1/returns/list",
    "total_records": len(returns_list),
    "has_next": has_next,
    "visual_status_sys_name_distribution": status_dist,
    "type_distribution": type_dist,
    "all_leaf_field_paths": sorted(field_paths),
    "sample_returns": returns_list[:5],
    "all_records": returns_list,
}
path = os.path.join(OUTPUT_DIR, "02e_returns_sample.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print("\n已保存: %s" % path)

client.close()
