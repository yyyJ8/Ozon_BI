"""回滚测试：store_id=0（全部店铺）时 batch_update 按真实店铺写入 + 快照同步"""
import sys
sys.path.insert(0, r"D:\OzonSku")

from unittest.mock import patch

from sqlalchemy import text

from app.api.sku_management import batch_update, archive_sku
from app.database import SessionLocal
from app.models import Product, SkuManagement
from app.schemas.sku_management import SkuManagementUpdate, SkuManagementBatchUpdate

TEST_GREEN = 2602.00
SKU = 5376335343  # 真实店铺 = 5

db = SessionLocal()
try:
    # ── 场景 1：store_id=0 提交绿标价，应写入真实店铺 5 ──
    payload = SkuManagementBatchUpdate(
        items=[SkuManagementUpdate(sku_id=SKU, green_price_rub=TEST_GREEN)]
    )
    with patch.object(db, "commit", lambda: None):
        result = batch_update(payload, store_id=0, db=db)

    # 1a. sku_management（store 5）已写入
    mgmt = db.query(SkuManagement).filter_by(store_id=5, sku_id=SKU).first()
    assert mgmt is not None, "store=0 时未找到 store5 的 sku_management 记录"
    assert float(mgmt.green_price_rub) == TEST_GREEN, f"绿标价未写入: {mgmt.green_price_rub}"
    assert mgmt.discount_pct is not None, "折扣未重算"
    print(f"[场景1] store_id=0 → 真实店铺5写入: green={mgmt.green_price_rub}, discount={mgmt.discount_pct} ✓")

    # 1b. 快照表当日记录已同步（store 5）
    snap = db.execute(text(
        "SELECT record_date, green_price, discount_pct FROM ozon.sku_daily_snapshot "
        "WHERE store_id=5 AND sku_id=:sku ORDER BY record_date DESC LIMIT 1"
    ), {"sku": SKU}).fetchone()
    assert snap is not None and float(snap[1]) == TEST_GREEN, f"快照未同步: {snap}"
    print(f"[场景1] 快照同步: {snap} ✓")

    # 1c. 返回全量数据非空（store_id=0 响应不因过滤而变空）
    assert isinstance(result, list) and len(result) > 0, "store_id=0 响应为空!"
    print(f"[场景1] 响应行数={len(result)}（全部店铺）✓")

    # ── 场景 2（回归）：store_id=5 正常写入 ──
    payload5 = SkuManagementBatchUpdate(
        items=[SkuManagementUpdate(sku_id=SKU, green_price_rub=TEST_GREEN)]
    )
    with patch.object(db, "commit", lambda: None):
        result5 = batch_update(payload5, store_id=5, db=db)
    mgmt5 = db.query(SkuManagement).filter_by(store_id=5, sku_id=SKU).first()
    assert float(mgmt5.green_price_rub) == TEST_GREEN
    assert len(result5) > 0
    print(f"[场景2] store_id=5 正常: green={mgmt5.green_price_rub}, 响应行数={len(result5)} ✓")

    # ── 场景 3（回归）：store_id=1 提交 store5 的 SKU（不在店1）→ 静默跳过、不报错 ──
    before3 = db.query(SkuManagement).filter_by(store_id=5, sku_id=SKU).first().green_price_rub
    payload1 = SkuManagementBatchUpdate(
        items=[SkuManagementUpdate(sku_id=SKU, green_price_rub=9999.0)]
    )
    with patch.object(db, "commit", lambda: None):
        result1 = batch_update(payload1, store_id=1, db=db)
    after3 = db.query(SkuManagement).filter_by(store_id=5, sku_id=SKU).first().green_price_rub
    assert float(after3) == float(before3), "store=1 不应改动 store5 的数据"
    print(f"[场景3] store_id=1 下该SKU不存在 → 跳过且未误写: {after3} ✓")

    # ── 场景 4：archive_sku store_id=0 归档真实店铺记录 ──
    with patch.object(db, "commit", lambda: None):
        arch = archive_sku(SKU, store_id=0, db=db)
    assert arch["archived"] is True, f"归档失败: {arch}"
    arch_row = db.query(SkuManagement).filter_by(store_id=5, sku_id=SKU).first()
    assert arch_row.is_archived is True
    print(f"[场景4] store_id=0 归档 store5 记录: {arch} ✓")

    print("\n✅ 全部场景通过")
finally:
    db.rollback()
    db.close()
    print("（已回滚，未改动真实数据）")
