# assistant/finance-assistant/src/agent/nodes/generate_chart_node.py
"""
Node function to generate Plotly charts based on SQL results.
"""

import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, Optional, List

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

# Configure logging for this node
logger = logging.getLogger(__name__)

def generate_chart_node(state: AgentState) -> dict:
    """
    Generates a Plotly chart JSON based on the SQL query results (List of Dicts).
    Uses simple heuristics to determine the most appropriate chart type.

    Args:
        state (AgentState): The current graph state. Needs 'sql_results_list'.

    Returns:
        dict: A dictionary containing 'chart_json' (Plotly JSON string) if successful,
              otherwise None.
    """
    logger.info("--- Executing Node: generate_chart_node (Modularized) ---")
    results_list = state.get('sql_results_list')
    error = state.get('error')

    if error:
        logger.warning(f"Skipping chart generation due to previous error: {error}")
        return {"chart_json": None}
    if results_list is None: # Check if None
        logger.warning("Skipping chart generation as results list is None.")
        return {"chart_json": None}
    if not results_list: # Check if empty list
        logger.info("Skipping chart generation as results list is empty.")
        return {"chart_json": None}

    try:
        df = pd.DataFrame(results_list)
        if df.empty: # Double check after conversion
            logger.warning("DataFrame created from results list is empty. Skipping chart generation.")
            return {"chart_json": None}

        logger.info(f"Reconstructed DataFrame for charting, shape: {df.shape}")
        logger.debug(f"DataFrame columns: {df.columns.tolist()}")
        logger.debug(f"DataFrame dtypes:\n{df.dtypes}")

        fig = None # Initialize fig to None

        # --- Charting Heuristics ---
        num_rows, num_cols = df.shape
        col_names_lower = df.columns.str.lower()
        # Identify numeric columns, excluding known identifiers like id/year
        numeric_cols = [
            col for col in df.columns
            if pd.api.types.is_numeric_dtype(df[col])
            and col.lower() not in ['id', 'year']
        ]
        logger.debug(f"Identified numeric columns for plotting: {numeric_cols}")

        # Identify potential time columns
        time_cols = [
            col for col in df.columns
            if 'date' in col.lower() or 'month' in col.lower() or 'year' in col.lower()
        ]
        logger.debug(f"Identified potential time columns: {time_cols}")
        date_col_present = bool(time_cols) # Simplified check

        # Heuristic 1: Time series data (one time column, one numeric value) -> Line Chart
        if date_col_present and len(numeric_cols) == 1:
            # Prefer 'date' > 'month' > 'yearmonth' > 'year' for time axis
            if 'date' in col_names_lower: time_col_name = df.columns[col_names_lower.tolist().index('date')]
            elif 'month' in col_names_lower: time_col_name = df.columns[col_names_lower.tolist().index('month')]
            # Add more specific checks if needed (e.g., 'yearmonth')
            else: time_col_name = time_cols[0] # Fallback to first identified time column

            value_col_name = numeric_cols[0]
            logger.info(f"Attempting Line Chart: X='{time_col_name}', Y='{value_col_name}'")
            try:
                # Attempt conversion to datetime for proper sorting/plotting
                try:
                    df[time_col_name] = pd.to_datetime(df[time_col_name], errors='coerce')
                    # Drop rows where conversion failed if any
                    df.dropna(subset=[time_col_name], inplace=True)
                except Exception as time_conv_err:
                    logger.warning(f"Could not convert time column '{time_col_name}' to datetime: {time_conv_err}. Sorting may be string-based.")
                    # Proceed with string sorting, might not be ideal

                if not df.empty:
                    df_sorted = df.sort_values(by=time_col_name)
                    fig = px.line(df_sorted, x=time_col_name, y=value_col_name,
                                  title=f"{value_col_name.capitalize()} Trend", markers=True)
                    fig.update_layout(xaxis_title=time_col_name.capitalize(), yaxis_title=value_col_name.capitalize())
                else:
                    logger.warning("DataFrame became empty after attempting date conversion/dropna. Skipping line chart.")

            except TypeError as sort_err:
                 logger.warning(f"TypeError during sorting/plotting line chart (column '{time_col_name}' might not be sortable): {sort_err}. Skipping line chart.")
            except Exception as line_err:
                 logger.warning(f"Could not generate line chart: {line_err}. Skipping line chart.")

        # Heuristic 2: Categorical vs Numerical (2 columns, one numeric) -> Bar Chart
        elif num_cols == 2 and len(numeric_cols) == 1:
            value_col_name = numeric_cols[0]
            # Identify the categorical column (the one that's not the value column)
            cat_col_name = next((col for col in df.columns if col != value_col_name), None)

            if cat_col_name:
                logger.info(f"Attempting Bar Chart: Category='{cat_col_name}', Value='{value_col_name}'")
                try:
                    max_bars = 15
                    # Aggregate in case SQL didn't, or sort if already aggregated
                    if df[cat_col_name].nunique() < len(df):
                        df_agg = df.groupby(cat_col_name)[value_col_name].sum().reset_index()
                        logger.debug(f"Aggregated data for bar chart, shape: {df_agg.shape}")
                    else:
                         df_agg = df # Assume already aggregated if unique categories match rows
                    df_agg_sorted = df_agg.sort_values(by=value_col_name, ascending=False)
                    df_chart = df_agg_sorted.head(max_bars)

                    title_suffix = f" (Top {max_bars})" if len(df_agg) > max_bars else ""
                    title = f"{value_col_name.capitalize()} by {cat_col_name.capitalize()}{title_suffix}"

                    fig = px.bar(df_chart, x=cat_col_name, y=value_col_name, title=title, text_auto='.2s')
                    fig.update_traces(textangle=0, textposition="outside")
                    fig.update_layout(xaxis_title=cat_col_name.capitalize(), yaxis_title=value_col_name.capitalize())
                except Exception as bar_err:
                    logger.warning(f"Could not generate bar chart: {bar_err}. Skipping bar chart.")
            else:
                logger.warning("Bar chart condition met but failed to identify categorical column.")

        # Heuristic 3: Single result row -> No Chart needed
        elif num_rows == 1 and len(numeric_cols) >= 1:
            logger.info("Single row result. Skipping graphical chart generation.")
            return {"chart_json": None}

        # Fallback: No specific chart type matched
        if fig is None:
            logger.info("No specific chart type matched heuristics. Skipping chart generation.")
            return {"chart_json": None}

        # --- Common Layout Updates ---
        fig.update_layout(
            margin=dict(l=40, r=20, t=60, b=40), # Adjust margins as needed
            title_x=0.5, # Center title
            legend_title_text=None # Remove legend title
        )

        chart_json = fig.to_json()
        logger.info("Plotly chart JSON generated successfully.")
        return {"chart_json": chart_json}

    except Exception as e:
        logger.error(f"Unexpected error during chart generation: {e}", exc_info=True)
        # Return None or potentially an error state update? For now, just None.
        return {"chart_json": None}