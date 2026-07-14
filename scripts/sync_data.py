"""
手动触发全量同步
运行: python scripts/sync_data.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger

from app.clients.ozon import get_ozon_client
from app.database import SessionLocal
from app.services.sync_service import run_full_sync


def main():
    logger.info("=== Ozon BI 数据同步 ===")
    client = get_ozon_client()
    db = SessionLocal()
    try:
        results = run_full_sync(db, client, days_back=30)

        print("\n=== 同步结果 ===")
        for step, res in results.items():
            if "error" in res:
                print(f"  FAIL {step}: {res['error']}")
            else:
                print(f"  OK   {step}: {res}")
    except Exception as e:
        logger.error(f"同步异常: {e}")
        raise
    finally:
        client.close()
        db.close()


if __name__ == "__main__":
    main()
