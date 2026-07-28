"""
异常检测引擎 — 从 YAML 配置加载规则，查询数据源，判定异常

规则可热改：修改 app/anomaly_rules.yaml 即可生效，不需要改代码。
"""
import operator as op
import os
from datetime import date, timedelta
from typing import Any, Optional

import yaml
from sqlalchemy import text
from sqlalchemy.orm import Session


# ═══════════════════════════════════════════════════════════════
# YAML 加载
# ═══════════════════════════════════════════════════════════════

_RULES_CACHE: Optional[dict] = None
_RULES_MTIME: float = 0


def _get_rules_path() -> str:
    return os.path.join(os.path.dirname(__file__), "..", "anomaly_rules.yaml")


def load_rules(force: bool = False) -> dict:
    """加载异常规则 YAML，带文件修改时间缓存"""
    global _RULES_CACHE, _RULES_MTIME
    path = _get_rules_path()
    mtime = os.path.getmtime(path)
    if not force and _RULES_CACHE is not None and mtime == _RULES_MTIME:
        return _RULES_CACHE
    with open(path, "r", encoding="utf-8") as f:
        _RULES_CACHE = yaml.safe_load(f)
    _RULES_MTIME = mtime
    return _RULES_CACHE


# ═══════════════════════════════════════════════════════════════
# 操作符映射
# ═══════════════════════════════════════════════════════════════

_OP_MAP = {
    "gte": op.ge,
    "lte": op.le,
    "gt": op.gt,
    "lt": op.lt,
    "eq": op.eq,
}

_OP_LABEL = {
    "gte": "≥",
    "lte": "≤",
    "gt": ">",
    "lt": "<",
    "eq": "=",
}


def _check_condition(value: Any, operator_str: str, threshold: Any) -> bool:
    """对单个值执行条件判定"""
    fn = _OP_MAP.get(operator_str)
    if fn is None:
        return False
    try:
        return fn(float(value or 0), float(threshold))
    except (TypeError, ValueError):
        return False


def _condition_label(field: str, operator_str: str, value: Any) -> str:
    """生成人类可读的条件表达式，如 'returns_units ≥ 4'"""
    return f"{field} {_OP_LABEL.get(operator_str, operator_str)} {value}"


# ═══════════════════════════════════════════════════════════════
# 数据源查询
# ═══════════════════════════════════════════════════════════════

def _query_daily_summary(db: Session, store_id: int, date_from: date, date_to: date) -> list[dict]:
    """查询 sku_daily_summary 按月聚合"""
    store_clause = "store_id = :store_id AND " if store_id != 0 else ""
    params = {"store_id": store_id, "date_from": date_from, "date_to": date_to}

    rows = db.execute(text(f"""
        SELECT store_id, sku_id,
               SUM(ordered_units)      AS ordered_units,
               SUM(revenue)            AS revenue,
               SUM(returns_units)      AS returns_units,
               SUM(net_profit)         AS net_profit,
               CASE WHEN SUM(revenue) > 0
                    THEN SUM(net_profit) / SUM(revenue) * 100
                    ELSE 0 END         AS profit_margin,
               MAX(stock_present)      AS stock_present
        FROM ozon.sku_daily_summary
        WHERE {store_clause}date BETWEEN :date_from AND :date_to
        GROUP BY store_id, sku_id
    """), params).fetchall()

    return [
        {
            "store_id": r[0], "sku_id": r[1], "ordered_units": int(r[2] or 0),
            "revenue": float(r[3] or 0), "returns_units": int(r[4] or 0),
            "net_profit": float(r[5] or 0), "profit_margin": float(r[6] or 0),
            "stock_present": int(r[7] or 0),
        }
        for r in rows
    ]


def _query_ad_performance(db: Session, store_id: int, date_from: date, date_to: date) -> list[dict]:
    """查询 ad_sku_daily_stats 按月聚合"""
    store_clause = "store_id = :store_id AND " if store_id != 0 else ""
    params = {"store_id": store_id, "date_from": date_from, "date_to": date_to}

    rows = db.execute(text(f"""
        SELECT store_id, sku_id,
               SUM(spend)              AS spend,
               SUM(clicks)             AS clicks,
               SUM(impressions)        AS impressions,
               SUM(sold_units)         AS sold_units,
               SUM(COALESCE(total_ordered, 0)) AS total_ordered,
               CASE WHEN SUM(impressions) > 0
                    THEN SUM(clicks)::float / SUM(impressions) * 100
                    ELSE 0 END         AS ctr,
               CASE WHEN SUM(COALESCE(total_ordered, 0)) > 0
                    THEN SUM(spend) / SUM(COALESCE(total_ordered, 0)) * 100
                    ELSE 0 END         AS drr_total
        FROM ozon.ad_sku_daily_stats
        WHERE {store_clause}stat_date BETWEEN :date_from AND :date_to
          AND sku_id > 0
        GROUP BY store_id, sku_id
    """), params).fetchall()

    return [
        {
            "store_id": r[0], "sku_id": r[1], "spend": float(r[2] or 0),
            "clicks": int(r[3] or 0), "impressions": int(r[4] or 0),
            "sold_units": int(r[5] or 0), "total_ordered": float(r[6] or 0),
            "ctr": float(r[7] or 0), "drr_total": float(r[8] or 0),
        }
        for r in rows
    ]


def _query_stock_snapshot(db: Session, store_id: int) -> list[dict]:
    """查询 stocks 实时库存快照"""
    store_clause = "store_id = :store_id AND " if store_id != 0 else ""
    params = {"store_id": store_id}

    rows = db.execute(text(f"""
        SELECT store_id, sku_id,
               COALESCE(SUM(present), 0) AS present
        FROM ozon.stocks
        WHERE {store_clause}1=1
        GROUP BY store_id, sku_id
    """), params).fetchall()

    return [
        {"store_id": r[0], "sku_id": r[1], "present": int(r[2] or 0)}
        for r in rows
    ]


_DATA_SOURCE_QUERIES = {
    "get_daily_summary": _query_daily_summary,
    "get_ad_performance": _query_ad_performance,
    "get_stock_snapshot": _query_stock_snapshot,
}


# ═══════════════════════════════════════════════════════════════
# 严重程度判定
# ═══════════════════════════════════════════════════════════════

def _determine_severity(row: dict, rule: dict) -> str:
    """根据 severity_map 或固定 severity 判定严重程度"""
    severity_map = rule.get("severity_map")
    if severity_map:
        # 有 severity_map：遍历 key 找匹配
        for level_key in ["critical", "warning", "info"]:
            if level_key in severity_map:
                # 对每个 field 检查是否匹配该级别
                for condition in rule.get("conditions", []):
                    field = condition["field"]
                    if field in row:
                        # critical: profit_margin < 0, warning: profit_margin < 10
                        level_threshold = _extract_threshold(severity_map[level_key])
                        if level_threshold is not None:
                            if level_key == "critical" and _check_condition(row[field], condition["op"], level_threshold):
                                return "critical"
                            elif level_key == "warning" and _check_condition(row[field], condition["op"], level_threshold):
                                if "critical" in severity_map:
                                    critical_val = _extract_threshold(severity_map["critical"])
                                    if critical_val is not None and _check_condition(row[field], condition["op"], critical_val):
                                        return "critical"
                                return "warning"
    return rule.get("severity", "info")


def _extract_threshold(desc: str) -> Optional[float]:
    """从 severity_map 描述中提取数值阈值，如 '< 0   → 亏损' → 0"""
    import re
    match = re.search(r'([<>]=?)\s*(-?[\d.]+)', desc)
    if match:
        return float(match.group(2))
    return None


# ═══════════════════════════════════════════════════════════════
# 产品信息批量补充
# ═══════════════════════════════════════════════════════════════

def _fetch_product_info(db: Session, store_id: int, sku_ids: list[int]) -> dict[int, dict]:
    """批量获取产品名称、货号、主图"""
    if not sku_ids:
        return {}
    store_clause = "store_id = :store_id AND " if store_id != 0 else ""
    rows = db.execute(text(f"""
        SELECT sku_id, offer_id, name, primary_image
        FROM ozon.products
        WHERE {store_clause}sku_id = ANY(:skus)
    """), {"store_id": store_id, "skus": sku_ids}).fetchall()

    return {
        r[0]: {"offer_id": r[1], "name": r[2], "primary_image": r[3]}
        for r in rows
    }


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

def detect_anomalies(
    db: Session,
    store_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    """
    执行全部异常检测规则，返回:

    {
        "summary": {"total_anomalies": N, "by_type": {...}},
        "items": [
            {sku_id, offer_id, name, primary_image, anomaly_type, severity,
             description, metrics, triggered_conditions}
        ]
    }
    """
    # 默认日期范围：当月 1 日 → 昨天
    if date_to is None:
        date_to = date.today() - timedelta(days=1)
    if date_from is None:
        date_from = date_to.replace(day=1)

    rules_config = load_rules()
    anomaly_rules = rules_config.get("anomaly_rules", {})

    # 用于汇总
    by_type: dict[str, int] = {}
    results: list[dict] = []

    # 收集所有命中的 sku_id，最后批量取产品信息
    all_sku_ids: set[int] = set()

    for rule_name, rule in anomaly_rules.items():
        data_source_key = rule.get("data_source")
        query_fn = _DATA_SOURCE_QUERIES.get(data_source_key)
        if query_fn is None:
            continue

        # 执行查询
        if data_source_key == "get_stock_snapshot":
            rows = query_fn(db, store_id)
        else:
            rows = query_fn(db, store_id, date_from, date_to)

        conditions = rule.get("conditions", [])
        require_all = rule.get("require", "all") == "all"

        for row in rows:
            # 判定条件
            if require_all:
                matched = all(
                    _check_condition(row.get(c["field"]), c["op"], c["value"])
                    for c in conditions
                )
            else:
                matched = any(
                    _check_condition(row.get(c["field"]), c["op"], c["value"])
                    for c in conditions
                )

            if not matched:
                continue

            # 判定严重程度
            severity = _determine_severity(row, rule)

            # 提取触发指标
            metrics = {}
            triggered_conditions = []
            for c in conditions:
                field = c["field"]
                val = row.get(field)
                metrics[field] = float(val) if val is not None else 0.0
                triggered_conditions.append(_condition_label(field, c["op"], c["value"]))

            all_sku_ids.add(row["sku_id"])

            results.append({
                "sku_id": row["sku_id"],
                "anomaly_type": rule_name,
                "severity": severity,
                "description": rule.get("description", rule_name),
                "metrics": metrics,
                "triggered_conditions": triggered_conditions,
            })

            by_type[rule_name] = by_type.get(rule_name, 0) + 1

    # 批量获取产品信息
    product_map = _fetch_product_info(db, store_id, list(all_sku_ids))

    # 合并产品信息到结果
    for item in results:
        pinfo = product_map.get(item["sku_id"], {})
        item["offer_id"] = pinfo.get("offer_id")
        item["name"] = pinfo.get("name")
        item["primary_image"] = pinfo.get("primary_image")

    # 构建 summary
    total = sum(by_type.values())
    summary = {"total_anomalies": total, "by_type": by_type}

    return {"summary": summary, "items": results}
