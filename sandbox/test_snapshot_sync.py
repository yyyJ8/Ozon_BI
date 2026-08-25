"""回滚事务测试：batch_update 修改绿标价 → sku_management 与 sku_daily_snapshot 同事务同步"""
import sys
sys.path.insert(0, r"D:\OzonSku")

from unittest.mock import patch

from sqlalchemy import text

from app.api.sku_management import batch_update
from app.database import SessionLocal
from app.models import Product, SkuManagement
from app.schemas.sku_management import SkuManagementUpdate, SkuManagementBatchUpdate

TEST_GREEN_PRICE = 1234.56

db = SessionLocal()
try:
    prod = db.query(Product).filter(
        Product.store_id == 1,
        Product.marketing_seller_price.isnot(None),
    ).first()
    assert prod, "没有可用的测试 SKU"
    sku = prod.sku_id
    print(f"测试 SKU: {sku}  售价: {prod.marketing_seller_price}")

    mgmt_before = db.query(SkuManagement).filter_by(store_id=1, sku_id=sku).first()
    print("修改前 sku_management.green_price_rub =", mgmt_before.green_price_rub if mgmt_before else None)

    snap_before = db.execute(text(
        "SELECT record_date, green_price FROM ozon.sku_daily_snapshot "
        "WHERE store_id=1 AND sku_id=:sku ORDER BY record_date DESC LIMIT 1"
    ), {"sku": sku}).fetchall()
    print("修改前最新快照:", snap_before[0] if snap_before else None)

    # 调用 batch_update（mock commit 防止真实提交，最后统一 rollback）
    payload = SkuManagementBatchUpdate(
        items=[SkuManagementUpdate(sku_id=sku, green_price_rub=TEST_GREEN_PRICE)]
    )
    with patch.object(db, "commit", lambda: None):
        result = batch_update(payload, store_id=1, db=db)

    # 断言 1：sku_management 已更新（会话内可见）
    mgmt = db.query(SkuManagement).filter_by(store_id=1, sku_id=sku).first()
    assert mgmt is not None, "sku_management 无记录"
    print("修改后 sku_management.green_price_rub =", mgmt.green_price_rub)
    print("修改后 sku_management.discount_pct   =", mgmt.discount_pct)
    assert float(mgmt.green_price_rub) == TEST_GREEN_PRICE

    # 断言 2：快照表当日记录已同步
    snap = db.execute(text(
        "SELECT record_date, green_price, discount_pct FROM ozon.sku_daily_snapshot "
        "WHERE store_id=1 AND sku_id=:sku ORDER BY record_date DESC LIMIT 3"
    ), {"sku": sku}).fetchall()
    print("修改后快照最新3条:")
    for r in snap:
        print("  ", r)
    latest = snap[0]
    assert latest[1] is not None and float(latest[1]) == TEST_GREEN_PRICE, "快照 green_price 未同步"
    assert latest[2] is not None, "快照 discount_pct 未同步"
    # 折扣公式校验: (1 - green/price) * 100
    expect_discount = round((1 - TEST_GREEN_PRICE / float(prod.marketing_seller_price)) * 100, 2)
    print(f"期望 discount_pct = {expect_discount}")
    assert abs(float(latest[2]) - expect_discount) < 0.01

    print("\n✅ 全部断言通过：sku_management 与 sku_daily_snapshot 同事务同步成功")
finally:
    db.rollback()
    db.close()
    print("（已回滚，未改动真实数据）")
