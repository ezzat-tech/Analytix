from dataclasses import dataclass, field
from typing import Dict, List, Optional
from fastapi import HTTPException

from src.main import Orchestrator
from src.query.query_engine import QueryEngine
from src.llm.llm_client import LLMClient
from src.llm.config import LLMConfig
from src.shared.tools import generate_session_id
from src.shared.session_manager import SessionManager
from src.api.schemas import Message

@dataclass
class SessionBundle:
    session_id: str
    orchestrator: Orchestrator
    query_engine: QueryEngine
    messages: List[Message] = field(default_factory=list)

class SessionRegistry:
    """
    Server-side registry that manages live Agent bundles.
    Maps session_id -> SessionBundle.
    """
    def __init__(self):
        self._sessions: Dict[str, SessionBundle] = {}

    def get_session(self, session_id: str) -> SessionBundle:
        """Retrieve an active session or raise 404."""
        if session_id not in self._sessions:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found or expired")
        return self._sessions[session_id]

    def get_or_create(self, session_id: Optional[str] = None) -> SessionBundle:
        """Retrieve existing session or initialize a new agent chain."""
        # 1. If session_id provided and exists, return it
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]

        # 2. Generate ID if not provided
        sid = session_id or generate_session_id()

        # 3. Initialize agent chain
        llm_config = LLMConfig()
        llm = LLMClient(config=llm_config)
        orchestrator = Orchestrator(session_id=sid, llm_client=llm)
        query_engine = QueryEngine(orchestrator=orchestrator)

        bundle = SessionBundle(
            session_id=sid,
            orchestrator=orchestrator,
            query_engine=query_engine,
            messages=[]
        )

        self._sessions[sid] = bundle
        return bundle

    async def hydrate_session(self, session_id: str) -> SessionBundle:
        """
        Load a session from disk and restore the live agent state.
        """
        # Load persisted state via SessionManager
        session_data = SessionManager.load_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail=f"No persisted session found for {session_id}")

        # Re-initialize agent chain
        llm_config = LLMConfig()
        llm = LLMClient(config=llm_config)
        orchestrator = Orchestrator(session_id=session_id, llm_client=llm)
        query_engine = QueryEngine(orchestrator=orchestrator)

        # Restore messages
        messages = [
            Message(role=m["role"], content=m["content"])
            for m in session_data.get("messages", [])
        ]

        # Restore DataFrame if present
        dataset_path = session_data.get("dataset_path")
        if dataset_path:
            try:
                await orchestrator.load_data(dataset_path)
            except Exception as e:
                print(f"Error restoring dataset {dataset_path} on session hydration: {e}")

        bundle = SessionBundle(
            session_id=session_id,
            orchestrator=orchestrator,
            query_engine=query_engine,
            messages=messages
        )

        self._sessions[session_id] = bundle
        return bundle

    def delete_session(self, session_id: str):
        """Remove from memory and disk."""
        if session_id in self._sessions:
            del self._sessions[session_id]
        SessionManager.delete_session(session_id)

    def reload_all_configs(self):
        """Reload LLM configurations for all active sessions."""
        for bundle in self._sessions.values():
            if hasattr(bundle.orchestrator, "llm_client"):
                bundle.orchestrator.llm_client.reload_config()
