import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
cur = conn.cursor()

# 修正计数：postings 是订单数，products[].quantity 才是件数
cur.execute("""
    SELECT
        SUM((prod->>'quantity')::int) as units,
        COUNT(*) as posts
    FROM ozon.postings,
         jsonb_array_elements(products) AS prod
    WHERE status = 'delivered'
""")
r = cur.fetchone()
delivered_units = r[0] or 0
delivered_posts = r[1] or 0

cur.execute("""
    SELECT
        SUM((prod->>'quantity')::int) as units,
        COUNT(*) as posts
    FROM ozon.postings,
         jsonb_array_elements(products) AS prod
    WHERE status = 'cancelled'
""")
r = cur.fetchone()
cancelled_units = r[0] or 0
cancelled_posts = r[1] or 0

cur.execute("SELECT SUM(ordered_units) FROM ozon.sku_daily_summary WHERE date >= '2026-04-01' AND date <= '2026-06-01'")
ordered_units = cur.fetchone()[0] or 0

cur.execute("SELECT SUM(returns_units) FROM ozon.sku_daily_summary WHERE date >= '2026-04-01'")
returns_units = cur.fetchone()[0] or 0

net = delivered_units - returns_units
evap = ordered_units - delivered_units

print(f'========== 修正后的 全店漏斗(件数口径) ==========')
print(f'  Analytics 下单:        {ordered_units:5d} 件  (4/1~6/1)')
print(f'  Posting 送达:          {delivered_units:5d} 件  ({delivered_posts} 个订单)')
print(f'  Posting 取消:          {cancelled_units:5d} 件  ({cancelled_posts} 个订单)')
print(f'  蒸发 (下单-送达):       {evap:5d} 件')
if ordered_units > 0:
    print(f'  成交率:                {delivered_units/ordered_units*100:.1f}%')
    print(f'  蒸发率:                {evap/ordered_units*100:.1f}%')
print(f'  ─────────────────────────────')
print(f'  Finance 退货:          {returns_units:5d} 件')
if delivered_units > 0:
    print(f'  退货率(退货/送达):      {returns_units/delivered_units*100:.1f}%')
print(f'  净成交 (送达-退货):     {net:5d} 件')

# Postings 同步覆盖了多少天
cur.execute("SELECT MIN(created_at)::date, MAX(created_at)::date FROM ozon.postings")
r = cur.fetchone()
print(f'\nPostings 覆盖时间: {r[0]} ~ {r[1]}')

conn.close()
