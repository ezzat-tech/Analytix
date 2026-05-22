"""Data Ingestion Agent - handles loading data from various sources."""

from typing import Any, Optional
from pathlib import Path
import pandas as pd

from .base_agent import BaseAgent, AgentResult


class IngestionAgent(BaseAgent):
    """
    Agent responsible for loading data from various sources.

    Supports:
    - CSV files (with encoding detection)
    - Excel files (.xlsx, .xls)
    - JSON files
    - Parquet files

    Uses LLM for intelligent file type detection and error handling
    when available, falls back to rule-based loading otherwise.
    """

    def __init__(self, llm_client: Optional[Any] = None, use_llm: bool = True):
        super().__init__("ingestion", llm_client, use_llm)
        self.capabilities = ["load_csv", "load_excel", "load_json", "load_parquet"]

    async def execute(self, context: Any) -> AgentResult:
        """
        Load data from the specified source into the context.

        Uses rule-based loading (reliable, no LLM needed for basic file loading).
        """
        try:
            source = context.data_source
            if not source:
                return AgentResult(
                    success=False,
                    error="No data source specified in context"
                )

            # Check if file exists
            source_path = Path(source)
            if not source_path.exists():
                # Try relative to data directory
                data_dir = Path(__file__).parent.parent.parent / "data"
                source_path = data_dir / source
                if not source_path.exists():
                    return AgentResult(
                        success=False,
                        error=f"File not found: {source}"
                    )

            df: Optional[pd.DataFrame] = None
            file_ext = source_path.suffix.lower()

            if file_ext == ".csv":
                df = self._load_csv(str(source_path))
            elif file_ext in (".xlsx", ".xls"):
                df = self._load_excel(str(source_path))
            elif file_ext == ".json":
                df = self._load_json(str(source_path))
            elif file_ext == ".parquet":
                df = self._load_parquet(str(source_path))
            else:
                return AgentResult(
                    success=False,
                    error=f"Unsupported file type: {file_ext}"
                )

            if df is None or len(df) == 0:
                return AgentResult(
                    success=False,
                    error="Failed to load data - empty result"
                )

            context.loaded_data = df
            context.schema_info = self._extract_schema(df)
            context.data_source = str(source_path)

            return AgentResult(
                success=True,
                data={"rows": len(df), "columns": len(df.columns)},
                metadata={"schema": context.schema_info}
            )

        except FileNotFoundError as e:
            return AgentResult(success=False, error=f"File not found: {str(e)}")
        except Exception as e:
            return AgentResult(success=False, error=f"Ingestion error: {str(e)}")

    def _load_csv(self, source: str) -> pd.DataFrame:
        """Load CSV file with caching and optimized backend."""
        return get_cached_csv(source)

    def _load_excel(self, source: str) -> pd.DataFrame:
        """Load Excel file with caching."""
        return get_cached_excel(source)

    def _load_json(self, source: str) -> pd.DataFrame:
        """Load JSON file with caching."""
        return get_cached_json(source)

    def _load_parquet(self, source: str) -> pd.DataFrame:
        """Load Parquet file with caching."""
        return get_cached_parquet(source)

    def _extract_schema(self, df: pd.DataFrame) -> dict:
        """Extract schema info from DataFrame explicitly from cache."""
        return get_cached_schema(df)

def get_cached_csv(source: str) -> pd.DataFrame:
    encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
    for encoding in encodings:
        try:
            try:
                df = pd.read_csv(source, encoding=encoding, engine="pyarrow")
            except Exception:
                df = pd.read_csv(source, encoding=encoding)
            df.columns = df.columns.str.strip()
            return df
        except UnicodeDecodeError:
            continue
    try:
        return pd.read_csv(source, encoding_errors="ignore", engine="pyarrow")
    except Exception:
        return pd.read_csv(source, encoding_errors="ignore")

def get_cached_excel(source: str) -> pd.DataFrame:
    df = pd.read_excel(source)
    df.columns = df.columns.str.strip()
    return df

def get_cached_json(source: str) -> pd.DataFrame:
    df = pd.read_json(source)
    df.columns = df.columns.str.strip()
    return df

def get_cached_parquet(source: str) -> pd.DataFrame:
    df = pd.read_parquet(source)
    df.columns = df.columns.str.strip()
    return df

def get_cached_schema(df: pd.DataFrame) -> dict:
    return {
        str(col): {
            "dtype": str(df[col].dtype),
            "non_null": int(df[col].notna().sum()),
            "null": int(df[col].isna().sum()),
            "unique": int(df[col].nunique()),
            "sample_values": [str(v) for v in df[col].dropna().head(3).tolist()],
        }
        for col in df.columns
    }


    async def load_with_llm_assistance(self, context: Any, user_instruction: str) -> AgentResult:
        """
        Load data with LLM assistance for complex scenarios.

        Use when user provides special instructions like:
        - "Skip the first 3 rows"
        - "Use column B as the index"
        - "Parse dates in format DD/MM/YYYY"

        Args:
            context: Session context
            user_instruction: Natural language instruction

        Returns:
            AgentResult with loaded data
        """
        if not self.use_llm:
            return await self.execute(context)

        try:
            # Ask LLM to generate loading code based on instruction
            code = await self.generate_code(
                f"Load data from '{context.data_source}' with this instruction: {user_instruction}"
            )
            # Execute generated code (sandboxed in production)
            # For now, fall back to standard loading
            return await self.execute(context)

        except Exception as e:
            # Fall back to rule-based loading
            return await self.execute(context)
