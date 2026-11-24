import json
import os
import re
from pathlib import Path
from typing import Annotated, Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _extract_board_id(raw: str) -> str:
    """Accept either a numeric Monday.com board ID or a full board URL."""
    val = (raw or "").strip()
    if not val:
        return ""
    match = re.search(r"/boards/(\d+)", val)
    return match.group(1) if match else val

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
    NVIDIA_MODEL: str = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3.5-bolt-e4b")

    # Monday.com API Settings (Optional live connector)
    MONDAY_API_TOKEN: str = os.getenv("MONDAY_API_TOKEN", "") or os.getenv("MONDAY_API_KEY", "")
    MONDAY_API_URL: str = "https://api.monday.com/v2"
    MONDAY_DEALS_BOARD_ID: str = _extract_board_id(
        os.getenv("MONDAY_DEALS_BOARD_ID", "") or os.getenv("MONDAY_DEAL_BOARD_ID", "")
    )
    MONDAY_WO_BOARD_ID: str = _extract_board_id(
        os.getenv("MONDAY_WO_BOARD_ID", "")
        or os.getenv("MONDAY_WORK_ORDER_BOARD_ID", "")
        or os.getenv("MONDAY_WORKORDERS_BOARD_ID", "")
    )
    MONDAY_DEAL_BOARD_ID: str = ""
    MONDAY_WORK_ORDER_BOARD_ID: str = ""
    MONDAY_WORKORDERS_BOARD_ID: str = ""
    MONDAY_API_KEY: str = ""
    MONDAY_SIGNING_SECRET: str = os.getenv("MONDAY_SIGNING_SECRET", "")
    MONDAY_DATA_SOURCE_PRIORITY: str = os.getenv("MONDAY_DATA_SOURCE_PRIORITY", "monday_first")
    CACHE_TTL_SECONDS: int = 600  # 10 minutes

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
    CORS_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://mango-plant-08ea0340f.1.azurestaticapps.net",
    ]
    CORS_ORIGIN_REGEX: Optional[str] = r"^https:\/\/.*\.(azurestaticapps\.net|vercel\.app|onrender\.com)$"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v):
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("["):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed if str(x).strip()]
                except json.JSONDecodeError:
                    pass
            return [x.strip() for x in s.split(",") if x.strip()]
        return v

    @model_validator(mode="after")
    def _normalize_monday_settings(self):
        if not self.MONDAY_API_TOKEN and self.MONDAY_API_KEY:
            self.MONDAY_API_TOKEN = self.MONDAY_API_KEY
        self.MONDAY_DEALS_BOARD_ID = _extract_board_id(
            self.MONDAY_DEALS_BOARD_ID or self.MONDAY_DEAL_BOARD_ID
        )
        self.MONDAY_WO_BOARD_ID = _extract_board_id(
            self.MONDAY_WO_BOARD_ID or self.MONDAY_WORK_ORDER_BOARD_ID or self.MONDAY_WORKORDERS_BOARD_ID
        )
        return self

settings = Settings()
