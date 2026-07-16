"""
Ozon Performance API（广告 API）客户端

认证: OAuth 2.0 client_credentials → Bearer token（30分钟有效）

统计端点:
  - GET /api/client/statistics/daily?dateFrom=...&dateTo=... → CSV（每日活动统计，~45天）
  - POST /api/client/statistics → UUID → poll → download ZIP
    （异步报告，返回活动内 SKU 明细而非每日统计，格式不同）
"""
import io
import time
import zipfile
from typing import Optional

import httpx
from loguru import logger

from app.config import settings


class OzonPerfClient:
    """Ozon Performance API（广告）HTTP 客户端"""

    BASE_URL = "https://api-performance.ozon.ru"

    def __init__(self, client_id: str, client_secret: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = httpx.Client(
            base_url=self.BASE_URL,
            timeout=30.0,
            follow_redirects=True,
        )
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0

    # ── 认证 ──────────────────────────────────────────────

    def _ensure_token(self) -> str:
        """获取或刷新 OAuth token（提前5分钟刷新）"""
        if self._token and time.time() < self._token_expires_at - 300:
            return self._token

        logger.info("获取 Performance API OAuth token ...")
        resp = httpx.post(
            self.BASE_URL + "/api/client/token",
            json={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "client_credentials",
            },
            timeout=15.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        expires_in = data.get("expires_in", 1800)
        self._token_expires_at = time.time() + expires_in
        logger.info(f"Token 获取成功，有效期 {expires_in}s")
        return self._token

    @property
    def _auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._ensure_token()}",
            "Content-Type": "application/json",
        }

    # ── 活动列表 ──────────────────────────────────────────

    def get_campaigns(self) -> list[dict]:
        """GET /api/client/campaign → list[dict]"""
        resp = self._http.get("/api/client/campaign", headers=self._auth_headers)
        resp.raise_for_status()
        data = resp.json()
        return data.get("list", []) if isinstance(data, dict) else data

    # ── 每日统计（同步端点）───────────────────────────────

    def get_daily_stats(
        self,
        date_from: str,
        date_to: str,
        campaign_ids: Optional[list[str]] = None,
    ) -> list[dict]:
        """获取广告每日统计（同步端点，支持 ~45 天）

        GET /api/client/statistics/daily?dateFrom=...&dateTo=...

        返回 CSV 格式:
        ID;Название;Дата;Показы;Клики;Расход, ₽;Заказы, шт.;Заказы, ₽

        注意: 端点返回所有活动的统计数据，不受 campaign_ids 过滤。
              campaign_ids 参数仅在异步报告端点生效。
        """
        resp = self._http.get(
            "/api/client/statistics/daily",
            params={"dateFrom": date_from, "dateTo": date_to},
            headers=self._auth_headers,
        )
        resp.raise_for_status()
        return self._parse_csv(resp.text)

    # ── CSV 解析 ──────────────────────────────────────────

    @staticmethod
    def _parse_csv(text: str) -> list[dict]:
        """解析分号分隔的 CSV（俄式数字格式）

        表头: ID;Название;Дата;Показы;Клики;Расход, ₽;Заказы, шт.;Заказы, ₽
        映射: campaign_id, campaign_name, date, impressions, clicks, spend, orders_count, orders_sum

        数字格式:
          "123,45"   → 123.45  (俄式小数点，逗号)
          "4 500,00" → 4500.00 (千分位空格)
        """
        text = text.lstrip("﻿")  # strip BOM
        text = text.strip()
        if not text:
            return []

        lines = text.split("\n")
        header = [h.strip() for h in lines[0].strip().split(";")]

        key_map = {
            "ID": "campaign_id",
            "Название": "campaign_name",
            "Дата": "date",
            "Показы": "impressions",
            "Клики": "clicks",
            "Расход": "spend",
            "Расход, ₽": "spend",
            "Заказы, шт.": "orders_count",
            "Заказы": "orders_sum",
            "Заказы, ₽": "orders_sum",
        }
        mapped_header = [key_map.get(h, h) for h in header]

        rows = []
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            vals = line.split(";")
            if len(vals) < len(mapped_header):
                continue

            row = {}
            for i, key in enumerate(mapped_header):
                raw = vals[i].strip() if i < len(vals) else ""
                if key in ("campaign_id", "campaign_name", "date"):
                    row[key] = raw
                elif key in ("impressions", "clicks", "orders_count"):
                    row[key] = int(raw) if raw else 0
                elif key in ("spend", "orders_sum"):
                    row[key] = _parse_russian_number(raw)
            rows.append(row)
        return rows

    # ── 清理 ──────────────────────────────────────────────

    def close(self):
        self._http.close()

    # ── SKU 日报（异步报告 + ZIP 下载）─────────────────────

    REPORT_BATCH_SIZE = 10
    REPORT_POLL_TIMEOUT = 300  # 5 分钟

    def get_sku_daily_stats(
        self,
        date_from: str,
        date_to: str,
        campaign_ids: Optional[list[str]] = None,
    ) -> list[dict]:
        """获取 SKU 级别的广告日明细（异步报告模式）

        POST /api/client/statistics → 轮询 → 下载 ZIP → 解压 CSV → 解析

        限制: 每批最多 10 个活动, 同时只能 1 个活跃请求。
              数据支持 ~45 天, 日常建议 dateFrom=dateTo=昨天。

        返回的 dict 字段:
          campaign_id, sku_id, sku_name, sku_price,
          impressions, clicks, ctr, add_to_cart, avg_cpc,
          spend, sold_units, sales_promotion,
          total_ordered, drr_promotion, drr_total, date_added
        """
        if campaign_ids is None:
            campaigns = self.get_campaigns()
            active_types = ("SKU", "ALL_SKU_PROMO")
            campaign_ids = [
                c["id"] for c in campaigns
                if c.get("advObjectType") in active_types
            ]
            logger.info(f"SKU 报告: 自动选择 {len(campaign_ids)} 个活动")

        if not campaign_ids:
            return []

        batches = [
            campaign_ids[i:i + self.REPORT_BATCH_SIZE]
            for i in range(0, len(campaign_ids), self.REPORT_BATCH_SIZE)
        ]
        logger.info(f"SKU 报告: {len(campaign_ids)} 个活动 → {len(batches)} 批")

        all_rows: list[dict] = []
        for bi, batch in enumerate(batches, 1):
            try:
                logger.info(f"  批次 {bi}/{len(batches)}: {len(batch)} 个活动")
                uuid_val = self._request_async_report(date_from, date_to, batch)
                zip_bytes = self._poll_async_report(uuid_val)
                rows = self._parse_async_report_zip(zip_bytes)
                all_rows.extend(rows)
                logger.info(f"    获取 {len(rows)} 行 SKU 数据")
            except Exception as e:
                logger.error(f"  批次 {bi} 失败: {e}")

        return all_rows

    def _request_async_report(
        self, date_from: str, date_to: str, campaign_ids: list[str],
    ) -> str:
        """POST /api/client/statistics → 返回报告 UUID"""
        body = {
            "campaigns": campaign_ids,
            "dateFrom": date_from,
            "dateTo": date_to,
        }

        def _do_post():
            return self._http.post(
                "/api/client/statistics",
                json=body,
                headers=self._auth_headers,
            )

        resp = _do_post()
        if resp.status_code == 429:
            logger.warning("429 限流，等待已有报告完成...")
            for attempt in range(30):  # 最多等 5 分钟
                time.sleep(10)
                resp = _do_post()
                if resp.status_code != 429:
                    logger.info(f"  429 解除（等待 {(attempt+1)*10}s）")
                    break
            else:
                # 所有重试用完仍429，跳过这批而不是崩溃
                logger.error("  429 持续 5 分钟仍未解除，放弃本批")
                return ""
        data = resp.json()
        uuid_val = data.get("UUID", "")
        if not uuid_val:
            raise RuntimeError(f"报告未返回 UUID: {data}")
        return uuid_val

    def _poll_async_report(self, uuid_val: str) -> bytes:
        """轮询状态 → OK → 下载 ZIP → 返回 bytes"""
        deadline = time.time() + self.REPORT_POLL_TIMEOUT
        url = f"/api/client/statistics/{uuid_val}"
        last_state = ""

        while time.time() < deadline:
            resp = self._http.get(url, headers=self._auth_headers)
            resp.raise_for_status()
            data = resp.json()
            state = data.get("state", "")

            if state != last_state:
                logger.info(f"    报告 {uuid_val[:8]}...: {last_state} → {state}")
                last_state = state

            if state == "OK":
                link = data.get("link", "")
                if not link:
                    raise RuntimeError(f"报告 OK 但缺少 download link")
                zip_resp = self._http.get(link, headers=self._auth_headers)
                zip_resp.raise_for_status()
                return zip_resp.content

            elif state in ("ERROR", "FAILED"):
                raise RuntimeError(f"报告生成失败: {data}")

            time.sleep(5)

        raise TimeoutError(f"报告轮询超时: {uuid_val}")

    @staticmethod
    def _parse_async_report_zip(zip_bytes: bytes) -> list[dict]:
        """解压 ZIP，解析每个 campaign 的 CSV → 合并返回"""
        all_rows: list[dict] = []
        buffer = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(buffer, "r") as zf:
            for name in zf.namelist():
                if name.endswith(".csv"):
                    # 文件名格式: {campaign_id}_{from}_{to}.csv
                    campaign_id = name.split("_")[0]
                    with zf.open(name) as f:
                        csv_text = f.read().decode("utf-8-sig")
                        rows = _parse_async_csv(csv_text, campaign_id)
                        all_rows.extend(rows)
        return all_rows


def _parse_russian_number(s: str) -> float:
    """解析俄式数字: "4 500,00"→4500.00, "123,45"→123.45"""
    s = s.strip()
    if not s:
        return 0.0
    s = s.replace("₽", "").replace(" ", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_async_csv(text: str, campaign_id: str) -> list[dict]:
    """解析异步报告 ZIP 内的单个 campaign CSV

    表头（分号分隔）:
      sku;Название товара;Цена товара, ₽;Показы;Клики;CTR, %;
      Добавления в корзину;Средняя стоимость клика, ₽;Расход, ₽, с НДС;
      Продано товаров;Продажи в продвижении, ₽;Продано товаров модели;
      Продажи в продвижении с заказов модели, ₽;ДРР в продвижении, %;
      Заказано на сумму, ₽;ДРР (общий), %;Дата добавления

    跳过汇总行（sku="Всего"）和修正行（sku="Корректировка"）。
    """
    text = text.lstrip("﻿").strip()
    if not text:
        return []

    lines = text.split("\n")
    # 第一行可能是注释标题，找到真正的表头行
    header_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("sku;"):
            header_idx = i
            break

    header = [h.strip() for h in lines[header_idx].strip().split(";")]

    key_map = {
        "sku": "sku_id",
        "Название товара": "sku_name",
        "Цена товара, ₽": "sku_price",
        "Показы": "impressions",
        "Клики": "clicks",
        "CTR, %": "ctr",
        "Добавления в корзину": "add_to_cart",
        "Средняя стоимость клика, ₽": "avg_cpc",
        "Расход, ₽, с НДС": "spend",
        "Продано товаров": "sold_units",
        "Продажи в продвижении, ₽": "sales_promotion",
        "Заказано на сумму, ₽": "total_ordered",
        "ДРР в продвижении, %": "drr_promotion",
        "ДРР (общий), %": "drr_total",
        "Дата добавления": "date_added",
    }
    mapped = [key_map.get(h, h) for h in header]

    rows = []
    for line in lines[header_idx + 1:]:
        line = line.strip()
        if not line:
            continue
        vals = line.split(";")
        if len(vals) < len(mapped):
            continue

        row = {"campaign_id": campaign_id}
        for i, key in enumerate(mapped):
            raw = vals[i].strip() if i < len(vals) else ""

            if key == "sku_id":
                try:
                    row[key] = int(raw)
                except (ValueError, TypeError):
                    continue  # skip "Всего", "Корректировка" etc.

            elif key == "sku_name":
                row[key] = raw

            elif key == "date_added":
                try:
                    from datetime import date as date_type
                    parts = raw.split(".")
                    if len(parts) == 3:
                        row[key] = date_type(int(parts[2]), int(parts[1]), int(parts[0])).isoformat()
                    elif raw and raw != "01.01.0001":
                        row[key] = raw
                    else:
                        row[key] = None
                except (ValueError, IndexError):
                    row[key] = None

            elif key in ("impressions", "clicks", "add_to_cart", "sold_units"):
                row[key] = int(raw) if raw else 0

            elif key in ("sku_price", "ctr", "avg_cpc", "spend",
                         "sales_promotion", "total_ordered",
                         "drr_promotion", "drr_total"):
                row[key] = _parse_russian_number(raw)

        # 确保有 sku_id（跳过汇总/修正行）
        if "sku_id" not in row or row["sku_id"] == 0:
            continue
        rows.append(row)

    return rows


# ── 工厂函数 ──────────────────────────────────────────────

def get_perf_client() -> OzonPerfClient:
    return OzonPerfClient(
        client_id=settings.ozon_perf_client_id,
        client_secret=settings.ozon_perf_client_secret,
    )
