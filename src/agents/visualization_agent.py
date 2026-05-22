"""Visualization Agent - chart generation and plotting through AutoCoding."""

import io
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Any, Optional, List

from .base_agent import BaseAgent, AgentResult
from .error_classifier import classify_error

class VisualizationAgent(BaseAgent):
    """
    Agent responsible for generating visualizations natively via dynamic plotting scripts.
    """

    def __init__(self, llm_client: Optional[Any] = None, use_llm: bool = True, output_dir: str = "./outputs"):
        super().__init__("visualization", llm_client, use_llm)
        self.capabilities = ["histogram", "scatter", "boxplot", "heatmap", "line", "bar", "visualization", "chart"]
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self, context: Any, query: str = "", chart_types: Optional[List[str]] = None, conversation_context: str = "") -> AgentResult:
        if context.loaded_data is None:
             return AgentResult(success=False, error="No data loaded - run IngestionAgent first")

        df = context.loaded_data
        query = query or "Create appropriate and insightful visualizations for this dataset."

        history_block = ""
        if conversation_context:
            history_block = f"\nConversation so far:\n{conversation_context}\n"

        prompt = f"""
        {history_block}
        User Request: "{query}"

        Dataset Info:
        Rows: {len(df)}
        Columns: {list(df.columns)}

        Generate the exact Python script using `matplotlib.pyplot` (as plt) and `seaborn` (as sns) to dynamically plot beautiful charts perfectly addressing the user's specific request.
        The dataframe is loaded in the variable `df`.
        You MUST save each explicitly generated figure cleanly (e.g., `plt.savefig(filepath)`).
        To do this correctly, build your file paths dynamically strictly using the `save_dir` string provided in your namespace.
        Example: filepath = save_dir + "/my_custom_chart.png"
        Crucially, append every single saved filepath string to the `generated_paths` list variable inside your namespace so they can be retrieved by the UI.
        DO NOT use plt.show(), just save them and close them with plt.close().
        Use print() statements to heavily document your analytical summaries or chart logic descriptions if necessary.
        Return ONLY code without markdown blocks or explanations.
        """

        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            sns.set_theme(style="whitegrid")

            def execute_code(code):
                generated_paths = []
                local_env = {
                    "pd": pd,
                    "np": np,
                    "df": df,
                    "plt": plt,
                    "sns": sns,
                    "save_dir": str(self.output_dir),
                    "generated_paths": generated_paths
                }
                old_stdout = sys.stdout
                sys.stdout = my_stdout = io.StringIO()
                try:
                    exec(code, {}, local_env)
                finally:
                    sys.stdout = old_stdout

                return {
                    "stdout": my_stdout.getvalue(),
                    "paths": local_env.get("generated_paths", [])
                }

            # Use the new reflection loop
            result_data, clean_code, error = await self.generate_executed_code(
                prompt,
                execution_fn=execute_code,
                temperature=0.1
            )

            if error:
                classification = classify_error(error, clean_code)
                return AgentResult(
                    success=False,
                    error=f"Visualization script failed after retries: {error}",
                    error_category=classification["category"],
                    error_details=classification,
                    metadata={"generated_code": clean_code}
                )

            stdout_output = result_data.get("stdout", "")
            paths_returned = result_data.get("paths", [])
            context.visualizations.extend(paths_returned)

            return AgentResult(
                success=True,
                data={"paths": paths_returned, "stdout": stdout_output},
                metadata={"code_executed": clean_code, "stdout": stdout_output}
            )

        except Exception as e:
            return AgentResult(success=False, error=f"Visualization script error: {str(e)}")
