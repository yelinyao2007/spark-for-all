from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    app_mode: Literal['live', 'demo'] = 'live'
    database_path: str = 'data/spark.sqlite3'
    session_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    api_timeout_seconds: float = Field(default=25, gt=0, le=120)
    turn_timeout_seconds: float = Field(default=90, gt=0, le=180)
    anysearch_api_key: str = ''
    anysearch_base_url: str = 'https://api.anysearch.com'
    search_cache_seconds: int = Field(default=600, ge=0)
    search_daily_limit: int = Field(default=100, ge=1)
    llm_base_url: str = 'https://api.openai.com/v1'
    llm_api_key: str = ''
    llm_model: str = ''
    xingyun_app_id: str = ''
    xingyun_app_secret: str = ''
    xingyun_browser_auth_approved: bool = False
    cookie_secure: bool = False
