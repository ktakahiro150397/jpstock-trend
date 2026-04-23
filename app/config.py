from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "jpstock-trend"
    app_env: str = "dev"
    secret_key: str = "change-me"
    timezone: str = "Asia/Tokyo"

    database_url: str = "sqlite:///./app.db"

    symbol_list: str = "7203.T,6758.T,AAPL"
    analysis_lookback_days: int = 500
    notify_threshold: int = 70

    discord_webhook_url: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:8000/auth/callback"
    allowed_emails: str = ""
    auth_skip_enabled: bool = False
    auth_skip_email: str = "dev@example.com"
    auth_skip_name: str = "Dev User"

    weekly_cron_day_of_week: str = "sun"
    weekly_cron_hour: int = 9
    weekly_cron_minute: int = 0
    ingest_cron_hour: int = 6
    ingest_cron_minute: int = 30
    yahoo_request_interval_seconds: float = 2.0
    yahoo_max_retries: int = 3
    yahoo_rate_limit_cooldown_seconds: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def symbols(self) -> list[str]:
        return [s.strip() for s in self.symbol_list.split(",") if s.strip()]

    @property
    def allowed_email_list(self) -> list[str]:
        return [e.strip().lower() for e in self.allowed_emails.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
