"""Shared session context for inter-agent data sharing."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pandas as pd


@dataclass
class SessionContext:
    """
    Shared context passed between all agents during a session.

    Holds loaded data, schema info, profiles, analysis results,
    visualizations, and error tracking.
    """

    session_id: str
    loaded_data: Optional[pd.DataFrame] = None
    data_source: Optional[str] = None
    schema_info: Optional[Dict[str, Any]] = None
    data_profile: Optional[Dict[str, Any]] = None
    analysis_cache: Dict[str, Any] = field(default_factory=dict)
    query_history: List[str] = field(default_factory=list)
    visualizations: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    report: Optional[str] = None

    def add_query(self, query: str):
        """Add a query to the history."""
        self.query_history.append(query)

    def add_error(self, error: str):
        """Record an error that occurred during processing."""
        self.errors.append(error)

    def get_column_names(self) -> List[str]:
        """Get list of column names from loaded data."""
        if self.loaded_data is not None:
            return list(self.loaded_data.columns)
        return []

    def get_numeric_columns(self) -> List[str]:
        """Get list of numeric column names."""
        if self.loaded_data is not None:
            return list(self.loaded_data.select_dtypes(include=["number"]).columns)
        return []

    def get_categorical_columns(self) -> List[str]:
        """Get list of categorical column names."""
        if self.loaded_data is not None:
            return list(
                self.loaded_data.select_dtypes(include=["object", "category"]).columns
            )
        return []

    def get_datetime_columns(self) -> List[str]:
        """Get list of datetime column names."""
        if self.loaded_data is not None:
            return list(self.loaded_data.select_dtypes(include=["datetime64"]).columns)
        return []

    def get_schema_summary(self) -> str:
        """Get a human-readable schema summary."""
        if self.schema_info:
            lines = []
            for col, info in self.schema_info.items():
                dtype = info.get("dtype", "unknown")
                unique = info.get("unique", "?")
                missing = info.get("missing", "?")
                lines.append(f"  {col}: {dtype} (unique={unique}, missing={missing})")
            return "\n".join(lines)
        return "No schema loaded"

    def get_data_shape(self) -> tuple:
        """Get the shape of loaded data (rows, columns)."""
        if self.loaded_data is not None:
            return self.loaded_data.shape
        return (0, 0)

    def clear_data(self):
        """Clear loaded data and derived state."""
        self.loaded_data = None
        self.schema_info = None
        self.data_profile = None
        self.analysis_cache = {}
        self.visualizations = []
        self.report = None

    def to_dict(self) -> dict:
        """Convert context to dictionary (excluding DataFrame)."""
        return {
            "session_id": self.session_id,
            "data_source": self.data_source,
            "schema_info": self.schema_info,
            "data_profile": self.data_profile,
            "analysis_cache": self.analysis_cache,
            "query_history": self.query_history.copy(),
            "visualizations": self.visualizations.copy(),
            "errors": self.errors.copy(),
            "data_shape": self.get_data_shape(),
        }
