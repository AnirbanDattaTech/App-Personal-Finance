# FILE: assistant/finance-assistant/app/server.py
# PURPOSE: Defines the FastAPI server to expose the LangGraph agent via LangServe.

from fastapi import FastAPI
from langserve import add_routes
import uvicorn
from pydantic import BaseModel, Field # Use Field for explicit descriptions/validation
from typing import Optional, Any
import logging
from pathlib import Path
import sys

# --- Add project root to path for module resolution ---
# This helps ensure 'src.agent' can be imported correctly, especially when running with `langgraph start`
# or `uvicorn`. Adjust the number of .parent calls if the server.py location changes relative to the root.
# app/server.py -> app -> finance-assistant -> assistant -> app-personal-finance (project root)
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
src_path = project_root / "assistant" / "finance-assistant" / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
# ---

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    # 1. Import the compiled graph object and the AgentState
    from agent.graph import graph as finance_assistant_graph # Rename to avoid potential namespace conflicts
    from agent.state import AgentState # Needed for understanding the output structure
    logger.info("Successfully imported graph and AgentState from src.agent")
except ImportError as e:
    logger.error(f"CRITICAL ERROR: Failed to import graph or AgentState from src.agent. "
                 f"Ensure assistant/finance-assistant/src/agent/graph.py and state.py exist "
                 f"and PYTHONPATH is configured correctly. Error: {e}", exc_info=True)
    # Optionally raise the error to prevent server startup with missing core components
    raise ImportError("Could not import agent graph or state. Server cannot start.") from e
except Exception as e:
    logger.error(f"An unexpected error occurred during import: {e}", exc_info=True)
    raise

# --- Define API Input Schema ---
# This model defines the structure expected within the 'input' key of the request payload.
# It should contain the fields needed to initialize the AgentState for a new run.
class AssistantInput(BaseModel):
    """Input schema for the Finance Assistant Agent."""
    original_query: str = Field(..., description="The user's natural language query.")
    # If other fields need to be configurable at invocation time, add them here.
    # Example: session_id: Optional[str] = None

    # Add model config if needed, e.g., for example payloads in OpenAPI docs
    # class Config:
    #     schema_extra = {
    #         "example": {
    #             "original_query": "What was my total grocery spend last month?"
    #         }
    #     }

# --- Define API Output Schema ---
# This model defines the structure that will be nested within the 'output' key of the response payload.
# It selects and structures the relevant fields from the final AgentState.
class AssistantOutput(BaseModel):
    """Output schema for the Finance Assistant Agent."""
    final_response: Optional[str] = Field(None, description="The final text response generated for the user.")
    chart_json: Optional[str] = Field(None, description="Plotly chart JSON representation, if one was generated.")
    sql_results_str: Optional[str] = Field(None, description="SQL query results formatted as a string, if applicable.")
    error: Optional[str] = Field(None, description="Any error message captured during the agent's execution.")

    # class Config:
    #     schema_extra = {
    #         "example": {
    #             "final_response": "Your total grocery spend last month was INR 5,432.10.",
    #             "chart_json": "{...plotly json...}",
    #             "sql_results_str": "Category | Total Amount\nGrocery | 5432.10",
    #             "error": None
    #         }
    #     }


# --- Initialize FastAPI App ---
logger.info("Initializing FastAPI application...")
app = FastAPI(
    title="Personal Finance Assistant Agent API",
    version="0.1.0",
    description="API endpoint for interacting with the LangGraph-based Personal Finance Assistant.",
    # Add other FastAPI configurations like docs_url if needed
)

# --- Basic Health Check Endpoint ---
@app.get("/", tags=["Health"])
async def read_root():
    """Simple health check endpoint."""
    logger.debug("Root endpoint '/' accessed.")
    return {"status": "ok", "message": "Finance Assistant API is running."}

# --- Add LangServe Routes ---
# This function configures the necessary endpoints (/invoke, /stream, /batch, /stream_log, etc.)
# for the given LangGraph agent.
logger.info("Adding LangServe routes for the finance assistant graph...")
add_routes(
    app,
    finance_assistant_graph,    # The imported compiled LangGraph runnable
    path="/assistant",          # The base path for the agent endpoints (e.g., POST /assistant/invoke)
    input_type=AssistantInput,  # Specifies the Pydantic model for input validation (maps to AgentState start)
    output_type=AssistantOutput,# Specifies the Pydantic model for the output structure (maps to AgentState end)
    # enable_feedback_endpoint=True, # Uncomment to enable feedback endpoint (requires LangSmith)
    # config_keys=["configurable"] # Add this if your graph uses configurable fields via AgentState/RunnableConfig
    # tags=["Assistant Agent"]       # Tag for OpenAPI documentation grouping
)
logger.info(f"LangServe routes added successfully at path '/assistant'.")


# --- Run with Uvicorn (for direct execution, e.g., python app/server.py) ---
# Note: `langgraph start` is the recommended way to run this in development
# as it handles hot-reloading and environment setup based on langgraph.json.
if __name__ == "__main__":
    logger.info("Starting Uvicorn server directly (use 'langgraph dev' for development)...")
    # Use port 8000 as the default, matching LangServe's common practice
    # Host '0.0.0.0' makes it accessible on the network
    uvicorn.run(app, host="0.0.0.0", port=8000)