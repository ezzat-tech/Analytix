"""
Multi-Agent Data Analysis Orchestrator

Main entry point for the data analysis pipeline.
Coordinates specialized agents via a state machine.
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional

# Add the src directory to the path so internal imports work
src_dir = str(Path(__file__).parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from orchestrator.state_machine import StateMachine, State, Event, StateData
from agents import (
    IngestionAgent,
    ExplorationAgent,
    AnalysisAgent,
    VisualizationAgent,
    ReportingAgent,
    TransformationAgent,
)
from agents.base_agent import AgentResult
from shared.context import SessionContext
from shared.tools import generate_session_id
from config.settings import settings
from query import QueryEngine



class Orchestrator:
    """
    Main orchestrator that coordinates the multi-agent pipeline.

    Uses a state machine to manage transitions between:
    IDLE -> LOADING -> LOADED -> EXPLORING -> EXPLORED ->
    ANALYZING -> ANALYZED -> VISUALIZING -> VIZ_READY ->
    REPORTING -> COMPLETE
    """

    def __init__(self, session_id: Optional[str] = None, llm_client=None):
        self.session_id = session_id or generate_session_id()
        self.llm = llm_client

        # Initialize state machine
        self.state_machine = StateMachine(
            persistence_path=settings.state_dir
        )

        # Initialize shared context
        self.context = SessionContext(session_id=self.session_id)

        # Initialize agents with LLM support
        self.agents = {
            "ingestion": IngestionAgent(llm_client=self.llm),
            "exploration": ExplorationAgent(llm_client=self.llm),
            "analysis": AnalysisAgent(llm_client=self.llm),
            "visualization": VisualizationAgent(
                llm_client=self.llm,
                output_dir=str(settings.output_dir)
            ),
            "reporting": ReportingAgent(
                llm_client=self.llm,
                output_dir=str(settings.output_dir)
            ),
            "transformation": TransformationAgent(llm_client=self.llm),
        }

        # Setup state machine
        self._setup_states()
        self._setup_transitions()

    def _setup_states(self):
        """Register state handlers with the state machine."""
        self.state_machine.register_state(State.LOADING, self._on_loading)
        self.state_machine.register_state(State.EXPLORING, self._on_exploring)
        self.state_machine.register_state(State.ANALYZING, self._on_analyzing)
        self.state_machine.register_state(State.VISUALIZING, self._on_visualizing)
        self.state_machine.register_state(State.REPORTING, self._on_reporting)

    def _setup_transitions(self):
        """Define valid state transitions."""
        transitions = [
            (State.IDLE, "load", State.LOADING),
            (State.LOADING, "loaded", State.LOADED),
            (State.LOADED, "explore", State.EXPLORING),
            (State.EXPLORING, "explored", State.EXPLORED),
            (State.EXPLORED, "analyze", State.ANALYZING),
            (State.ANALYZING, "analyzed", State.ANALYZED),
            (State.ANALYZED, "visualize", State.VISUALIZING),
            (State.VISUALIZING, "viz_ready", State.VIZ_READY),
            (State.VIZ_READY, "report", State.REPORTING),
            (State.REPORTING, "complete", State.COMPLETE),
            (State.COMPLETE, "reset", State.IDLE),
        ]
        for from_state, event, to_state in transitions:
            self.state_machine.add_transition(from_state, event, to_state)

    async def _on_loading(self, data: StateData):
        """Handle LOADING state - execute ingestion agent."""
        result = await self.agents["ingestion"].execute(self.context)
        if result.success:
            data.schema = self.context.schema_info
            await self.state_machine.handle_event(Event(type="loaded"))
        else:
            data.error = result.error
            self.context.add_error(result.error)

    async def _on_exploring(self, data: StateData):
        """Handle EXPLORING state - execute exploration agent."""
        result = await self.agents["exploration"].execute(self.context)
        if result.success:
            data.profile = result.data
            await self.state_machine.handle_event(Event(type="explored"))
        else:
            data.error = result.error
            self.context.add_error(result.error)

    async def _on_analyzing(self, data: StateData):
        """Handle ANALYZING state - execute analysis agent."""
        result = await self.agents["analysis"].execute(self.context)
        if result.success:
            data.analysis_results = result.data
            await self.state_machine.handle_event(Event(type="analyzed"))
        else:
            data.error = result.error
            self.context.add_error(result.error)

    async def _on_visualizing(self, data: StateData):
        """Handle VISUALIZING state - execute visualization agent."""
        result = await self.agents["visualization"].execute(self.context)
        if result.success:
            data.visualizations = result.data.get("paths", [])
            await self.state_machine.handle_event(Event(type="viz_ready"))
        else:
            data.error = result.error
            self.context.add_error(result.error)

    async def _on_reporting(self, data: StateData):
        """Handle REPORTING state - execute reporting agent."""
        result = await self.agents["reporting"].execute(self.context)
        if result.success:
            data.report = result.data
            await self.state_machine.handle_event(Event(type="complete"))
        else:
            data.error = result.error
            self.context.add_error(result.error)

    async def run_pipeline(self, data_source: str) -> str:
        """
        Execute the full analysis pipeline on a data source.

        Args:
            data_source: Path to data file (CSV, Excel, JSON, etc.)

        Returns:
            Generated report string
        """
        self.context.data_source = data_source
        self.state_machine.state_data.session_id = self.session_id
        self.state_machine.state_data.data_source = data_source

        # Convert to absolute path if relative
        source_path = Path(data_source)
        if not source_path.is_absolute():
            source_path = settings.data_dir / data_source
            if not source_path.exists():
                source_path = Path(data_source)

        self.context.data_source = str(source_path)

        try:
            # Execute pipeline steps
            await self.state_machine.handle_event(
                Event(type="load", payload={"source": str(source_path)})
            )
            await self.state_machine.handle_event(Event(type="explore"))
            await self.state_machine.handle_event(Event(type="analyze"))
            await self.state_machine.handle_event(Event(type="visualize"))
            await self.state_machine.handle_event(Event(type="report"))

            return self.state_machine.state_data.report or "No report generated"

        except Exception as e:
            error_msg = f"Pipeline error: {str(e)}"
            self.context.add_error(error_msg)
            return error_msg

    async def load_data(self, data_source: str):
        """
        Load data through the state machine (IDLE -> LOADING -> LOADED).

        Use this for interactive/query mode where you need data loaded
        without running the full pipeline.

        Args:
            data_source: Path to data file
        """
        source_path = Path(data_source)
        if not source_path.is_absolute():
            source_path = settings.data_dir / data_source
            if not source_path.exists():
                source_path = Path(data_source)

        self.context.data_source = str(source_path)
        self.state_machine.state_data.session_id = self.session_id
        self.state_machine.state_data.data_source = str(source_path)

        await self.state_machine.handle_event(
            Event(type="load", payload={"source": str(source_path)})
        )

    async def route_to_agent(
        self,
        agent_name: str,
        params: dict = None,
        _retry_depth: int = 0,
    ) -> AgentResult:
        """
        Route a query to a specific agent via the state machine.

        Every query runs fresh through the LLM — no result caching.
        Session persistence (chat history + dataset path) is handled
        separately by SessionManager in app.py.

        If the agent fails with a recoverable error (e.g. type coercion,
        missing values), the orchestrator automatically delegates a repair
        job to TransformationAgent and retries the original agent once.

        Args:
            agent_name: Agent to route to (exploration, analysis, visualization, reporting, transformation)
            params: Optional parameters for the agent
            _retry_depth: Internal counter to prevent infinite delegation loops

        Returns:
            AgentResult from the agent execution
        """
        params = params or {}

        if agent_name not in self.agents:
            return AgentResult(
                success=False,
                error=f"Unknown agent: {agent_name}"
            )

        if self.context.loaded_data is None:
            return AgentResult(
                success=False,
                error="No data loaded. Call load_data() first."
            )

        # Execute agent via state machine one-shot query — always fresh
        agent = self.agents[agent_name]
        conv_ctx = params.get("conversation_context", "")

        async def _run_agent(state_data):
            if agent_name == "exploration":
                return await agent.execute(self.context, query=params.get("query", ""), conversation_context=conv_ctx)
            elif agent_name == "analysis":
                analysis_type = params.get("analysis_type", "full")
                return await agent.execute(self.context, query=params.get("query", ""), analysis_type=analysis_type, conversation_context=conv_ctx)
            elif agent_name == "visualization":
                chart_types = params.get("chart_types")
                return await agent.execute(self.context, query=params.get("query", ""), chart_types=chart_types, conversation_context=conv_ctx)
            elif agent_name == "reporting":
                # Ensure exploration and analysis have run before reporting
                if self.context.data_profile is None:
                    await self.agents["exploration"].execute(self.context, query="")
                if not self.context.analysis_results:
                    await self.agents["analysis"].execute(self.context, query="")
                return await agent.execute(self.context)
            elif agent_name == "transformation":
                return await agent.execute(self.context, query=params.get("query", ""), conversation_context=conv_ctx)
            else:
                return await agent.execute(self.context)

        result = await self.state_machine.query_agent(
            _run_agent, self.state_machine.state_data
        )

        # --- Hierarchical Delegation: Auto-repair on recoverable errors ---
        max_delegation_depth = 1
        if (
            not result.success
            and _retry_depth < max_delegation_depth
            and result.error_category
            and result.error_details
            and result.error_details.get("recoverable")
        ):
            import logging
            logger = logging.getLogger(__name__)

            repair_hint = result.error_details.get("repair_hint", "")
            logger.info(
                f"[Delegation] Agent '{agent_name}' failed with recoverable "
                f"error '{result.error_category}'. Delegating repair to "
                f"TransformationAgent: {repair_hint}"
            )

            # Delegate repair to TransformationAgent
            repair_result = await self.state_machine.query_agent(
                lambda sd: self.agents["transformation"].execute(
                    self.context, query=repair_hint
                ),
                self.state_machine.state_data,
            )

            if repair_result.success:
                logger.info(
                    f"[Delegation] Repair succeeded. Retrying '{agent_name}'..."
                )
                # Retry the original agent with incremented depth
                return await self.route_to_agent(
                    agent_name, params, _retry_depth=_retry_depth + 1
                )
            else:
                logger.warning(
                    f"[Delegation] Repair failed: {repair_result.error}. "
                    f"Returning original error to user."
                )

        return result

    def get_current_state(self) -> State:
        """Get current state machine state."""
        return self.state_machine.get_current_state()

    def get_context_summary(self) -> dict:
        """Get summary of current session context."""
        return self.context.to_dict()

    async def reset(self):
        """Reset orchestrator for new pipeline."""
        self.context.clear_data()
        self.context.errors = []
        self.context.query_history = []
        self.state_machine.reset()



