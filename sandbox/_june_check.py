import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
cur = conn.cursor()

cur.execute("""SELECT status, COUNT(*), SUM((prod->>'quantity')::int) as units
FROM ozon.postings, jsonb_array_elements(products) AS prod
WHERE created_at >= '2026-06-01' AND created_at < '2026-07-01'
GROUP BY status ORDER BY 2 DESC""")
print('=== 6月 posting 状态 ===')
for r in cur.fetchall():
    print(f'  {r[0]:20s}: {r[1]:4d}单 {r[2]:4d}件')

cur.execute("""SELECT status, COUNT(*)
FROM ozon.postings
WHERE created_at >= '2026-06-01'
GROUP BY status ORDER BY 2 DESC""")
print('\n=== 6月至今所有 posting ===')
for r in cur.fetchall():
    print(f'  {r[0]:20s}: {r[1]:4d}单')

cur.execute("SELECT SUM(ordered_units) FROM ozon.sku_daily_summary WHERE date >= '2026-06-01' AND date < '2026-07-01'")
print(f'\n6月 ordered_units: {cur.fetchone()[0]}')

cur.execute("SELECT SUM(delivered_units) FROM ozon.sku_daily_summary WHERE date >= '2026-06-01' AND date < '2026-07-01'")
print(f'6月 delivered_units: {cur.fetchone()[0]}')

conn.close()
