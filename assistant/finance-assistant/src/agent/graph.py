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
from agent.nodes.generate_sql_node import generate_sql_node
from agent.nodes.execute_sql_node import execute_sql_node
from agent.nodes.generate_chart_node import generate_chart_node
from agent.nodes.generate_response_node import generate_response_node

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==========================================================================
#                       NODE FUNCTIONS (Remaining - To be moved)
# ==========================================================================

# Note: The above functions are imported from their respective modules.

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