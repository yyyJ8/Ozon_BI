"""
SQLAlchemy 数据库连接
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖：获取数据库 session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
