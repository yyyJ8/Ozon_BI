"""导出 products 表到 sandbox/products.json 供 Node 脚本使用"""
import json, os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()
db_url = (f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
          f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
db = sessionmaker(bind=create_engine(db_url))()
rows = db.execute(text(
    "SELECT sku_id, offer_id, price, old_price, marketing_seller_price "
    "FROM ozon.products WHERE is_archived = false ORDER BY sku_id"
)).fetchall()
db.close()

data = [{"sku_id": r[0], "offer_id": r[1], "db_price": float(r[2]) if r[2] else None,
          "old_price": float(r[3]) if r[3] else None, "msp": float(r[4]) if r[4] else None}
        for r in rows]
Path(__file__).resolve().parent.joinpath("products.json").write_text(
    json.dumps(data, ensure_ascii=False), encoding="utf-8")
print(f"已导出 {len(data)} 条")
