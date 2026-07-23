"""
应用配置 — 从 .env 读取数据库连接信息
Ozon API 凭证已迁移到 ozon.stores 表，不再通过 .env 管理
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── 数据库 ──
    db_host: str = "192.168.111.78"
    db_port: int = 5432
    db_name: str = "ai_application"
    db_user: str = "wensixin"
    db_password: str = ""

    # ── 定时任务 ──
    sync_cron_hours: str = "9,19"  # 每天几点执行全量同步（逗号分隔）
    ad_sync_days: int = 3          # 每次同步拉取最近N天的广告SKU明细

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def database_url_async(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
