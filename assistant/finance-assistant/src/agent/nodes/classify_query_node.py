# src/agent/nodes/classify_query_node.py
"""
Node function to classify the user's query.
Loads its prompt from a YAML file.
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, Optional

from langchain_core.prompts import ChatPromptTemplate
from agent.state import AgentState

# --- TEMP: Import LLM directly from graph.py ---
# This assumes LLM is defined globally in graph.py.
# A better approach (dependency injection) might be implemented later.
try:
    from agent.graph import LLM
except ImportError:
    LLM = None # Set LLM to None if import fails
    logging.error("Could not import LLM directly from agent.graph. Ensure it's defined there.")
# --- END TEMP ---

# Configure logging for this node
logger = logging.getLogger(__name__)

# Define the path to the prompt file relative to this file
PROMPT_FILE_PATH = Path(__file__).parent.parent / "prompts" / "classify_query_prompt.yaml"

def load_prompt_content_from_yaml(file_path: Path, key: str) -> Optional[str]:
    """Loads specific string content from a key in a YAML file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            if isinstance(data, dict) and key in data:
                content = data[key]
                if isinstance(content, str):
                    logger.debug(f"Content for key '{key}' loaded successfully from {file_path}")
                    return content
                else:
                    logger.error(f"Key '{key}' in {file_path} does not contain a string.")
                    return None
            else:
                logger.error(f"Invalid YAML structure or key '{key}' not found in {file_path}.")
                return None
    except FileNotFoundError:
        logger.error(f"Prompt file not found: {file_path}")
        return None
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {file_path}: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading prompt from {file_path}: {e}", exc_info=True)
        return None

def classify_query_node(state: AgentState) -> dict:
    """
    Classifies the user's original query into 'simple', 'advanced', or 'irrelevant'.
    Loads its system prompt from classify_query_prompt.yaml.

    Args:
        state (AgentState): The current state of the graph. Must contain 'original_query'.

    Returns:
        dict: A dictionary containing the 'classification' key with the determined category,
              or an 'error' key if classification fails.
    """
    logger.info("--- Executing Node: classify_query_node ---")
    query = state.get('original_query')

    # Check if LLM was imported/initialized successfully
    if LLM is None:
        logger.error("LLM instance is not available for classification.")
        # Return error state immediately if LLM is missing
        return {"error": "LLM not configured", "classification": "simple"}

    if not query:
        logger.error("Original query is missing in state for classification.")
        return {"error": "Missing user query.", "classification": "irrelevant"}

    # --- Load System Prompt from YAML ---
    system_prompt_content = load_prompt_content_from_yaml(PROMPT_FILE_PATH, 'system_prompt')

    if system_prompt_content is None:
        # Handle error loading prompt (e.g., return error state)
        error_msg = f"Failed to load system prompt from {PROMPT_FILE_PATH}"
        logger.error(error_msg)
        # Default classification on error, include specific error message
        return {"error": error_msg, "classification": "simple"}

    logger.debug(f"Classifying query: '{query}' using loaded system prompt.")

    # --- Construct the prompt using the loaded system message ---
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_content),
        # Keep the user message dynamic, passing the query from the state
        ("user", "Classify the following user query: {user_query}")
    ])

    # Define the input for the chain based on the prompt template variables
    chain_input = {"user_query": query}

    # Create the chain: Prompt -> LLM
    chain = prompt | LLM

    try:
        # Invoke the LLM
        response = chain.invoke(chain_input)
        # Clean the LLM response
        classification = response.content.strip().lower().replace("'", "").replace('"', '').replace(".", "")
        logger.info(f"Gemini raw classification response: '{response.content}' -> Cleaned: '{classification}'")

        # Validate the classification output
        valid_classifications = ['simple', 'advanced', 'irrelevant']
        if classification not in valid_classifications:
            logger.warning(f"LLM returned an unexpected classification: '{classification}'. Defaulting to 'simple'.")
            classification = 'simple'

    except Exception as e:
        logger.error(f"LLM call failed during query classification for query '{query}': {e}", exc_info=True)
        return {"error": f"Failed to classify query due to LLM error: {e}", "classification": "simple"}

    # Return the classification
    return {"classification": classification}
