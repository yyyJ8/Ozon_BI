"""
库存数据实时性深度验证

1. 5分钟持续监控 — 每30s轮询一次，看是否有任何库存变化
2. 对比 /v4/product/info/stocks vs /v2/analytics/stock_on_warehouses 数据一致性
3. 尝试其他可能的库存相关接口
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

CLIENT_ID = os.getenv("OZON_CLIENT_ID")
API_KEY = os.getenv("OZON_API_KEY")
BASE_URL = "https://api-seller.ozon.ru"
HEADERS = {"Client-Id": CLIENT_ID, "Api-Key": API_KEY, "Content-Type": "application/json"}
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def iso_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def save_json(filename, data):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =================================================================
# Part A: Compare v4 stocks vs v2 analytics stock_on_warehouses
# =================================================================

def compare_endpoints(client):
    print("=" * 70)
    print("  Part A: v4/stocks vs v2/analytics/stock_on_warehouses comparison")
    print("=" * 70)

    # Get v4 stocks
    resp_v4 = client.post("/v4/product/info/stocks",
                          json={"filter": {"visibility": "ALL"}, "limit": 100})
    v4_items = resp_v4.json().get("items", [])

    # Get v2 analytics
    resp_v2 = client.post("/v2/analytics/stock_on_warehouses",
                          json={"limit": 100, "offset": 0, "warehouse_type": "ALL"})
    v2_rows = resp_v2.json().get("result", {}).get("rows", [])

    print(f"  v4/stocks: {len(v4_items)} products")
    print(f"  v2/analytics: {len(v2_rows)} rows (sku-warehouse level)")

    # Map from sku (v2) to offer_id (v4)
    sku_to_offer = {}
    for item in v4_items:
        for s in item.get("stocks", []):
            sku_to_offer[s.get("sku")] = item.get("offer_id")

    # Aggregate v2 by offer_id
    v2_by_offer = {}
    for row in v2_rows:
        sku = row.get("sku")
        offer_id = sku_to_offer.get(sku, f"unknown_sku_{sku}")
        if offer_id not in v2_by_offer:
            v2_by_offer[offer_id] = {
                "free_to_sell": 0, "promised": 0, "reserved": 0,
                "warehouses": []
            }
        v2_by_offer[offer_id]["free_to_sell"] += row.get("free_to_sell_amount", 0) or 0
        v2_by_offer[offer_id]["promised"] += row.get("promised_amount", 0) or 0
        v2_by_offer[offer_id]["reserved"] += row.get("reserved_amount", 0) or 0
        v2_by_offer[offer_id]["warehouses"].append(
            f"{row.get('warehouse_name')}:{row.get('free_to_sell_amount')}"
        )

    # Compare
    print()
    print(f"  {'offer_id':25s} | {'v4 present':>10s} | {'v2 free_to_sell':>14s} | {'v2 promised':>10s} | match?")
    print(f"  {'-'*25}-+-{'-'*10}-+-{'-'*14}-+-{'-'*10}-+-------")

    matches = 0
    mismatches = 0
    for item in v4_items[:15]:
        offer_id = item.get("offer_id", "?")
        v4_present = sum((s.get("present", 0) or 0) for s in item.get("stocks", []))

        v2_data = v2_by_offer.get(offer_id, {})
        v2_free = v2_data.get("free_to_sell", "N/A")

        match = "OK" if v4_present == v2_free else "DIFF"
        if v4_present == v2_free:
            matches += 1
        else:
            mismatches += 1

        print(f"  {offer_id:25s} | {v4_present:>10d} | {str(v2_free):>14s} | "
              f"{str(v2_data.get('promised','?')):>10s} | {match}")

    print(f"\n  Result: {matches} match, {mismatches} mismatch")

    # Pair counts
    print(f"\n  -- v2 warehouse detail (sample) --")
    for offer_id, data in list(v2_by_offer.items())[:3]:
        print(f"  {offer_id}: {data['warehouses']}")

    save_json("A_v4_vs_v2_comparison.json", {
        "v4_items": v4_items[:10],
        "v2_rows": v2_rows[:20],
        "v2_by_offer": {k: v for k, v in list(v2_by_offer.items())[:10]},
    })


# =================================================================
# Part B: 5-min continuous monitoring (every 30s, focused on high-stock items)
# =================================================================

def monitor_5min(client):
    print()
    print("=" * 70)
    print("  Part B: 5-minute continuous monitoring (every 30s)")
    print("=" * 70)

    # Get top 5 products by stock
    resp = client.post("/v4/product/info/stocks",
                       json={"filter": {"visibility": "ALL"}, "limit": 100})
    items = resp.json().get("items", [])

    ranked = []
    for item in items:
        total = sum((s.get("present", 0) or 0) for s in item.get("stocks", []))
        ranked.append((total, item))
    ranked.sort(key=lambda x: -x[0])
    top5 = [item for _, item in ranked[:5]]

    offer_ids = [item["offer_id"] for item in top5]
    print(f"  Monitoring top 5 by stock:")
    for item in top5:
        total = sum((s.get("present", 0) or 0) for s in item.get("stocks", []))
        print(f"    {item['offer_id']:30s} total={total}")

    payload = {"filter": {"offer_id": offer_ids}, "limit": 100}

    timeline = []
    for i in range(11):  # 0min to 5min, every 30s
        local_time = iso_now()
        resp = client.post("/v4/product/info/stocks", json=payload)
        data = resp.json()
        server_date = resp.headers.get("Date", "N/A")

        snapshot = {"seq": i, "local_time": local_time,
                     "server_date": server_date, "items": data.get("items", [])}
        timeline.append(snapshot)

        # Print summary
        line = f"  [{i:2d}] {datetime.now().strftime('%H:%M:%S')} "
        for item in data.get("items", []):
            total = sum((s.get("present", 0) or 0) for s in item.get("stocks", []))
            reserved = sum((s.get("reserved", 0) or 0) for s in item.get("stocks", []))
            line += f"| {item['offer_id'][-12:]:12s} p{total:4d}r{reserved:2d} "
        print(line)

        if i < 10:
            time.sleep(30)

    # Detect changes
    print()
    print(f"  -- Change analysis --")
    changes_found = False
    baseline = timeline[0]["items"]
    for t in range(1, len(timeline)):
        for idx, (item_b, item_t) in enumerate(zip(baseline, timeline[t]["items"])):
            if json.dumps(item_t, sort_keys=True) != json.dumps(item_b, sort_keys=True):
                changes_found = True
                elapsed = t * 30
                print(f"  [CHANGE] {item_b['offer_id']} changed at +{elapsed}s (seq #{t})")
                print(f"    baseline: {json.dumps(item_b.get('stocks'), ensure_ascii=False)}")
                print(f"    now:      {json.dumps(item_t.get('stocks'), ensure_ascii=False)}")

    if not changes_found:
        print(f"  [INFO] No stock changes detected during 5-minute monitoring window")

    save_json("B_5min_monitoring.json", timeline)


# =================================================================
# Part C: Try other potential stock-related endpoints
# =================================================================

def probe_other_endpoints(client):
    print()
    print("=" * 70)
    print("  Part C: Probe other potential stock-related endpoints")
    print("=" * 70)

    endpoints = [
        ("/v1/product/info/stocks", {"filter": {"visibility": "ALL"}, "limit": 5}),
        ("/v3/product/info/stocks", {"filter": {"visibility": "ALL"}, "limit": 5}),
        ("/v1/report/stock/create", {"date_from": "2026-07-20", "date_to": "2026-07-21"}),
        ("/v1/report/stock/info", {}),
        ("/v1/report/products/create", {"date_from": "2026-07-20", "date_to": "2026-07-21"}),
        ("/v1/report/products/movement/create", {"date_from": "2026-07-20", "date_to": "2026-07-21"}),
        ("/v2/analytics/data", {
            "date_from": "2026-07-20",
            "date_to": "2026-07-21",
            "metrics": ["ordered_units"],
            "dimension": ["sku", "day"],
            "limit": 5,
        }),
    ]

    results = {}
    for path, payload in endpoints:
        resp = client.post(path, json=payload)
        status = resp.status_code
        body_preview = resp.text[:300] if status != 200 else (
            json.dumps(resp.json(), ensure_ascii=False)[:300]
        )
        print(f"  {path:45s} -> {status}  {body_preview[:120]}")
        results[path] = {"status": status, "body_preview": body_preview}

        if status == 200:
            # Check for time fields in response
            data = resp.json()
            keys = set()
            def collect(k_obj, depth=3, prefix=""):
                if depth <= 0 or k_obj is None:
                    return
                if isinstance(k_obj, dict):
                    for k, v in k_obj.items():
                        keys.add(f"{prefix}{k}")
                        if isinstance(v, (dict, list)):
                            collect(v, depth - 1, f"{prefix}{k}.")
                elif isinstance(k_obj, list) and k_obj:
                    for i, item in enumerate(k_obj[:2]):
                        collect(item, depth - 1, f"{prefix}[{i}].")
            collect(data, depth=3)
            time_keys = [k for k in keys if any(t in k.lower() for t in
                        ["time", "date", "day", "hour", "minute", "update"])]
            if time_keys:
                print(f"        [TIMEFIELDS] {time_keys}")

    save_json("C_endpoint_probes.json", results)


# =================================================================
# main
# =================================================================

def main():
    print("=" * 70)
    print("  Ozon Inventory Real-time Deep Verification")
    print(f"  Start: {iso_now()}")
    print("=" * 70)

    client = httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=30.0)
    try:
        # Part A: Compare APIs
        compare_endpoints(client)

        # Part C: Probe other endpoints
        probe_other_endpoints(client)

        # Part B: 5-min monitoring (this takes ~5 min, runs last)
        monitor_5min(client)

    finally:
        client.close()

    print()
    print("=" * 70)
    print(f"  Done @ {iso_now()}")
    print("=" * 70)


if __name__ == "__main__":
    main()
