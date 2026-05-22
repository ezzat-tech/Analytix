"""
Query Engine - Natural Language Interface for Multi-Agent Data Analysis

Routes user queries to appropriate specialized agents via the Orchestrator:
- ExplorationAgent: summaries, profiling, data quality
- AnalysisAgent: statistics, correlations, aggregations, outliers
- VisualizationAgent: charts and plots
- ReportingAgent: insights, recommendations

The LLM determines intent and the Orchestrator handles agent execution
through the state machine.
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional

import pandas as pd


class QueryResult:
    """Result of a query execution."""

    def __init__(
        self,
        success: bool,
        answer: str,
        data: Optional[Any] = None,
        visualization_path: Optional[str] = None,
        error: Optional[str] = None,
        agent_used: Optional[str] = None,
    ):
        self.success = success
        self.answer = answer
        self.data = data
        self.visualization_path = visualization_path
        self.error = error
        self.agent_used = agent_used

    def __str__(self) -> str:
        return self.answer


class QueryEngine:
    """
    Natural language query engine for multi-agent system.

    Classifies query intent and routes to the appropriate agent
    through the Orchestrator's state machine.
    """

    INTENT_SAMPLES = {
        "conversational": [
            "hello there, how are you today?",
            "who are you and what can you do?",
            "thank you for your help, I appreciate it!",
            "can you explain how this application works?"
        ],
        "exploration": [
            "summarize the dataset columns and general structure",
            "show me the schema, data types, and total row count",
            "are there any missing values or null counts in the data?",
            "give me a basic profile check of this spreadsheet"
        ],
        "analysis": [
            "calculate the average and standard deviation of values",
            "find the correlation matrix between the numeric columns",
            "group the records by category and calculate outlier statistics",
            "what is the statistical summary of the numeric variables?"
        ],
        "visualization": [
            "plot a histogram chart of the distribution",
            "generate a scatter plot of variable X versus Y",
            "show me a boxplot of categories by experience level",
            "draw a correlation heatmap graph of the numeric columns"
        ],
        "reporting": [
            "what are the key insights and findings in this data?",
            "provide recommendations based on the analysis conclusions",
            "what main trends or takeaways should I focus on?",
            "generate a summary report of your main data findings"
        ],
        "transformation": [
            "drop the rows where the values are null or empty",
            "fill the missing values with zero or standard mean",
            "create a new column representing the total sales profit",
            "filter the data where region is equals to North"
        ]
    }

    def __init__(self, orchestrator):
        """
        Initialize the query engine.

        Args:
            orchestrator: Orchestrator instance that manages agents and state machine
        """
        self.orchestrator = orchestrator
        self.llm = orchestrator.llm
        self.use_llm = orchestrator.llm is not None

    async def query(self, query_text: str, context: Any = None, conversation_history: list = None) -> QueryResult:
        """
        Execute a natural language query by routing to appropriate agent.

        Args:
            query_text: User's question in natural language
            context: Session context with loaded data (defaults to orchestrator's context)
            conversation_history: List of recent message dicts [{"role": ..., "content": ...}]

        Returns:
            QueryResult with answer and optional data/viz
        """
        ctx = context or self.orchestrator.context

        if ctx is None or ctx.loaded_data is None:
            return QueryResult(
                success=False,
                answer="No data loaded. Please load a dataset first.",
                error="No data available"
            )

        df = ctx.loaded_data

        # Build conversation context string from recent history
        conv_ctx = self._format_conversation_history(conversation_history)

        # Determine which agent should handle this query
        # Tier 1: Fast Rule-based match (100% deterministic, ultra-fast, handles common conversational words)
        fast_match = self._simple_classify(query_text)
        if fast_match == "conversational":
            agent_name = "conversational"
            params = {}
        else:
            # Tier 2: Semantic routing (ultra-fast semantic similarity)
            semantic_agent = self._semantic_classify(query_text)
            if semantic_agent:
                agent_name = semantic_agent
                params = {}
            # Tier 3: LLM Intent Classification (deep reasoning & parameter extraction)
            elif self.use_llm:
                routing = await self._classify_intent(query_text, df)
                agent_name = routing.get("agent") if routing else None
                params = routing.get("params", {}) if routing else {}
            # Tier 4: Keyword fallback
            else:
                agent_name = fast_match
                params = {}

        # Attach conversation context so agents can understand follow-ups
        params["conversation_context"] = conv_ctx

        # Route to appropriate agent through orchestrator
        if agent_name == "conversational":
            return await self._handle_conversational(query_text, ctx, params)
        elif agent_name == "exploration":
            return await self._handle_exploration(query_text, ctx, params)
        elif agent_name == "analysis":
            return await self._handle_analysis(query_text, ctx, params)
        elif agent_name == "visualization":
            return await self._handle_visualization(query_text, ctx, params)
        elif agent_name == "reporting":
            return await self._handle_reporting(query_text, ctx, params)
        elif agent_name == "transformation":
            return await self._handle_transformation(query_text, ctx, params)
        else:
            # Default to conversational for general queries
            return await self._handle_conversational(query_text, ctx, params)

    @staticmethod
    def _format_conversation_history(messages: list, max_messages: int = 10, max_chars: int = 500) -> str:
        """
        Format recent chat messages into a concise context string for the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_messages: Maximum number of recent messages to include
            max_chars: Maximum characters per message (truncated with ...)

        Returns:
            Formatted string of recent conversation, or empty string
        """
        if not messages:
            return ""

        recent = messages[-max_messages:]
        lines = []
        for msg in recent:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "").strip()
            if len(content) > max_chars:
                content = content[:max_chars] + "..."
            lines.append(f"{role}: {content}")

        return "\n".join(lines)

    async def _classify_intent(self, query: str, df: pd.DataFrame) -> Dict:
        """
        Use LLM to classify query intent and extract parameters.

        Returns: {"agent": "exploration|analysis|visualization|reporting", "params": {...}}
        """
        # Build data summary for context
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()

        data_summary = {
            "columns": list(df.columns),
            "numeric": numeric_cols[:10],
            "categorical": categorical_cols[:10],
            "datetime": datetime_cols,
        }

        agent_descriptions = """
- "conversational": For general greetings, chit-chat, explaining general concepts, answering general questions about the application or how the pipeline works, explaining the meaning of columns, or answering follow-up questions without requiring code execution or calculations. Examples: "hello", "what can you do?", "what does column X mean?", "how does this system work?", "thank you"

- "exploration": For questions about data structure, schema, profiling, quality, missing values, column types, row counts. Examples: "summarize the data", "what columns are there?", "any missing values?", "show me the schema"

- "analysis": For statistical analysis - correlations, aggregations, group-by, outliers, descriptive stats. Examples: "correlation between X and Y", "average sales by region", "find outliers", "statistics for price"

- "visualization": For creating charts and plots. Examples: "plot a histogram", "scatter plot of X vs Y", "show me a chart of sales", "boxplot for price"

- "reporting": For insights, recommendations, summaries of findings. Examples: "what insights can you find?", "recommendations?", "key findings", "what should I focus on?"

- "transformation": For cleaning, mutating, grouping, or modifying the dataset directly. Examples: "drop the missing values", "fill na with 0", "create a new column for total_sales", "filter where region is North", "use SQL to calculate moving average"
"""

        prompt = f"""You are a query router for a multi-agent data analysis system.

Classify this query and route to the appropriate agent:

{agent_descriptions}

Dataset columns:
{json.dumps(data_summary, indent=2)}

User query: "{query}"

Extract any relevant parameters:
- column names mentioned
- specific values (thresholds, categories)
- chart types requested

Respond with JSON only:
{{
    "agent": "conversational|exploration|analysis|visualization|reporting|transformation",
    "params": {{
        "columns": ["col1", "col2"],
        "threshold": 1000,
        "chart_type": "histogram"
    }},
    "confidence": 0.95
}}"""

        try:
            response = self.llm.generate(prompt, temperature=0.1)
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
        except Exception:
            pass

        # Fall back to fast keyword classification if LLM JSON parsing fails (common in smaller local models)
        fallback_agent = self._simple_classify(query)
        return {"agent": fallback_agent, "params": {}, "confidence": 0.5}

    def _ensure_embeddings_cached(self):
        """Pre-calculate embeddings for intent sample sentences if not already cached."""
        if hasattr(self, "_cached_embeddings") and self._cached_embeddings:
            return

        self._cached_embeddings = {}
        if not self.use_llm:
            return

        import logging
        logger = logging.getLogger(__name__)
        logger.info("Initializing semantic routing embeddings pool...")

        for intent, samples in self.INTENT_SAMPLES.items():
            vectors = []
            for sample in samples:
                try:
                    # Request embedding vector from the LLM client
                    v = self.llm.get_embeddings(sample)
                    if v:
                        vectors.append(v)
                except Exception as e:
                    logger.warning(f"Failed to embed sample '{sample}': {e}")
            if vectors:
                self._cached_embeddings[intent] = vectors

    def _semantic_classify(self, query: str) -> Optional[str]:
        """Classify a query intent using pure-Python cosine similarity of cached vectors."""
        self._ensure_embeddings_cached()
        if not hasattr(self, "_cached_embeddings") or not self._cached_embeddings:
            return None

        try:
            query_vector = self.llm.get_embeddings(query)
            if not query_vector:
                return None
        except Exception:
            return None

        best_intent = None
        best_avg_similarity = -1.0

        import math

        def dot_product(v1, v2):
            return sum(a * b for a, b in zip(v1, v2))

        def magnitude(v):
            return math.sqrt(sum(a * a for a in v))

        def cosine_similarity(v1, v2):
            mag = magnitude(v1) * magnitude(v2)
            if not mag:
                return 0.0
            return dot_product(v1, v2) / mag

        for intent, sample_vectors in self._cached_embeddings.items():
            similarities = []
            for sample_vector in sample_vectors:
                sim = cosine_similarity(query_vector, sample_vector)
                similarities.append(sim)
            
            if similarities:
                # Average similarity score for this intent group
                avg_sim = sum(similarities) / len(similarities)
                if avg_sim > best_avg_similarity:
                    best_avg_similarity = avg_sim
                    best_intent = intent

        # If similarity is extremely weak or routing is uncertain, fallback to traditional routers
        if best_avg_similarity < 0.45:
            return None

        return best_intent

    def _simple_classify(self, query: str) -> str:
        """Simple keyword-based classification when LLM unavailable."""
        query_lower = query.lower()

        if any(w in query_lower for w in ["hello", "hi", "hey", "how are you", "who are you", "whats up", "what's up", "sup", "yo", "help", "thanks", "thank you"]):
            return "conversational"
        elif any(w in query_lower for w in ["plot", "chart", "graph", "histogram", "scatter", "visualiz"]):
            return "visualization"
        elif any(w in query_lower for w in ["insight", "recommend", "suggest", "finding", "conclusion"]):
            return "reporting"
        elif any(w in query_lower for w in ["correlat", "average", "mean", "median", "outlier", "statistic"]):
            return "analysis"
        elif any(w in query_lower for w in ["drop", "clean", "fill", "mutate", "add column", "filter", "replace", "sql"]):
            return "transformation"
        else:
            return "exploration"

    async def _handle_exploration(
        self, query: str, context: Any, params: Dict
    ) -> QueryResult:
        """Route query to ExplorationAgent via Orchestrator."""
        params["query"] = query
        result = await self.orchestrator.route_to_agent("exploration", params)

        if result.success:
            stdout_output = result.data
            code_used = result.metadata.get("code_executed", "")

            if self.use_llm:
                prompt = f"""You are a professional Data Analyst.
                The user asked: "{query}"

                The agent executed a data exploration task and got this raw output:
                {stdout_output}

                Please provide a professional, conversational response to the user.
                Explain the findings clearly, highlight key structural details of the data, and avoid just listing values.
                Be concise but insightful.
                """
                answer = self.llm.generate(prompt, temperature=0.3)
                # Append raw output as a technical appendix
                answer += f"\n\n---\n**Technical Details (Raw Output):**\n```text\n{stdout_output}\n```"
            else:
                answer = f"**Exploration Output:**\n```text\n{stdout_output}\n```"

            return QueryResult(
                success=True,
                answer=answer,
                data=code_used,
                agent_used="exploration"
            )
        return QueryResult(success=False, answer=f"Exploration failed: {result.error}", error=result.error)

    async def _handle_analysis(
        self, query: str, context: Any, params: Dict
    ) -> QueryResult:
        """Route query to AnalysisAgent via Orchestrator."""
        params["query"] = query
        result = await self.orchestrator.route_to_agent("analysis", params)

        if result.success:
            stdout_output = result.data
            code_used = result.metadata.get("code_executed", "")

            if self.use_llm:
                prompt = f"""You are a professional Data Analyst.
                The user asked: "{query}"

                The agent performed a statistical analysis and got this raw output:
                {stdout_output}

                Please provide a professional, conversational response to the user.
                Interpret the statistics in plain English, explain what they mean for the dataset, and present findings in a structured way.
                Be concise but insightful.
                """
                answer = self.llm.generate(prompt, temperature=0.3)
                # Append raw output as a technical appendix
                answer += f"\n\n---\n**Technical Details (Raw Output):**\n```text\n{stdout_output}\n```"
            else:
                answer = f"**Analysis Output:**\n```text\n{stdout_output}\n```"

            return QueryResult(
                success=True,
                answer=answer,
                data=code_used,
                agent_used="analysis"
            )
        return QueryResult(success=False, answer=f"Analysis failed: {result.error}", error=result.error)

    async def _handle_visualization(
        self, query: str, context: Any, params: Dict
    ) -> QueryResult:
        """Route query to VisualizationAgent via Orchestrator."""
        params["query"] = query
        result = await self.orchestrator.route_to_agent("visualization", params)
        
        if result.success:
            paths = result.data.get("paths", [])
            stdout = result.data.get("stdout", "")
            code_used = result.metadata.get("code_executed", "")
            
            answer = f"Generated {len(paths)} visualization(s)."
            if stdout:
                answer += f"\n\n**Logic Trace:**\n```text\n{stdout}\n```"
                
            return QueryResult(
                success=True,
                answer=answer,
                data=code_used,
                visualization_path=paths[0] if paths else None,
                agent_used="visualization"
            )
        return QueryResult(success=False, answer=f"Visualization failed: {result.error}", error=result.error)

    async def _handle_reporting(
        self, query: str, context: Any, params: Dict
    ) -> QueryResult:
        """Route query to ReportingAgent via Orchestrator."""
        result = await self.orchestrator.route_to_agent("reporting", params)

        if result.success:
            report = result.data

            # Extract relevant section based on query
            if self.use_llm:
                prompt = f"""User asked: "{query}"

Full report:
{report[:3000]}

Extract and summarize the most relevant parts of the report to answer this query.
Focus on insights and recommendations if asked."""
                answer = self.llm.generate(prompt, temperature=0.3)
            else:
                answer = report[:1000] + "..." if len(report) > 1000 else report

            return QueryResult(
                success=True,
                answer=answer,
                data=report,
                agent_used="reporting"
            )

        return QueryResult(
            success=False,
            answer=f"Reporting failed: {result.error}",
            error=result.error,
            agent_used="reporting"
        )
        
    async def _handle_transformation(
        self, query: str, context: Any, params: Dict
    ) -> QueryResult:
        """Route query to TransformationAgent via Orchestrator."""
        agent_params = {"query": query}
        agent_params.update(params)

        result = await self.orchestrator.route_to_agent("transformation", agent_params)

        if result.success:
            code_used = result.metadata.get("code_executed", "")
            if self.use_llm:
                prompt_text = f"""
                You just mutated a dataset using this Python/SQL code:
                {code_used}
                
                The user asked: "{query}"
                
                Respond in exactly 1-2 concise, conversational sentences confirming that their request was executed and explain highly briefly what the code did.
                """
                answer = self.llm.generate(prompt_text, temperature=0.2)
            else:
                answer = "Transformation applied successfully."
                
            return QueryResult(
                success=True,
                answer=answer,
                data=code_used,
                agent_used="transformation"
            )

        return QueryResult(
            success=False,
            answer=f"Transformation failed: {result.error}",
            error=result.error,
            agent_used="transformation"
        )

    async def _handle_conversational(
        self, query: str, context: Any, params: Dict
    ) -> QueryResult:
        """Handle conversational/general queries directly using the LLM without running any code."""
        df = context.loaded_data
        
        # Build context about the active dataset
        dataset_info = ""
        if df is not None:
            dataset_info = f"""
Active Dataset Metadata context:
- Source Path: {context.data_source}
- Shape: {len(df)} rows, {len(df.columns)} columns
- Columns: {list(df.columns)}
"""
            
        prompt = f"""You are a helpful, professional Data Analyst AI assistant.
You have an active data analysis session.

{dataset_info}

Recent Conversation Context (chat history):
{params.get("conversation_context", "None")}

User Query: "{query}"

Provide a helpful, direct, and conversational response to the user.
Since this is a general/conversational query, DO NOT generate or mention any Python code blocks or Sandboxed executions.
Just answer their question directly, accurately, and professionally based on the active dataset metadata or general knowledge.
"""
        
        try:
            answer = self.llm.generate(prompt, temperature=0.5)
            return QueryResult(
                success=True,
                answer=answer,
                agent_used="conversational"
            )
        except Exception as e:
            return QueryResult(
                success=False,
                answer=f"Failed to generate response: {str(e)}",
                error=str(e),
                agent_used="conversational"
            )

    def get_help_text(self) -> str:
        """Return help text for users."""
        return """
Query Engine - Ask questions about your data

Queries are routed through the Orchestrator to specialized agents:

Examples by agent:

**Exploration Agent** (data structure & quality):
- "Summarize the data"
- "What columns are there?"
- "Any missing values?"
- "Show me the schema"

**Analysis Agent** (statistics & aggregations):
- "Correlation between sales and cost"
- "Average sales by region"
- "Find outliers in price"
- "Statistics for numeric columns"

**Visualization Agent** (charts):
- "Plot a histogram of sales"
- "Scatter plot of price vs quantity"
- "Show me a boxplot"

**Reporting Agent** (insights & recommendations):
- "What insights can you find?"
- "Give me recommendations"
- "Key findings from the analysis"

Type 'help' for this message, 'schema' for columns, 'sample' for data preview.
Type 'state' to see current orchestrator state.
Type 'quit' or 'exit' to leave.
"""
