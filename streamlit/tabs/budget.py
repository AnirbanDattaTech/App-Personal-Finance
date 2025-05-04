# streamlit/tabs/budget.py
"""
Renders the 'Budget' tab UI, dynamically fetching data from and sending
updates to the backend FastAPI budget API.
Uses st.expander to hide the edit form by default, improving compactness.
Applies add_expense.py form layout strategy for alignment.
"""
import streamlit as st
import plotly.graph_objects as go
import datetime
import pandas as pd # Using pandas for easy bar chart data creation
import requests # To make API calls
import logging # For logging API errors
from typing import Dict, Any, Optional
import time # For sleep after toast

# --- Configuration ---
# Base URL of the running FastAPI backend
API_BASE_URL = "http://127.0.0.1:8000"
BUDGET_API_URL = f"{API_BASE_URL}/budgets"

# Configure logging
logger = logging.getLogger(__name__)


# --- Helper Function for API GET Request ---
# [NOTE: fetch_budget_data_from_api function remains the same as provided]
def fetch_budget_data_from_api(year_month: str) -> Optional[Dict[str, Any]]:
    """Fetches the budget summary data from the backend API for a given month."""
    get_url = f"{BUDGET_API_URL}/{year_month}"
    try:
        logger.info(f"Attempting to fetch budget data from: {get_url}")
        response = requests.get(get_url, timeout=10)
        response.raise_for_status()
        api_response = response.json()
        logger.info(f"Successfully fetched budget data for {year_month}.")
        if "data" in api_response and isinstance(api_response["data"], dict):
            return api_response["data"]
        else:
            logger.error(f"API response for {year_month} missing 'data' dictionary: {api_response}")
            st.error("Received unexpected data format from the budget API.")
            return None
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error fetching budget data from {get_url}.")
        st.error(f"Could not connect to the backend API at {API_BASE_URL}. Is it running?")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching budget data from {get_url}.")
        st.error("The request to the backend API timed out.")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching budget data: {e.response.status_code} - {e.response.text}")
        st.error(f"Failed to fetch budget data. API returned status {e.response.status_code}.")
        return None
    except requests.exceptions.RequestException as e:
        logger.exception(f"General error fetching budget data: {e}")
        st.error(f"An unexpected error occurred while fetching budget data: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error processing API response: {e}")
        st.error(f"An error occurred processing the API response: {e}")
        return None

# --- Helper Function for API POST Request ---
# [NOTE: post_budget_update function remains the same as provided]
def post_budget_update(year_month: str, account: str, payload: Dict[str, Any]) -> bool:
    """Posts budget updates to the backend API."""
    post_url = f"{BUDGET_API_URL}/{year_month}/{account}"
    try:
        logger.info(f"Attempting to POST budget update to: {post_url} with payload: {payload}")
        response = requests.post(post_url, json=payload, timeout=15)
        response.raise_for_status()
        response_data = response.json()
        if response_data.get("success"):
            logger.info(f"Successfully updated budget for {account} in {year_month}.")
            return True
        else:
            error_message = response_data.get("message", "Unknown error from API.")
            logger.warning(f"API reported failure updating budget: {error_message}")
            st.toast(f"⚠️ {error_message}", icon="⚠️")
            return False
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error posting budget update to {post_url}.")
        st.toast(f"❌ Error: Could not connect to the backend API at {API_BASE_URL}.", icon="❌")
        return False
    except requests.exceptions.Timeout:
        logger.error(f"Timeout posting budget update to {post_url}.")
        st.toast("❌ Error: The request to the backend API timed out.", icon="❌")
        return False
    except requests.exceptions.HTTPError as e:
        error_detail = "Unknown error"
        try:
            error_json = e.response.json()
            if "detail" in error_json:
                 if isinstance(error_json["detail"], list) and error_json["detail"]:
                      first_error = error_json["detail"][0]
                      loc = first_error.get('loc', ['?', '?'])
                      field = loc[-1] if len(loc) > 1 else 'N/A'
                      error_detail = f"{first_error.get('msg', 'Validation error')} (Field: {field})"
                 elif isinstance(error_json["detail"], str):
                      error_detail = error_json["detail"]
                 else:
                      error_detail = str(error_json["detail"])
            else:
                error_detail = e.response.text
        except Exception:
            error_detail = e.response.text
        logger.error(f"HTTP error posting budget update: {e.response.status_code} - {error_detail}")
        st.toast(f"❌ Error {e.response.status_code}: {error_detail}", icon="❌")
        return False
    except requests.exceptions.RequestException as e:
        logger.exception(f"General error posting budget update: {e}")
        st.toast(f"❌ Error: An unexpected error occurred: {e}", icon="❌")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error processing POST response: {e}")
        st.toast(f"❌ Error processing API response: {e}", icon="❌")
        return False


# --- Helper Function for Bar Chart (Remains the same) ---
# [NOTE: create_budget_bar_chart function remains the same as provided]
def create_budget_bar_chart(budget: float, spend: float, title: str) -> go.Figure:
    """Creates a simple Plotly bar chart comparing budget vs spend."""
    display_budget_for_range = max(budget, 1.0) if spend > 0 else budget
    df = pd.DataFrame({'Category': ['Budget', 'Current Spend'], 'Amount': [budget, spend]})
    fig = go.Figure()
    fig.add_trace(go.Bar(x=['Budget'], y=[budget], name='Budget', marker_color='lightblue', text=f"₹{budget:,.0f}", textposition='outside', hoverinfo='name+y'))
    fig.add_trace(go.Bar(x=['Current Spend'], y=[spend], name='Current Spend', marker_color='salmon', text=f"₹{spend:,.0f}", textposition='outside', hoverinfo='name+y'))
    fig.update_layout(
        title=dict(text=title, x=0.5, font_size=16),
        yaxis_title="Amount (INR)", xaxis_title=None, xaxis=dict(showticklabels=False),
        yaxis=dict(range=[0, max(display_budget_for_range, spend) * 1.2]), showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        bargap=0.4, margin=dict(l=40, r=20, t=50, b=90), height=350
    )
    fig.update_yaxes(hoverformat = ".2f")
    return fig

# --- Main Render Function ---
def render():
    """Renders the Budget page dynamically using API data."""
    st.subheader("Monthly Budget Overview")

    current_date = datetime.date.today()
    current_year_month = current_date.strftime("%Y-%m")
    current_month_display = current_date.strftime("%B %Y")

    api_data = fetch_budget_data_from_api(current_year_month)

    if api_data is None:
        st.warning("Could not load budget data. Please ensure the backend API is running and refresh.")
        if st.button("Retry Fetching Data"):
            st.rerun()
        return

    col_icici, col_sbi = st.columns(2)
    accounts_to_display = ["Anirban-ICICI", "Anirban-SBI"]
    account_columns = {"Anirban-ICICI": col_icici, "Anirban-SBI": col_sbi}

    for account_name in accounts_to_display:
        with account_columns[account_name]:
            account_data = api_data.get(account_name, {})
            budget = float(account_data.get("budget_amount", 0.0))
            spend = float(account_data.get("current_spend", 0.0))
            start_balance = float(account_data.get("start_balance", 0.0))
            end_balance = float(account_data.get("end_balance", 0.0))
            remaining = budget - spend

            st.markdown(f"##### {account_name} ({current_month_display})")

            # Metrics Display remains the same
            st.metric(label="Budget", value=f"₹{budget:,.2f}")
            row2_col1, row2_col2 = st.columns(2)
            with row2_col1:
                st.metric(label="Current Spend", value=f"₹{spend:,.2f}")
            with row2_col2:
                st.metric(label="Remaining", value=f"₹{remaining:,.2f}")
            row3_col1, row3_col2 = st.columns(2)
            with row3_col1:
                st.metric(label="Start Balance", value=f"₹{start_balance:,.2f}")
            with row3_col2:
                st.metric(label="End Balance", value=f"₹{end_balance:,.2f}")

            # --- Edit Form within Expander ---
            with st.expander("Update Budget/Balances", expanded=False):
                # Use a unique key for the form based on the account
                with st.form(key=f"edit_form_{account_name}"):

                    new_budget = st.number_input(
                        label="Budget Amount",
                        min_value=0.0, value=budget, format="%.2f",
                        step=1000.0, key=f"edit_budget_{account_name}",
                        label_visibility="visible"
                    )

                    # CHANGE: Row 2 - Balances (Side-by-side)
                    form_col1, form_col2 = st.columns(2)
                    with form_col1:
                        new_start_balance = st.number_input(
                            label="Starting Balance",
                            value=start_balance, format="%.2f",
                            step=1000.0, key=f"edit_start_bal_{account_name}",
                            label_visibility="visible"
                        )
                    with form_col2:
                        new_end_balance = st.number_input(
                            label="Ending Balance",
                            value=end_balance, format="%.2f",
                            step=1000.0, key=f"edit_end_bal_{account_name}",
                            label_visibility="visible"
                        )

                    submitted = st.form_submit_button("Save")

                    if submitted:
                        # Submission logic remains the same
                        update_payload = {
                            "budget_amount": new_budget,
                            "start_balance": new_start_balance,
                            "end_balance": new_end_balance
                        }
                        success = post_budget_update(current_year_month, account_name, update_payload)
                        if success:
                            st.toast("✅ Budget updated!", icon="✅")
                            time.sleep(1) # Keep brief pause before rerun
                            st.rerun()
            # --- End Edit Form ---

            # Progress Bar remains the same
            progress_value = 0.0
            if budget > 0:
                progress_value = max(0.0, min(1.0, spend / budget))
            elif spend > 0:
                progress_value = 1.0
            st.progress(progress_value)

            # Bar Chart remains the same
            chart = create_budget_bar_chart(budget, spend, f"{account_name}")
            st.plotly_chart(chart, use_container_width=True)

    # Refresh button remains at bottom left
    st.divider()
    if st.button("🔄 Refresh", key="update_spend_button", help="Fetch latest data"):
        st.rerun()