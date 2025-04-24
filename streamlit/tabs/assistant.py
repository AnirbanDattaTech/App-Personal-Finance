# streamlit/tabs/assistant_tab.py
import streamlit as st
import requests
import json
import plotly.io as pio
import pandas as pd # Keep for potential future use, even if not displaying df directly now
import logging

# Configure Logging (optional but good practice)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
# Make sure this matches the port where your uvicorn server is running
LANGSERVE_API_URL = "http://localhost:8000/assistant/invoke"

# --- Helper Functions ---
def call_assistant_api(query: str) -> dict | None:
    """Sends the query to the LangServe backend and returns the parsed response."""
    payload = {"input": {"original_query": query}}
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    try:
        logger.info(f"Sending request to API: {LANGSERVE_API_URL} with query: '{query}'")
        response = requests.post(LANGSERVE_API_URL, json=payload, headers=headers, timeout=120) # Increased timeout
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        response_data = response.json()
        logger.info(f"API Raw Response: {response_data}") # Log the raw response

        # --- Extract the relevant 'output' part ---
        # LangServe wraps the graph output in an 'output' key
        if "output" in response_data:
            # Further extract based on AssistantOutput Pydantic model in server.py
            api_output = response_data.get("output", {})
            # Log extracted output for debugging
            logger.info(f"Extracted API Output: {api_output}")
            return api_output
        else:
            logger.error(f"API response missing 'output' key. Response: {response_data}")
            st.error("Received an unexpected response format from the assistant.")
            return None

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


# --- Main Render Function ---
def render():
    """Renders the Assistant tab."""
    st.subheader("💰 Personal Finance Assistant")

    # --- Layout ---
    # Row 1: Chat Interface
    chat_col = st.container() # Use container for chat flow

    # Row 2: Visualization and Data (using columns)
    viz_col, data_col = st.columns([0.6, 0.4]) # Allocate 60% width to viz, 40% to data

    # --- Initialize Chat History ---
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Greetings! How can I help you with your finances today?"}
        ]

    # --- Display Prior Chat Messages ---
    with chat_col:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"]) # Display assistant/user text

                # Display chart/data associated with previous assistant messages
                if message["role"] == "assistant":
                    if "chart_json" in message and message["chart_json"]:
                        try:
                            chart_fig = pio.from_json(message["chart_json"])
                            # Use the viz_col from the *outer scope* to display charts below chat
                            with viz_col:
                                st.plotly_chart(chart_fig, use_container_width=True)
                        except Exception as e:
                            logger.error(f"Error rendering previous chart: {e}")
                            with viz_col:
                                st.warning("Could not render previous chart.")

                    if "sql_results_str" in message and message["sql_results_str"]:
                        # Use the data_col from the *outer scope*
                         with data_col:
                            with st.expander("View Raw Data"):
                                 st.text(message["sql_results_str"])


    # --- Chat Input ---
    if prompt := st.chat_input("Ask me about your expenses..."):
        logger.info(f"User input received: '{prompt}'")
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message
        with chat_col:
            with st.chat_message("user"):
                st.markdown(prompt)

        # --- Call Backend API & Process Response ---
        with chat_col:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.markdown("Thinking...") # Provide feedback

                # Call the backend
                api_response = call_assistant_api(prompt)

                if api_response:
                    final_response = api_response.get("final_response", "Sorry, I couldn't generate a response.")
                    chart_json = api_response.get("chart_json") # Can be None
                    sql_results_str = api_response.get("sql_results_str") # Can be None
                    error_msg = api_response.get("error") # Check for errors from the agent

                    if error_msg:
                        logger.error(f"Assistant API returned an error: {error_msg}")
                        final_response = f"An error occurred: {error_msg}" # Display error to user
                        message_placeholder.error(final_response) # Use error styling
                    else:
                        message_placeholder.markdown(final_response) # Display final text

                    # Store results with the message for potential redisplay if needed
                    assistant_message_data = {
                        "role": "assistant",
                        "content": final_response,
                        "chart_json": chart_json,
                        "sql_results_str": sql_results_str
                    }
                    st.session_state.messages.append(assistant_message_data)

                    # --- Display Chart and Data in Row 2 ---
                    # Clear previous row 2 content before displaying new results
                    with viz_col:
                        # st.empty() # Optional: Explicitly clear if needed
                        if chart_json:
                            try:
                                chart_fig = pio.from_json(chart_json)
                                st.plotly_chart(chart_fig, use_container_width=True)
                                logger.info("Chart displayed successfully.")
                            except Exception as e:
                                logger.error(f"Error rendering chart JSON: {e}")
                                st.warning("Could not display the generated chart.")
                        # else:
                        #     st.write("") # Keep the column, but empty if no chart

                    with data_col:
                        # st.empty() # Optional: Explicitly clear if needed
                        if sql_results_str and not error_msg : # Only show if no error and results exist
                            with st.expander("View Retrieved Data", expanded=False):
                                 st.text(sql_results_str)
                                 logger.info("SQL results string displayed.")
                        # else:
                        #     st.write("") # Keep the column, but empty if no data

                else:
                    # Handle API call failure (error already shown by call_assistant_api)
                     message_placeholder.error("Failed to get a response from the assistant.")
                     st.session_state.messages.append({
                         "role": "assistant",
                         "content": "Failed to get a response from the assistant."
                     })
                     # Clear row 2 as well
                     with viz_col: st.empty()
                     with data_col: st.empty()