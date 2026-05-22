"""Shared utility functions for the analysis pipeline."""

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np


def generate_session_id() -> str:
    """Generate a unique session ID."""
    import uuid
    return str(uuid.uuid4())[:8]


def sanitize_column_name(name: str) -> str:
    """
    Sanitize column name for safe use in code/SQL.

    Converts "Column Name (2023)" to "column_name_2023"
    """
    # Replace non-alphanumeric with underscore
    sanitized = "".join(c if c.isalnum() else "_" for c in str(name))
    # Remove leading digits
    while sanitized and sanitized[0].isdigit():
        sanitized = sanitized[1:]
    # Collapse multiple underscores
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    return sanitized.lower().strip("_")


def detect_column_type(series: pd.Series) -> str:
    """
    Detect the semantic type of a column.

    Returns: "numeric", "categorical", "datetime", "text", "boolean", "id"
    """
    dtype = series.dtype

    # Check for datetime
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"

    # Check for boolean
    if set(series.dropna().unique()).issubset({True, False, 0, 1}):
        return "boolean"

    # Check for numeric
    if pd.api.types.is_numeric_dtype(dtype):
        unique_ratio = series.nunique() / len(series)
        # If very few unique values relative to size, might be categorical
        if unique_ratio < 0.05 and series.nunique() < 20:
            return "categorical"
        # If unique count equals row count, might be ID
        if series.nunique() == len(series):
            return "id"
        return "numeric"

    # Check for categorical (low cardinality)
    if series.nunique() < 20 or series.nunique() / len(series) < 0.05:
        return "categorical"

    return "text"


def format_number(value: Any, precision: int = 2) -> str:
    """Format a number with appropriate suffixes."""
    if value is None or pd.isna(value):
        return "N/A"

    try:
        num = float(value)
        if abs(num) >= 1e9:
            return f"{num / 1e9:.{precision}f}B"
        elif abs(num) >= 1e6:
            return f"{num / 1e6:.{precision}f}M"
        elif abs(num) >= 1e3:
            return f"{num / 1e3:.{precision}f}K"
        else:
            return f"{num:.{precision}f}"
    except (TypeError, ValueError):
        return str(value)


def calculate_memory_usage(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate memory usage breakdown.

    Returns dict with total_mb, per_column dict.
    """
    memory_bytes = df.memory_usage(deep=True)
    total_bytes = memory_bytes.sum()

    return {
        "total_mb": round(total_bytes / (1024 ** 2), 2),
        "per_column": {
            col: round(bytes_ / (1024 ** 2), 4)
            for col, bytes_ in memory_bytes.items()
        }
    }


def get_outlier_indices(series: pd.Series, method: str = "iqr") -> List[int]:
    """
    Find indices of outlier values in a numeric series.

    Args:
        series: Numeric pandas Series
        method: "iqr" or "zscore"

    Returns:
        List of row indices that are outliers
    """
    if not pd.api.types.is_numeric_dtype(series):
        return []

    if method == "iqr":
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = (series < lower) | (series > upper)
    elif method == "zscore":
        mean = series.mean()
        std = series.std()
        if std == 0:
            return []
        zscores = (series - mean) / std
        mask = abs(zscores) > 3
    else:
        return []

    return series[mask].index.tolist()


def safe_read_csv(
    filepath: Union[str, Path],
    encoding: str = "utf-8",
    fallback_encodings: List[str] = None
) -> pd.DataFrame:
    """
    Read CSV with encoding fallback.

    Tries multiple encodings before giving up.
    """
    fallback_encodings = fallback_encodings or ["latin-1", "cp1252", "iso-8859-1"]

    for enc in [encoding] + fallback_encodings:
        try:
            return pd.read_csv(filepath, encoding=enc)
        except UnicodeDecodeError:
            continue

    # Last resort - ignore errors
    return pd.read_csv(filepath, encoding=encoding, encoding_errors="ignore")


def hash_dataframe(df: pd.DataFrame) -> str:
    """Generate a hash of DataFrame content for caching."""
    # Hash the underlying data
    data_hash = hashlib.md5(
        pd.util.hash_pandas_object(df, index=True).values
    ).hexdigest()
    return data_hash[:12]


def ensure_dir(path: Union[str, Path]) -> Path:
    """Ensure directory exists, create if needed."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate string to max length with suffix."""
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def validate_python_syntax(code: str) -> tuple:
    """
    Validate Python code syntax before execution.

    Args:
        code: Python code string to validate

    Returns:
        (is_valid: bool, error_message: str or None)
    """
    import ast

    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
        return False, error_msg


def clean_generated_code(code: str) -> str:
    """
    Clean LLM-generated code by removing markdown artifacts and whitespace issues.

    Args:
        code: Raw code string from LLM

    Returns:
        Cleaned code string
    """
    # Remove markdown code blocks
    code = code.replace("```python", "").replace("```py", "").replace("```", "")

    # Strip leading/trailing whitespace
    code = code.strip()

    # Remove any leading/trailing quotes that might wrap the code
    if (code.startswith('"') and code.endswith('"')) or \
       (code.startswith("'") and code.endswith("'")):
        code = code[1:-1]

    # Fix common LLM issues
    lines = code.split('\n')
    cleaned_lines = []

    for line in lines:
        # Remove trailing whitespace
        line = line.rstrip()
        # Skip lines that are just markdown artifacts
        if line.strip() in ('', 'python'):
            continue
        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)
