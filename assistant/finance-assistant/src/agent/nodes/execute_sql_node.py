# assistant/finance-assistant/src/agent/nodes/execute_sql_node.py
"""
Node function to execute the generated SQL query.
Imports shared database engine.
"""

import logging
import pandas as pd
from sqlalchemy import text, Engine # Import Engine type hint
from typing import List, Dict, Any, Optional


# Configure logging for this node
logger = logging.getLogger(__name__)

# --- Import Agent State ---
try:
    from agent.state import AgentState
except ImportError:
    logging.error("Failed to import AgentState from agent.state. Defining fallback.")
    from typing import TypedDict
    class AgentState(TypedDict):
        original_query: str
        classification: Optional[str]
        sql_query: Optional[str]
        sql_results_str: Optional[str]
        sql_results_list: Optional[List[Dict[str, Any]]]
        chart_json: Optional[str]
        final_response: Optional[str]
        error: Optional[str]

# --- Import Shared Clients ---
try:
    # Assumes shared_clients.py is in the parent directory 'agent'
    from agent.shared_clients import engine # Import only the engine
    if not isinstance(engine, Engine) and engine is not None:
         logger.warning(f"Imported 'engine' may not be a SQLAlchemy Engine instance (type: {type(engine)}).")
except ImportError:
    logging.error("Could not import 'engine' from agent.shared_clients. Using fallback None.")
    engine = None
except Exception as e:
     logging.error(f"Unexpected error importing 'engine': {e}", exc_info=True)
     engine = None


# Configure logging for this node
logger = logging.getLogger(__name__)


def execute_sql_node(state: AgentState) -> dict:
    """
    Executes the generated SQL query against the SQLite database using the shared engine.
    Returns results as a string and a serializable list of dictionaries.

    Args:
        state (AgentState): The current graph state. Must contain 'sql_query' if no prior error.

    Returns:
        dict: A dictionary containing 'sql_results_list' (List[Dict]) and
              'sql_results_str' (string representation), or an 'error' key if execution fails.
    """
    logger.info("--- Executing Node: execute_sql_node (Modularized) ---")
    sql_query = state.get('sql_query')

    # Check for shared resource availability
    if engine is None:
        logger.error("Database engine not available for SQL execution.")
        # Return error state immediately if engine is missing
        return {"error": "Database engine not configured", "sql_results_list": [], "sql_results_str": "Error: DB not configured."}

    if state.get('error'):
        logger.warning(f"Skipping SQL execution due to previous error: {state['error']}")
        # Return empty results but don't overwrite error
        return {"sql_results_list": [], "sql_results_str": f"Error state detected: {state['error']}"}

    if not sql_query:
        logger.error("No SQL query found in state to execute.")
        # Set error state
        return {"error": "SQL query generation failed or was missing.", "sql_results_list": [], "sql_results_str": "Error: No SQL query found."}

    logger.info(f"Attempting to execute SQL query: [{sql_query}]")
    try:
        # Use the imported engine
        with engine.connect() as connection:
            df = pd.read_sql(sql=text(sql_query), con=connection) # Use text() for query safety
        logger.info(f"SQL query executed successfully. Number of rows returned: {len(df)}")

        results_list: List[Dict[str, Any]] = [] # Initialize as empty list
        results_str: str = ""                   # Initialize as empty string

        if not df.empty:
            # Formatting (optional but good)
            for col in df.columns:
                if 'date' in col.lower():
                    # Safely attempt date formatting
                    try:
                        df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')
                    except Exception as fmt_err:
                        logger.warning(f"Could not format date column '{col}': {fmt_err}")
                elif 'amount' in col.lower() and pd.api.types.is_numeric_dtype(df[col]):
                    # Safely attempt amount formatting
                    try:
                        df[col] = df[col].round(2)
                    except Exception as fmt_err:
                        logger.warning(f"Could not format amount column '{col}': {fmt_err}")

            # Handle potential NaT/NaN introduced by formatting before conversion
            df = df.fillna('<NA>') # Replace Pandas NA types with a string placeholder

            # Convert DataFrame to list of dictionaries (JSON serializable)
            results_list = df.to_dict('records')
            # Create string version for LLM summary
            results_str = df.to_string(index=False, na_rep='<NA>')
        else:
            results_list = [] # Explicitly set to empty list
            results_str = "Query returned no results."

        # Return success state
        return {"sql_results_list": results_list, "sql_results_str": results_str}

    except Exception as e:
        # Catch broader exceptions during SQL execution or pandas processing
        logger.error(f"SQL execution or processing failed for query [{sql_query}]: {e}", exc_info=True)
        error_msg = f"Failed to execute SQL query or process results. Error: {e}. Query Attempted: [{sql_query}]"
        # Set error state
        return {"error": error_msg, "sql_results_list": [], "sql_results_str": f"Error executing SQL."}