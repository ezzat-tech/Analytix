"""Transformation agent for dataset mutation and cleaning operations."""

import duckdb
import pandas as pd
from typing import Any, Dict
from agents.base_agent import BaseAgent, AgentResult


class TransformationAgent(BaseAgent):
    """
    Agent responsible for modifying, cleaning, and transforming data.
    Generates and executes Pandas or DuckDB SQL code against the loaded DataFrame.
    """

    def __init__(self, llm_client=None):
        super().__init__(
            agent_id="transformation",
            llm_client=llm_client,
            use_llm=True
        )
        self.capabilities = ["clean", "mutate", "sql", "transform"]

    async def execute(self, context: Any, query: str = "", conversation_context: str = "") -> AgentResult:
        """
        Execute a transformation prompt.
        
        Args:
            context: SessionContext containing the loaded dataframe.
            query: The user's natural language request (e.g., "drop missing values").
            conversation_context: Recent chat history for follow-up understanding.
        """
        if context.loaded_data is None:
            return AgentResult(success=False, error="No data loaded for transformation.")
            
        if not query:
            return AgentResult(success=False, error="No transformation query provided.")

        df = context.loaded_data

        history_block = ""
        if conversation_context:
            history_block = f"\nConversation so far:\n{conversation_context}\n"

        # 1. Ask LLM to generate the mutation code
        prompt = f"""
        {history_block}
        User Request: "{query}"
        
        Dataset Info:
        Rows: {len(df)}
        Columns: {list(df.columns)}
        
        Generate the exact Python or DuckDB SQL code to perform this transformation on the variable `df`.
        Return ONLY code.
        """
        
        try:
            # Generate code with syntax validation and retry
            clean_code, validation_error = await self.generate_validated_code(
                prompt, temperature=0.1
            )

            # If validation failed after retries, return error
            if validation_error:
                return AgentResult(
                    success=False,
                    error=f"Code generation failed after retries: {validation_error}",
                    metadata={"generated_code": clean_code}
                )

            # 2. Execute the code in a restricted local environment
            local_env = {
                "pd": pd,
                "duckdb": duckdb,
                "df": df.copy() # Operate on a copy initially
            }

            exec(clean_code, {}, local_env)

            # Retrieve the mutated dataframe
            mutated_df = local_env.get("df")

            if mutated_df is None or not isinstance(mutated_df, pd.DataFrame):
                return AgentResult(
                    success=False,
                    error="Agent ran successfully but did not produce a valid `df` DataFrame."
                )

            # 3. Update the global context with the new dataframe
            context.loaded_data = mutated_df

            # Since data mutated, clear cached statistics!
            context.data_profile = None
            context.schema_info = None
            context.analysis_cache.clear()

            return AgentResult(
                success=True,
                data=clean_code,  # Return the code so UI can display it
                metadata={"code_executed": clean_code}
            )

        except Exception as e:
            error_msg = f"Failed to execute transformation: {str(e)}"
            return AgentResult(success=False, error=error_msg)
