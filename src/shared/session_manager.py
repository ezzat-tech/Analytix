import json
import os
import glob
from datetime import datetime
from config.settings import settings

class SessionManager:
    """Manages local chat history and session persistence."""
    
    @staticmethod
    def get_sessions_dir() -> str:
        sessions_dir = settings.state_dir / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        return str(sessions_dir)
        
    @classmethod
    def save_session(cls, session_id: str, messages: list, dataset_path: str, dataset_name: str):
        sessions_dir = cls.get_sessions_dir()
        filepath = os.path.join(sessions_dir, f"{session_id}.json")
        
        title = "New Analysis"
        if dataset_name:
            title = f"Analysis: {dataset_name}"
            
        # Keep only the last 200 messages to prevent unbounded JSON growth
        MAX_STORED_MESSAGES = 200
        trimmed_messages = messages[-MAX_STORED_MESSAGES:]
            
        # Attempt to title the session based on the user's first real query
        if len(trimmed_messages) > 0:
            first_user = next((m["content"] for m in trimmed_messages if m["role"] == "user"), None)
            if first_user:
                title = first_user[:35] + ("..." if len(first_user) > 35 else "")
                
        payload = {
            "session_id": session_id,
            "title": title,
            "dataset_path": dataset_path,
            "dataset_name": dataset_name,
            "updated_at": datetime.now().isoformat(),
            "messages": trimmed_messages
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
            
    @classmethod
    def load_session(cls, session_id: str) -> dict:
        """Fetch a specific session. Returns empty dict if not found."""
        sessions_dir = cls.get_sessions_dir()
        filepath = os.path.join(sessions_dir, f"{session_id}.json")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
        
    @classmethod
    def list_sessions(cls) -> list:
        """Returns sorted list of all local sessions."""
        sessions_dir = cls.get_sessions_dir()
        files = glob.glob(os.path.join(sessions_dir, "*.json"))
        sessions = []
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    sessions.append({
                        "session_id": data.get("session_id", ""),
                        "title": data.get("title", "Unnamed Session"),
                        "updated_at": data.get("updated_at", "")
                    })
            except Exception:
                continue
        # Sort by updated_at descending (newest first)
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return sessions
        
    @classmethod
    def delete_session(cls, session_id: str) -> bool:
        sessions_dir = cls.get_sessions_dir()
        filepath = os.path.join(sessions_dir, f"{session_id}.json")
        if os.path.exists(filepath):
            # Clean up associated mutated data files (never delete original uploads)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                dataset_path = data.get("dataset_path", "")
                if dataset_path and "mutated_" in os.path.basename(dataset_path):
                    if os.path.exists(dataset_path):
                        os.remove(dataset_path)
            except Exception:
                pass
            os.remove(filepath)
            return True
        return False
