"""Event definitions for state transitions."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Event:
    """Events that trigger state transitions."""

    type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
