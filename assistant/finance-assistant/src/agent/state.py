# assistant/finance-assistant/src/agent/state.py
"""Define the state structures for the agent."""

from __future__ import annotations # Ensures compatibility with type hints

# Use typing.TypedDict for standard LangGraph state
from typing import TypedDict, Optional, List, Dict, Any
import pandas as pd

# Define the structure of the state that will be passed between nodes
class AgentState(TypedDict):
    """Represents the state shared across the agent graph."""
    original_query: str           # The initial question from the user
    classification: Optional[str]   # 'simple', 'advanced', 'irrelevant'
    sql_query: Optional[str]        # Generated SQL query
    sql_results_str: Optional[str]  # SQL results as a formatted string
    # sql_results_df: Any             # SQL results as a Pandas DataFrame (use Any for now, handle serialization if needed)
    sql_results_list: Optional[List[Dict[str, Any]]] # SQL results as a list of dictionaries, store results as serializable list of dicts
    chart_json: Optional[str]       # Plotly figure JSON representation
    final_response: Optional[str]   # Final text response for the user
    error: Optional[str]            # To capture errors during execution