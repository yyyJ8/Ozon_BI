import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
cur = conn.cursor()

# 各表行数
for tbl in ['products','stocks','sku_daily_summary','finance_transactions','postings']:
    cur.execute(f'SELECT COUNT(*) FROM ozon.{tbl}')
    print(f'{tbl:30s}: {cur.fetchone()[0]:5d} rows')

# SkuDailySummary
cur.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM ozon.sku_daily_summary")
r = cur.fetchone()
print(f'\nSkuDailySummary: {r[0]} rows, {r[1]} ~ {r[2]}')

cur.execute("SELECT data_quality, COUNT(*) FROM ozon.sku_daily_summary GROUP BY data_quality")
print(f'  quality: {dict(cur.fetchall())}')

cur.execute("""SELECT
    COUNT(*) FILTER (WHERE ordered_units > 0) as has_sales,
    COUNT(*) FILTER (WHERE returns_units > 0) as has_returns
FROM ozon.sku_daily_summary""")
r = cur.fetchone()
print(f'  has_sales={r[0]}, has_returns={r[1]}')

# Postings 状态
cur.execute('SELECT status, COUNT(*) FROM ozon.postings GROUP BY status ORDER BY 2 DESC')
print(f'\nPostings status:')
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]}')

# 取消原因
cur.execute('SELECT cancel_reason_id, COUNT(*) FROM ozon.postings WHERE status = %s GROUP BY 1 ORDER BY 2 DESC', ('cancelled',))
print(f'\nCancel reasons:')
for r in cur.fetchall():
    print(f'  reason_id={r[0]}: {r[1]}')

# 漏斗
cur.execute("SELECT SUM(ordered_units) FROM ozon.sku_daily_summary WHERE date >= '2026-04-01'")
ordered = cur.fetchone()[0] or 0
cur.execute("SELECT COUNT(*) FROM ozon.postings WHERE status = 'delivered'")
delivered = cur.fetchone()[0] or 0
cur.execute("SELECT COUNT(*) FROM ozon.postings WHERE status = 'cancelled'")
cancelled = cur.fetchone()[0] or 0
cur.execute("SELECT SUM(returns_units) FROM ozon.sku_daily_summary WHERE date >= '2026-04-01'")
returns = cur.fetchone()[0] or 0
net = delivered - returns
evap = ordered - delivered

print(f'\n========== 4月至今 订单漏斗 ==========')
print(f'  Analytics 下单:     {ordered:5d} 件')
print(f'  Posting 送达:       {delivered:5d} 件  ({delivered/ordered*100:.1f}% 成交率)')
print(f'  Posting 取消:       {cancelled:5d} 件')
print(f'  蒸发 (下单-送达):    {evap:5d} 件  ({evap/ordered*100:.1f}% 蒸发率)')
print(f'  Finance 退货:       {returns:5d} 件')
print(f'  ─────────────────────────────')
print(f'  净成交 (送达-退货):  {net:5d} 件')

conn.close()
