"""
应用配置 — 从 .env 读取
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── 数据库 ──
    db_host: str = "192.168.111.78"
    db_port: int = 5432
    db_name: str = "ai_application"
    db_user: str = "wensixin"
    db_password: str = ""

    # ── Ozon Seller API（主账号）──
    ozon_client_id: str = ""
    ozon_api_key: str = ""

    # ── Ozon Performance API（广告）──
    ozon_perf_client_id: str = ""
    ozon_perf_client_secret: str = ""

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def database_url_async(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
