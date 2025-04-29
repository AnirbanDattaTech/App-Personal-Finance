# assistant/finance-assistant/src/agent/nodes/generate_sql_node.py
"""
Node function to generate the SQL query.
Loads its prompt from a YAML file.
Imports shared LLM and Schema Metadata.
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, Optional, Any

from langchain_core.prompts import ChatPromptTemplate

# --- Import Agent State ---
try:
    from agent.state import AgentState
except ImportError:
    # Fallback for potential direct execution or import issues
    logging.error("Failed to import AgentState from agent.state. Defining fallback.")
    from typing import TypedDict, List
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
    from agent.shared_clients import LLM, SCHEMA_METADATA
except ImportError:
    logging.error("Could not import LLM or SCHEMA_METADATA from agent.shared_clients. Using fallback None.")
    LLM = None
    SCHEMA_METADATA = None # Or provide a minimal fallback schema if needed

# Configure logging for this node
logger = logging.getLogger(__name__)

# Define the path to the prompt file relative to this file's parent directory
PROMPT_FILE_PATH = Path(__file__).parent.parent / "prompts" / "generate_sql_prompt.yaml"

def load_prompt_template_from_yaml(file_path: Path) -> Optional[str]:
    """Loads the template string from a YAML file."""
    if not file_path.is_file():
        logger.error(f"Prompt file not found: {file_path}")
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            prompt_data = yaml.safe_load(f)
            # Assuming a simple structure like { 'template': '...' }
            if isinstance(prompt_data, dict) and 'template' in prompt_data:
                 template_str = prompt_data['template']
                 if isinstance(template_str, str):
                     logger.debug(f"Prompt template loaded successfully from {file_path}")
                     return template_str
                 else:
                     logger.error(f"'template' key in {file_path} does not contain a string.")
                     return None
            # If the YAML just contains the string directly
            elif isinstance(prompt_data, str):
                 logger.debug(f"Prompt template loaded directly as string from {file_path}")
                 return prompt_data
            else:
                logger.error(f"Invalid prompt file format in {file_path}. Expected dict with 'template' key or direct string.")
                return None
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML prompt file {file_path}: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading prompt template from {file_path}: {e}", exc_info=True)
        return None

def generate_sql_node(state: AgentState) -> dict:
    """
    Generates an SQLite query based on the user's original query and schema metadata.
    Uses shared LLM and SCHEMA_METADATA imported from shared_clients.
    Loads prompt from YAML.
    """
    logger.info("--- Executing Node: generate_sql_node (Modularized) ---")
    query = state.get('original_query')

    # Check for shared resource availability
    if LLM is None:
        logger.error("LLM not available for SQL generation.")
        return {"error": "LLM not configured", "sql_query": None}
    if SCHEMA_METADATA is None:
        logger.error("Schema Metadata not available for SQL generation.")
        # Provide a fallback schema if needed, or return error
        # SCHEMA_METADATA = "Fallback Schema: ..."
        return {"error": "Schema metadata unavailable.", "sql_query": None}
    elif "Fallback Schema" in SCHEMA_METADATA: # Check if using fallback
         logger.warning("Using fallback schema metadata for SQL generation.")


    if state.get('error'):
         logger.warning(f"Skipping SQL generation due to previous error: {state['error']}")
         # Return empty dict to avoid overwriting existing error
         return {}
    if not query:
        logger.error("Original query is missing in state for SQL generation.")
        return {"error": "Missing user query.", "sql_query": None}

    logger.debug(f"Generating SQL for query: '{query}'")

    # --- Load Prompt from YAML ---
    template_string = load_prompt_template_from_yaml(PROMPT_FILE_PATH)
    if template_string is None:
        error_msg = f"Failed to load SQL generation prompt template from {PROMPT_FILE_PATH}"
        logger.error(error_msg)
        return {"error": error_msg, "sql_query": None}

    prompt = ChatPromptTemplate.from_template(template_string)
    # --- End Prompt Loading ---

    chain = prompt | LLM

    try:
        input_data = {"schema_info": SCHEMA_METADATA, "user_query": query}
        response = chain.invoke(input_data)
        # Clean the LLM response
        sql_query = response.content.strip().replace("```sql", "").replace("```", "").strip()
        if sql_query.endswith(';'):
            sql_query = sql_query[:-1].strip() # Remove trailing semicolon
        logger.info(f"LLM raw SQL response: '{response.content}' -> Cleaned: '{sql_query}'")

        # Basic validation
        if not sql_query or not sql_query.lower().startswith("select"):
             logger.error(f"Generated query is empty or does not start with SELECT: '{sql_query}'")
             # Return potentially problematic query with error
             return {"error": "Failed to generate a valid SELECT query.", "sql_query": sql_query or "Empty response"}

    except KeyError as e:
        logger.error(f"KeyError during chain invocation in SQL generation. Check prompt variables vs input dict. Error: {e}", exc_info=True)
        return {"error": f"Internal error matching input to prompt variables: {e}", "sql_query": None}
    except Exception as e:
        logger.error(f"LLM call failed during SQL generation for query '{query}': {e}", exc_info=True)
        return {"error": f"Failed to generate SQL query due to LLM error: {e}", "sql_query": None}

    # Return success state
    return {"sql_query": sql_query}