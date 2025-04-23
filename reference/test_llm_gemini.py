# reference/test_llm_gemini.py
"""
Basic test script using LangGraph and Gemini. Includes model listing.
"""

import pandas as pd
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, TypedDict, Annotated
import operator

# --- ✅ Import Google SDK ---
import google.generativeai as genai

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Load Environment Variables (API Key) ---
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists(): load_dotenv(dotenv_path=ENV_PATH); logging.info(".env file loaded.")
else: logging.warning(f".env file not found at {ENV_PATH}.")

# --- Configure API Key and Check ---
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    logging.error("GOOGLE_API_KEY not found. Exiting.")
    exit()
else:
    try:
        # --- ✅ Configure the SDK directly ---
        genai.configure(api_key=api_key)
        logging.info("GOOGLE_API_KEY found and Google AI SDK configured.")
    except Exception as e:
        logging.error(f"Failed to configure Google AI SDK: {e}", exc_info=True)
        exit()

# --- ✅ List Available Models ---
print("\n--- Available Google Generative AI Models (for generateContent) ---")
print("-" * 60)
models_available_for_chat = []
try:
    models_listed = False
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            models_listed = True
            print(f"- {model.name} ({model.display_name})")
            models_available_for_chat.append(model.name) # Store usable model names

    if not models_listed:
        print("No models supporting 'generateContent' found for your API key.")
except Exception as e:
    logging.error(f"Failed to list models: {e}", exc_info=True)
    print(f"\nError: Could not retrieve model list.")
print("-" * 60)
# --- End Model Listing ---


# --- Load Sample Data ---
DATA_FILE = PROJECT_ROOT / "data/expenses.csv"
df = pd.DataFrame()
df_sample = "" # Initialize

try:
    if DATA_FILE.exists():
        df = pd.read_csv(DATA_FILE)
        df_sample = df[['date', 'category', 'sub_category', 'user', 'amount']].head().to_markdown(index=False)
        logging.info(f"Loaded data sample from {DATA_FILE}")
    else:
        logging.error(f"Data file not found at {DATA_FILE}. Cannot proceed with LLM test.")
        # Don't exit immediately, maybe user just wanted to list models
except Exception as e:
    logging.error(f"Error loading data file {DATA_FILE}: {e}", exc_info=True)
    # Don't exit immediately

# --- Define LangGraph State ---
class SimpleAgentState(TypedDict):
    question: str
    data_summary: str
    llm_response: str

# --- Define Graph Nodes ---
def get_user_question(state: SimpleAgentState) -> Dict:
    logging.info("Node: get_user_question")
    # ... (node logic remains the same) ...
    return {}

def call_gemini(state: SimpleAgentState) -> Dict:
    logging.info("Node: call_gemini")
    question = state.get('question', '')
    data_summary = state.get('data_summary', '')

    if not question: return {"llm_response": "Error: Question missing."}
    if not data_summary: logging.warning("Data summary is missing.")

    # --- ✅ Select a model (using the one user specified or default) ---
    # model_to_use = "models/gemini-1.5-flash-latest" # Or use the name from .env / config
    # model_to_use = "models/gemini-pro" # Example alternative
    # Let's stick to the user's current choice for the test run:
    model_to_use = "gemini-1.5-flash" # LangChain often handles the 'models/' prefix
    # model_to_use = "gemini-2.0-flash-thinking-exp"

    # Check if the chosen model is in the list of available ones (optional sanity check)
    full_model_name_check = f"models/{model_to_use}" # Check with prefix
    if models_available_for_chat and full_model_name_check not in models_available_for_chat:
         logging.warning(f"Model '{model_to_use}' (as {full_model_name_check}) was not found in the list of models supporting 'generateContent'. LangChain might still work or might default.")

    try:
        # Use the specific model chosen for the test
        llm = ChatGoogleGenerativeAI(model=model_to_use)
        logging.info(f"Initialized LangChain Gemini model: {llm.model}")
    except Exception as e:
        logging.error(f"Failed to initialize ChatGoogleGenerativeAI model: {e}", exc_info=True)
        return {"llm_response": f"Error: Could not initialize LangChain LLM - {e}"}

    prompt = f"""
You are a helpful assistant analyzing personal expense data.
Answer the following question based *only* on the provided data summary.

Data Summary (First 5 Rows):
{data_summary}

Question: {question}

Answer:
"""
    logging.info(f"Sending prompt to {model_to_use}...")
    try:
        response = llm.invoke(prompt)
        logging.info(f"Received response from {model_to_use}.")
        llm_response_content = response.content if hasattr(response, 'content') else str(response)
        return {"llm_response": llm_response_content}
    except Exception as e:
        logging.error(f"Error during LLM call with {model_to_use}: {e}", exc_info=True)
        return {"llm_response": f"Error: Failed to get response from LLM - {e}"}

# --- Define Graph ---
workflow = StateGraph(SimpleAgentState)
workflow.add_node("fetch_question", get_user_question)
workflow.add_node("generate_answer", call_gemini)
workflow.set_entry_point("fetch_question")
workflow.add_edge("fetch_question", "generate_answer")
workflow.add_edge("generate_answer", END)
app = workflow.compile()
logging.info("LangGraph compiled.")

# --- Run the Test ---
if __name__ == "__main__":
    print("\n" + "-" * 30)
    print("--- Basic LangGraph Gemini Test ---")
    print("-" * 30)

    # Only proceed if data was loaded successfully for the test part
    if df_sample:
        test_question = "List the categories present in the sample data."
        print(f"Test Question: {test_question}")
        initial_state: SimpleAgentState = {
            "question": test_question,
            "data_summary": df_sample,
            "llm_response": ""
        }
        print("\nInvoking LangGraph...")
        try:
            final_state = app.invoke(initial_state)
            print("\n--- Final LLM Response ---")
            print(final_state.get("llm_response", "No response generated."))
        except Exception as e:
            print(f"\nError invoking LangGraph: {e}")
            logging.error("Error during graph invocation", exc_info=True)
    else:
        print("\nSkipping LangGraph invocation as data sample failed to load.")

    print("-" * 30)