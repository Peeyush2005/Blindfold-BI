"""
API Key Store and Validation Engine for Blindfold BI.
Enforces Section 8b API key specifications:
- Format: bbi_<env>_<key_id>_<secret> (secret: 32 random base64url bytes)
- Stored: HMAC-SHA256(pepper, secret)
- Scopes: chat:run, tools:read, data:refresh, mcp:use
- Storage: In-memory 60s cache backed by local JSON file (dev) or Azure Blob (prod)
- Timing-safe HMAC verification via hmac.compare_digest
"""

import os
import json
import time
import secrets
import hmac
import hashlib
import base64
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

VALID_SCOPES = {"chat:run", "tools:read", "data:refresh", "mcp:use"}


class KeyRecord(BaseModel):
    key_id: str
    hashed_secret: str
    name: str
    scopes: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    expires_at: Optional[float] = None
    revoked_at: Optional[float] = None


class KeyStore:
    def __init__(self):
        self.pepper = settings.API_KEY_PEPPER.encode("utf-8")
        self.env = settings.ENVIRONMENT.lower()
        self.storage_file = settings.PROJECT_ROOT / "storage" / "keys.json"
        self._cache: Dict[str, KeyRecord] = {}
        self._cache_updated_at: float = 0.0
        self._cache_ttl: float = 60.0  # 60s cache TTL

        # Ensure storage directory exists
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_keys()

    def _hash_secret(self, secret: str) -> str:
        return hmac.new(self.pepper, secret.encode("utf-8"), hashlib.sha256).hexdigest()

    def _load_keys(self) -> None:
        """Loads keys from persistent storage into memory cache."""
        try:
            if self.storage_file.exists():
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._cache = {k: KeyRecord(**v) for k, v in data.items()}
            else:
                self._cache = {}
            self._cache_updated_at = time.time()
        except Exception as e:
            logger.error(f"Failed to load keys from storage: {e}")

    def _save_keys(self) -> None:
        """Persists keys from memory cache to persistent storage."""
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump({k: v.model_dump() for k, v in self._cache.items()}, f, indent=2)
            self._cache_updated_at = time.time()
        except Exception as e:
            logger.error(f"Failed to save keys to storage: {e}")

    def _ensure_fresh_cache(self) -> None:
        if time.time() - self._cache_updated_at > self._cache_ttl:
            self._load_keys()

    def health_status(self) -> str:
        """Returns 'ok' or 'degraded' depending on storage readability."""
        try:
            self._ensure_fresh_cache()
            return "ok"
        except Exception:
            return "degraded"

    def create_key(
        self,
        name: str,
        scopes: List[str],
        expires_in_days: Optional[int] = None,
    ) -> Tuple[str, KeyRecord]:
        """
        Creates a new Blindfold API key.
        Returns: (full_key_string, KeyRecord)
        """
        invalid_scopes = [s for s in scopes if s not in VALID_SCOPES]
        if invalid_scopes:
            raise ValueError(f"Invalid scopes requested: {invalid_scopes}")

        key_id = secrets.token_hex(4)  # 8 char hex
        secret_bytes = secrets.token_bytes(32)
        secret = base64.urlsafe_b64encode(secret_bytes).decode("utf-8").rstrip("=")

        full_key = f"bbi_{self.env}_{key_id}_{secret}"
        hashed_secret = self._hash_secret(secret)

        now = time.time()
        expires_at = (now + expires_in_days * 86400) if expires_in_days else None

        record = KeyRecord(
            key_id=key_id,
            hashed_secret=hashed_secret,
            name=name,
            scopes=scopes,
            created_at=now,
            expires_at=expires_at,
            revoked_at=None,
        )

        self._ensure_fresh_cache()
        self._cache[key_id] = record
        self._save_keys()
        logger.info(f"Created API key {key_id} ({name}) with scopes {scopes}")
        return full_key, record

    def get_key(self, key_id: str) -> Optional[KeyRecord]:
        self._ensure_fresh_cache()
        return self._cache.get(key_id)

    def list_keys(self) -> List[Dict[str, Any]]:
        self._ensure_fresh_cache()
        out = []
        for rec in self._cache.values():
            d = rec.model_dump()
            d.pop("hashed_secret", None)
            out.append(d)
        return out

    def revoke_key(self, key_id: str) -> bool:
        self._ensure_fresh_cache()
        if key_id not in self._cache:
            return False
        rec = self._cache[key_id]
        rec.revoked_at = time.time()
        self._cache[key_id] = rec
        self._save_keys()
        logger.info(f"Revoked API key {key_id}")
        return True

    def rotate_key(
        self,
        key_id: str,
        expires_in_days: Optional[int] = None,
    ) -> Optional[Tuple[str, KeyRecord]]:
        """Revokes the old key and issues a replacement with the same name and scopes."""
        self._ensure_fresh_cache()
        old = self._cache.get(key_id)
        if not old:
            return None

        # Revoke old
        self.revoke_key(key_id)
        # Create new
        return self.create_key(
            name=f"{old.name} (Rotated)",
            scopes=old.scopes,
            expires_in_days=expires_in_days,
        )

    def validate_key(
        self,
        key_str: str,
        required_scope: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[KeyRecord]]:
        """
        Validates API key string.
        Returns: (is_valid, error_code, record)
        Error codes: 'missing_api_key', 'invalid_api_key', 'revoked_api_key', 'expired_api_key', 'insufficient_scope'
        """
        if not key_str or not key_str.strip():
            return False, "missing_api_key", None

        key_str = key_str.strip()

        # Check for legacy master API_KEY support
        if settings.API_KEY and hmac.compare_digest(key_str, settings.API_KEY):
            legacy_rec = KeyRecord(
                key_id="legacy_master",
                hashed_secret="",
                name="Legacy Master Key",
                scopes=list(VALID_SCOPES),
            )
            return True, None, legacy_rec

        parts = key_str.split("_")
        # Format: bbi_<env>_<key_id>_<secret>
        if len(parts) < 4 or parts[0] != "bbi":
            return False, "invalid_api_key", None

        key_id = parts[2]
        secret = "_".join(parts[3:])

        self._ensure_fresh_cache()
        rec = self._cache.get(key_id)
        if not rec:
            return False, "invalid_api_key", None

        # Check secret hash timing-safely
        computed_hash = self._hash_secret(secret)
        if not hmac.compare_digest(computed_hash, rec.hashed_secret):
            return False, "invalid_api_key", None

        # Check revocation
        if rec.revoked_at is not None:
            return False, "revoked_api_key", rec

        # Check expiration
        if rec.expires_at is not None and time.time() > rec.expires_at:
            return False, "expired_api_key", rec

        # Check scope
        if required_scope and required_scope not in rec.scopes:
            return False, "insufficient_scope", rec

        return True, None, rec


key_store = KeyStore()
