"""State persistence layer for crash recovery and session management."""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import asdict
from datetime import datetime

from .states import State
from .state_machine import StateData


class PersistenceError(Exception):
    """Raised when state persistence operations fail."""
    pass


class StatePersister:
    """
    Handles persistence operations for state machine data.

    Provides methods for saving, loading, and managing session state files.
    """

    def __init__(self, persistence_path: Path):
        self.persistence_path = persistence_path

    def _ensure_dir(self):
        """Ensure persistence directory exists."""
        self.persistence_path.mkdir(parents=True, exist_ok=True)

    def save(self, session_id: str, state_data: StateData, current_state: State) -> Path:
        """
        Save state data to disk.

        Args:
            session_id: Unique session identifier
            state_data: Current state data
            current_state: Current state enum value

        Returns:
            Path to the saved state file
        """
        try:
            self._ensure_dir()
            state_file = self.persistence_path / f"{session_id}.json"

            state_dict = {
                "session_id": session_id,
                "current_state": current_state.name,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "data_source": state_data.data_source,
                    "schema": state_data.schema,
                    "profile": state_data.profile,
                    "analysis_results": state_data.analysis_results,
                    "visualizations": state_data.visualizations,
                    "report": state_data.report,
                    "error": state_data.error,
                }
            }

            with open(state_file, "w") as f:
                json.dump(state_dict, f, indent=2)

            return state_file

        except Exception as e:
            raise PersistenceError(f"Failed to save state: {str(e)}")

    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load state data from disk.

        Args:
            session_id: Unique session identifier

        Returns:
            Dictionary with state data or None if not found
        """
        state_file = self.persistence_path / f"{session_id}.json"

        if not state_file.exists():
            return None

        try:
            with open(state_file, "r") as f:
                return json.load(f)
        except Exception as e:
            raise PersistenceError(f"Failed to load state: {str(e)}")

    def delete(self, session_id: str) -> bool:
        """
        Delete a saved state.

        Args:
            session_id: Unique session identifier

        Returns:
            True if deleted, False if state didn't exist
        """
        state_file = self.persistence_path / f"{session_id}.json"

        if state_file.exists():
            state_file.unlink()
            return True
        return False

    def list_sessions(self) -> list:
        """
        List all saved session IDs.

        Returns:
            List of session ID strings
        """
        if not self.persistence_path.exists():
            return []

        sessions = []
        for f in self.persistence_path.glob("*.json"):
            sessions.append(f.stem)

        return sessions

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get summary info about a session without full state.

        Args:
            session_id: Unique session identifier

        Returns:
            Dictionary with session metadata or None
        """
        state_file = self.persistence_path / f"{session_id}.json"

        if not state_file.exists():
            return None

        try:
            with open(state_file, "r") as f:
                data = json.load(f)
                return {
                    "session_id": data.get("session_id"),
                    "current_state": data.get("current_state"),
                    "timestamp": data.get("timestamp"),
                    "data_source": data.get("data", {}).get("data_source"),
                }
        except Exception:
            return None
