"""Base class for all analysis agents with LLM support."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Callable
from dataclasses import dataclass, field

from shared.tools import validate_python_syntax, clean_generated_code


@dataclass
class AgentResult:
    """Result returned by agent execution."""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    error_category: Optional[str] = None  # e.g. "type_coercion", "missing_values", "column_not_found"
    error_details: Optional[Dict[str, Any]] = field(default_factory=dict)  # structured context for recovery
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base class for all specialized agents.

    Supports optional LLM integration for intelligent code generation
    and natural language understanding.
    """

    def __init__(
        self,
        agent_id: str,
        llm_client: Optional[Any] = None,
        use_llm: bool = True
    ):
        self.agent_id = agent_id
        self.llm = llm_client
        self.use_llm = use_llm and llm_client is not None
        self.skills = self._load_skills()
        self.capabilities: list[str] = []

    def _load_skills(self) -> str:
        """Load skill.md file for this agent."""
        skill_file = Path(__file__).parent / f"{self.agent_id}_skill.md"
        if skill_file.exists():
            return skill_file.read_text()
        return ""

    @abstractmethod
    async def execute(self, context: Any) -> AgentResult:
        """
        Execute the agent's task and return result.

        Args:
            context: Shared session context with data and state

        Returns:
            AgentResult with success status, data, and optional error
        """
        pass

    def can_handle(self, task_type: str) -> bool:
        """Check if this agent can handle a specific task type."""
        return task_type in self.capabilities

    def get_capabilities(self) -> list[str]:
        """Return list of capabilities this agent supports."""
        return self.capabilities.copy()

    def describe(self) -> dict:
        """Return agent description and capabilities."""
        return {
            "agent_id": self.agent_id,
            "capabilities": self.capabilities,
            "has_llm": self.use_llm,
        }

    async def generate_code(self, prompt: str, **kwargs) -> str:
        """
        Generate code using LLM with skill context.

        Args:
            prompt: Code generation request
            **kwargs: Additional generation options

        Returns:
            Generated code string
        """
        if not self.use_llm:
            raise RuntimeError("LLM not available for code generation")

        return self.llm.generate_code(
            prompt=prompt,
            skills=self.skills,
            **kwargs
        )

    async def generate_executed_code(
        self,
        prompt: str,
        execution_fn: Callable[[str], Any],
        max_retries: int = 3,
        temperature: float = 0.1,
        **kwargs
    ) -> Tuple[Any, str, Optional[str]]:
        """
        Generates code, executes it, and reflects on errors to self-correct.

        Args:
            prompt: The initial request for code
            execution_fn: A function that takes code (str) and returns the result (Any)
            max_retries: How many times to attempt correction
            temperature: Generation temperature
            **kwargs: Additional LLM parameters

        Returns:
            Tuple of (final_result, last_code, error_message)
        """
        if not self.use_llm:
            raise RuntimeError("LLM not available for code generation")

        current_prompt = prompt
        last_code = ""

        for attempt in range(max_retries):
            # 1. Generate code
            raw_code = self.llm.generate_code(
                prompt=current_prompt,
                skills=self.skills,
                temperature=temperature,
                **kwargs
            )
            clean_code = clean_generated_code(raw_code)
            last_code = clean_code

            # 2. Syntax Check
            is_valid, syntax_error = validate_python_syntax(clean_code)
            if not is_valid:
                last_error = f"Syntax Error: {syntax_error}"
                current_prompt = f"""
                Your previous code had a syntax error. Please fix it.

                ERROR: {last_error}

                CODE TO FIX:
                {clean_code}

                Return ONLY the corrected Python code.
                """
                continue

            # 3. Execution
            try:
                result = execution_fn(clean_code)
                return result, clean_code, None
            except Exception as e:
                last_error = f"Execution Error: {str(e)}"
                current_prompt = f"""
                The code you wrote is syntactically correct but failed during execution.

                ERROR: {last_error}

                CODE THAT FAILED:
                {clean_code}

                Please analyze the error and provide a corrected version of the code.
                Return ONLY the corrected Python code.
                """
                continue

        return None, last_code, last_error

    async def generate_validated_code(
        self,
        prompt: str,
        max_retries: int = 3,
        temperature: float = 0.1,
        **kwargs
    ) -> Tuple[str, Optional[str]]:
        """
        Generates code and reflects on syntax errors to self-correct.

        Returns:
            Tuple of (clean_code, error_message)
        """
        if not self.use_llm:
            raise RuntimeError("LLM not available for code generation")

        current_prompt = prompt
        last_code = ""
        last_error = None

        for attempt in range(max_retries):
            raw_code = self.llm.generate_code(
                prompt=current_prompt,
                skills=self.skills,
                temperature=temperature,
                **kwargs
            )
            clean_code = clean_generated_code(raw_code)
            last_code = clean_code

            is_valid, syntax_error = validate_python_syntax(clean_code)
            if not is_valid:
                last_error = f"Syntax Error: {syntax_error}"
                current_prompt = f"""
                Your previous code had a syntax error. Please fix it.

                ERROR: {last_error}

                CODE TO FIX:
                {clean_code}

                Return ONLY the corrected Python code.
                """
                continue
            
            return clean_code, None

        return last_code, last_error

    def get_rule_based_result(self, context: Any) -> AgentResult:
        """
        Fallback method when LLM is not available.

        Agents should implement their rule-based logic here.
        """
        return AgentResult(
            success=False,
            error=f"LLM required but not available for {self.agent_id} agent"
        )
