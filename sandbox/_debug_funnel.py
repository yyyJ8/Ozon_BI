"""排查 delivered > ordered 的数据问题"""
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
cur = conn.cursor()

date_start = '2026-04-01'
date_end = '2026-06-01'

# 1. Postings 的 created_at 真的在范围内吗？
cur.execute("""
    SELECT MIN(created_at), MAX(created_at), COUNT(*)
    FROM ozon.postings
    WHERE created_at >= %s AND created_at < %s
""", (date_start, date_end))
r = cur.fetchone()
print(f'1. Postings created_at 范围: {r[0]} ~ {r[1]}, 共 {r[2]} 条')
print(f'   确认：全部在 {date_start} ~ {date_end} 内？ → {"YES" if r[0] and r[1] else "NO DATA"}')

# 2. 按 SKU 比较：Analytics ordered vs Posting delivered
cur.execute("""
    WITH analytics AS (
        SELECT sku_id, SUM(ordered_units) as ordered
        FROM ozon.sku_daily_summary
        WHERE date >= %s AND date < %s
        GROUP BY sku_id
    ),
    posting_units AS (
        SELECT (prod->>'sku')::bigint as sku_id, SUM((prod->>'quantity')::int) as delivered
        FROM ozon.postings,
             jsonb_array_elements(products) AS prod
        WHERE status = 'delivered' AND created_at >= %s AND created_at < %s
        GROUP BY (prod->>'sku')::bigint
    )
    SELECT
        COALESCE(a.sku_id, p.sku_id) as sku_id,
        COALESCE(a.ordered, 0) as ordered,
        COALESCE(p.delivered, 0) as delivered,
        COALESCE(p.delivered, 0) - COALESCE(a.ordered, 0) as diff
    FROM analytics a
    FULL OUTER JOIN posting_units p ON a.sku_id = p.sku_id
    WHERE COALESCE(p.delivered, 0) - COALESCE(a.ordered, 0) > 3
    ORDER BY diff DESC
""", (date_start, date_end, date_start, date_end))
rows = cur.fetchall()
print(f'\n2. delivered > ordered 的 SKU (差>3件):')
for r in rows:
    print(f'   sku={r[0]} ordered={r[1]} delivered={r[2]} diff=+{r[3]}')

# 3. 关键：Postings 里有没有 Analytics 完全没记录的 SKU？
cur.execute("""
    SELECT DISTINCT (prod->>'sku')::bigint as sku_id
    FROM ozon.postings, jsonb_array_elements(products) AS prod
    WHERE status = 'delivered' AND created_at >= %s AND created_at < %s
    EXCEPT
    SELECT DISTINCT sku_id FROM ozon.sku_daily_summary
    WHERE date >= %s AND date < %s
""", (date_start, date_end, date_start, date_end))
missing_skus = [r[0] for r in cur.fetchall()]
print(f'\n3. Postings 有但 Analytics 完全没有的 SKU: {len(missing_skus)} 个')
if missing_skus:
    cur.execute("""
        SELECT (prod->>'sku')::bigint as sku_id, COUNT(*) as posts, SUM((prod->>'quantity')::int) as units
        FROM ozon.postings, jsonb_array_elements(products) AS prod
        WHERE status = 'delivered' AND created_at >= %s AND created_at < %s
          AND (prod->>'sku')::bigint = ANY(%s)
        GROUP BY (prod->>'sku')::bigint
        ORDER BY units DESC
    """, (date_start, date_end, missing_skus))
    for r in cur.fetchall():
        print(f'   sku={r[0]} postings={r[1]} units={r[2]}')

# 4. 按天比较：是不是某几天差异特别大？
cur.execute("""
    WITH daily_analytics AS (
        SELECT date, SUM(ordered_units) as ordered
        FROM ozon.sku_daily_summary
        WHERE date >= %s AND date < %s
        GROUP BY date
    ),
    daily_postings AS (
        SELECT created_at::date as date, SUM((prod->>'quantity')::int) as delivered
        FROM ozon.postings, jsonb_array_elements(products) AS prod
        WHERE status = 'delivered' AND created_at >= %s AND created_at < %s
        GROUP BY created_at::date
    )
    SELECT
        da.date,
        COALESCE(da.ordered, 0) as ordered,
        COALESCE(dp.delivered, 0) as delivered,
        COALESCE(dp.delivered, 0) - COALESCE(da.ordered, 0) as diff
    FROM daily_analytics da
    FULL OUTER JOIN daily_postings dp ON da.date = dp.date
    ORDER BY diff DESC
    LIMIT 15
""", (date_start, date_end, date_start, date_end))
print(f'\n4. 按天差异 (TOP 15):')
for r in cur.fetchall():
    print(f'   {r[0]} ordered={r[1]} delivered={r[2]} diff={r[3]:+d}')

# 5. 同一个 posting 被展开成几条？
cur.execute("""
    SELECT posting_number, COUNT(*) as product_rows
    FROM ozon.postings, jsonb_array_elements(products) AS prod
    WHERE status = 'delivered' AND created_at >= %s AND created_at < %s
    GROUP BY posting_number
    HAVING COUNT(*) > 1
    ORDER BY product_rows DESC
    LIMIT 10
""", (date_start, date_end))
print(f'\n5. 多 SKU 的 posting (展开后多条):')
for r in cur.fetchall():
    print(f'   {r[0][:25]}... → {r[1]} 条product行')

conn.close()
