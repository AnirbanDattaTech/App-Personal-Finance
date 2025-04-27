#!/usr/bin/env python3
"""
test_llm.py - Lists models or tests a specific LLM.
# (Keep the rest of the docstring)
"""

import os
import logging
import argparse
from pathlib import Path
from typing import Optional, List
import sys
try: from langchain_openai import ChatOpenAI; OPENAI_LC_INSTALLED = True
except ImportError: ChatOpenAI = None; OPENAI_LC_INSTALLED = False

# --- Only import non-critical stdlib here ---
# Defer imports of external libraries until needed / checked

from dotenv import load_dotenv

# --- Configuration ---
# --- MODIFICATION: Fix basicConfig call ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# --- END MODIFICATION ---
logger = logging.getLogger(__name__)
# (Keep Path Definitions as before)
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DATA_DIR = ROOT_DIR / "data"
CSV_PATH = DATA_DIR / "expenses.csv"
ENV_PATH = ROOT_DIR / ".env"
CSV_HEAD_ROWS = 5
# (Keep .env loading as before)
load_dotenv()

# --- Model Listing Functions ---
# (Keep list_google_models and list_openai_models as before, including internal try-except imports)
def list_google_models() -> List[str]:
    logger.info("Attempting to list Google Generative AI models...")
    model_names = []
    try: import google.generativeai as genai
    except ImportError: print("\nERROR: 'google-generativeai' not installed."); return model_names
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key: logger.error("GOOGLE_API_KEY not found"); print("\nERROR: GOOGLE_API_KEY not set."); return model_names
    try:
        genai.configure(api_key=api_key); logger.debug("Google AI SDK configured.")
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods or \
               'models/gemini' in model.name or 'models/gemma' in model.name: model_names.append(model.name)
        logger.info(f"Found {len(model_names)} potential Google models.")
    except Exception as e: logger.error(f"Failed list: {e}", exc_info=True); print(f"\nERROR: Google list: {e}")
    print("\n--- Available Google Models (Gemini/Gemma families) ---")
    if model_names: [print(f"- {name}") for name in sorted(model_names)]
    else: print("No Google models found or error occurred.")
    print("-" * 55); return model_names

def list_openai_models() -> List[str]:
    logger.info("Attempting to list OpenAI models...")
    model_names = []
    try: from openai import OpenAI, OpenAIError
    except ImportError: print("\nERROR: 'openai' not installed."); return model_names
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: logger.error("OPENAI_API_KEY not found"); print("\nERROR: OPENAI_API_KEY not set."); return model_names
    try:
        client = OpenAI(api_key=api_key); logger.debug("OpenAI client initialized.")
        models_response = client.models.list(); logger.debug("Received OpenAI model list.")
        for model in models_response:
             if hasattr(model, 'id') and \
                ('gpt' in model.id or 'text-' in model.id) and \
                not any(x in model.id for x in ['embed','whisper','dall-e','tts','vision','image']):
                  model_names.append(model.id)
        logger.info(f"Found {len(model_names)} potential OpenAI text models.")
    except OpenAIError as e: logger.error(f"OpenAI API error: {e}", exc_info=True); print(f"\nERROR: OpenAI API list: {e}")
    except Exception as e: logger.error(f"Failed list: {e}", exc_info=True); print(f"\nERROR: OpenAI list: {e}")
    print("\n--- Available OpenAI Models (GPT/Text families) ---")
    if model_names: [print(f"- {name}") for name in sorted(model_names)]
    else: print("No relevant OpenAI models found or error occurred.")
    print("-" * 55); return model_names

# --- Data Loading Function ---
def load_csv_sample(file_path: Path, num_rows: int) -> Optional[str]:
    """Loads the head of the CSV file and returns it as a plain string."""
    try: import pandas as pd
    except ImportError: logger.error("Pandas failed import in load_csv_sample."); print("\nERROR: Pandas required."); return None
    logger.info(f"Loading first {num_rows} rows from {file_path}...")
    if not file_path.is_file(): logger.error(f"CSV not found: {file_path}"); print(f"\nERROR: Data file not found: {file_path}"); return None
    try:
        df = pd.read_csv(file_path, nrows=num_rows, on_bad_lines='warn')
        logger.info(f"Read head ({len(df)} rows).");
        if df.empty: logger.warning("CSV empty."); return "(CSV Sample is Empty)"
        return df.to_string(index=False)
    except pd.errors.EmptyDataError: logger.warning(f"CSV empty (read error): {file_path}"); return "(CSV Sample is Empty)"
    except Exception as e: logger.error(f"Error reading CSV: {e}", exc_info=True); print(f"\nERROR: Read CSV: {e}"); return None

# --- LLM Testing Function ---
def test_model_with_data(model_name: str, data_sample_str: str) -> None:
    """Tests the specified LLM model by asking it to sum amounts."""
    try: from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError: ChatGoogleGenerativeAI = None
    try: from langchain_openai import ChatOpenAI
    except ImportError: ChatOpenAI = None
    try: from langchain_core.exceptions import LangChainException
    except ImportError: LangChainException = Exception # Fallback
    logger.info(f"Testing model '{model_name}' with data sample.")
    llm = None; api_key = None; provider = "Unknown"
    if ('gemini' in model_name or 'gemma' in model_name):
        provider = "Google"
        if not ChatGoogleGenerativeAI: print(f"\nERROR: LangChain Google wrapper missing for {model_name}."); return
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key: logger.error("GOOGLE_API_KEY not found"); print("\nERROR: GOOGLE_API_KEY not set."); return
        try: llm = ChatGoogleGenerativeAI(model=model_name.replace('models/', ''), google_api_key=api_key, temperature=0); logger.info(f"Initialized Google LC client: {model_name}")
        except Exception as e: logger.error(f"Failed init: {e}", exc_info=True); print(f"\nERROR: Init Google client: {e}"); return
    elif ('gpt' in model_name or 'text-' in model_name):
        provider = "OpenAI"
        if not ChatOpenAI: print(f"\nERROR: LangChain OpenAI wrapper missing for {model_name}."); return
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key: logger.error("OPENAI_API_KEY not found"); print("\nERROR: OPENAI_API_KEY not set."); return
        try: llm = ChatOpenAI(model=model_name, openai_api_key=api_key, temperature=0); logger.info(f"Initialized OpenAI LC client: {model_name}")
        except Exception as e: logger.error(f"Failed init: {e}", exc_info=True); print(f"\nERROR: Init OpenAI client: {e}"); return
    else: logger.error(f"Unknown provider/wrapper: {model_name}"); print(f"\nERROR: Unknown model/lib: '{model_name}'."); return

    if llm:
        print(f"\n--- Testing Model: {model_name} ({provider}) ---")
        prompt = f"""Given the following data sample as plain text:

{data_sample_str}

Calculate the sum of the 'amount' column from the data shown above.
Respond ONLY with the final numerical total. Do not include explanations, currency symbols, commas, or any other text.
"""
        print("Sending request...")
        try:
            response = llm.invoke(prompt)
            if hasattr(response, 'content'): llm_response_content = response.content
            elif isinstance(response, str): llm_response_content = response
            else: llm_response_content = str(response)
            llm_response_content = llm_response_content.strip()
            logger.info(f"Received response from {model_name}: '{llm_response_content}'")
            print("\n--- LLM Response ---"); print(llm_response_content); print("-" * 20)
            try: float(llm_response_content.replace(',', '')); print("✅ Numerical.")
            except ValueError: print("⚠️ Not numerical.")
        except LangChainException as e: logger.error(f"LangChain error: {e}", exc_info=True); print(f"\nERROR: LangChain call: {e}")
        except Exception as e: logger.error(f"Unexpected error: {e}", exc_info=True); print(f"\nERROR: Unexpected call: {e}")
        print("-" * 55)

# --- Main Execution Logic ---
def main():
    logger.info(f"--- Running test_llm.py using Python: {sys.executable} ---")
    parser = argparse.ArgumentParser(
        description="List available LLMs or test a specific LLM with sample data.",
        usage="%(prog)s [<model_name>]"
    )
    parser.add_argument(
        "model_name", nargs='?', type=str,
        help="Optional: Model name to test (e.g., 'models/gemini-1.5-flash-latest', 'gpt-4o')."
    )
    args = parser.parse_args()

    if args.model_name:
        # Mode 2: Test model - Check Pandas dependency HERE
        try:
             import pandas as pd # Attempt import right before use
             logger.info("Pandas imported successfully within main() for testing.")
        except ImportError:
             logger.error("Pandas import failed within main().")
             print("\nError: Pandas library is required for testing mode but failed to import.")
             print("Please ensure 'pandas' is installed correctly in the environment.")
             return # Exit if pandas cannot be imported

        print(f"Attempting to test model: {args.model_name}")
        data_sample = load_csv_sample(CSV_PATH, CSV_HEAD_ROWS)
        if data_sample:
            test_model_with_data(args.model_name, data_sample)
        else:
            print("\nCannot perform model test because data sample failed to load (or Pandas missing).")
    else:
        # Mode 1: List models
        print("No model specified...")
        list_google_models()
        list_openai_models()
        print("\nTo test a model, run: python test_llm.py \"<model_name>\"")

if __name__ == "__main__":
    main()
    print("\n--- Script Finished ---")