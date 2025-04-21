# reference/test_llm_gemini.py
"""
Basic test script using LangGraph and Gemini to answer simple questions
based on a small sample (head) of the expense data.

Demonstrates:
- Loading environment variables (API key).
- Loading CSV data with Pandas.
- Setting up a simple LangGraph state and graph.
- Using LangChain's ChatGoogleGenerativeAI model.
- Passing data sample within the prompt (NOTE: Not scalable for large data).
"""

import pandas as pd
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, TypedDict, Annotated
import operator

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
# from langgraph.checkpoint.sqlite import SqliteSaver # If you want to add memory later

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Load Environment Variables (API Key) ---
# Load from .env file in the project root directory
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
    logging.info(".env file loaded.")
else:
    logging.warning(f".env file not found at {ENV_PATH}. Make sure GOOGLE_API_KEY is set elsewhere if needed.")

# Check if API key is available
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    logging.error("GOOGLE_API_KEY not found in environment variables. Please set it in the .env file.")
    exit() # Stop execution if key is missing
else:
    logging.info("GOOGLE_API_KEY found.")


# --- Load Sample Data ---
DATA_FILE = PROJECT_ROOT / "dummy_expenses_generated.csv"
df = pd.DataFrame() # Initialize empty dataframe

try:
    if DATA_FILE.exists():
        df = pd.read_csv(DATA_FILE)
        # Keep only essential columns for the small prompt sample
        df_sample = df[['date', 'category', 'sub_category', 'user', 'amount']].head().to_markdown(index=False)
        logging.info(f"Loaded data sample from {DATA_FILE}")
        # print("\n--- Data Sample Sent to LLM ---")
        # print(df_sample)
        # print("-----------------------------\n")
    else:
        logging.error(f"Data file not found at {DATA_FILE}. Cannot proceed.")
        exit()
except Exception as e:
    logging.error(f"Error loading or processing data file {DATA_FILE}: {e}", exc_info=True)
    exit()


# --- Define LangGraph State ---
class SimpleAgentState(TypedDict):
    """Defines the state passed between nodes in the graph."""
    question: str # The user's question
    data_summary: str # A small summary/sample of the data
    llm_response: str # The final response from the LLM

# --- Define Graph Nodes ---

def get_user_question(state: SimpleAgentState) -> Dict:
    """Node to simply retrieve the question from the initial state."""
    logging.info("Node: get_user_question")
    question = state.get('question', '')
    if not question:
        logging.error("No question provided in initial state.")
        # Handle error appropriately, maybe raise exception or return error state
        return {"llm_response": "Error: No question was provided."}
    # In this simple example, we just pass it along implicitly
    # The 'data_summary' is also assumed to be in the initial state
    return {} # No state change needed here as question is already present

def call_gemini(state: SimpleAgentState) -> Dict:
    """Node to format the prompt and call the Gemini LLM."""
    logging.info("Node: call_gemini")
    question = state.get('question', '')
    data_summary = state.get('data_summary', '') # Get the data sample

    if not question:
        return {"llm_response": "Error: Question missing."}
    if not data_summary:
        logging.warning("Data summary is missing, LLM will have limited context.")

    # Initialize the Gemini LLM
    # Ensure API key is used automatically from environment by LangChain
    try:
        # Use gemini-1.5-flash for speed and cost-effectiveness in testing
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
        logging.info(f"Initialized Gemini model: {llm.model}")
    except Exception as e:
        logging.error(f"Failed to initialize Gemini model: {e}", exc_info=True)
        return {"llm_response": f"Error: Could not initialize LLM - {e}"}

    # Simple Prompt Engineering: Combine question and data sample
    prompt = f"""
You are a helpful assistant analyzing personal expense data.
Answer the following question based *only* on the provided data summary.

Data Summary (First 5 Rows):
{data_summary}

Question: {question}

Answer:
"""
    logging.info("Sending prompt to Gemini...")
    # print(f"DEBUG Prompt:\n{prompt}") # Uncomment for debugging

    try:
        # Invoke the LLM
        response = llm.invoke(prompt)
        logging.info("Received response from Gemini.")
        # Extract the text content from the response object
        llm_response_content = response.content if hasattr(response, 'content') else str(response)
        return {"llm_response": llm_response_content}
    except Exception as e:
        logging.error(f"Error during LLM call: {e}", exc_info=True)
        return {"llm_response": f"Error: Failed to get response from LLM - {e}"}

# --- Define Graph ---
workflow = StateGraph(SimpleAgentState)

# Add nodes
workflow.add_node("fetch_question", get_user_question) # Simple node, might not be strictly necessary here
workflow.add_node("generate_answer", call_gemini)

# Define edges
workflow.set_entry_point("fetch_question")
workflow.add_edge("fetch_question", "generate_answer")
workflow.add_edge("generate_answer", END) # End after getting the answer

# Compile the graph
app = workflow.compile()
logging.info("LangGraph compiled.")

# --- Run the Test ---
if __name__ == "__main__":
    print("-" * 30)
    print("--- Basic LangGraph Gemini Test ---")
    print("-" * 30)

    # Example Question
    # test_question = "What is the total amount spent in the first few transactions shown?" # Tests reasoning on sample
    test_question = "List the categories present in the sample data." # Tests extraction from sample
    # test_question = "Who spent money in this sample?"

    print(f"Test Question: {test_question}")

    # Prepare the initial state for the graph
    initial_state: SimpleAgentState = {
        "question": test_question,
        "data_summary": df_sample, # Pass the pre-loaded data sample
        "llm_response": "" # Initialize response field
    }

    print("\nInvoking LangGraph...")

    # Run the graph
    # Stream events for more detailed output (optional)
    # for event in app.stream(initial_state):
    #     print(event)

    # Or just get the final state
    final_state = app.invoke(initial_state)

    print("\n--- Final LLM Response ---")
    print(final_state.get("llm_response", "No response generated."))
    print("-" * 30)