"""中台数据库连接管理 — omsprod (PostgreSQL) + db_warehouse (MySQL)"""
import os
from contextlib import contextmanager

import psycopg2
import psycopg2.pool
import pymysql


# ── PostgreSQL omsprod ─────────────────────────────────────────────

_pg_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _get_pg_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pg_pool
    if _pg_pool is None:
        _pg_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            host=os.getenv("OMS_PG_HOST", "pgm-7xvui1j4600t1u27-l2.pg.rds.aliyuncs.com"),
            port=int(os.getenv("OMS_PG_PORT", "5432")),
            dbname=os.getenv("OMS_PG_DB", "omsprod"),
            user=os.getenv("OMS_PG_USER", "readuser"),
            password=os.getenv("OMS_PG_PASSWORD", "Yy20251106!rus"),
            connect_timeout=10,
        )
    return _pg_pool


def get_oms_pg():
    """获取 PostgreSQL omsprod 连接（FastAPI 依赖）"""
    pool = _get_pg_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


# ── MySQL db_warehouse ──────────────────────────────────────────────

_mysql_config: dict | None = None


def _get_mysql_config() -> dict:
    global _mysql_config
    if _mysql_config is None:
        _mysql_config = {
            "host": os.getenv("DW_MYSQL_HOST", "223.84.201.140"),
            "port": int(os.getenv("DW_MYSQL_PORT", "9030")),
            "user": os.getenv("DW_MYSQL_USER", "wangyilong"),
            "password": os.getenv("DW_MYSQL_PASSWORD", "wAng0730lonG"),
            "charset": "utf8mb4",
            "connect_timeout": 10,
            "cursorclass": pymysql.cursors.DictCursor,
        }
    return _mysql_config


def get_oms_mysql():
    """获取 MySQL db_warehouse 连接（FastAPI 依赖）"""
    conn = pymysql.connect(**_get_mysql_config())
    try:
        yield conn
    finally:
        conn.close()


# ── 上下文管理器（供脚本使用）───────────────────────────────────────

@contextmanager
def oms_pg_ctx():
    """用法: with oms_pg_ctx() as conn: ..."""
    pool = _get_pg_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


@contextmanager
def oms_mysql_ctx():
    """用法: with oms_mysql_ctx() as conn: ..."""
    conn = pymysql.connect(**_get_mysql_config())
    try:
        yield conn
    finally:
        conn.close()
