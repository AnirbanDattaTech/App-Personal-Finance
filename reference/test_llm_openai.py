# FILE: test_llm_openai.py
# PURPOSE: Test OpenAI API connection and list available models.

import os
from openai import OpenAI
from dotenv import load_dotenv
import logging

# --- Configuration ---
# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def list_openai_models():
    """Connects to OpenAI using the API key from environment variables
    and lists the available models.
    """
    # --- Load API Key ---
    # Load environment variables from a .env file if it exists
    load_dotenv()
    logging.info("Attempting to load environment variables from .env file.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.error("FATAL: OPENAI_API_KEY environment variable not set.")
        print("\nError: OPENAI_API_KEY not found.")
        print("Please ensure you have the key set in your environment variables or in a .env file.")
        return # Stop execution if key is missing

    logging.info("OPENAI_API_KEY found.")

    # --- Initialize Client ---
    try:
        client = OpenAI(api_key=api_key)
        logging.info("OpenAI client initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
        print(f"\nError initializing OpenAI client: {e}")
        return # Stop execution if client fails

    # --- Fetch and List Models ---
    try:
        logging.info("Attempting to fetch the list of available models...")
        models_response = client.models.list()
        logging.info(f"Successfully received model list response.") # Type: {type(models_response)}

        print("\nAvailable OpenAI Models:")
        print("-" * 25)

        count = 0
        # The response object is iterable (often openai.pagination.SyncPage)
        for model in models_response:
            # Check if the model object has an 'id' attribute (standard way to get model name)
            if hasattr(model, 'id'):
                print(f"- {model.id}")
                count += 1
            else:
                # Log if an unexpected model format is encountered
                logging.warning(f"Encountered model data without an 'id': {model}")

        print("-" * 25)
        logging.info(f"Successfully listed {count} models.")
        if count == 0:
             print("No models were listed. Check API key permissions or connection.")

    except Exception as e:
        logging.error(f"An error occurred while fetching or listing models: {e}", exc_info=True)
        print(f"\nAn error occurred while fetching models: {e}")
        print("Please check your API key, network connection, and OpenAI service status.")

# --- Main Execution ---
if __name__ == "__main__":
    print("--- Testing OpenAI Model Listing ---")
    list_openai_models()
    print("\n--- Test Complete ---")