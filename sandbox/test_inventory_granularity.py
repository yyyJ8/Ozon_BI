"""
库存数据时间颗粒度测试

测试 Ozon API 返回的库存数据是否为实时数据。

测试维度:
  1. /v4/product/info/stocks — 当前库存接口，多次调用观察变化
  2. 快速连续调用（间隔 ~1s），看两次之间数据是否可能变化
  3. 延时调用（间隔 ~60s），看数据是否更新
  4. /v2/analytics/stock_on_warehouses — 历史库存分析接口
  5. 全量拉取 response 原始 JSON，检查是否有 last_update / updated_at 等时间字段

用法:
  cd D:\OzonSku && python sandbox\test_inventory_granularity.py
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

HEADERS = {
    "Client-Id": CLIENT_ID,
    "Api-Key": API_KEY,
    "Content-Type": "application/json",
}

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def log(msg: str):
    print(f"[{ts()}] {msg}")


def save_json(filename: str, data):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"  -> saved: {filename}")


def collect_keys(obj, depth=3, prefix=""):
    """递归收集 JSON 中所有 key 名称（用于发现隐藏字段）"""
    keys = set()
    if depth <= 0 or obj is None:
        return keys
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(f"{prefix}{k}")
            if isinstance(v, (dict, list)):
                keys |= collect_keys(v, depth - 1, f"{prefix}{k}.")
    elif isinstance(obj, list) and obj:
        for i, item in enumerate(obj[:3]):
            keys |= collect_keys(item, depth - 1, f"{prefix}[{i}].")
    return keys


# =================================================================
# 测试 1: 单次调用 /v4/product/info/stocks
# =================================================================

def test_single_call(client: httpx.Client):
    print()
    print("=" * 70)
    print("  Test 1: Single call /v4/product/info/stocks")
    print("=" * 70)

    # v4 接口要求 filter 字段
    payloads_to_try = [
        {"filter": {"visibility": "ALL"}, "limit": 10, "cursor": ""},
        {"filter": {"visibility": "VISIBLE"}, "limit": 10},
        {"filter": {}, "limit": 10},
    ]

    data = None
    items = []
    for i, payload in enumerate(payloads_to_try):
        resp = client.post("/v4/product/info/stocks", json=payload)
        print(f"  Payload [{i+1}]: {json.dumps(payload)}")
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            break
        else:
            print(f"  Error: {resp.text[:300]}")

    if data is None:
        print("  [FAIL] All payload variants failed for /v4/product/info/stocks")
        # fallback: try v3
        print()
        print("  Fallback: trying /v3/product/info/stocks ...")
        for payload in [{"filter": {"visibility": "ALL"}, "limit": 10}, {"limit": 10}]:
            resp = client.post("/v3/product/info/stocks", json=payload)
            print(f"  Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                break
            else:
                print(f"  Error: {resp.text[:300]}")

    if data is None:
        print("  [FAIL] All attempts failed.")
        return None

    save_json("01_single_call.json", data)

    top_keys = list(data.keys())
    print(f"  Top-level keys: {top_keys}")

    # v4 returns items/cursor/total at top level; v3 wraps in result
    items = data.get("items", data.get("result", {}).get("items", []))
    total = data.get("total", data.get("result", {}).get("total", "N/A"))
    cursor = data.get("cursor", data.get("result", {}).get("cursor", "N/A"))

    print(f"  total: {total}")
    print(f"  cursor: {cursor}")
    print(f"  items count: {len(items)}")

    if items:
        item = items[0]
        print()
        print(f"  -- First product --")
        print(f"  offer_id:    {item.get('offer_id', 'N/A')}")
        print(f"  product_id:  {item.get('product_id', 'N/A')}")
        print(f"  all fields:  {sorted(item.keys())}")

        stocks = item.get("stocks", [])
        print(f"  stocks count: {len(stocks)}")
        for j, s in enumerate(stocks):
            print(f"    [{j}] warehouse_id={s.get('warehouse_id')}, "
                  f"present={s.get('present')}, reserved={s.get('reserved')}, "
                  f"type={s.get('type', 'N/A')}")
            extra_keys = set(s.keys()) - {"warehouse_id", "present", "reserved", "type"}
            if extra_keys:
                print(f"        extra fields: { {k: s[k] for k in extra_keys} }")

        # 深度检查整个 response
        print()
        print(f"  -- Deep JSON key scan (depth=3) --")
        all_keys = collect_keys(data, depth=3)
        time_keys = [k for k in all_keys if any(t in k.lower() for t in
                    ["time", "date", "update", "created", "changed", "modified", "timestamp"])]
        if time_keys:
            print(f"  [OK] Time-related fields found: {time_keys}")
        else:
            print(f"  [WARN] No time-related fields found!")
        print(f"  All unique keys: {sorted(all_keys)}")

    return items


# =================================================================
# 测试 2: 快速连续调用 (间隔 ~1s, 共 5 次)
# =================================================================

def test_rapid_polling(client: httpx.Client, first_items: list | None):
    print()
    print("=" * 70)
    print("  Test 2: Rapid polling (5 calls, ~1.2s interval)")
    print("  Goal: detect second-level / minute-level data refresh")
    print("=" * 70)

    if not first_items:
        print("  [WARN] No product data, skipping")
        return

    offer_ids = [item.get("offer_id") for item in first_items[:3] if item.get("offer_id")]
    if not offer_ids:
        product_ids = [item.get("product_id") for item in first_items[:3] if item.get("product_id")]
        payload = {"filter": {"product_id": product_ids}, "limit": 100}
    else:
        payload = {"filter": {"offer_id": offer_ids}, "limit": 100}

    snapshots = []
    for i in range(5):
        local_time = iso_now()
        resp = client.post("/v4/product/info/stocks", json=payload)
        server_date = resp.headers.get("Date", "N/A")

        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", data.get("result", {}).get("items", []))
            snapshot = {
                "seq": i + 1,
                "local_time": local_time,
                "server_date": server_date,
                "items": items,
            }
            snapshots.append(snapshot)
            for item in items:
                stocks = item.get("stocks", [])
                vals = "/".join(
                    f"WH{s.get('warehouse_id','?')}:p{s.get('present',0)}r{s.get('reserved',0)}"
                    for s in stocks[:3]
                )
                print(f"  [{i+1}] {iso_now()}  {str(item.get('offer_id','?')):20s} -> {vals}")
        else:
            print(f"  [{i+1}] ERROR: {resp.status_code} {resp.text[:200]}")
            break

        if i < 4:
            time.sleep(1.2)

    save_json("02_rapid_polling.json", snapshots)

    print()
    print(f"  -- Change detection --")
    if len(snapshots) >= 2:
        changed = False
        for idx in range(len(snapshots[0]["items"])):
            item0 = snapshots[0]["items"][idx]
            for s in range(1, len(snapshots)):
                item_n = snapshots[s]["items"][idx]
                if json.dumps(item_n, sort_keys=True) != json.dumps(item0, sort_keys=True):
                    changed = True
                    print(f"  [OK] Product {item0.get('offer_id')} changed at call #{s+1}!")
                    print(f"       before: {json.dumps(item0.get('stocks','?'), ensure_ascii=False)}")
                    print(f"       after:  {json.dumps(item_n.get('stocks','?'), ensure_ascii=False)}")
                    break
            if changed:
                break
        if not changed:
            print(f"  [INFO] No stock changes across 5 rapid calls (~6s window)")
            print(f"         Data may be cached, or no orders occurred in this period")
    else:
        print(f"  [WARN] Not enough snapshots to compare")


# =================================================================
# 测试 3: 延时对比 (间隔 ~60s)
# =================================================================

def test_delayed_polling(client: httpx.Client, first_items: list | None):
    print()
    print("=" * 70)
    print("  Test 3: Delayed polling (60s interval)")
    print("  Goal: detect minute-level data refresh")
    print("=" * 70)

    if not first_items:
        print("  [WARN] No product data, skipping")
        return

    offer_ids = [item.get("offer_id") for item in first_items[:3] if item.get("offer_id")]
    if not offer_ids:
        product_ids = [item.get("product_id") for item in first_items[:3] if item.get("product_id")]
        payload = {"filter": {"product_id": product_ids}, "limit": 100}
    else:
        payload = {"filter": {"offer_id": offer_ids}, "limit": 100}

    # Call 1
    t0 = iso_now()
    resp = client.post("/v4/product/info/stocks", json=payload)
    if resp.status_code != 200:
        print(f"  ERROR: {resp.status_code} {resp.text[:200]}")
        return
    before = resp.json()
    before_items = before.get("items", before.get("result", {}).get("items", []))

    print(f"  [before] {t0}")
    for item in before_items:
        stocks = item.get("stocks", [])
        vals = "/".join(
            f"WH{s.get('warehouse_id','?')}:p{s.get('present',0)}r{s.get('reserved',0)}"
            for s in stocks[:3]
        )
        print(f"    {str(item.get('offer_id','?')):20s} -> {vals}")

    # Wait 60s
    print()
    print(f"  Waiting 60 seconds...")
    for remaining in range(60, 0, -10):
        print(f"    ... {remaining}s")
        time.sleep(10)

    # Call 2
    t1 = iso_now()
    resp = client.post("/v4/product/info/stocks", json=payload)
    if resp.status_code != 200:
        print(f"  ERROR: {resp.status_code} {resp.text[:200]}")
        return
    after = resp.json()
    after_items = after.get("items", after.get("result", {}).get("items", []))

    print()
    print(f"  [after]  {t1}")
    for item in after_items:
        stocks = item.get("stocks", [])
        vals = "/".join(
            f"WH{s.get('warehouse_id','?')}:p{s.get('present',0)}r{s.get('reserved',0)}"
            for s in stocks[:3]
        )
        print(f"    {str(item.get('offer_id','?')):20s} -> {vals}")

    save_json("03_delayed_before.json", before)
    save_json("03_delayed_after.json", after)

    print()
    print(f"  -- Comparison --")
    changed = False
    for b, a in zip(before_items, after_items):
        if json.dumps(b, sort_keys=True) != json.dumps(a, sort_keys=True):
            changed = True
            print(f"  [OK] {b.get('offer_id')}: data changed within 60s!")
            print(f"       before: {json.dumps(b.get('stocks','?'), ensure_ascii=False)}")
            print(f"       after:  {json.dumps(a.get('stocks','?'), ensure_ascii=False)}")
    if not changed:
        print(f"  [INFO] No stock changes within 60 seconds")


# =================================================================
# 测试 4: /v2/analytics/stock_on_warehouses
# =================================================================

def test_analytics_stock(client: httpx.Client):
    print()
    print("=" * 70)
    print("  Test 4: /v2/analytics/stock_on_warehouses")
    print("  Goal: check historical stock analytics (daily granularity?)")
    print("=" * 70)

    payloads_to_try = [
        {"limit": 10, "offset": 0, "warehouse_type": "ALL"},
        {"limit": 10},
        {},
    ]

    for i, payload in enumerate(payloads_to_try):
        resp = client.post("/v2/analytics/stock_on_warehouses", json=payload)
        print(f"  Payload [{i+1}]: {json.dumps(payload)}")
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            save_json("04_analytics_stock.json", data)
            print(f"  Top-level keys: {list(data.keys())}")
            result = data if "result" not in data else data["result"]

            rows = result.get("rows", result.get("items", []))
            print(f"  Data rows: {len(rows)}")
            if rows:
                print(f"  Row fields: {sorted(rows[0].keys())}")
                time_keys = [k for k in rows[0].keys()
                           if any(t in k.lower() for t in
                                  ["time", "date", "day", "hour", "minute"])]
                if time_keys:
                    print(f"  [OK] Time fields: {time_keys}")
                    for k in time_keys:
                        vals = [str(r.get(k, "")) for r in rows[:5]]
                        print(f"       {k} examples: {vals}")
                else:
                    print(f"  [INFO] No time field, only: {sorted(rows[0].keys())}")
            else:
                print(f"  Full response: {json.dumps(data, ensure_ascii=False)[:500]}")
            return

        print(f"  Body: {resp.text[:300]}")

    print(f"  [WARN] All payload formats failed for /v2/analytics/stock_on_warehouses")


# =================================================================
# 测试 5: 全量扫描
# =================================================================

def test_full_scan(client: httpx.Client):
    print()
    print("=" * 70)
    print("  Test 5: Full scan - pull ALL product stock data")
    print("  Goal: check distribution + hidden timestamp fields")
    print("=" * 70)

    all_items = []
    cursor = ""
    page = 0
    limit = 1000
    all_keys_deep = set()

    while True:
        page += 1
        payload = {"filter": {"visibility": "ALL"}, "limit": limit, "cursor": cursor}
        resp = client.post("/v4/product/info/stocks", json=payload)

        if resp.status_code != 200:
            print(f"  ERROR page {page}: {resp.status_code} {resp.text[:200]}")
            break

        data = resp.json()
        items = data.get("items", data.get("result", {}).get("items", []))
        all_items.extend(items)
        all_keys_deep |= collect_keys(data, depth=4)

        print(f"  page {page}: {len(items)} items (total {len(all_items)})", end="")

        cursor = data.get("cursor", "")
        if cursor:
            print(f", cursor={cursor[:30]}...")
        else:
            print(", no cursor (done)")
            break

    save_json("05_full_scan_sample.json", all_items[:50])

    print()
    print(f"  -- Full scan stats --")
    print(f"  Total products: {len(all_items)}")

    total_present = 0
    total_reserved = 0
    warehouse_set = set()
    has_stock = 0
    zero_stock = 0

    for item in all_items:
        for s in item.get("stocks", []):
            present = s.get("present", 0) or 0
            reserved = s.get("reserved", 0) or 0
            total_present += present
            total_reserved += reserved
            warehouse_set.add(s.get("warehouse_id"))

        total = sum((s.get("present", 0) or 0) for s in item.get("stocks", []))
        if total > 0:
            has_stock += 1
        else:
            zero_stock += 1

    print(f"  Warehouses: {len(warehouse_set)} -- {sorted(warehouse_set)}")
    print(f"  Total present: {total_present}")
    print(f"  Total reserved: {total_reserved}")
    print(f"  Products with stock: {has_stock}")
    print(f"  Products with zero stock: {zero_stock}")

    time_keys = [k for k in all_keys_deep if any(t in k.lower() for t in
                ["time", "date", "update", "created", "changed", "modified", "timestamp"])]
    print()
    print(f"  -- Full key scan --")
    if time_keys:
        print(f"  [OK] Time-related fields: {sorted(time_keys)}")
    else:
        print(f"  [WARN] No time-related fields found in full scan!")
    print(f"  All unique keys: {sorted(all_keys_deep)}")


# =================================================================
# 测试 6: 响应头分析
# =================================================================

def test_headers_timing(client: httpx.Client):
    print()
    print("=" * 70)
    print("  Test 6: Response header timing analysis")
    print("=" * 70)

    resp = client.post("/v4/product/info/stocks",
                       json={"filter": {"visibility": "ALL"}, "limit": 1})
    print(f"  Status: {resp.status_code}")
    print()
    print(f"  All response headers:")
    for k, v in sorted(resp.headers.items()):
        marker = "**" if any(t in k.lower() for t in
                             ["date", "time", "cache", "age", "expire", "last", "x-"]) else "  "
        print(f"    {marker} {k}: {v}")

    date_val = resp.headers.get("Date", "")
    if date_val:
        from email.utils import parsedate_to_datetime
        server_dt = parsedate_to_datetime(date_val)
        local_dt = datetime.now(timezone.utc)
        diff = (local_dt - server_dt).total_seconds()
        print()
        print(f"  Server time (Date header): {server_dt.isoformat()}")
        print(f"  Local time:                {local_dt.isoformat()}")
        print(f"  Time difference:           {diff:.1f}s")
        if abs(diff) < 2:
            print(f"  [OK] Server clock is in sync with local time")


# =================================================================
# main
# =================================================================

def main():
    print("=" * 70)
    print("  Ozon Inventory Data Time Granularity Test")
    print(f"  Start: {iso_now()}")
    print(f"  Client ID: {CLIENT_ID}")
    print("=" * 70)

    client = httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=30.0)

    try:
        # Test 1: Single call to understand structure
        first_items = test_single_call(client)

        # Test 6: Response header analysis
        test_headers_timing(client)

        # Test 2: Rapid polling (seconds-level)
        test_rapid_polling(client, first_items)

        # Test 4: Analytics endpoint
        test_analytics_stock(client)

        # Test 5: Full scan
        test_full_scan(client)

        # Test 3: Delayed polling (minute-level) — last, because it waits 60s
        test_delayed_polling(client, first_items)

    finally:
        client.close()

    print()
    print("=" * 70)
    print(f"  Test completed @ {iso_now()}")
    print(f"  Detailed JSON output: {OUTPUT_DIR}")
    print("=" * 70)
    print()
    print("  =======================================================")
    print("  Summary:")
    print("  - If NO time/date/update fields found -> API returns no data timestamp")
    print("  - If rapid polling shows no change but delayed does -> data has N-min delay")
    print("  - If rapid polling shows changes -> data is near real-time (sec-min)")
    print("  - /v2/analytics/stock_on_warehouses may show daily/historical data")
    print("  =======================================================")


if __name__ == "__main__":
    main()
