"""
验证 3: Ozon Performance API（广告API）连接 + 数据采样

测试 店铺1: Тихое Счастье（安静幸福）
认证方式: OAuth 2.0 client credentials -> Bearer token

API 基础: https://api-performance.ozon.ru
  认证: POST /api/client/token
  活动列表: GET /api/client/campaign
  每日统计(CSV): GET /api/client/statistics/daily
  活动统计(CSV): GET /api/client/statistics/campaigns

重点关注:
  1. OAuth 2.0 token 获取
  2. 广告活动列表（类型、状态分布）
  3. 广告统计数据（花费、展示、点击、订单）
  4. 查找广告费对应的 operation_type (OperationMarketplaceCostPerClick)
"""
import csv
import io
import json
import os
import sys
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv

load_dotenv()

PERF_CLIENT_ID = os.getenv("OZON_PERF_CLIENT_ID")
PERF_CLIENT_SECRET = os.getenv("OZON_PERF_CLIENT_SECRET")
API_BASE = "https://api-performance.ozon.ru"

client = httpx.Client(base_url=API_BASE, timeout=30.0, follow_redirects=True)

# ── helpers ──────────────────────────────────────────────

def ps(title):
    print(); print("=" * 60); print("  %s" % title); print("=" * 60)

def dump(data, max_len=2000):
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if len(text) > max_len:
        print(text[:max_len] + "\n  ... (truncated, %d chars)" % len(text))
    else:
        print(text)

def parse_csv(text):
    """解析 Ozon Performance API 返回的 CSV"""
    lines = text.strip().split('\n')
    if not lines:
        return [], []
    header = lines[0].split(';')
    rows = []
    for line in lines[1:]:
        if line.strip():
            vals = line.split(';')
            rows.append(dict(zip(header, vals)))
    return header, rows


# ════════════════════════════════════════════════════════
print()
print("  Ozon Performance API（广告API）验证")
print("  店铺1: Тихое Счастье（安静幸福）")
print("  Client-ID: %s" % PERF_CLIENT_ID)
print("  时间: %s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# ── 1. Token ─────────────────────────────────────────────
ps("1. 获取 Access Token (OAuth 2.0)")

payload = {
    "client_id": PERF_CLIENT_ID,
    "client_secret": PERF_CLIENT_SECRET,
    "grant_type": "client_credentials",
}
resp = client.post("/api/client/token", json=payload)
print("  Status: %d" % resp.status_code)

if resp.status_code != 200:
    print("  Error: %s" % resp.text[:800])
    sys.exit(1)

token_data = resp.json()
access_token = token_data["access_token"]
token_type = token_data.get("token_type", "Bearer")
expires_in = token_data.get("expires_in", 0)

print("  Token 类型: %s" % token_type)
print("  有效期: %d 秒 (%.1f 小时)" % (expires_in, expires_in / 3600))
print("  Token 前缀: %s..." % access_token[:30])

auth_headers = {
    "Authorization": "%s %s" % (token_type, access_token),
    "Content-Type": "application/json",
}

# ── 2. 活动列表 ───────────────────────────────────────────
ps("2. GET /api/client/campaign — 广告活动列表")

resp2 = client.get("/api/client/campaign", headers=auth_headers)
print("  Status: %d" % resp2.status_code)

campaigns = []
if resp2.status_code == 200:
    raw = resp2.json()
    campaigns = raw.get("list", [])
    print("  活动总数: %d" % len(campaigns))

    if campaigns:
        print("  活动字段列表: %s" % list(campaigns[0].keys()))

        # 状态分布
        state_counts = {}
        type_counts = {}
        for c in campaigns:
            s = c.get("state", "UNKNOWN")
            t = c.get("advObjectType", "UNKNOWN")
            state_counts[s] = state_counts.get(s, 0) + 1
            type_counts[t] = type_counts.get(t, 0) + 1

        print("\n  状态分布:")
        for s, n in sorted(state_counts.items(), key=lambda x: -x[1]):
            print("    %-35s %d" % (s, n))

        print("\n  活动类型分布:")
        for t, n in sorted(type_counts.items(), key=lambda x: -x[1]):
            print("    %-35s %d" % (t, n))

        # 有标题（SKU推广等手动创建的活动有标题）
        named = [c for c in campaigns if c.get("title")]
        print("\n  有标题的活动: %d 个" % len(named))
        for c in named:
            print("    id=%-10s  state=%-30s  type=%-20s  title=%s" % (
                c["id"], c.get("state",""), c.get("advObjectType",""), c.get("title","")))

        # 第一条详情
        print("\n  第一条活动详情:")
        dump(campaigns[0], max_len=1000)
else:
    print("  Error: %s" % resp2.text[:800])

# ── 3. 每日统计数据 (CSV) ────────────────────────────────
ps("3. GET /api/client/statistics/daily — 每日广告统计 (CSV)")

date_to = datetime.now().strftime("%Y-%m-%d")
date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
print("  日期范围: %s ~ %s" % (date_from, date_to))
print("  注意: 此端点返回 CSV 格式")

resp3 = client.get(
    "/api/client/statistics/daily",
    params={"from": date_from, "to": date_to},
    headers=auth_headers,
)
print("  Status: %d" % resp3.status_code)

if resp3.status_code == 200:
    raw_text = resp3.text
    print("  原始长度: %d 字符" % len(raw_text))
    print("\n  原始 CSV 前 500 字符:")
    print(raw_text[:500])
    print("  ...")

    # 解析 CSV
    header, rows = parse_csv(raw_text)
    print("\n  解析结果:")
    print("  表头: %s" % header)
    print("  数据行数: %d" % len(rows))

    if rows:
        # 数值汇总
        total_cost = 0.0
        total_clicks = 0
        total_impressions = 0
        total_orders = 0
        total_revenue = 0.0

        for row in rows:
            # CSV 用法币符号, 需要清理
            cost_str = row.get("Расход, ₽", "0").replace(",", ".")
            rev_str = row.get("Заказы, ₽", "0").replace(",", ".")
            total_cost += float(cost_str) if cost_str else 0
            total_clicks += int(row.get("Клики", 0) or 0)
            total_impressions += int(row.get("Показы", 0) or 0)
            total_orders += int(row.get("Заказы, шт.", 0) or 0)
            total_revenue += float(rev_str) if rev_str else 0

        print("\n  30天汇总:")
        print("    花费(RUB):     %.2f" % total_cost)
        print("    展示:          %d" % total_impressions)
        print("    点击:          %d" % total_clicks)
        print("    订单:          %d" % total_orders)
        print("    订单金额(RUB): %.2f" % total_revenue)
        if total_clicks > 0:
            print("    CPC(RUB):      %.2f" % (total_cost / total_clicks))
        if total_impressions > 0:
            print("    CTR:           %.2f%%" % (total_clicks / total_impressions * 100))
        if total_orders > 0:
            print("    CPA(RUB):      %.2f" % (total_cost / total_orders))

        # 按日期汇总
        print("\n  按日花费:")
        daily = {}
        for row in rows:
            cost_str = row.get("Расход, ₽", "0").replace(",", ".")
            daily[row.get("Дата", "?")] = daily.get(row.get("Дата", "?"), 0) + float(cost_str) if cost_str else 0
        for d in sorted(daily.keys()):
            print("    %s  cost=%.2f" % (d, daily[d]))

        # 按活动汇总
        print("\n  按活动花费 (top 10):")
        by_campaign = {}
        for row in rows:
            cost_str = row.get("Расход, ₽", "0").replace(",", ".")
            by_campaign[row.get("ID", "?")] = by_campaign.get(row.get("ID", "?"), 0) + float(cost_str) if cost_str else 0
        for cid, cost in sorted(by_campaign.items(), key=lambda x: -x[1])[:10]:
            # 找活动名称
            title = ""
            for c in campaigns:
                if c.get("id") == cid:
                    title = c.get("title", "")
                    break
            print("    %-10s  %-30s  cost=%.2f" % (cid, title[:28], cost))

        # 保存CSV到文件
        out_path = "output/advertising_daily_stats.csv"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(raw_text)
        print("\n  CSV 已保存到: %s" % out_path)
else:
    print("  Error Response:")
    print(resp3.text[:1000])

# ── 4. 活动级统计数据 (CSV) ─────────────────────────────
ps("4. GET /api/client/statistics/campaigns — 活动级统计 (CSV)")

resp4 = client.get(
    "/api/client/statistics/campaigns",
    params={"from": date_from, "to": date_to},
    headers=auth_headers,
)
print("  Status: %d" % resp4.status_code)

if resp4.status_code == 200:
    raw_text = resp4.text
    print("  原始长度: %d 字符" % len(raw_text))
    print("\n  原始 CSV (前500字符):")
    print(raw_text[:500])

    header, rows = parse_csv(raw_text)
    print("\n  表头: %s" % header)
    print("  数据行数: %d" % len(rows))

    if rows:
        print("\n  各活动汇总:")
        for row in rows:
            cost_str = row.get("Расход, ₽", "0").replace(",", ".")
            print("    id=%-10s  Показы=%-6s  Клики=%-4s  Расход=%-8s  Заказы(шт)=%-3s  Заказы(₽)=%-8s" % (
                row.get("ID", ""),
                row.get("Показы", 0),
                row.get("Клики", 0),
                cost_str,
                row.get("Заказы, шт.", 0),
                row.get("Заказы, ₽", "").replace(",", ".") if row.get("Заказы, ₽") else "0",
            ))
else:
    print("  Error Response:")
    print(resp4.text[:500])

# ── 5. db: 查询已有的广告费用记录 ────────────────────────
ps("5. DB: 查看已有的广告费用记录 (OperationMarketplaceCostPerClick)")

try:
    from app.config import settings
    from app.database import SessionLocal
    from app.models import FinanceTransaction

    # 检查是否可用
    db = SessionLocal()
    total = db.query(FinanceTransaction).filter(
        FinanceTransaction.operation_type == "OperationMarketplaceCostPerClick"
    ).count()
    print("  OperationMarketplaceCostPerClick 总记录数: %d" % total)

    if total > 0:
        records = db.query(FinanceTransaction).filter(
            FinanceTransaction.operation_type == "OperationMarketplaceCostPerClick"
        ).order_by(FinanceTransaction.operation_date.desc()).limit(10).all()

        print("\n  最近 10 条:")
        for r in records:
            print("    date=%-12s  sku=%-10s  amount=%-10s  type=%s" % (
                r.operation_date, r.sku_id, r.amount, r.operation_type))
    else:
        # 可能用不同的 operation_type
        all_types = db.query(FinanceTransaction.operation_type).distinct().all()
        print("\n  所有 operation_type:")
        for t, in all_types:
            print("    %s" % t)

    db.close()
except Exception as e:
    print("  DB 查询失败: %s" % e)
    print("  (这是正常的，如果 sandbox 没有配置好 DB 连接)")

# ── 完成 ─────────────────────────────────────────────────
client.close()
print()
ps("验证完成")
