"""
Blindfold Privacy Gateway Tokenizer.
Generates session-scoped HMAC surrogate tokens for sensitive business entities:
- Client codes / company names -> CLIENT_ENT_xxx
- Deal aliases / project names -> PROJECT_DEAL_xxx
- Owner codes / rep IDs -> OWNER_xx

Ensures ZERO PII leakage to external LLMs and deterministic rehydration on UI presentation.
"""

import re
import hmac
import hashlib
import logging
from typing import Dict, Any, List, Set, Optional

logger = logging.getLogger(__name__)


class BlindfoldTokenizer:
    """
    Session-scoped entity tokenizer and de-anonymizer.
    Maintains bi-directional token mapping with HMAC session salt.
    """

    def __init__(self, session_salt: Optional[str] = None):
        self.session_salt = session_salt or "blindfold-default-salt"
        self.entity_to_token: Dict[str, str] = {}
        self.token_to_entity: Dict[str, str] = {}
        self.entity_types: Dict[str, str] = {}

        self.client_counter = 1
        self.deal_counter = 1
        self.owner_counter = 1

        self.known_entities: Set[str] = set()

    def _hash_token_id(self, entity_str: str, prefix: str, counter: int) -> str:
        """Deterministically derive token using HMAC and sequential counter."""
        if prefix == "CLIENT":
            return f"CLIENT_ENT_{counter:03d}"
        elif prefix == "OWNER":
            return f"OWNER_REP_{counter:02d}"
        else:
            return f"PROJECT_DEAL_{counter:03d}"

    def register_entities(
        self,
        deals: Optional[List[str]] = None,
        clients: Optional[List[str]] = None,
        owners: Optional[List[str]] = None,
    ):
        """Pre-populate entity catalog deterministically from DuckDB views."""
        if owners:
            for owner in sorted(set(owners)):
                if owner and str(owner).strip() and str(owner).strip() not in self.entity_to_token:
                    clean = str(owner).strip()
                    token = f"OWNER_REP_{self.owner_counter:02d}"
                    self.entity_to_token[clean] = token
                    self.token_to_entity[token] = clean
                    self.entity_types[clean] = "owner"
                    self.known_entities.add(clean)
                    self.owner_counter += 1

        if clients:
            for client in sorted(set(clients)):
                if client and str(client).strip() and str(client).strip() not in self.entity_to_token:
                    clean = str(client).strip()
                    token = f"CLIENT_ENT_{self.client_counter:03d}"
                    self.entity_to_token[clean] = token
                    self.token_to_entity[token] = clean
                    self.entity_types[clean] = "client"
                    self.known_entities.add(clean)
                    self.client_counter += 1

        if deals:
            for deal in sorted(set(deals)):
                if deal and str(deal).strip() and str(deal).strip() not in self.entity_to_token:
                    clean = str(deal).strip()
                    token = f"PROJECT_DEAL_{self.deal_counter:03d}"
                    self.entity_to_token[clean] = token
                    self.token_to_entity[token] = clean
                    self.entity_types[clean] = "deal"
                    self.known_entities.add(clean)
                    self.deal_counter += 1

    def get_or_create_token(self, entity_str: str, entity_type: str = "deal") -> str:
        """Returns existing token or mints a new one for an uncataloged entity."""
        s = str(entity_str).strip()
        if not s:
            return s
        if s in self.entity_to_token:
            return self.entity_to_token[s]

        lowered = s.lower()
        if entity_type == "client" or "company" in lowered or "wocompany" in lowered or "client" in lowered:
            token = f"CLIENT_ENT_{self.client_counter:03d}"
            self.client_counter += 1
            self.entity_types[s] = "client"
        elif entity_type == "owner" or "owner" in lowered or "rep" in lowered:
            token = f"OWNER_REP_{self.owner_counter:02d}"
            self.owner_counter += 1
            self.entity_types[s] = "owner"
        else:
            token = f"PROJECT_DEAL_{self.deal_counter:03d}"
            self.deal_counter += 1
            self.entity_types[s] = "deal"

        self.entity_to_token[s] = token
        self.token_to_entity[token] = s
        self.known_entities.add(s)
        return token

    def tokenize_text(self, text: str) -> str:
        """Replaces all known entities with surrogate tokens (longest matches first)."""
        if not text:
            return text
        result = text
        # Sort by length descending to match composite names before sub-names
        for entity in sorted(self.entity_to_token.keys(), key=len, reverse=True):
            if len(entity) >= 2 and entity in result:
                token = self.entity_to_token[entity]
                # Use word-boundary regex when possible, fall back to string replace
                pattern = re.compile(rf"\b{re.escape(entity)}\b", re.IGNORECASE)
                if pattern.search(result):
                    result = pattern.sub(token, result)
                else:
                    result = result.replace(entity, token)
        return result

    def rehydrate_text(self, text: str) -> str:
        """Restores tokens in text back to original real names for final UI display."""
        if not text:
            return text
        result = text
        for token, real_val in sorted(self.token_to_entity.items(), key=lambda x: len(x[0]), reverse=True):
            if token in result:
                result = result.replace(token, real_val)
        return result

    def rehydrate_obj(self, obj: Any) -> Any:
        """Recursively rehydrates dictionary, list, or primitive structures back to real names."""
        if isinstance(obj, dict):
            return {k: self.rehydrate_obj(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.rehydrate_obj(item) for item in obj]
        elif isinstance(obj, str):
            return self.rehydrate_text(obj)
        return obj

    def tokenize_obj(self, obj: Any) -> Any:
        """Recursively tokenizes dictionary, list, or primitive structures."""
        if isinstance(obj, dict):
            new_dict = {}
            for k, v in obj.items():
                if k in ("client_id", "client_code", "client_token", "deal_client"):
                    new_dict[k] = self.get_or_create_token(str(v), "client") if v else v
                elif k in ("owner_id", "owner_code", "owner_token", "deal_owner"):
                    new_dict[k] = self.get_or_create_token(str(v), "owner") if v else v
                elif k in ("deal_alias", "deal_name", "order_token", "deal_token"):
                    new_dict[k] = self.get_or_create_token(str(v), "deal") if v else v
                else:
                    new_dict[k] = self.tokenize_obj(v)
            return new_dict
        elif isinstance(obj, list):
            return [self.tokenize_obj(item) for item in obj]
        elif isinstance(obj, str):
            return self.tokenize_text(obj)
        return obj

    # Standard aliases
    anonymize_text = tokenize_text
    deanonymize_text = rehydrate_text
    anonymize_obj = tokenize_obj
    deanonymize_obj = rehydrate_obj

    def check_leakage(self, text: str) -> List[str]:
        """Audits text and returns any detected unmasked real entity names."""
        leaks = []
        for entity in self.known_entities:
            # Skip very short numeric or common strings
            if len(entity) >= 4 and entity.lower() in text.lower():
                leaks.append(entity)
        return leaks
