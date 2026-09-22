import os
from pathlib import Path
from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[
            Path(__file__).resolve().parent.parent.parent / ".env",
            Path(__file__).resolve().parent.parent / ".env",
            ".env",
        ],
        extra="ignore",
    )

    # App Settings
    APP_NAME: str = "Blindfold BI - Skylark Drones"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # File Paths
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
    CONTRACTS_PATH: Path = PROJECT_ROOT / "contracts" / "metric_contract.yaml"
    SCHEMA_MAP_PATH: Path = PROJECT_ROOT / "contracts" / "schema_map.yaml"
    DEALS_EXCEL_PATH: Path = PROJECT_ROOT / "backend" / "tests" / "fixtures" / "Deal funnel Data.xlsx"
    WO_EXCEL_PATH: Path = PROJECT_ROOT / "backend" / "tests" / "fixtures" / "Work_Order_Tracker Data.xlsx"

    # LLM Settings (NVIDIA NIM Free Tier)
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_BASE_URL: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    NVIDIA_MODEL: str = os.getenv("NVIDIA_MODEL", "openai/gpt-oss-120b")
    # Optional comma-separated fallback chain, tried in order after NVIDIA_MODEL. IDs must exist in your NVIDIA catalog.
    NVIDIA_FALLBACK_MODELS: str = os.getenv("NVIDIA_FALLBACK_MODELS", "openai/gpt-oss-20b")

    # Monday.com API Settings (Optional live connector)
    MONDAY_API_TOKEN: str = os.getenv("MONDAY_API_TOKEN", "")
    MONDAY_API_URL: str = "https://api.monday.com/v2"
    MONDAY_DEALS_BOARD_ID: str = os.getenv("MONDAY_DEALS_BOARD_ID", "")
    MONDAY_WO_BOARD_ID: str = os.getenv("MONDAY_WO_BOARD_ID", "")
    MONDAY_SIGNING_SECRET: str = os.getenv("MONDAY_SIGNING_SECRET", "")
    MONDAY_DATA_SOURCE_PRIORITY: str = os.getenv("MONDAY_DATA_SOURCE_PRIORITY", "monday_first")
    CACHE_TTL_SECONDS: int = 600  # 10 minutes
    # Local Excel fixtures are for tests/dev only. None = allowed unless ENVIRONMENT == "production".
    ALLOW_FIXTURE_FALLBACK: Optional[bool] = None

    # Security & API Key
    API_KEY: str = os.getenv("API_KEY", "skylark-secret-v1-key")
    LLM_MODE: str = os.getenv("LLM_MODE", "on")
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    AS_OF_DATE: str = "15 Jan 2026"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    API_KEY_PEPPER: str = os.getenv("API_KEY_PEPPER", "dev-pepper-blindfold-bi-secret-32b")
    ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "dev-admin-token-super-secret-12345")
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = os.getenv("AZURE_STORAGE_CONNECTION_STRING", None)
    AZURE_STORAGE_CONTAINER: str = os.getenv("AZURE_STORAGE_CONTAINER", "blindfold-keys")

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://mango-plant-08ea0340f.1.azurestaticapps.net",
    ]
    CORS_ORIGIN_REGEX: Optional[str] = r"^https:\/\/.*\.azurestaticapps\.net$"

    @property
    def fixtures_allowed(self) -> bool:
        if self.ALLOW_FIXTURE_FALLBACK is not None:
            return bool(self.ALLOW_FIXTURE_FALLBACK)
        return self.ENVIRONMENT.strip().lower() != "production"

    @model_validator(mode="after")
    def _no_dev_secrets_in_production(self):
        """The repo is public, so the development defaults must never be accepted in production."""
        if self.ENVIRONMENT.strip().lower() == "production":
            if self.API_KEY == "skylark-secret-v1-key":
                self.API_KEY = ""
            if self.ADMIN_TOKEN == "dev-admin-token-super-secret-12345":
                self.ADMIN_TOKEN = ""
        return self


settings = Settings()
