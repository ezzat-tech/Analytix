import os
import pandas as pd
from typing import List, Dict, Any

def serialize_dataframe(df: pd.DataFrame, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Converts a DataFrame to a JSON-serializable list of dictionaries.
    Returns the first 'limit' rows.
    """
    if df is None:
        return None
    import json
    # Use Pandas' built-in to_json to natively serialize NaN and datetime objects safely,
    # then load back into a standard Python list of dicts for FastAPI's responder.
    return json.loads(df.head(limit).to_json(orient="records"))

def serialize_visualizations(paths: List[str]) -> List[str]:
    """
    Maps absolute system paths of generated plots to relative static URLs.
    Example: 'C:/path/to/outputs/plot_1.png' -> '/static/plot_1.png'
    """
    if not paths:
        return []

    return [f"/static/{os.path.basename(path)}" for path in paths]
