"""Analysis Agent - statistical analysis and aggregations through AutoCoding."""

import io
import sys
import pandas as pd
import numpy as np
import duckdb
from typing import Any, Optional

from .base_agent import BaseAgent, AgentResult
from .error_classifier import classify_error

class AnalysisAgent(BaseAgent):
    """
    Agent responsible for advanced statistical analysis and groupings natively via dynamic Python scripts.
    """

    def __init__(self, llm_client: Optional[Any] = None, use_llm: bool = True):
        super().__init__("analysis", llm_client, use_llm)
        self.capabilities = ["descriptive_stats", "correlation", "aggregation", "groupby", "outlier_detection", "analysis"]

    async def execute(self, context: Any, query: str = "", analysis_type: str = "full", conversation_context: str = "") -> AgentResult:
        if context.loaded_data is None:
             return AgentResult(success=False, error="No data loaded - run IngestionAgent first")

        df = context.loaded_data
        query = query or f"Perform a comprehensive {analysis_type} statistical analysis on the current data."

        history_block = ""
        if conversation_context:
            history_block = f"\nConversation so far:\n{conversation_context}\n"

        prompt = f"""
        {history_block}
        User Request: "{query}"

        Dataset Info:
        Rows: {len(df)}
        Columns: {list(df.columns)}

        Generate the exact Python script to structurally analyze this dataset using advanced Statistics or Pandas aggregations according to the user's request.
        The dataframe is loaded in the variable `df`. You may import `numpy` or `scipy` if needed.
        Use print() statements to meticulously format and output your statistical insights, numeric boundaries, arrays, and group-by aggregations.
        DO NOT modify the dataframe directly.
        Return ONLY code without markdown blocks or explanations.
        """

        try:
            # Execution function to be used by the reflection loop
            def execute_code(code):
                old_stdout = sys.stdout
                sys.stdout = my_stdout = io.StringIO()
                try:
                    exec(code, {}, {
                        "pd": pd,
                        "np": np,
                        "duckdb": duckdb,
                        "df": df
                    })
                finally:
                    sys.stdout = old_stdout
                return my_stdout.getvalue()

            # Use the new reflection loop: Generate -> Execute -> Reflect -> Correct
            stdout_output, clean_code, error = await self.generate_executed_code(
                prompt,
                execution_fn=execute_code,
                temperature=0.1
            )

            if error:
                classification = classify_error(error, clean_code)
                return AgentResult(
                    success=False,
                    error=f"Analysis script failed after retries: {error}",
                    error_category=classification["category"],
                    error_details=classification,
                    metadata={"generated_code": clean_code}
                )

            context.analysis_results = {"stdout": stdout_output}

            return AgentResult(
                success=True,
                data=stdout_output,
                metadata={"code_executed": clean_code, "stdout": stdout_output}
            )

        except Exception as e:
            return AgentResult(success=False, error=f"Analysis script error: {str(e)}")
