import streamlit as st
import pandas as pd
from db_utils import insert_expense, fetch_last_expenses
import json
import datetime
from typing import Dict, Any, Optional
import logging
import time

@st.cache_data
def load_metadata() -> Optional[Dict[str, Any]]:
    try:
        with open("expense_metadata.json", "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load metadata: {e}")
        st.error("Could not load metadata.")
        return None

def render():
    # Step 1: Rerun logic (must go at the top)
    if "trigger_rerun" in st.session_state and time.time() > st.session_state["trigger_rerun"]:
        st.session_state.pop("trigger_rerun")
        st.rerun()

    st.subheader("Add New Expense")

    metadata = load_metadata()
    if metadata is None:
        return

    all_accounts = metadata.get("Account", [])
    all_categories = sorted(list(metadata.get("categories", {}).keys()))
    user_map = metadata.get("User", {})
    category_map = metadata.get("categories", {})

    if not all_accounts or not all_categories:
        st.error("Invalid metadata structure.")
        return

    expense_date = st.date_input("Date of Expense", value=datetime.date.today())

    selected_category = st.selectbox("Category", options=all_categories, index=0, key="add_category")
    available_subcategories = sorted(category_map.get(selected_category, []))

    with st.form("expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            selected_account = st.selectbox("Account", options=all_accounts, key="add_account")
            selected_sub_category = st.selectbox("Sub-category", options=available_subcategories, key="add_sub_category", disabled=not available_subcategories)
        with col2:
            expense_type = st.text_input("Type (Description)", max_chars=60, key="add_type")
            expense_user = user_map.get(selected_account, "Unknown")
            expense_amount = st.number_input("Amount (INR)", min_value=0.01, format="%.2f", step=10.0, key="add_amount")

        submitted = st.form_submit_button("Add Expense")

        if submitted:
            is_valid = True
            if not expense_type: st.toast("⚠️ Please enter a Type.", icon="⚠️"); is_valid = False
            if expense_amount <= 0: st.toast("⚠️ Enter valid amount.", icon="⚠️"); is_valid = False
            if available_subcategories and not selected_sub_category: st.toast("⚠️ Select a sub-category.", icon="⚠️"); is_valid = False

            if is_valid:
                final_sub_category = selected_sub_category if available_subcategories else ""
                dt = pd.to_datetime(expense_date)

                expense_data = {
                    "date": dt.strftime("%Y-%m-%d"),
                    "year": dt.year,
                    "month": dt.to_period("M").strftime("%Y-%m"),
                    "week": dt.strftime("%G-W%V"),
                    "day_of_week": dt.day_name(),
                    "account": selected_account,
                    "category": selected_category,
                    "sub_category": final_sub_category,
                    "type": expense_type,
                    "user": expense_user,
                    "amount": expense_amount
                }

                success = insert_expense(expense_data)
                if success:
                    st.toast("✅ Expense added!", icon="✅")
                    st.success("Entry saved.")
                    st.session_state["last_added"] = expense_data
                    st.session_state["highlight_time"] = time.time()
                    st.session_state["trigger_rerun"] = time.time() + 3  # rerun after table is visible
                else:
                    st.toast("❌ Failed to save to DB.", icon="❌")

    st.markdown("---")
    st.subheader("Last 10 Expenses Added")

    try:
        df = fetch_last_expenses(10)
        if df.empty:
            st.info("No recent expenses recorded yet.")
            return

        highlight_index = None
        last = st.session_state.get("last_added", None)
        t0 = st.session_state.get("highlight_time", None)

        if t0 and time.time() - t0 > 5:
            st.session_state.pop("last_added", None)
            st.session_state.pop("highlight_time", None)
        elif last is not None:
            match = df[
                (df["date"] == last["date"]) &
                (df["account"] == last["account"]) &
                (df["category"] == last["category"]) &
                (df["sub_category"] == last["sub_category"]) &
                (df["type"] == last["type"]) &
                (df["user"] == last["user"]) &
                (df["amount"] == float(last["amount"]))
            ]
            if not match.empty:
                highlight_index = match.index[0]

        display_df = df.drop(columns=["id", "year", "month", "week", "day_of_week"], errors="ignore").rename(columns={
            "date": "Date", "account": "Account", "category": "Category",
            "sub_category": "Sub Category", "type": "Type", "user": "User", "amount": "Amount"
        })

        def highlight(row):
            return ['background-color: #d1ffd6'] * len(row) if row.name == highlight_index else [''] * len(row)

        st.dataframe(
            display_df.style
                .format({"Date": "{:%Y-%m-%d}", "Amount": "₹{:.2f}"})
                .apply(highlight, axis=1),
            use_container_width=True, height=380, hide_index=True
        )

    except Exception as e:
        logging.exception("Failed to display table")
        st.error(f"Error loading recent expenses: {e}")
