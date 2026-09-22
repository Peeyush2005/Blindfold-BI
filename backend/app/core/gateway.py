"""
Blindfold Gateway Service.
Coordinates session-scoped tokenizer instances, DuckDB catalog population,
and entity masking/rehydration lifecycle.
"""

import logging
from typing import Dict, Any, Optional
from app.core.tokenizer import BlindfoldTokenizer
from app.data.duckdb_store import duckdb_store

logger = logging.getLogger(__name__)


class BlindfoldGatewayService:
    """Manages session tokenizers and guarantees Zero PII leakage across sessions."""

    def __init__(self):
        self._sessions: Dict[str, BlindfoldTokenizer] = {}
        self._global_tokenizer = BlindfoldTokenizer(session_salt="global-skylark-salt")
        self._initialized = False

    def init_catalog(self):
        """Loads all real entity identifiers from DuckDB into token catalog."""
        try:
            if not duckdb_store.initialized:
                logger.info("Blindfold Gateway catalog deferred: no data loaded yet.")
                return

            # Deals catalog
            d_rows, _, _ = duckdb_store.query(
                "SELECT DISTINCT deal_alias, client_id, owner_id FROM deals WHERE deal_alias IS NOT NULL;"
            )
            # Work Orders catalog
            w_rows, _, _ = duckdb_store.query(
                "SELECT DISTINCT deal_alias, client_id, owner_id FROM work_orders WHERE deal_alias IS NOT NULL;"
            )

            deals = set()
            clients = set()
            owners = set()

            for r in d_rows + w_rows:
                if r.get("deal_alias"):
                    deals.add(str(r["deal_alias"]))
                if r.get("client_id"):
                    clients.add(str(r["client_id"]))
                if r.get("owner_id"):
                    owners.add(str(r["owner_id"]))

            self._global_tokenizer.register_entities(
                deals=list(deals),
                clients=list(clients),
                owners=list(owners),
            )
            self._initialized = True
            logger.info(
                f"Blindfold Gateway catalog initialized with {len(deals)} deals, "
                f"{len(clients)} clients, {len(owners)} owners."
            )
        except Exception as e:
            logger.error(f"Failed to initialize Blindfold Gateway catalog: {e}")

    def get_tokenizer(self, session_id: str = "default") -> BlindfoldTokenizer:
        """Retrieves or creates a session-scoped BlindfoldTokenizer."""
        if not self._initialized:
            self.init_catalog()

        if session_id not in self._sessions:
            # Create session tokenizer inheriting global catalog
            tok = BlindfoldTokenizer(session_salt=f"salt-{session_id}")
            tok.entity_to_token = dict(self._global_tokenizer.entity_to_token)
            tok.token_to_entity = dict(self._global_tokenizer.token_to_entity)
            tok.entity_types = dict(self._global_tokenizer.entity_types)
            tok.known_entities = set(self._global_tokenizer.known_entities)
            tok.client_counter = self._global_tokenizer.client_counter
            tok.deal_counter = self._global_tokenizer.deal_counter
            tok.owner_counter = self._global_tokenizer.owner_counter
            self._sessions[session_id] = tok

        return self._sessions[session_id]

    # Convenience delegators using global/default tokenizer
    def anonymize_text(self, text: str, session_id: str = "default") -> str:
        return self.get_tokenizer(session_id).tokenize_text(text)

    def deanonymize_text(self, text: str, session_id: str = "default") -> str:
        return self.get_tokenizer(session_id).rehydrate_text(text)

    def anonymize_obj(self, obj: Any, session_id: str = "default") -> Any:
        return self.get_tokenizer(session_id).tokenize_obj(obj)

    def register_entities(self, deals=None, clients=None, owners=None):
        self._global_tokenizer.register_entities(deals=deals, clients=clients, owners=owners)

    @property
    def entity_to_token(self):
        return self._global_tokenizer.entity_to_token

    @property
    def token_to_entity(self):
        return self._global_tokenizer.token_to_entity


blindfold_gateway = BlindfoldGatewayService()
# Backward-compatibility alias
blindfold = blindfold_gateway
