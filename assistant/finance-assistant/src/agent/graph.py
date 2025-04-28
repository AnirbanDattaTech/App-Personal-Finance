# src/agent/graph.py
"""
Defines the graph structure and nodes for the finance assistant agent.
Imports shared clients (LLM, DB engine) and metadata from shared_clients.
Imports node logic from the nodes/ directory.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langgraph.graph import StateGraph, END
from sqlalchemy import text # Still needed for execute_sql_node
import logging
from typing import List, Dict, Any

# --- Import Agent State and Shared Resources ---
from agent.state import AgentState
# Import the initialized clients and metadata from the shared module
from agent.shared_clients import LLM, engine, SCHEMA_METADATA

# --- Import Node Functions ---
from agent.nodes.classify_query_node import classify_query_node
# Add imports for other nodes as they are moved:
# from agent.nodes.generate_sql_node import generate_sql_node
# from agent.nodes.execute_sql_node import execute_sql_node
# from agent.nodes.generate_chart_node import generate_chart_node
# from agent.nodes.generate_response_node import generate_response_node

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==========================================================================
#                       NODE FUNCTIONS (Remaining - To be moved)
# ==========================================================================

# *** classify_query_node function definition removed ***

# *** LLM, engine, SCHEMA_METADATA initialization removed ***


def generate_sql_node(state: AgentState) -> dict:
    """
    Generates an SQLite query based on the user's original query and schema metadata.
    Uses shared LLM and SCHEMA_METADATA imported from shared_clients.
    """
    logger.info("--- Executing Node: generate_sql_node ---")
    query = state.get('original_query')

    # Check for shared resource availability
    if LLM is None:
        return {"error": "LLM not configured", "sql_query": None}
    if not SCHEMA_METADATA or "Fallback Schema" in SCHEMA_METADATA:
        logger.warning("Using fallback or missing schema metadata for SQL generation.")
        # Optionally return error: return {"error": "Schema metadata unavailable.", "sql_query": None}

    if state.get('error'):
         logger.warning(f"Skipping SQL generation due to previous error: {state['error']}")
         return {}
    if not query:
        logger.error("Original query is missing in state for SQL generation.")
        return {"error": "Missing user query.", "sql_query": None}

    logger.debug(f"Generating SQL for query: '{query}'")

    # --- Prompt Definition (Keep here for now, move later) ---
    template_string = """System: You are an expert SQLite query generator. Your task is to generate a precise and syntactically correct SQLite query for the 'expenses' table based ONLY on the user's question and the provided schema metadata.

Schema Metadata:
------
{schema_info}
------

Query Generation Instructions:
1.  Analyze the user's question and the detailed schema metadata.
2.  Identify the relevant columns, filters, aggregations (SUM, AVG, COUNT), and grouping clauses needed.
3.  Use the 'purpose_for_llm' descriptions in the metadata to understand column usage and handle potential ambiguities (e.g., prefer 'Household.Electricity Bill' for bill payments, consider context for 'Amazon').
4.  Construct a single, valid SQLite query.
5.  Interpret timeframes relative to a plausible current date (e.g., assume mid-2024 or later for 'last month', 'this year'). Use specific 'YYYY-MM-DD' date formats in WHERE clauses (e.g., `date BETWEEN '2024-01-01' AND '2024-01-31'`).
6.  Respond ONLY with the raw SQL query. Do NOT include any explanations, comments, or markdown formatting (like ```sql or ```).
7.  Ensure the query terminates correctly (no trailing semicolon needed typically for execution libraries).

User: Generate the SQLite query for the following question: {user_query}
"""
    prompt = ChatPromptTemplate.from_template(template_string)
    # --- End Prompt Definition ---

    chain = prompt | LLM

    try:
        input_data = {"schema_info": SCHEMA_METADATA, "user_query": query}
        response = chain.invoke(input_data)
        sql_query = response.content.strip().replace("```sql", "").replace("```", "").strip()
        if sql_query.endswith(';'):
            sql_query = sql_query[:-1].strip()
        logger.info(f"Gemini raw SQL response: '{response.content}' -> Cleaned: '{sql_query}'")

        if not sql_query or not sql_query.lower().startswith("select"):
             logger.error(f"Generated query is empty or does not start with SELECT: '{sql_query}'")
             return {"error": "Failed to generate a valid SELECT query.", "sql_query": sql_query or "Empty response"}

    except KeyError as e:
        logger.error(f"KeyError during chain invocation in SQL generation. Error: {e}", exc_info=True)
        return {"error": f"Internal error matching input to prompt variables: {e}"}
    except Exception as e:
        logger.error(f"LLM call failed during SQL generation for query '{query}': {e}", exc_info=True)
        return {"error": f"Failed to generate SQL query due to LLM error: {e}", "sql_query": None}

    return {"sql_query": sql_query}


def execute_sql_node(state: AgentState) -> dict:
    """
    Executes the generated SQL query against the SQLite database.
    Uses shared database engine imported from shared_clients.
    """
    logger.info("--- Executing Node: execute_sql_node ---")
    sql_query = state.get('sql_query')

    # Check for shared resource availability
    if engine is None:
        return {"error": "Database engine not configured", "sql_results_list": [], "sql_results_str": "Error: DB not configured."}

    if state.get('error'):
        logger.warning(f"Skipping SQL execution due to previous error: {state['error']}")
        return {"sql_results_list": [], "sql_results_str": f"Error: {state['error']}"}
    if not sql_query:
        logger.error("No SQL query found in state to execute.")
        return {"error": "SQL query generation failed or was missing.", "sql_results_list": [], "sql_results_str": "Error: No SQL query found."}

    logger.info(f"Attempting to execute SQL query: [{sql_query}]")
    try:
        with engine.connect() as connection:
            df = pd.read_sql(sql=text(sql_query), con=connection)
        logger.info(f"SQL query executed successfully. Number of rows returned: {len(df)}")

        results_list: List[Dict[str, Any]] = []
        results_str: str = ""

        if not df.empty:
            # Formatting (optional but good)
            for col in df.columns:
                if 'date' in col.lower():
                    try: df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d')
                    except Exception: pass
                elif 'amount' in col.lower() and pd.api.types.is_numeric_dtype(df[col]):
                    try: df[col] = df[col].round(2)
                    except Exception: pass
            results_list = df.to_dict('records')
            results_str = df.to_string(index=False, na_rep='<NA>')
        else:
            results_list = []
            results_str = "Query returned no results."

        return {"sql_results_list": results_list, "sql_results_str": results_str}

    except Exception as e:
        logger.error(f"SQL execution failed for query [{sql_query}]: {e}", exc_info=True)
        error_msg = f"Failed to execute SQL query. Error: {e}. Query Attempted: [{sql_query}]"
        return {"error": error_msg, "sql_results_list": [], "sql_results_str": f"Error executing SQL."}


def generate_chart_node(state: AgentState) -> dict:
    """
    Generates a Plotly chart JSON based on the SQL query results (List of Dicts).
    """
    logger.info("--- Executing Node: generate_chart_node ---")
    results_list = state.get('sql_results_list')
    error = state.get('error')

    if error:
        logger.warning(f"Skipping chart generation due to previous error: {error}")
        return {"chart_json": None}
    if results_list is None:
        logger.warning("Skipping chart generation as results list is None.")
        return {"chart_json": None}
    if not results_list:
        logger.info("Skipping chart generation as results list is empty.")
        return {"chart_json": None}

    try:
        df = pd.DataFrame(results_list)
        if df.empty:
            logger.warning("DataFrame created from results list is empty. Skipping chart generation.")
            return {"chart_json": None}
        logger.info(f"Reconstructed DataFrame for charting, shape: {df.shape}")

        # --- Charting Logic (remains the same) ---
        fig = None
        # ... (rest of charting logic remains unchanged) ...
        num_rows, num_cols = df.shape
        col_names_lower = df.columns.str.lower()
        numeric_cols = [
            col for col in df.columns
            if pd.api.types.is_numeric_dtype(df[col])
            and col.lower() not in ['id', 'year']
        ]
        date_col_present = 'date' in col_names_lower or 'month' in col_names_lower or 'yearmonth' in col_names_lower

        if date_col_present and len(numeric_cols) == 1:
            # Logic for Line Chart
            if 'date' in col_names_lower: time_col = df.columns[col_names_lower.tolist().index('date')]
            elif 'month' in col_names_lower: time_col = df.columns[col_names_lower.tolist().index('month')]
            else: time_col = df.columns[col_names_lower.tolist().index('yearmonth')]
            value_col = numeric_cols[0]
            try:
                try: df[time_col] = pd.to_datetime(df[time_col])
                except Exception: pass # Ignore conversion errors, sort as strings
                df_sorted = df.sort_values(by=time_col)
                fig = px.line(df_sorted, x=time_col, y=value_col, title=f"{value_col.capitalize()} Trend", markers=True)
                fig.update_layout(xaxis_title=time_col.capitalize(), yaxis_title=value_col.capitalize())
            except Exception as line_err: logger.warning(f"Could not generate line chart: {line_err}")

        elif num_cols == 2 and len(numeric_cols) == 1:
            # Logic for Bar Chart
            value_col = numeric_cols[0]
            cat_col = next((col for col in df.columns if col != value_col), None)
            if cat_col:
                try:
                    max_bars = 15
                    df_agg = df.sort_values(by=value_col, ascending=False)
                    df_chart = df_agg.head(max_bars)
                    title_suffix = f" (Top {max_bars})" if len(df_agg) > max_bars else ""
                    title = f"{value_col.capitalize()} by {cat_col.capitalize()}{title_suffix}"
                    fig = px.bar(df_chart, x=cat_col, y=value_col, title=title, text_auto='.2s')
                    fig.update_traces(textangle=0, textposition="outside")
                    fig.update_layout(xaxis_title=cat_col.capitalize(), yaxis_title=value_col.capitalize())
                except Exception as bar_err: logger.warning(f"Could not generate bar chart: {bar_err}")

        elif num_rows == 1 and len(numeric_cols) == 1:
            logger.info("Single numeric value result. Skipping graphical chart generation.")
            return {"chart_json": None}


        if fig is None:
            logger.info("No specific chart type matched heuristics. Skipping chart generation.")
            return {"chart_json": None}

        fig.update_layout(margin=dict(l=40, r=20, t=60, b=40), title_x=0.5, legend_title_text=None)
        chart_json = fig.to_json()
        logger.info("Plotly chart JSON generated successfully.")
        return {"chart_json": chart_json}

    except Exception as e:
        logger.error(f"Unexpected error during chart generation: {e}", exc_info=True)
        return {"chart_json": None}


def generate_response_node(state: AgentState) -> dict:
    """
    Generates the final natural language response.
    Uses shared LLM imported from shared_clients.
    """
    logger.info("--- Executing Node: generate_response_node ---")
    query = state.get('original_query', "An unspecified query")
    sql_results_str = state.get('sql_results_str', '')
    error = state.get('error')
    classification = state.get('classification')
    chart_available = state.get('chart_json') is not None

    # Check for shared resource availability
    if LLM is None and not error:
        return {"error": "LLM not configured", "final_response": "Error: LLM not available for response generation."}

    final_response = ""

    if error:
        logger.warning(f"Generating response based on detected error: {error}")
        error_str = str(error)
        # Simplified error formatting
        if "LLM not configured" in error_str or "Database engine not configured" in error_str:
             final_response = f"I'm sorry, I encountered an issue: {error_str}. Please check the backend configuration."
        elif "Failed to execute SQL" in error_str or "syntax error" in error_str.lower():
            final_response = f"I encountered an issue trying to retrieve the data. Perhaps try asking differently?"
        elif "Failed to generate SQL" in error_str:
             final_response = f"I had trouble understanding how to fetch the data. Could you please rephrase?"
        elif "Failed to classify query" in error_str:
             final_response = f"I had trouble understanding your request type. Could you clarify?"
        elif "Missing user query" in error_str or "metadata is unavailable" in error_str or "Schema metadata file not found" in error_str:
             final_response = f"There was an internal setup issue preventing me from processing your request."
        else: # Generic error
            final_response = f"I'm sorry, I encountered an issue processing your request. Please try again."

    elif classification == 'irrelevant':
         final_response = "This question doesn't seem related to your financial expenses. Could you ask something about your spending?"

    elif not error and (not sql_results_str or sql_results_str == "Query returned no results."):
         final_response = "I looked through your expense records based on your query, but couldn't find any matching transactions."

    elif not error and sql_results_str:
        logger.info("Generating summary response using PromptTemplate.")
        chart_mention = "I've also prepared a chart to visualize this." if chart_available else ""

        # --- Prompt Definition (Keep here for now, move later) ---
        template_string = """System: You are a friendly financial assistant summarizing financial data for users based in India.

Instructions:
* Answer the user's question ({user_query}) using the key information from the data below.
* Summarize findings/trends if data is tabular. State single numbers clearly. Do NOT just repeat the raw data.
* {chart_mention_instruction} Mention the chart briefly if applicable.
* Keep the tone conversational (use "You"/"Your"). Avoid jargon.
* IMPORTANT: Always use 'INR' (Indian Rupees) when referring to monetary values. Do NOT use '$' or other currency symbols.

Retrieved Data:
{sql_data}

Assistant: """
        prompt = PromptTemplate(
            template=template_string,
            input_variables=["user_query", "sql_data", "chart_mention_instruction"]
        )
        # --- End Prompt Definition ---

        chain = prompt | LLM

        try:
            input_dict = {
                "user_query": query,
                "sql_data": sql_results_str,
                "chart_mention_instruction": chart_mention
            }
            response = chain.invoke(input_dict)
            final_response = response.content.strip()
            logger.info("Successfully generated summary response from LLM.")

        except Exception as e:
            logger.error(f"LLM call failed during final response generation: {e}", exc_info=True)
            final_response = f"I retrieved the data:\n{sql_results_str}\nBut I had trouble summarizing it. Please note the currency is INR."

    else:
        logger.error("Reached end of generate_response_node without generating a response. State: %s", {k:v for k,v in state.items() if k != 'sql_results_list'})
        final_response = "I'm sorry, I wasn't able to determine a response for your query."

    if not final_response:
        logger.warning("Final response was empty after processing, providing default.")
        final_response = "I'm sorry, I couldn't process that request properly."

    return {"final_response": final_response}


# ==========================================================================
#                       EDGE LOGIC FUNCTION
# ==========================================================================

def should_continue(state: AgentState) -> str:
    """
    Determines the next node to execute based on the current state.
    """
    logger.info("--- Evaluating Edge: should_continue ---")
    classification = state.get('classification')
    error = state.get('error')

    if error:
        logger.warning(f"Error detected in state ('{error}'), routing directly to 'generate_response'.")
        return "generate_response"
    elif classification == 'irrelevant':
        logger.info("Classification is 'irrelevant', routing to 'generate_response'.")
        return "generate_response"
    elif classification in ['simple', 'advanced']:
        logger.info(f"Classification is '{classification}', routing to 'generate_sql'.")
        return "generate_sql"
    else:
        logger.error(f"Unknown or missing classification ('{classification}') in state. Routing to generate_response.")
        return "generate_response"

# ==========================================================================
#                       GRAPH DEFINITION
# ==========================================================================

logger.info("Defining LangGraph workflow structure...")
workflow = StateGraph(AgentState)
logger.debug("StateGraph initialized.")

# Add nodes using imported or locally defined functions
workflow.add_node("classify_query", classify_query_node) # Use imported function
workflow.add_node("generate_sql", generate_sql_node)     # Keep local for now
workflow.add_node("execute_sql", execute_sql_node)       # Keep local for now
workflow.add_node("generate_chart", generate_chart_node) # Keep local for now
workflow.add_node("generate_response", generate_response_node) # Keep local for now
logger.info("Nodes added to the graph.")

workflow.set_entry_point("classify_query")
logger.info("Graph entry point set to 'classify_query'.")

workflow.add_conditional_edges(
    source="classify_query",
    path=should_continue,
    path_map={
        "generate_sql": "generate_sql",
        "generate_response": "generate_response"
    }
)
logger.info("Conditional edge added from 'classify_query'.")

workflow.add_edge("generate_sql", "execute_sql")
workflow.add_edge("execute_sql", "generate_chart")
workflow.add_edge("generate_chart", "generate_response")
logger.info("Linear edges defined.")

workflow.add_edge("generate_response", END)
logger.info("Final edge added from 'generate_response' to END.")

# ==========================================================================
#                       Compile & Assign Entry Point Variable ('graph')
# ==========================================================================
graph = workflow.compile()
logger.info("LangGraph workflow compiled successfully. Runnable 'graph' object created.")

# Optional: Add a simple test execution block
if __name__ == "__main__":
    logger.info("--- Running Direct Script Test ---")
    # Ensure clients are initialized before running test
    if LLM is None or engine is None:
        logger.error("Cannot run direct test: LLM or Database Engine not initialized (imported as None).")
    else:
        test_queries = [
            "What was my total spend last month?",
            "Show my grocery expenses",
            "what is the weather?",
            "Compare spending between Anirban and Puspita for Rent",
        ]
        test_input = {"original_query": test_queries[0]}

        logger.info(f"Test Input: {test_input}")
        try:
            for output_chunk in graph.stream(test_input, {"recursion_limit": 10}):
                node_name = list(output_chunk.keys())[0]
                node_data = output_chunk[node_name]
                logger.info(f"--- Step Output: {node_name} ---")
                log_output = {k: (v[:100] + '...' if isinstance(v, str) and len(v) > 100 else v)
                              for k, v in node_data.items() if k != 'sql_results_list'}
                logger.info(f"{log_output}")
        except Exception as e:
            logger.error(f"Test execution failed: {e}", exc_info=True)

    logger.info("--- Direct Script Test Complete ---")