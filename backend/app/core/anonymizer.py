import re
import logging
from typing import Dict, Any, List, Set

logger = logging.getLogger(__name__)

class BlindfoldGateway:
    """
    Decentralized and Anonymous Privacy Gateway.
    Tokenizes all real client names, deal names, and personnel codes before any
    payload is passed to the LLM (e.g., NVIDIA NIM).
    Re-hydrates tokens to original entity names strictly on final UI presentation.
    """
    def __init__(self):
        self.entity_to_token: Dict[str, str] = {}
        self.token_to_entity: Dict[str, str] = {}
        self.client_counter = 1
        self.deal_counter = 1
        self.owner_counter = 1
        self.known_deal_names: Set[str] = set()

    def register_entities(self, deals_list: List[str], clients_list: List[str], owners_list: List[str]):
        """Pre-populate entity catalogs to ensure deterministic token assignment."""
        for owner in sorted(set(owners_list)):
            if owner and owner not in self.entity_to_token:
                token = f"OWNER_REP_{self.owner_counter:02d}"
                self.entity_to_token[owner] = token
                self.token_to_entity[token] = owner
                self.owner_counter += 1

        for client in sorted(set(clients_list)):
            if client and client not in self.entity_to_token:
                token = f"CLIENT_ENT_{self.client_counter:03d}"
                self.entity_to_token[client] = token
                self.token_to_entity[token] = client
                self.client_counter += 1

        for deal in sorted(set(deals_list)):
            if deal and deal not in self.entity_to_token:
                self.known_deal_names.add(deal)
                token = f"PROJECT_DEAL_{self.deal_counter:03d}"
                self.entity_to_token[deal] = token
                self.token_to_entity[token] = deal
                self.deal_counter += 1

    def get_or_create_token(self, entity_str: str, entity_type: str = "generic") -> str:
        s = entity_str.strip()
        if not s:
            return s
        if s in self.entity_to_token:
            return self.entity_to_token[s]

        # Check by pattern
        if re.search(r"company|wocompany", s, re.IGNORECASE):
            token = f"CLIENT_ENT_{self.client_counter:03d}"
            self.client_counter += 1
        elif re.search(r"owner", s, re.IGNORECASE):
            token = f"OWNER_REP_{self.owner_counter:02d}"
            self.owner_counter += 1
        else:
            token = f"PROJECT_DEAL_{self.deal_counter:03d}"
            self.deal_counter += 1

        self.entity_to_token[s] = token
        self.token_to_entity[token] = s
        return token

    def anonymize_text(self, text: str) -> str:
        """Substitutes any known real names/codes with tokens in a text string."""
        if not text:
            return text
        anonymized = text
        # Replace known entities sorted by length descending so longest phrases match first
        for entity in sorted(self.entity_to_token.keys(), key=len, reverse=True):
            if len(entity) >= 3 and entity in anonymized:
                token = self.entity_to_token[entity]
                # Word boundary match where applicable
                pattern = re.compile(rf"\b{re.escape(entity)}\b", re.IGNORECASE)
                anonymized = pattern.sub(token, anonymized)
        return anonymized

    def deanonymize_text(self, text: str) -> str:
        """Restores tokens back to real names in the generated text."""
        if not text:
            return text
        deanonymized = text
        for token, real_val in sorted(self.token_to_entity.items(), key=lambda x: len(x[0]), reverse=True):
            if token in deanonymized:
                deanonymized = deanonymized.replace(token, real_val)
        return deanonymized

    def anonymize_obj(self, obj: Any) -> Any:
        """Recursively tokenizes dictionary or list structures."""
        if isinstance(obj, dict):
            new_dict = {}
            for k, v in obj.items():
                if k in ["client_code", "deal_client"]:
                    new_dict[k] = self.get_or_create_token(str(v), "client") if v else v
                elif k in ["deal_name"]:
                    new_dict[k] = self.get_or_create_token(str(v), "deal") if v else v
                elif k in ["owner_code", "deal_owner"]:
                    new_dict[k] = self.get_or_create_token(str(v), "owner") if v else v
                else:
                    new_dict[k] = self.anonymize_obj(v)
            return new_dict
        elif isinstance(obj, list):
            return [self.anonymize_obj(item) for item in obj]
        elif isinstance(obj, str):
            return self.anonymize_text(obj)
        return obj

    def get_token_map(self) -> Dict[str, str]:
        """Returns the token -> entity dictionary for audit inspection."""
        return dict(self.token_to_entity)

blindfold = BlindfoldGateway()
