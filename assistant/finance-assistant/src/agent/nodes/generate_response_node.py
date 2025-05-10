# assistant/finance-assistant/src/agent/nodes/generate_response_node.py
"""
Node function to generate the final natural language response.
Loads its prompt from a YAML file.
Imports shared LLM.
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, Optional, Any, List

from langchain_core.prompts import PromptTemplate

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
    from agent.shared_clients import LLM
except ImportError:
    logging.error("Could not import 'LLM' from agent.shared_clients. Using fallback None.")
    LLM = None
except Exception as e:
     logging.error(f"Unexpected error importing 'LLM': {e}", exc_info=True)
     LLM = None


# Configure logging for this node
logger = logging.getLogger(__name__)

# Define the path to the prompt file relative to this file's parent directory
PROMPT_FILE_PATH = Path(__file__).parent.parent / "prompts" / "generate_response_prompt.yaml"

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


def generate_response_node(state: AgentState) -> dict:
    """
    Generates the final natural language response based on the state.
    Uses shared LLM imported from shared_clients.
    Loads prompt from YAML.
    Instructs the LLM to use INR as the currency.

    Args:
        state (AgentState): The current graph state. Needs 'original_query'.
                           Uses 'sql_results_str', 'error', 'classification',
                           and checks for 'chart_json'.

    Returns:
        dict: A dictionary containing the 'final_response' string.
    """
    logger.info("--- Executing Node: generate_response_node (Modularized) ---")
    query = state.get('original_query', "An unspecified query")
    sql_results_str = state.get('sql_results_str', '') # Use the string representation
    error = state.get('error')
    classification = state.get('classification')
    chart_available = state.get('chart_json') is not None

    # Check for shared resource availability (LLM)
    if LLM is None and not error: # Only fail if no error AND LLM is missing
        logger.error("LLM not available for response generation.")
        return {"error": "LLM not configured", "final_response": "Error: LLM not available for response generation."}

    final_response = ""

    # --- Handle Error Cases First ---
    if error:
        logger.warning(f"Generating response based on detected error: {error}")
        error_str = str(error)
        # Simplify error messages shown to user
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
        else: # Generic error fallback
            final_response = f"I'm sorry, I encountered an issue processing your request. Please try again."
        logger.info(f"Generated error response: '{final_response}'")

    # --- Handle Non-Error Cases ---
    elif classification == 'irrelevant':
         final_response = "This question doesn't seem related to your financial expenses. Could you ask something about your spending?"
         logger.info("Generated response for 'irrelevant' classification.")

    elif not error and (not sql_results_str or sql_results_str == "Query returned no results."):
         final_response = "I looked through your expense records based on your query, but couldn't find any matching transactions."
         logger.info("Generated response for query with no results.")

    elif not error and sql_results_str:
        logger.info("Generating summary response using PromptTemplate from YAML.")
        chart_mention = "I've also prepared a chart to visualize this." if chart_available else ""

        # --- Load Prompt from YAML ---
        template_string = load_prompt_template_from_yaml(PROMPT_FILE_PATH)
        if template_string is None:
            error_msg = f"Failed to load response generation prompt template from {PROMPT_FILE_PATH}"
            logger.error(error_msg)
            # Fallback response if prompt loading fails
            final_response = f"I retrieved the data:\n{sql_results_str}\nBut had an internal issue generating the summary. Currency is INR."
            return {"final_response": final_response} # Exit early

        prompt = PromptTemplate(
            template=template_string,
            input_variables=["user_query", "sql_data", "chart_mention_instruction"]
        )
        # --- End Prompt Loading ---

        chain = prompt | LLM # Assumes LLM is initialized

        try:
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
            # Provide fallback response mentioning data retrieved but summarization failed
            final_response = f"I retrieved the data:\n{sql_results_str}\nBut I had trouble summarizing it. Please note the currency is INR."

    else:
        # This case should ideally not be reached if logic is correct
        logger.error("Reached end of generate_response_node without generating a response under expected conditions. State: %s", {k:v for k,v in state.items() if k not in ['sql_results_list', 'sql_results_df']}) # Exclude potentially large/complex items from log
        final_response = "I'm sorry, I wasn't able to determine a response for your query."

    # Final check if response is empty for some reason
    if not final_response:
        logger.warning("Final response was empty after processing, providing default.")
        final_response = "I'm sorry, I couldn't process that request properly."

    # Return final response state update
    return {"final_response": final_response}