import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App Settings
    APP_NAME: str = "Blindfold BI - Skylark Drones"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # File Paths
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
    CONTRACTS_PATH: Path = PROJECT_ROOT / "contracts" / "metric_contract.yaml"
    DEALS_EXCEL_PATH: Path = PROJECT_ROOT / "Deal funnel Data.xlsx"
    WO_EXCEL_PATH: Path = PROJECT_ROOT / "Work_Order_Tracker Data.xlsx"

    # LLM Settings (NVIDIA NIM Free Tier)
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_BASE_URL: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    NVIDIA_MODEL: str = os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")

    # Monday.com API Settings (Optional live connector)
    MONDAY_API_TOKEN: str = os.getenv("MONDAY_API_TOKEN", "")
    MONDAY_API_URL: str = "https://api.monday.com/v2"
    MONDAY_DEALS_BOARD_ID: str = os.getenv("MONDAY_DEALS_BOARD_ID", "")
    MONDAY_WO_BOARD_ID: str = os.getenv("MONDAY_WO_BOARD_ID", "")
    MONDAY_SIGNING_SECRET: str = os.getenv("MONDAY_SIGNING_SECRET", "")
    CACHE_TTL_SECONDS: int = 600  # 10 minutes

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

settings = Settings()
