"""OZON 直发信息 — 操作日志（按天分文件，北京时间）"""
import os
from datetime import datetime, timezone, timedelta

LOG_BASE = os.path.join(os.path.dirname(__file__), "..", "logs", "ozon_direct")
BJT = timezone(timedelta(hours=8))


def _bj_now() -> datetime:
    return datetime.now(BJT)


def log_operation(action: str, detail: str = ""):
    """记录操作日志"""
    now = _bj_now()
    day_dir = os.path.join(LOG_BASE, now.strftime("%Y-%m-%d"))
    os.makedirs(day_dir, exist_ok=True)

    log_file = os.path.join(day_dir, "ozon_direct.log")
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {action}"
    if detail:
        line += f" | {detail}"
    line += "\n"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)
