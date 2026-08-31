"""钉钉自定义机器人通知 — 业务事件推送（如直发收货上架）

配置（.env）:
    DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx
    DINGTALK_SECRET=SECxxxx   # 安全设置→加签密钥；不填则不签名

未配置 webhook 时所有发送静默跳过，不影响业务。
"""
import base64
import hashlib
import hmac
import threading
import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote_plus

import httpx
from loguru import logger

from app.config import settings

BJT = timezone(timedelta(hours=8))  # 北京时间


def _sign(timestamp_ms: int) -> str:
    """钉钉加签: HMAC-SHA256(timestamp + '\\n' + secret) → base64 → urlencode"""
    secret = (settings.dingtalk_secret or "").strip()
    if not secret:
        return ""
    string_to_sign = f"{timestamp_ms}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"), string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
    return quote_plus(base64.b64encode(hmac_code))


def send_dingtalk(text: str, at_mobiles: Optional[list[str]] = None) -> bool:
    """发送文本消息到钉钉群（同步）。未配置 webhook 时返回 False，不抛异常。

    at_mobiles: @ 的手机号列表（钉钉按手机号匹配 @人）
    """
    url = (settings.dingtalk_webhook_url or "").strip()
    if not url:
        logger.debug("[钉钉] webhook 未配置，跳过通知")
        return False

    timestamp = str(round(time.time() * 1000))
    sign = _sign(timestamp)
    if sign:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}timestamp={timestamp}&sign={sign}"

    payload = {"msgtype": "text", "text": {"content": text}}
    at_list = [m.strip() for m in (at_mobiles or []) if m.strip()]
    if at_list:
        payload["text"]["content"] = text + "".join(f" @{m}" for m in at_list)
        payload["at"] = {"atMobiles": at_list}
    try:
        resp = httpx.post(url, json=payload, timeout=5)
        data = resp.json()
        if data.get("errcode") == 0:
            logger.info(f"[钉钉] 发送成功: {text[:50]}")
            return True
        logger.error(f"[钉钉] 发送失败: {data}")
    except Exception as e:
        logger.error(f"[钉钉] 发送异常: {e}")
    return False


def send_dingtalk_async(text: str, at_mobiles: Optional[list[str]] = None):
    """后台线程发送，不阻塞业务请求"""
    threading.Thread(
        target=send_dingtalk, args=(text,), kwargs={"at_mobiles": at_mobiles}, daemon=True
    ).start()


def _at_mobiles() -> list[str]:
    """从 .env 读取通知时 @ 的手机号列表"""
    raw = (settings.dingtalk_at_mobiles or "").strip()
    return [m.strip() for m in raw.split(",") if m.strip()]


def notify_received_shipment(pr_no, sku, product_name, receiving_date):
    """直发收货上架通知（异步，失败不影响业务）"""
    now = datetime.now(BJT)
    lines = [
        "📦 直发收货上架",
        f"申购单号：{pr_no or '-'}",
        f"SKU：{sku or '-'}",
        f"产品：{product_name or '-'}",
    ]
    if receiving_date:
        rd = receiving_date.strftime("%Y-%m-%d") if isinstance(receiving_date, date) else str(receiving_date)
        lines.append(f"收货时间：{rd}")
    lines.append(f"通知时间：{now.strftime('%Y-%m-%d %H:%M:%S')}")
    send_dingtalk_async("\n".join(lines), at_mobiles=_at_mobiles())
