# streamlit/tabs/assistant_tab.py
# FIX 4: Moved chart/SQL column & placeholder definitions *inside* the assistant chat message block.
import streamlit as st
import requests
import json
import plotly.io as pio
# import pandas as pd
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
LANGSERVE_INVOKE_URL = "http://localhost:8000/assistant/invoke" # Use invoke endpoint

# --- Helper Function (Non-Streaming) ---
def call_assistant_api(query: str) -> dict | None:
    """Sends the query to the LangServe invoke endpoint and returns the parsed output."""
    payload = {"input": {"original_query": query}}
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    try:
        logger.info(f"Sending request to API: {LANGSERVE_INVOKE_URL} with query: '{query}'")
        response = requests.post(LANGSERVE_INVOKE_URL, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        response_data = response.json()
        logger.info(f"API Raw Response: {response_data}")
        if "output" in response_data:
            api_output = response_data.get("output", {})
            logger.info(f"Extracted API Output: {api_output}")
            if not isinstance(api_output, dict):
                 logger.error(f"API 'output' key did not contain a dictionary. Response: {response_data}")
                 st.error("Received an unexpected response format from the assistant (output is not a dict).")
                 return None
            return api_output
        else:
            logger.error(f"API response missing 'output' key. Response: {response_data}")
            st.error("Received an unexpected response format from the assistant.")
            return None
    # --- (Keep existing exception handling) ---
    except requests.exceptions.RequestException as e:
        logger.error(f"API call failed: {e}", exc_info=True)
        st.error(f"Failed to connect to the assistant backend: {e}")
        return None
    except json.JSONDecodeError:
        logger.error(f"Failed to decode API JSON response: {response.text}")
        st.error("Received an invalid response from the assistant (not valid JSON).")
        return None
    except Exception as e:
         logger.error(f"An unexpected error occurred during API call: {e}", exc_info=True)
         st.error(f"An unexpected error occurred: {e}")
         return None

# --- Main Render Function (Non-Streaming - Final Layout Fix) ---
def render():
    """Renders the Assistant tab using the invoke endpoint."""
    st.subheader("Personal Finance Assistant")

    # --- Initialize Chat History ---
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Greetings! How can I help you with your finances today?"}
        ]

    # --- Display Prior Chat Messages (Text Only) ---
    # This loop ONLY displays the text history.
    logger.debug(f"Displaying {len(st.session_state.messages)} messages from history.")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"]) # Display only text content

    # --- Chat Input and Processing Block ---
    if prompt := st.chat_input("Ask me about your expenses..."):
        logger.info(f"User input received: '{prompt}'")

        # 1. Add user message to state FIRST
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 2. Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)

        # 3. Process NEW Assistant Response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Thinking...")

            # 4. Call the backend API
            api_response = call_assistant_api(prompt)

            # 5. Process the response
            if api_response:
                # Extract data
                final_response = api_response.get("final_response", "Sorry, I couldn't generate a response.")
                chart_json = api_response.get("chart_json")
                sql_query = api_response.get("sql_query")
                error_msg = api_response.get("error")

                # 6. Display final text response FIRST
                if error_msg:
                    logger.error(f"Assistant API returned an error: {error_msg}")
                    final_response = f"An error occurred: {error_msg}"
                    message_placeholder.error(final_response)
                else:
                    message_placeholder.markdown(final_response) # Fill the text placeholder

                # 7. Add complete assistant message data to history AFTER processing
                assistant_message_data = {
                    "role": "assistant",
                    "content": final_response,
                    "chart_json": chart_json,
                    "sql_query": sql_query
                }
                st.session_state.messages.append(assistant_message_data)

                # --- ** 8. Define Layout & Display Chart/SQL for the NEW response HERE ** ---
                # Define columns and placeholders *inside* the assistant message block,
                # after the text response has been rendered.
                if chart_json or sql_query: # Only create columns if there's something to show
                    viz_col, sql_col = st.columns([0.6, 0.4])
                    placeholder_viz = viz_col.empty()
                    placeholder_sql = sql_col.empty()

                    with placeholder_viz:
                        if chart_json and not error_msg:
                            try:
                                chart_fig = pio.from_json(chart_json)
                                st.plotly_chart(chart_fig, use_container_width=True)
                                logger.info("Chart displayed successfully.")
                            except Exception as e:
                                logger.error(f"Error rendering chart JSON: {e}")
                                st.warning("Could not display the generated chart.")

                    with placeholder_sql:
                        if sql_query and not error_msg :
                            with st.expander("View Generated SQL", expanded=False):
                                 st.code(sql_query, language="sql")
                                 logger.info("SQL query displayed.")

            else:
                # Handle API call failure
                 message_placeholder.error("Failed to get a response from the assistant.")
                 st.session_state.messages.append({
                     "role": "assistant",
                     "content": "Failed to get a response from the assistant."
                 })