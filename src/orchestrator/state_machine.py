"""Core state machine engine for orchestrating agent workflows."""

from enum import Enum
from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass, field
import asyncio
import json
from pathlib import Path

from .states import State
from .events import Event


@dataclass
class StateData:
    """Data passed between states during transitions."""

    session_id: str
    current_state: State = State.IDLE
    data_source: Optional[str] = None
    schema: Optional[dict] = None
    profile: Optional[dict] = None
    analysis_results: Optional[dict] = None
    visualizations: Optional[list] = None
    report: Optional[str] = None
    error: Optional[str] = None


class StateMachineError(Exception):
    """Base exception for state machine errors."""
    pass


class InvalidTransitionError(StateMachineError):
    """Raised when an invalid state transition is requested."""
    pass


class StateMachine:
    """
    Async-first state machine with persistence support.

    Manages state transitions, guards, and handlers for the multi-agent
    orchestration system.
    """

    def __init__(self, persistence_path: Path = Path("./state")):
        self.states: Dict[State, dict] = {}
        self.transitions: Dict[State, Dict[str, State]] = {}
        self.handlers: Dict[State, Callable] = {}
        self.guards: Dict[State, Callable] = {}
        self.current_state = State.IDLE
        self.state_data = StateData(session_id="")
        self.persistence_path = persistence_path
        self.event_queue: asyncio.Queue = asyncio.Queue()

    def register_state(
        self,
        state: State,
        handler: Callable,
        guard: Optional[Callable] = None
    ):
        """Register a state with its entry handler and optional guard condition."""
        self.handlers[state] = handler
        if guard:
            self.guards[state] = guard

    def add_transition(self, from_state: State, event_type: str, to_state: State):
        """Define a valid state transition triggered by an event."""
        if from_state not in self.transitions:
            self.transitions[from_state] = {}
        self.transitions[from_state][event_type] = to_state

    def can_transition(self, event: Event) -> bool:
        """
        Check if a transition is valid and guard conditions pass.

        Returns True if:
        - Current state has transitions defined
        - Event type triggers a valid transition
        - Guard condition (if any) passes
        """
        if self.current_state not in self.transitions:
            return False
        if event.type not in self.transitions[self.current_state]:
            return False
        target_state = self.transitions[self.current_state][event.type]
        if target_state in self.guards:
            return self.guards[target_state](self.state_data)
        return True

    async def transition_to(self, state: State):
        """Execute state transition with persistence."""
        self.current_state = state
        if state in self.handlers:
            await self.handlers[state](self.state_data)
        await self.persist_state()

    async def handle_event(self, event: Event):
        """Process an event and trigger state transition."""
        if self.can_transition(event):
            next_state = self.transitions[self.current_state][event.type]
            await self.transition_to(next_state)
        else:
            raise InvalidTransitionError(
                f"Cannot transition from {self.current_state} with event '{event.type}'"
            )

    async def persist_state(self):
        """Save current state to disk for crash recovery."""
        self.persistence_path.mkdir(parents=True, exist_ok=True)
        state_file = self.persistence_path / f"{self.state_data.session_id}.json"

        state_dict = {
            "current_state": self.current_state.name,
            "state_data": {
                "session_id": self.state_data.session_id,
                "data_source": self.state_data.data_source,
                "schema": self.state_data.schema,
                "profile": self.state_data.profile,
                "analysis_results": self.state_data.analysis_results,
                "visualizations": self.state_data.visualizations,
                "report": self.state_data.report,
                "error": self.state_data.error,
            }
        }

        with open(state_file, "w") as f:
            json.dump(state_dict, f, indent=2)

    async def restore_state(self, session_id: str):
        """Restore state from disk for session recovery."""
        state_file = self.persistence_path / f"{session_id}.json"
        if state_file.exists():
            with open(state_file, "r") as f:
                data = json.load(f)
                self.state_data = StateData(
                    session_id=data["state_data"]["session_id"],
                    current_state=State[data["current_state"]],
                    data_source=data["state_data"].get("data_source"),
                    schema=data["state_data"].get("schema"),
                    profile=data["state_data"].get("profile"),
                    analysis_results=data["state_data"].get("analysis_results"),
                    visualizations=data["state_data"].get("visualizations"),
                    report=data["state_data"].get("report"),
                    error=data["state_data"].get("error"),
                )
                self.current_state = State[data["current_state"]]
        else:
            raise StateMachineError(f"No saved state found for session '{session_id}'")

    def get_current_state(self) -> State:
        """Return the current state."""
        return self.current_state

    async def query_agent(self, agent_handler: Callable, data: "StateData") -> Any:
        """
        Execute a single agent handler as a one-shot query operation.

        Temporarily enters QUERYING state, runs the handler, then restores
        the previous state. This allows ad-hoc queries without advancing
        the pipeline.

        Args:
            agent_handler: Async callable that takes StateData and returns a result
            data: StateData to pass to the handler

        Returns:
            Result from the agent handler
        """
        previous_state = self.current_state
        self.current_state = State.QUERYING
        try:
            result = await agent_handler(data)
            return result
        finally:
            self.current_state = previous_state

    def reset(self):
        """Reset the state machine to IDLE."""
        self.current_state = State.IDLE
        self.state_data = StateData(session_id=self.state_data.session_id)
