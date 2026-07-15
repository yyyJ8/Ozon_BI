"""
Ozon Seller API 客户端

封装所有用到的 Ozon API 接口，处理认证、限流、重试
"""
import time
from typing import Any, Optional

import httpx
from loguru import logger

from app.config import settings


class OzonClient:
    """Ozon Seller API HTTP 客户端"""

    def __init__(self, client_id: str, api_key: str):
        self._client = httpx.Client(
            base_url="https://api-seller.ozon.ru",
            headers={
                "Client-Id": client_id,
                "Api-Key": api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        self._last_req = 0.0

    def _rate_limit_wait(self):
        """确保请求间隔 ~0.8s，避免 429 限流"""
        elapsed = time.time() - self._last_req
        if elapsed < 0.8:
            time.sleep(0.8 - elapsed)

    def _request(self, path: str, json_data: Optional[dict] = None) -> dict:
        """通用请求方法，自动处理限流重试"""
        self._rate_limit_wait()
        resp = self._client.request("POST", path, json=json_data or {})

        # 429 → 等 2s 重试一次
        if resp.status_code == 429:
            logger.warning(f"429 rate limit on {path}, retrying after 2s...")
            time.sleep(2)
            self._rate_limit_wait()
            resp = self._client.request("POST", path, json=json_data or {})

        resp.raise_for_status()
        self._last_req = time.time()
        return resp.json()

    # ── 商品接口 ──────────────────────────────────────────

    def get_product_list(self) -> list[dict]:
        """获取所有商品 ID 列表（游标分页）"""
        all_items: list[dict] = []
        last_id = ""
        while True:
            data = self._request("/v3/product/list", {
                "filter": {"visibility": "ALL"},
                "limit": 1000,
                "last_id": last_id,
            })
            items = data.get("result", {}).get("items", [])
            all_items.extend(items)
            if not items:
                break
            last_id = str(items[-1].get("id", ""))
            if len(items) < 1000:
                break
        return all_items

    def get_product_info(self, product_ids: list[int]) -> list[dict]:
        """批量获取商品详情（每批最多 100 个 product_id）"""
        all_products: list[dict] = []
        for i in range(0, len(product_ids), 100):
            batch = product_ids[i:i + 100]
            data = self._request("/v3/product/info/list", {"product_id": batch})
            all_products.extend(data.get("items", []))
        return all_products

    # ── 销售分析接口 ──────────────────────────────────────

    def get_analytics(self, date_from: str, date_to: str,
                      offset: int = 0, limit: int = 1000) -> dict:
        """获取销售分析数据"""
        return self._request("/v1/analytics/data", {
            "date_from": date_from,
            "date_to": date_to,
            "metrics": ["ordered_units", "revenue"],
            "dimension": ["sku", "day"],
            "limit": limit,
            "offset": offset,
        })

    def get_all_analytics(self, date_from: str, date_to: str) -> list[dict]:
        """全量拉取销售分析（处理分页）"""
        all_rows: list[dict] = []
        offset = 0
        while True:
            data = self.get_analytics(date_from, date_to, offset=offset, limit=1000)
            rows = data.get("result", {}).get("data", [])
            all_rows.extend(rows)
            if len(rows) < 1000:
                break
            offset += 1000
        return all_rows

    # ── 财务接口 ──────────────────────────────────────────

    def get_finance_page(self, date_from: str, date_to: str,
                         page: int, page_size: int = 200) -> dict:
        """获取一页财务流水"""
        return self._request("/v3/finance/transaction/list", {
            "filter": {
                "date": {"from": date_from, "to": date_to},
            },
            "page": page,
            "page_size": page_size,
        })

    def get_all_finance(self, date_from: str, date_to: str) -> list[dict]:
        """全量拉取财务流水（处理分页）"""
        all_ops: list[dict] = []
        page = 1
        while True:
            data = self.get_finance_page(date_from, date_to, page=page)
            ops = data.get("result", {}).get("operations", [])
            if not ops:
                break
            all_ops.extend(ops)
            page += 1
        return all_ops

    # ── 订单履约接口 ──────────────────────────────────────

    def get_posting_fbo_page(self, date_from: str, date_to: str,
                              offset: int = 0, limit: int = 1000,
                              status: str = "") -> tuple[list[dict], bool]:
        """获取一页 FBO 订单（含 products、status、created_at 等完整字段）"""
        data = self._request("/v2/posting/fbo/list", {
            "dir": "asc",
            "filter": {
                "since": date_from + "T00:00:00Z",
                "to": date_to + "T23:59:59Z",
                "status": status,
            },
            "limit": limit,
            "offset": offset,
        })
        result = data.get("result", {})
        if isinstance(result, dict):
            return result.get("postings", []), result.get("has_next", False)
        return result, False if isinstance(result, list) else False

    def get_posting_fbs_page(self, date_from: str, date_to: str,
                              offset: int = 0, limit: int = 1000,
                              status: str = "") -> tuple[list[dict], bool]:
        """获取一页 FBS 订单"""
        data = self._request("/v3/posting/fbs/list", {
            "dir": "asc",
            "filter": {
                "since": date_from + "T00:00:00Z",
                "to": date_to + "T23:59:59Z",
                "status": status,
            },
            "limit": limit,
            "offset": offset,
        })
        result = data.get("result", {})
        if isinstance(result, dict):
            return result.get("postings", []), result.get("has_next", False)
        return result, False if isinstance(result, list) else False

    def get_all_postings(self, date_from: str, date_to: str,
                          schema: str = "FBO") -> list[dict]:
        """全量拉取订单履约数据（处理分页）"""
        all_postings: list[dict] = []
        offset = 0
        get_page = self.get_posting_fbo_page if schema == "FBO" else self.get_posting_fbs_page
        while True:
            postings, has_next = get_page(date_from, date_to, offset=offset)
            all_postings.extend(postings)
            if not has_next:
                break
            offset += len(postings)
        return all_postings

    def get_posting_detail(self, posting_number: str) -> dict | None:
        """获取单个 posting 详情（先试 FBO，失败试 FBS）"""
        for endpoint in ("/v2/posting/fbo/get", "/v3/posting/fbs/get"):
            try:
                resp = self._client.request("POST", endpoint, json={"posting_number": posting_number})
                if resp.status_code == 200:
                    return resp.json().get("result", {})
                if resp.status_code != 404:
                    resp.raise_for_status()
            except Exception:
                continue
        return None

    def close(self):
        self._client.close()


# 全局单例
def get_ozon_client() -> OzonClient:
    return OzonClient(
        client_id=settings.ozon_client_id,
        api_key=settings.ozon_api_key,
    )
