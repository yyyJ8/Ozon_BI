import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
cur = conn.cursor()

# 对齐日期范围：Postings 和 Analytics 都用同一段
date_start = '2026-04-01'
date_end = '2026-06-01'

cur.execute("SELECT SUM(ordered_units) FROM ozon.sku_daily_summary WHERE date >= %s AND date < %s", (date_start, date_end))
ordered_units = cur.fetchone()[0] or 0

cur.execute("""
    SELECT
        SUM((prod->>'quantity')::int) as units,
        COUNT(*) as posts
    FROM ozon.postings,
         jsonb_array_elements(products) AS prod
    WHERE status = 'delivered' AND created_at >= %s AND created_at < %s
""", (date_start, date_end))
r = cur.fetchone()
delivered_units = r[0] or 0
delivered_posts = r[1] or 0

cur.execute("""
    SELECT
        SUM((prod->>'quantity')::int) as units,
        COUNT(*) as posts
    FROM ozon.postings,
         jsonb_array_elements(products) AS prod
    WHERE status = 'cancelled' AND created_at >= %s AND created_at < %s
""", (date_start, date_end))
r = cur.fetchone()
cancelled_units = r[0] or 0
cancelled_posts = r[1] or 0

# Returns: 这些 postings 的退货（归因后也在这个日期范围）
cur.execute("SELECT SUM(returns_units) FROM ozon.sku_daily_summary WHERE date >= %s AND date < %s", (date_start, date_end))
returns_units = cur.fetchone()[0] or 0

net = delivered_units - returns_units
evap = ordered_units - delivered_units

print(f'========== 全店漏斗 ({date_start} ~ {date_end}) ==========')
print(f'')
print(f'  Analytics 下单:        {ordered_units:5d} 件')
print(f'  ───────────────────────────────')
print(f'  Posting 送达:          {delivered_units:5d} 件  ({delivered_posts} 单)')
print(f'  Posting 取消:          {cancelled_units:5d} 件  ({cancelled_posts} 单)')
print(f'  蒸发 (下单-送达):       {evap:5d} 件')
if ordered_units > 0:
    print(f'  成交率 (送达/下单):     {delivered_units/ordered_units*100:.1f}%')
print(f'  ───────────────────────────────')
print(f'  Finance 退货:          {returns_units:5d} 件')
if delivered_units > 0:
    print(f'  退货率 (退货/送达):     {returns_units/delivered_units*100:.1f}%')
print(f'  ───────────────────────────────')
print(f'  净成交 (送达-退货):     {net:5d} 件')
if ordered_units > 0:
    print(f'  净成交率 (净/下单):     {net/ordered_units*100:.1f}%')

conn.close()
