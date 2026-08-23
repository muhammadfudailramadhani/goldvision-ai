"""Konfigurasi aplikasi GoldVision AI — semua credential lewat environment variables (§7, §29)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Application
    app_env: str = "development"
    database_url: str = "sqlite:///./goldvision.db"

    # Channels — §4: WhatsApp WAJIB false sampai aktivasi diminta eksplisit
    telegram_enabled: bool = True
    telegram_bot_token: str = ""
    telegram_admin_id: str = ""
    whatsapp_enabled: bool = False
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""

    # Market data & AI — §47: localhost = mock
    market_data_mode: str = "mock"
    ai_mode: str = "mock"
    payment_mode: str = "sandbox"
    twelvedata_api_key: str = ""
    alphavantage_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
