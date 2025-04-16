# tabs/add_expense.py
import streamlit as st
import pandas as pd
from db_utils import insert_expense, fetch_last_expenses
import json
import datetime
from typing import Dict, Any, Optional
import logging # <<<--- ADD THIS IMPORT

@st.cache_data
def load_metadata() -> Optional[Dict[str, Any]]:
    """Loads metadata from the expense_metadata.json file."""
    try:
        with open("expense_metadata.json", "r") as f:
            metadata = json.load(f)
            logging.debug("Metadata loaded successfully for Add Expense.") # More specific log
            return metadata
    except FileNotFoundError:
        st.error("Error: expense_metadata.json not found.")
        logging.error("expense_metadata.json not found.")
        return None
    except json.JSONDecodeError:
        st.error("Error: Could not decode expense_metadata.json.")
        logging.error("Could not decode expense_metadata.json.")
        return None

def render():
    """Renders the 'Add Expense' page."""
    st.subheader("Add New Expense")

    metadata = load_metadata()
    if metadata is None:
        # Error already shown by load_metadata
        return

    # Fetch necessary lists from metadata safely
    all_accounts = metadata.get("Account", [])
    all_categories = sorted(list(metadata.get("categories", {}).keys()))
    user_map = metadata.get("User", {})
    category_map = metadata.get("categories", {})

    if not all_accounts or not all_categories:
        st.error("Metadata is missing essential 'Account' or 'categories' information.")
        logging.error("Metadata missing Account or categories in Add Expense.")
        return

    # --- Date Input ---
    expense_date = st.date_input(
        "Date of Expense",
        value=datetime.date.today(),
        help="Select the date the expense occurred (defaults to today)."
    )

    # --- Category / Sub-category Selection ---
    selected_category = st.selectbox(
        "Category", options=all_categories, index=0, key="add_category",
        help="Select the main expense category."
    )
    available_subcategories = sorted(category_map.get(selected_category, []))
    if not available_subcategories:
        st.warning(f"No sub-categories defined for '{selected_category}'. Please add them to metadata if needed.", icon="⚠️")

    # --- Expense Entry Form ---
    with st.form("expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            selected_account = st.selectbox(
                "Account", options=all_accounts, index=0, key="add_account",
                help="Select the account used for the expense."
            )
            selected_sub_category = st.selectbox(
                "Sub-category", options=available_subcategories, key="add_sub_category",
                help="Select the specific sub-category.",
                disabled=not available_subcategories
            )
        with col2:
            expense_type = st.text_input(
                "Type (Description)", max_chars=60, key="add_type",
                help="Enter a brief description (e.g., 'Lunch with team')."
            )
            expense_user = user_map.get(selected_account, "Unknown")
            # st.text(f"User: {expense_user}") # Display derived user
            expense_amount = st.number_input(
                "Amount (INR)", min_value=0.01, format="%.2f", step=10.0, key="add_amount",
                help="Enter the expense amount (must be positive)."
            )

        submitted = st.form_submit_button("Add Expense")
        if submitted:
            is_valid = True
            if not expense_type: st.toast("⚠️ Please enter a Type (Description).", icon="⚠️"); is_valid = False
            if expense_amount <= 0.0: st.toast("⚠️ Amount must be > 0.", icon="⚠️"); is_valid = False
            if available_subcategories and not selected_sub_category: st.toast(f"⚠️ Sub-category required for {selected_category}.", icon="⚠️"); is_valid = False
            # Check only if sub-category *should* exist but wasn't selected, or if selected one is invalid
            elif selected_sub_category and selected_sub_category not in available_subcategories: st.toast(f"❌ Invalid sub-category '{selected_sub_category}'.", icon="❌"); is_valid = False
            # Handle case where no sub-cats exist and none should be selected
            elif not available_subcategories and selected_sub_category: st.toast(f"❌ No sub-categories exist for {selected_category}.", icon="❌"); is_valid = False

            if is_valid:
                # Ensure sub-category is empty string if none are available/selected
                final_sub_category = selected_sub_category if available_subcategories else ""
                expense_data = {
                    "date": expense_date.strftime("%Y-%m-%d"), "account": selected_account,
                    "category": selected_category, "sub_category": final_sub_category,
                    "type": expense_type, "user": expense_user, "amount": expense_amount
                }
                try:
                    success = insert_expense(expense_data) # This function now logs internally
                    if success: st.toast(f"✅ Expense added!", icon="✅")
                    else: st.toast(f"❌ Failed to add expense (DB error).", icon="❌") # DB util logs specifics
                except Exception as e:
                    st.toast(f"❌ Error submitting expense: {e}", icon="❌")
                    logging.error(f"Exception during expense submission: {e}") # Log here too

    # --- Display Recent Expenses ---
    st.markdown("---")
    st.subheader("Last 10 Expenses Added")
    try:
        df_recent = fetch_last_expenses(10) # This function logs internally
        if df_recent.empty:
            st.info("No recent expenses recorded yet.")
        else:
            display_df_recent = df_recent.drop(columns=["id"], errors='ignore').rename(columns={
                "date": "Date", "account": "Account", "category": "Category",
                "sub_category": "Sub Category", "type": "Type", "user": "User", "amount": "Amount"
            })
            st.dataframe(
                display_df_recent.style.format({'Date': '{:%Y-%m-%d}', 'Amount': '₹{:.2f}'}),
                use_container_width=True, height=380, hide_index=True
            )
    except Exception as e:
        st.error(f"Error loading recent expenses: {e}")
        logging.error(f"Error displaying recent expenses: {e}")