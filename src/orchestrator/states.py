"""State definitions for the multi-agent orchestration system."""

from enum import Enum, auto


class State(Enum):
    """States representing the data analysis pipeline stages."""

    IDLE = auto()           # Waiting for user input
    LOADING = auto()        # Loading data from source
    LOADED = auto()         # Data ready for analysis
    EXPLORING = auto()      # Profiling data
    EXPLORED = auto()       # Profile complete
    ANALYZING = auto()      # Running analysis
    ANALYZED = auto()       # Analysis complete
    VISUALIZING = auto()    # Generating charts
    VIZ_READY = auto()      # Visualizations ready
    REPORTING = auto()      # Generating report
    COMPLETE = auto()       # Cycle finished
    QUERYING = auto()       # Processing an ad-hoc query via routing
