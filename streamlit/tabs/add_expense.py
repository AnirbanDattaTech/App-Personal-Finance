# streamlit/tabs/add_expense.py
import streamlit as st
import pandas as pd
from db_utils import insert_expense, fetch_last_expenses # Use direct import based on previous findings
import json
import datetime
from typing import Dict, Any, Optional
import logging
import time
from pathlib import Path

# Define Metadata Path relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
METADATA_FILE_PATH = PROJECT_ROOT / "metadata" / "expense_metadata.json"

@st.cache_data
def load_metadata() -> Optional[Dict[str, Any]]:
    """Loads metadata from the project's metadata directory."""
    if not METADATA_FILE_PATH.is_file():
        logging.error(f"Metadata file not found at: {METADATA_FILE_PATH}")
        st.error(f"Critical application error: Metadata configuration file not found at {METADATA_FILE_PATH}. Please ensure it exists.")
        return None
    try:
        with open(METADATA_FILE_PATH, "r") as f:
            metadata = json.load(f)
            logging.info(f"Metadata loaded successfully from {METADATA_FILE_PATH}")
            return metadata
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {METADATA_FILE_PATH}: {e}", exc_info=True)
        st.error(f"Critical application error: Metadata file ({METADATA_FILE_PATH.name}) seems corrupted.")
        return None
    except Exception as e:
        logging.exception(f"Failed to load or parse metadata from {METADATA_FILE_PATH}: {e}")
        st.error("Critical application error: An unexpected error occurred while loading metadata.")
        return None

def render():
    """Renders the Add Expense page."""
    if "trigger_rerun" in st.session_state and time.time() > st.session_state["trigger_rerun"]:
        st.session_state.pop("trigger_rerun", None)
        st.rerun()

    st.subheader("Add New Expense")

    metadata = load_metadata()
    if metadata is None:
        return

    # Extract metadata components safely
    all_accounts = metadata.get("Account", [])
    category_map = metadata.get("categories", {})
    all_categories = sorted(list(category_map.keys()))
    user_map = metadata.get("User", {})

    if not all_accounts or not all_categories or not category_map or not user_map:
        st.error("Metadata structure is invalid or incomplete. Cannot proceed.")
        logging.error("Invalid metadata structure detected after loading.")
        return

    # --- Inputs outside the form ---
    expense_date = st.date_input("Date of Expense", value=datetime.date.today(), key="add_date")
    selected_category = st.selectbox("Category", options=all_categories, index=0, key="add_category")
    available_subcategories = sorted(category_map.get(selected_category, []))

    # --- Input Form ---
    with st.form("expense_form", clear_on_submit=True):
        # Use columns for side-by-side layout
        col1, col2 = st.columns(2)

        # --- Widgets in Columns ---
        # It's important that the order matches visually top-to-bottom
        with col1:
            selected_account = st.selectbox("Account", options=all_accounts, key="add_account")
            subcat_disabled = not bool(available_subcategories)
            selected_sub_category = st.selectbox(
                "Sub-category",
                options=available_subcategories,
                key="add_sub_category", # Key remains the same
                disabled=subcat_disabled,
                help="Select a sub-category if applicable." if not subcat_disabled else "No sub-categories for this category."
            )

        with col2:
            expense_type = st.text_input("Type (Description)", max_chars=60, key="add_type", help="Enter a brief description of the expense.")
            expense_amount = st.number_input("Amount (INR)", min_value=0.01, format="%.2f", step=10.0, key="add_amount") # Key remains the same

        # --- Form Submission Button ---
        submitted = st.form_submit_button("Add Expense")

        # --- Submission Logic ---
        if submitted:
            is_valid = True
            expense_user = user_map.get(selected_account, "Unknown") # Derive user here
            if not expense_type.strip():
                st.toast("⚠️ Please enter a Type/Description.", icon="⚠️"); is_valid = False
            if expense_amount <= 0:
                 st.toast("⚠️ Amount must be greater than zero.", icon="⚠️"); is_valid = False
            if available_subcategories and not selected_sub_category:
                st.toast("⚠️ Please select a Sub-category.", icon="⚠️"); is_valid = False

            if is_valid:
                final_sub_category = selected_sub_category if available_subcategories else ""
                dt = pd.to_datetime(expense_date)
                expense_data = {
                    "date": dt.strftime("%Y-%m-%d"), "year": dt.year,
                    "month": dt.to_period("M").strftime("%Y-%m"), "week": dt.strftime("%G-W%V"),
                    "day_of_week": dt.day_name(), "account": selected_account,
                    "category": selected_category, "sub_category": final_sub_category,
                    "type": expense_type.strip(), "user": expense_user, "amount": expense_amount
                }
                success = insert_expense(expense_data)
                if success:
                    st.toast("✅ Expense added successfully!", icon="✅")
                    st.session_state["last_added"] = expense_data
                    st.session_state["highlight_time"] = time.time()
                else:
                    st.toast("❌ Failed to save expense to the database.", icon="❌")

    # --- Display Recent Entries ---
    if "last_added" in st.session_state and "highlight_time" in st.session_state:
         # Check if highlight time has expired
         if time.time() - st.session_state["highlight_time"] <= 5:
              st.success("Entry saved successfully!") # Show success message briefly
         else:
              # Clear state after timeout
              st.session_state.pop("last_added", None)
              st.session_state.pop("highlight_time", None)

    st.markdown("---")
    st.subheader("Last 10 Expenses Added")
    try:
        df = fetch_last_expenses(10)
        if df.empty:
            st.info("No recent expenses recorded yet.")
        else:
            highlight_index = None
            last_added_data = st.session_state.get("last_added")
            highlight_start_time = st.session_state.get("highlight_time")

            if highlight_start_time and (time.time() - highlight_start_time > 5):
                 st.session_state.pop("last_added", None)
                 st.session_state.pop("highlight_time", None)
                 last_added_data = None

            if last_added_data:
                match = df[
                    (df["date"].dt.strftime('%Y-%m-%d') == last_added_data["date"]) &
                    (df["account"] == last_added_data["account"]) &
                    (df["category"] == last_added_data["category"]) &
                    (df["sub_category"].fillna("") == last_added_data["sub_category"]) &
                    (df["type"] == last_added_data["type"]) &
                    (df["user"] == last_added_data["user"]) &
                    (df["amount"].round(2) == round(float(last_added_data["amount"]), 2))
                ]
                if not match.empty:
                    highlight_index = match.index[0]

            display_df = df.drop(columns=["id", "year", "month", "week", "day_of_week"], errors="ignore").rename(columns={
                "date": "Date", "account": "Account", "category": "Category",
                "sub_category": "Sub Category", "type": "Type", "user": "User", "amount": "Amount (INR)"
            })

            def highlight_row_conditionally(row):
                is_highlighted = row.name == highlight_index
                return ['background-color: #d1ffd6' if is_highlighted else '' for _ in row]

            st.dataframe(
                display_df.style
                    .format({"Date": "{:%Y-%m-%d}", "Amount (INR)": "₹{:.2f}"})
                    .apply(highlight_row_conditionally, axis=1),
                use_container_width=True, height=380, hide_index=True
            )
    except Exception as e:
        logging.exception("Failed to display recent expenses table")
        st.error(f"Error loading recent expenses: {e}")