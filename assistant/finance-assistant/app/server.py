# FILE: assistant/finance-assistant/app/server.py
# PURPOSE: Defines the FastAPI server to expose the LangGraph agent via LangServe.

import os,sys
from pathlib import Path
import logging
from typing import Optional, Any

# Third-party imports
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field
from langserve import add_routes

# --- Add project root's 'src' directory to path ---
# Calculate path relative to the current file (server.py)
# server.py is in app/, src/ is sibling to app/
try:
    current_dir = Path(__file__).resolve().parent # This is the 'app' directory
    src_dir = current_dir.parent / "src"        # Go up one level to 'finance-assistant' then into 'src'

    # Configure logging BEFORE potentially adding path, so log messages are captured
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s', # Added logger name
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__) # Logger for this server file

    if src_dir.is_dir() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
        logger.info(f"Added src directory to sys.path: {src_dir}")
    elif not src_dir.is_dir():
         # Log an error but allow execution to continue to see if agent import works via other means
         logger.error(f"Calculated src directory does not exist or is not a directory: {src_dir}. Imports might fail.")
    else:
         logger.debug(f"Src directory already in sys.path or not added: {src_dir}")

except Exception as path_ex:
     # Fallback logging if basicConfig failed or path calculation failed
     print(f"ERROR setting up paths/logging: {path_ex}")
     # Exit if paths cannot be determined, as imports will fail
     sys.exit("Fatal error during initial path setup.")
# ---

# --- Try importing agent AFTER adjusting path ---
try:
    # Import the compiled graph object and the AgentState
    # These imports MUST happen after sys.path is potentially modified
    from agent.graph import graph as finance_assistant_graph # Rename for clarity
    from agent.state import AgentState # Needed for output schema reference
    logger.info("Successfully imported graph and AgentState from src.agent")
except ImportError as e:
    logger.error(f"CRITICAL ERROR: Failed to import graph or AgentState from src.agent. "
                 f"Check PYTHONPATH and ensure '{src_dir}' exists and contains 'agent/'. Error: {e}", exc_info=True)
    # Raise the error to prevent server startup with missing core components
    raise ImportError("Could not import agent graph or state. Server cannot start.") from e
except Exception as e:
    logger.error(f"An unexpected error occurred during agent import: {e}", exc_info=True)
    raise # Re-raise other unexpected errors

# --- Define API Input Schema ---
class AssistantInput(BaseModel):
    """Input schema for the Finance Assistant Agent."""
    original_query: str = Field(..., description="The user's natural language query.")
    # Add other potential inputs like conversation history or session ID later
    # session_id: Optional[str] = None
    # history: Optional[List[Dict[str, str]]] = None

    # Pydantic v2 config example
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "original_query": "What was my total grocery spend last month?"
                }
            ]
        }
    }

# --- Define API Output Schema ---
# Selects relevant fields from the final AgentState for the response.
class AssistantOutput(BaseModel):
    """Output schema for the Finance Assistant Agent."""
    final_response: Optional[str] = Field(None, description="The final text response generated for the user.")
    chart_json: Optional[str] = Field(None, description="Plotly chart JSON representation, if one was generated.")
    sql_results_str: Optional[str] = Field(None, description="SQL query results formatted as a string, if applicable.")
    error: Optional[str] = Field(None, description="Any error message captured during the agent's execution.")

    # Pydantic v2 config example
    model_config = {
        "json_schema_extra": {
             "examples": [
                 {
                     "final_response": "Your total grocery spend last month was INR 5,432.10.",
                     "chart_json": "{ ...plotly json... }",
                     "sql_results_str": "Category | Total Amount\nGrocery  | 5432.10",
                     "error": None
                 }
            ]
        }
    }

# --- Initialize FastAPI App ---
logger.info("Initializing FastAPI application...")
app = FastAPI(
    title="Personal Finance Assistant Agent API",
    version="0.1.0", # Consider bumping version as features are added
    description="API endpoint for interacting with the LangGraph-based Personal Finance Assistant.",
    # Add other FastAPI configurations like root_path if deploying behind proxy
)

# --- Basic Health Check Endpoint ---
@app.get("/", tags=["Health Check"])
async def read_root():
    """Simple health check endpoint."""
    logger.debug("Root endpoint '/' accessed.")
    return {"status": "ok", "message": "Finance Assistant API is running."}

# --- Add LangServe Routes ---
# Configures /invoke, /stream, /batch, etc. for the agent graph.
logger.info(f"Adding LangServe routes for agent graph '{finance_assistant_graph.__class__.__name__}'...")
add_routes(
    app=app,
    runnable=finance_assistant_graph,    # The imported compiled LangGraph runnable
    path="/assistant",                   # Base path for agent endpoints (e.g., POST /assistant/invoke)
    input_type=AssistantInput,           # Pydantic model for input validation
    output_type=AssistantOutput,         # Pydantic model for output structuring
    # enable_feedback_endpoint=True,    # Uncomment to enable LangSmith feedback endpoint
    # playground_type="chat",           # Optionally configure playground type if needed later
    config_keys=["configurable"]         # Keys to make configurable at runtime (e.g., session_id, thread_id)
                                         # Add 'user_id' or 'thread_id' here if using LangSmith persistence per user
)
logger.info(f"LangServe routes added successfully at path '/assistant'. Playground at /assistant/playground/")


# --- Run with Uvicorn (for direct execution) ---
# Note: `uvicorn app.server:app --reload` or `langgraph dev` are typical for development.
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000)) # Allow port configuration via environment variable
    host = os.getenv("HOST", "0.0.0.0") # Default to accessible on network
    
    logger.info(f"Starting Uvicorn server directly on {host}:{port}...")
    logger.warning("Running directly with 'python app/server.py'. Use 'uvicorn' command or 'langgraph dev' for development features like hot-reloading.")
    
    # Run the Uvicorn server
    uvicorn.run(app, host=host, port=port)