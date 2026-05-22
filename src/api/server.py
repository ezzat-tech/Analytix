import os
import shutil
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.api.schemas import SessionCreate, SessionResponse, QueryRequest, QueryResponse, Message
from src.api.session_registry import SessionRegistry
from src.api.serializers import serialize_dataframe, serialize_visualizations
from src.config.settings import settings
from src.shared.session_manager import SessionManager
from src.llm import LLMConfig, AVAILABLE_MODELS, BACKEND_NAMES
from typing import Optional

app = FastAPI(title="Data Analyst Agent API")

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static mount for generated visualizations (PNGs)
app.mount("/static", StaticFiles(directory=str(settings.output_dir)), name="static")

# Global registry for active sessions
registry = SessionRegistry()

# Initialize logging
settings.setup_logging()

@app.post("/sessions", response_model=SessionResponse)
async def create_session():
    """Create a new analysis session."""
    bundle = registry.get_or_create()
    
    # Save the session to disk immediately so it shows up in history on load/refresh!
    SessionManager.save_session(
        bundle.session_id,
        messages=[],
        dataset_path="",
        dataset_name=""
    )
    
    return SessionResponse(
        session_id=bundle.session_id,
        created_at=datetime.now()
    )

@app.get("/sessions")
async def list_sessions():
    """List all persisted sessions on disk."""
    sessions = SessionManager.list_sessions()
    return sessions

@app.get("/sessions/{session_id}", response_model=SessionResponse)
async def load_session(session_id: str):
    """Load and hydrate a session from disk into memory."""
    bundle = await registry.hydrate_session(session_id)
    
    # Retrieve dataset details if loaded
    dataset_name = None
    dataset_shape = None
    dataset_columns = None
    
    if bundle.orchestrator.context.loaded_data is not None:
        df = bundle.orchestrator.context.loaded_data
        dataset_path = bundle.orchestrator.context.data_source or ""
        dataset_name = os.path.basename(dataset_path) if dataset_path else "dataset.csv"
        dataset_shape = list(df.shape)
        dataset_columns = list(df.columns)
        
    return SessionResponse(
        session_id=bundle.session_id,
        created_at=datetime.now(),
        dataset_name=dataset_name,
        dataset_shape=dataset_shape,
        dataset_columns=dataset_columns
    )

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Remove a session from memory and disk."""
    registry.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}

@app.post("/sessions/{session_id}/upload")
async def upload_data(session_id: str, file: UploadFile = File(...)):
    """Upload a dataset and load it into the active session."""
    bundle = registry.get_session(session_id)

    # Save uploaded file to settings.data_dir
    file_path = settings.data_dir / file.filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Load data into the agent orchestrator
    await bundle.orchestrator.load_data(str(file_path))

    # Persist the session to disk immediately with the loaded dataset info!
    history_dicts = [m.model_dump(mode='json') for m in bundle.messages]
    SessionManager.save_session(
        bundle.session_id,
        history_dicts,
        str(file_path),
        file.filename
    )

    # Return a preview of the loaded data
    df = bundle.orchestrator.context.loaded_data
    return {
        "filename": file.filename,
        "shape": df.shape,
        "columns": list(df.columns),
        "preview": serialize_dataframe(df)
    }

@app.post("/sessions/{session_id}/query", response_model=QueryResponse)
async def query_session(session_id: str, request: QueryRequest):
    """Process a natural language query for the active session."""
    bundle = registry.get_session(session_id)

    # 1. Execute query via QueryEngine
    # Pass a list of dicts as conversation history
    history_dicts = [m.model_dump(mode='json') for m in bundle.messages]
    result = await bundle.query_engine.query(
        request.text,
        conversation_history=history_dicts
    )

    # 2. Update session history
    user_msg = Message(role="user", content=request.text)
    assistant_msg = Message(role="assistant", content=result.answer)
    bundle.messages.extend([user_msg, assistant_msg])

    # 3. Persist session state to disk
    history_dicts = [m.model_dump(mode='json') for m in bundle.messages]
    dataset_path = bundle.orchestrator.context.data_source or ""
    dataset_name = os.path.basename(dataset_path) if dataset_path else ""

    SessionManager.save_session(
        bundle.session_id,
        history_dicts,
        dataset_path,
        dataset_name
    )

    # 4. Serialize response
    df = bundle.orchestrator.context.loaded_data
    viz_paths = bundle.orchestrator.context.visualizations

    return QueryResponse(
        answer=result.answer,
        table_data=serialize_dataframe(df) if result.success and "table" in result.answer.lower() else None,
        visualization_urls=serialize_visualizations(viz_paths),
        messages=bundle.messages
    )

@app.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    """Retrieve the chat history for a session."""
    bundle = registry.get_session(session_id)
    return bundle.messages

class LLMConfigRequest(BaseModel):
    backend: str
    model: str
    host: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None

@app.get("/llm/config")
async def get_llm_config():
    """Retrieve the current LLM configuration and choices."""
    config = LLMConfig()
    current = config.get_current_config()
    return {
        "current": current,
        "available_models": AVAILABLE_MODELS,
        "backends": BACKEND_NAMES
    }

@app.post("/llm/config")
async def update_llm_config(req: LLMConfigRequest):
    """Update active LLM backend, model and credentials."""
    config = LLMConfig()
    config.update_backend(req.backend)
    config.update_model(req.backend, req.model)
    if req.host and req.backend in ("ollama", "ollama_paid"):
        config.update_host(req.host)
    if req.api_key:
        config.save_credential(req.backend, req.api_key)
    if req.base_url and req.backend == "openai":
        # Save custom base url directly in config
        cfg = config.load_config()
        if "openai" not in cfg:
            cfg["openai"] = {}
        cfg["openai"]["base_url"] = req.base_url
        config.save_config(cfg)
        
    # Reload configuration across all active sessions in memory
    registry.reload_all_configs()
    return {"status": "success", "config": config.get_current_config()}
