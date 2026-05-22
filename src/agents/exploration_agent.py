"""Exploration Agent - data profiling and data understanding through dynamic code."""

import io
import sys
import pandas as pd
import duckdb
from typing import Any, Optional

from .base_agent import BaseAgent, AgentResult
from .error_classifier import classify_error

class ExplorationAgent(BaseAgent):
    """
    Agent responsible for profiling data and assessing quality natively using dynamic Python scripts.
    """

    def __init__(self, llm_client: Optional[Any] = None, use_llm: bool = True):
        super().__init__("exploration", llm_client, use_llm)
        self.capabilities = ["profile", "quality_check", "schema_analysis", "explore"]

    async def execute(self, context: Any, query: str = "", conversation_context: str = "") -> AgentResult:
        if context.loaded_data is None:
             return AgentResult(success=False, error="No data loaded - run IngestionAgent first")

        df = context.loaded_data
        query = query or "Provide a comprehensive data profile."

        history_block = ""
        if conversation_context:
            history_block = f"\nConversation so far:\n{conversation_context}\n"

        prompt = f"""
        {history_block}
        User Request: "{query}"

        Dataset Info:
        Rows: {len(df)}
        Columns: {list(df.columns)}

        Generate the exact Python script to explore this dataset and satisfy the user's request.
        The dataframe is loaded in the variable `df`.
        Use print() statements to meticulously output your findings, data previews (.head()), schemas, and exact statistics so the user can read them from stdout.
        DO NOT modify the dataframe directly.
        Return ONLY code without markdown blocks or explanations.
        """

        try:
            def execute_code(code):
                old_stdout = sys.stdout
                sys.stdout = my_stdout = io.StringIO()
                try:
                    exec(code, {}, {
                        "pd": pd,
                        "duckdb": duckdb,
                        "df": df
                    })
                finally:
                    sys.stdout = old_stdout
                return my_stdout.getvalue()

            stdout_output, clean_code, error = await self.generate_executed_code(
                prompt,
                execution_fn=execute_code,
                temperature=0.1
            )

            if error:
                classification = classify_error(error, clean_code)
                return AgentResult(
                    success=False,
                    error=f"Exploration script failed after retries: {error}",
                    error_category=classification["category"],
                    error_details=classification,
                    metadata={"generated_code": clean_code}
                )

            context.data_profile = {"stdout": stdout_output}

            return AgentResult(
                success=True,
                data=stdout_output,
                metadata={"code_executed": clean_code, "stdout": stdout_output}
            )

        except Exception as e:
            return AgentResult(success=False, error=f"Exploration script error: {str(e)}")
