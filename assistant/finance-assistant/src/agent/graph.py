# assistant/finance-assistant/src/agent/graph.py
"""Define the graph for the finance assistant agent."""

import os
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from langchain_google_genai import ChatGoogleGenerativeAI # Use Gemini
from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.pydantic_v1 import BaseModel, Field # Not needed right now
from langgraph.graph import StateGraph, END
from sqlalchemy import create_engine, text           # For database interaction
from pathlib import Path
import logging
from dotenv import load_dotenv
from typing import List, Dict, Any
import yaml # To load the metadata YAML

# Import the AgentState definition from the state.py file in the same directory
from agent.state import AgentState

# --- Basic Configuration ---
# Configure logging for better visibility
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Use a specific logger for this module

# Load .env file from the *project root* (app-personal-finance/)
# Adjust the number of .parent calls based on the script's location
# src/agent/graph.py -> src/agent -> src -> finance-assistant -> assistant -> app-personal-finance
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logger.info(f"Loaded environment variables from: {env_path}")
else:
    logger.warning(f".env file not found at {env_path}. Relying on system environment variables.")

# --- Database Setup ---
# Construct the path relative to the project root
DB_PATH = project_root / "data" / "expenses.db"
if not DB_PATH.exists():
    logger.error(f"CRITICAL: DATABASE NOT FOUND at expected location: {DB_PATH}")
    raise FileNotFoundError(f"Database file not found at {DB_PATH}. Ensure data/expenses.db exists in the project root.")
DB_URI = f"sqlite:///{DB_PATH.resolve()}"
try:
    # connect_args might be needed for specific DB types or async operations later
    engine = create_engine(DB_URI) #, connect_args={"check_same_thread": False})
    logger.info(f"Database engine created for: {DB_URI}")
    # Simple connection test
    with engine.connect() as conn:
         logger.info("Database connection test successful.")
except Exception as e:
    logger.error(f"Failed to create database engine or connect: {e}", exc_info=True)
    raise # Stop execution if DB setup fails

# --- LLM Setup (Gemini) ---
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    logger.error("CRITICAL: GOOGLE_API_KEY not found in environment variables.")
    raise ValueError("GOOGLE_API_KEY environment variable must be set in the .env file.")

try:
    # Initialize Gemini LLM - Using flash for speed/cost
    LLM = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-latest",
        # model="gemini-2.0-flash-thinking-exp-01-21",
        google_api_key=google_api_key,
        temperature=0.1, # Lower temperature for more deterministic tasks initially
        convert_system_message_to_human=True # Important for Gemini compatibility
    )
    logger.info("ChatGoogleGenerativeAI model initialized (gemini-1.5-flash-latest).")
    # logger.info("ChatGoogleGenerativeAI model initialized (gemini-2.0-flash-thinking-exp-01-21).")
except Exception as e:
    logger.error(f"Failed to initialize ChatGoogleGenerativeAI: {e}", exc_info=True)
    raise # Stop execution if LLM setup fails

# --- Metadata Loading ---
# Load the detailed metadata YAML file
metadata_path = project_root / "metadata" / "expenses_metadata_detailed.yaml"
SCHEMA_METADATA = "" # Initialize as empty string
try:
    if metadata_path.exists():
        with open(metadata_path, 'r', encoding='utf-8') as f:
            # Load the YAML content - consider formatting it for the prompt
            metadata_content = yaml.safe_load(f)
            # Basic string conversion - could be refined for better LLM digestion
            SCHEMA_METADATA = json.dumps(metadata_content, indent=2)
            logger.info(f"Successfully loaded metadata from {metadata_path}")
    else:
        logger.warning(f"Metadata file not found at {metadata_path}. SQL generation accuracy may be reduced.")
        # Provide a minimal fallback schema description if file is missing
        SCHEMA_METADATA = """
         Fallback Schema:
         Table: expenses
         Columns: id(TEXT PK), date(DATE 'YYYY-MM-DD'), year(INT), month(TEXT 'YYYY-MM'), week(TEXT 'YYYY-Www'), day_of_week(TEXT), account(TEXT), category(TEXT), sub_category(TEXT), type(TEXT), user(TEXT 'Anirban'|'Puspita'), amount(REAL INR).
         """
except Exception as e:
    logger.error(f"Failed to load or parse metadata YAML: {e}", exc_info=True)
    # Proceed with fallback schema or raise error depending on desired robustness
    SCHEMA_METADATA = """
     Fallback Schema: Table: expenses. Columns: id, date, year, month, week, day_of_week, account, category, sub_category, type, user, amount.
     """


# ==========================================================================
#                       NODE FUNCTIONS Will Go Here
# ==========================================================================
def classify_query_node(state: AgentState) -> dict:
    """
    Classifies the user's original query into 'simple', 'advanced', or 'irrelevant'.

    Args:
        state (AgentState): The current state of the graph. Must contain 'original_query'.

    Returns:
        dict: A dictionary containing the 'classification' key with the determined category,
              or an 'error' key if classification fails.
    """
    logger.info("--- Executing Node: classify_query_node ---")
    query = state.get('original_query') # Use .get() for safety

    if not query:
        logger.error("Original query is missing in state for classification.")
        # Return error and default classification
        return {"error": "Missing user query.", "classification": "irrelevant"}

    logger.debug(f"Classifying query: '{query}'")

    # Define the prompt for the classification task
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Your primary task is to classify user questions about personal finance data into one of three categories. Respond ONLY with a single word: 'simple', 'advanced', or 'irrelevant'.

Definitions:
- simple: Directly answerable with a standard SQL query on the 'expenses' table. Examples: totals, averages, filtering by date/category/user, specific lookups like 'What was my total spend last month?', 'Show my grocery expenses in Jan 2024', 'List expenses over 1000 INR'.
- advanced: Requires complex analysis beyond direct SQL (e.g., forecasting, prediction, anomaly detection, clustering, complex multi-step calculations). Examples: 'Predict my spending next week', 'Cluster my spending habits', 'Find unusual spending patterns'. FOR THIS INITIAL IMPLEMENTATION, TREAT 'advanced' THE SAME AS 'simple' downstream (proceed to SQL generation).
- irrelevant: Unrelated to the user's personal finance data stored in the expenses table. Examples: 'What is the weather like?', 'Who won the game?', 'General knowledge questions'.
"""),
        # Explicitly tell the LLM what to do with the user's query
        ("user", f"Classify the following user query: {query}")
    ])

    # Create the chain: Prompt -> LLM
    chain = prompt | LLM

    try:
        # Invoke the LLM
        response = chain.invoke({}) # Provide empty input as context is in the prompt
        # Clean the LLM response: lower case, remove extra characters/whitespace
        classification = response.content.strip().lower().replace("'", "").replace('"', '').replace(".", "")
        logger.info(f"Gemini raw classification response: '{response.content}' -> Cleaned: '{classification}'")

        # Validate the classification output
        valid_classifications = ['simple', 'advanced', 'irrelevant']
        if classification not in valid_classifications:
            logger.warning(f"LLM returned an unexpected classification: '{classification}'. Defaulting to 'simple'.")
            # Fallback to a safe default if the LLM response is malformed
            classification = 'simple'

    except Exception as e:
        logger.error(f"LLM call failed during query classification for query '{query}': {e}", exc_info=True)
        # If the LLM call fails, set an error and default classification
        return {"error": f"Failed to classify query due to LLM error: {e}", "classification": "simple"}

    # Return the classification in the expected dictionary format to update the state
    return {"classification": classification}

def generate_sql_node(state: AgentState) -> dict:
    """
    Generates an SQLite query based on the user's original query and schema metadata.
    Uses prompt variables to safely inject schema and query.

    Args:
        state (AgentState): The current state graph. Must contain 'original_query'.
                           Uses the pre-loaded SCHEMA_METADATA constant.

    Returns:
        dict: A dictionary containing the 'sql_query' key with the generated query string,
              or an 'error' key if SQL generation fails.
    """
    logger.info("--- Executing Node: generate_sql_node ---")
    query = state.get('original_query')

    if state.get('error'):
         logger.warning(f"Skipping SQL generation due to previous error: {state['error']}")
         return {}
    if not query:
        logger.error("Original query is missing in state for SQL generation.")
        return {"error": "Missing user query.", "sql_query": None}

    logger.debug(f"Generating SQL for query: '{query}'")

    if not SCHEMA_METADATA:
        logger.error("Schema metadata (SCHEMA_METADATA) is empty or was not loaded.")
        return {"error": "Database schema metadata is unavailable.", "sql_query": None}

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
    # --- Add logging to check prompt variables ---
    logger.debug(f"Prompt expected input variables: {prompt.input_variables}")

    chain = prompt | LLM

    try:
        # Prepare the input dictionary with keys matching the template variables
        input_data = {"schema_info": SCHEMA_METADATA, "user_query": query}

        # --- Add logging to show the exact data being passed ---
        logger.debug(f"Invoking SQL generation chain with input_data keys: {list(input_data.keys())}")
        logger.debug(f"Value for 'user_query' (first 50 chars): {str(input_data.get('user_query', 'MISSING'))[:50]}")
        logger.debug(f"Value for 'schema_info' present: {bool(input_data.get('schema_info'))}")

        # Invoke the chain directly with the dictionary containing the required keys
        response = chain.invoke(input_data)

        sql_query = response.content.strip().replace("```sql", "").replace("```", "").strip()
        if sql_query.endswith(';'):
            sql_query = sql_query[:-1].strip()

        logger.info(f"Gemini raw SQL response: '{response.content}' -> Cleaned: '{sql_query}'")

        if not sql_query or not sql_query.lower().startswith("select"):
             logger.error(f"Generated query is empty or does not start with SELECT: '{sql_query}'")
             return {"error": "Failed to generate a valid SELECT query.", "sql_query": sql_query or "Empty response"}

    except KeyError as e:
        # More specific logging for KeyError during invoke
        logger.error(f"KeyError during chain invocation in SQL generation. This usually means the input dict didn't match prompt variables. Error: {e}", exc_info=True)
        return {"error": f"Internal error matching input to prompt variables: {e}"}
    except Exception as e:
        logger.error(f"LLM call failed during SQL generation for query '{query}': {e}", exc_info=True)
        return {"error": f"Failed to generate SQL query due to LLM error: {e}", "sql_query": None}

    return {"sql_query": sql_query}

def execute_sql_node(state: AgentState) -> dict:
    """
    Executes the generated SQL query against the SQLite database using SQLAlchemy.
    Returns results as a string and a serializable list of dictionaries.

    Args:
        state (AgentState): The current graph state. Must contain 'sql_query' if no prior error.

    Returns:
        dict: A dictionary containing 'sql_results_list' (List[Dict]) and
              'sql_results_str' (string representation), or an 'error' key if execution fails.
    """
    logger.info("--- Executing Node: execute_sql_node ---")
    sql_query = state.get('sql_query')

    if state.get('error'):
        logger.warning(f"Skipping SQL execution due to previous error: {state['error']}")
        # Ensure results state fields are appropriately empty/error-indicating
        return {"sql_results_list": [], "sql_results_str": f"Error: {state['error']}"}
    if not sql_query:
        logger.error("No SQL query found in state to execute.")
        return {"error": "SQL query generation failed or was missing.", "sql_results_list": [], "sql_results_str": "Error: No SQL query found."}

    logger.info(f"Attempting to execute SQL query: [{sql_query}]")
    try:
        with engine.connect() as connection:
            df = pd.read_sql(sql=text(sql_query), con=connection)
        logger.info(f"SQL query executed successfully. Number of rows returned: {len(df)}")

        results_list: List[Dict[str, Any]] = [] # Initialize as empty list
        results_str: str = ""                   # Initialize as empty string

        if not df.empty:
            # Format data (optional but good) - Same logic as before
            for col in df.columns:
                if 'date' in col.lower():
                    try: df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d')
                    except Exception: pass # Ignore formatting errors
                elif 'amount' in col.lower() and pd.api.types.is_numeric_dtype(df[col]):
                    try: df[col] = df[col].round(2)
                    except Exception: pass # Ignore formatting errors

            results_list = df.to_dict('records') # Convert DataFrame to list of dictionaries
            results_str = df.to_string(index=False, na_rep='<NA>') # Create string version
        else:
            results_list = [] # Explicitly set to empty list
            results_str = "Query returned no results."

        return {"sql_results_list": results_list, "sql_results_str": results_str}

    except Exception as e:
        logger.error(f"SQL execution failed for query [{sql_query}]: {e}", exc_info=True)
        error_msg = f"Failed to execute SQL query. Error: {e}. Query Attempted: [{sql_query}]"
        return {"error": error_msg, "sql_results_list": [], "sql_results_str": f"Error executing SQL."}

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
    logger.info("--- Executing Node: generate_chart_node ---")
    # --- MODIFICATION: Get list instead of df ---
    results_list = state.get('sql_results_list')
    # --- END MODIFICATION ---
    error = state.get('error')
    query = state.get('original_query', 'Unknown query')

    # Pre-checks
    if error:
        logger.warning(f"Skipping chart generation due to previous error: {error}")
        return {"chart_json": None}
    if results_list is None: # Check if None (might happen if execute_sql had severe issue before returning)
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


        # --- Chart Generation Logic (using df) ---
        fig = None
        num_rows, num_cols = df.shape
        col_names_lower = df.columns.str.lower()

        numeric_cols = [
            col for col in df.columns
            if pd.api.types.is_numeric_dtype(df[col])
            and col.lower() not in ['id', 'year']
        ]
        logger.debug(f"Identified numeric columns for plotting: {numeric_cols}")

        date_col_present = 'date' in col_names_lower or 'month' in col_names_lower or 'yearmonth' in col_names_lower
        if date_col_present and len(numeric_cols) == 1:
            if 'date' in col_names_lower: time_col = df.columns[col_names_lower.tolist().index('date')]
            elif 'month' in col_names_lower: time_col = df.columns[col_names_lower.tolist().index('month')]
            else: time_col = df.columns[col_names_lower.tolist().index('yearmonth')]
            value_col = numeric_cols[0]
            logger.info(f"Attempting Line Chart: X='{time_col}', Y='{value_col}'")
            try:
                # Attempt conversion to datetime for robust sorting, handle failure gracefully
                try:
                    df[time_col] = pd.to_datetime(df[time_col])
                except Exception as time_conv_err:
                    logger.warning(f"Could not convert time column '{time_col}' to datetime: {time_conv_err}. Sorting may be string-based.")

                df_sorted = df.sort_values(by=time_col)
                fig = px.line(df_sorted, x=time_col, y=value_col, title=f"{value_col.capitalize()} Trend", markers=True)
                fig.update_layout(xaxis_title=time_col.capitalize(), yaxis_title=value_col.capitalize())
            except TypeError as sort_err:
                 logger.warning(f"TypeError during sorting/plotting line chart (column '{time_col}' might not be sortable): {sort_err}. Skipping line chart.")
            except Exception as line_err:
                 logger.warning(f"Could not generate line chart: {line_err}. Skipping line chart.")

        elif num_cols == 2 and len(numeric_cols) == 1:
            value_col = numeric_cols[0]
            cat_col = next((col for col in df.columns if col != value_col), None)
            if cat_col:
                logger.info(f"Attempting Bar Chart: Category='{cat_col}', Value='{value_col}'")
                try:
                    max_bars = 15
                    df_agg = df.sort_values(by=value_col, ascending=False)
                    df_chart = df_agg.head(max_bars)
                    title_suffix = f" (Top {max_bars})" if len(df_agg) > max_bars else ""
                    title = f"{value_col.capitalize()} by {cat_col.capitalize()}{title_suffix}"
                    fig = px.bar(df_chart, x=cat_col, y=value_col, title=title, text_auto='.2s')
                    fig.update_traces(textangle=0, textposition="outside")
                    fig.update_layout(xaxis_title=cat_col.capitalize(), yaxis_title=value_col.capitalize())
                except Exception as bar_err:
                    logger.warning(f"Could not generate bar chart: {bar_err}. Skipping bar chart.")
            else:
                logger.warning("Bar chart condition met but failed to identify categorical column.")

        elif num_rows == 1 and len(numeric_cols) == 1:
            logger.info("Single numeric value result. Skipping graphical chart generation.")
            return {"chart_json": None}

        if fig is None:
            logger.info("No specific chart type matched heuristics. Skipping chart generation.")
            return {"chart_json": None}

        fig.update_layout(
            margin=dict(l=40, r=20, t=60, b=40),
            title_x=0.5,
            legend_title_text=None
        )
        chart_json = fig.to_json()
        logger.info("Plotly chart JSON generated successfully.")
        return {"chart_json": chart_json}

    except Exception as e:
        logger.error(f"Unexpected error during chart generation: {e}", exc_info=True)
        return {"chart_json": None}


# Import PromptTemplate if not already imported at the top
from langchain_core.prompts import PromptTemplate # Or keep ChatPromptTemplate

def generate_response_node(state: AgentState) -> dict:
    """
    Generates the final natural language response. Uses PromptTemplate.
    Instructs the LLM to use INR as the currency.

    Args:
        state (AgentState): The current graph state. Needs 'original_query'.
                           Uses 'sql_results_str', 'error', 'classification',
                           and checks for 'chart_json'.

    Returns:
        dict: A dictionary containing the 'final_response' string.
    """
    logger.info("--- Executing Node: generate_response_node ---")
    query = state.get('original_query', "An unspecified query")
    # Use the potentially empty list from state if needed, but string is primary for summary
    sql_results_str = state.get('sql_results_str', '') # Use the string representation
    error = state.get('error')
    classification = state.get('classification')
    chart_available = state.get('chart_json') is not None

    final_response = ""

    # 1. Prioritize responding to errors
    if error:
        logger.warning(f"Generating response based on detected error: {error}")
        error_str = str(error)
        # Simple error mapping
        if "Failed to execute SQL" in error_str or "syntax error" in error_str.lower():
            final_response = f"I encountered an issue trying to retrieve the data ({error_str}). Perhaps try asking differently?"
        elif "Failed to generate SQL" in error_str:
             final_response = f"I had trouble understanding how to fetch the data ({error_str}). Could you please rephrase?"
        elif "Failed to classify query" in error_str:
             final_response = f"I had trouble understanding your request type ({error_str}). Could you clarify?"
        elif "Missing user query" in error_str or "metadata is unavailable" in error_str:
             final_response = f"There was an internal setup issue preventing me from processing your request: {error_str}"
        else: # Generic error
            final_response = f"I'm sorry, I encountered an issue: {error_str}. Please try again."

    # 2. Handle irrelevant classification
    elif classification == 'irrelevant':
         final_response = "This question doesn't seem related to your financial expenses. Could you ask something about your spending?"
         logger.info("Generated response for 'irrelevant' classification.")

    # 3. Handle no results (Check both empty string and specific message)
    elif not error and (not sql_results_str or sql_results_str == "Query returned no results."):
         final_response = "I looked through your expense records based on your query, but couldn't find any matching transactions."
         logger.info("Generated response for query with no results.")

    # 4. Generate a summary response based on successful SQL results
    elif not error and sql_results_str:
        logger.info("Generating summary response using PromptTemplate.")
        chart_mention = "I've also prepared a chart to visualize this." if chart_available else ""

        # --- MODIFICATION START: Added currency instruction ---
        template_string = """System: You are a friendly financial assistant summarizing financial data for users based in India.

Instructions:
*   Answer the user's question ({user_query}) using the key information from the data below.
*   Summarize findings/trends if data is tabular. State single numbers clearly. Do NOT just repeat the raw data.
*   {chart_mention_instruction} Mention the chart briefly if applicable.
*   Keep the tone conversational (use "You"/"Your"). Avoid jargon.
*   IMPORTANT: Always use 'INR' (Indian Rupees) when referring to monetary values. Do NOT use '$' or other currency symbols.

Retrieved Data:
{sql_data}

Assistant: """
        # --- MODIFICATION END ---

        prompt = PromptTemplate(
            template=template_string,
            input_variables=["user_query", "sql_data", "chart_mention_instruction"]
        )

        chain = prompt | LLM

        try:
            if LLM is None: raise ValueError("LLM client is not initialized.")

            input_dict = {
                "user_query": query,
                "sql_data": sql_results_str, # Pass the string representation
                "chart_mention_instruction": chart_mention
            }

            response = chain.invoke(input_dict)
            final_response = response.content.strip()
            logger.info("Successfully generated summary response from LLM.")

        except Exception as e:
            logger.error(f"LLM call failed during final response generation: {e}", exc_info=True)
            final_response = f"I retrieved the data:\n{sql_results_str}\nBut I had trouble summarizing it. Please note the currency is INR." # Add fallback currency note

    # 5. Fallback
    else:
        logger.error("Reached end of generate_response_node without generating a response. State: %s", {k:v for k,v in state.items() if k != 'sql_results_list'}) # Log state excluding list
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
    Determines the next node to execute based on the current state,
    specifically the query classification or presence of errors.

    Args:
        state (AgentState): The current graph state.

    Returns:
        str: The name of the next node to call ('generate_sql', 'generate_response'),
             or potentially END (though current logic routes errors to response).
    """
    logger.info("--- Evaluating Edge: should_continue ---")
    classification = state.get('classification')
    error = state.get('error') # Check if ANY previous node set an error

    # Priority 1: Handle errors immediately by routing to final response generation
    # The generate_response_node is responsible for formatting the error message.
    if error:
        logger.warning(f"Error detected in state ('{error}'), routing directly to 'generate_response'.")
        return "generate_response"

    # Priority 2: Handle irrelevant classification
    elif classification == 'irrelevant':
        logger.info("Classification is 'irrelevant', routing to 'generate_response'.")
        return "generate_response"

    # Priority 3: Proceed with data retrieval for simple/advanced queries
    elif classification in ['simple', 'advanced']:
        logger.info(f"Classification is '{classification}', routing to 'generate_sql'.")
        return "generate_sql"

    # Fallback: This case indicates an issue, likely with the classification node.
    # Route to response node to report the internal issue.
    else:
        logger.error(f"Unknown or missing classification ('{classification}') in state. Routing to generate_response.")
        # We don't set the error here, let generate_response handle the lack of valid path.
        # Alternatively, could set state['error'] = "Internal classification error" here.
        return "generate_response"

# ==========================================================================
#                       GRAPH DEFINITION
# ==========================================================================

logger.info("Defining LangGraph workflow structure...")

# Initialize the state graph with our AgentState definition
workflow = StateGraph(AgentState)
logger.debug("StateGraph initialized.")

# Add the nodes to the graph, associating a name with each function
workflow.add_node("classify_query", classify_query_node)
workflow.add_node("generate_sql", generate_sql_node)
workflow.add_node("execute_sql", execute_sql_node)
workflow.add_node("generate_chart", generate_chart_node)
workflow.add_node("generate_response", generate_response_node)
logger.info("Nodes added to the graph: classify_query, generate_sql, execute_sql, generate_chart, generate_response")

# Define the entry point of the graph
workflow.set_entry_point("classify_query")
logger.info("Graph entry point set to 'classify_query'.")

# Define the conditional edge after the classification node.
# The 'should_continue' function will determine which node to go to next.
workflow.add_conditional_edges(
    source="classify_query",  # keyword: source
    path=should_continue,     # keyword: path
    path_map={                # keyword: path_map
        "generate_sql": "generate_sql",
        "generate_response": "generate_response"
    }
)
logger.info("Conditional edge added from 'classify_query' based on 'should_continue' logic.")

# Define the linear flow for the main data processing path
# Connect nodes sequentially after the conditional split directs to 'generate_sql'
workflow.add_edge("generate_sql", "execute_sql")
workflow.add_edge("execute_sql", "generate_chart")
workflow.add_edge("generate_chart", "generate_response")
logger.info("Linear edges defined: generate_sql -> execute_sql -> generate_chart -> generate_response.")

# Define the final step: after generating the response, the graph ends.
workflow.add_edge("generate_response", END) # END is a special marker from langgraph.graph
logger.info("Final edge added from 'generate_response' to END.")

# ==========================================================================
#                       Compile & Assign Entry Point Variable ('graph')
# ==========================================================================

# Compile the workflow into a runnable application object
# The compiled object MUST be assigned to the variable name 'graph'
# as defined in langgraph.json
graph = workflow.compile()
logger.info("LangGraph workflow compiled successfully. Runnable 'graph' object created.")

# Optional: Add a simple test execution block (useful during development)
# This will only run if you execute graph.py directly (python src/agent/graph.py)
if __name__ == "__main__":
    logger.info("--- Running Direct Script Test ---")
    # Example test invocation (replace with relevant queries)
    test_queries = [
        "What was my total spend last month?",
        "Show my grocery expenses",
        "what is the weather?",
        "Compare spending between Anirban and Puspita for Rent",
        "Generate a query with syntax error deliberately" # Example for testing error path
    ]
    test_input = {"original_query": test_queries[0]} # Change index to test different queries

    logger.info(f"Test Input: {test_input}")
    try:
        # Use stream to see the steps
        for output_chunk in graph.stream(test_input, {"recursion_limit": 10}):
            # output is a dictionary where keys are node names, values are output dicts
            node_name = list(output_chunk.keys())[0]
            node_data = output_chunk[node_name]
            logger.info(f"--- Step Output: {node_name} ---")
            # Log relevant parts of the node output (avoid printing large dataframes directly)
            log_output = {k: (v[:100] + '...' if isinstance(v, str) and len(v) > 100 else v)
                          for k, v in node_data.items() if k != 'sql_results_df'} # Exclude df for brevity
            logger.info(f"{log_output}")

        # Optionally invoke again to get final state easily (can be large)
        # final_state = graph.invoke(test_input, {"recursion_limit": 10})
        # logger.info(f"--- Final State ---")
        # logger.info(json.dumps(final_state, indent=2, default=str)) # Use default=str for non-serializable like DataFrame

    except Exception as e:
        logger.error(f"Test execution failed: {e}", exc_info=True)

    logger.info("--- Direct Script Test Complete ---")