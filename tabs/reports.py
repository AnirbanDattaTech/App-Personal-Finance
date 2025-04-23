# tabs/reports.py
import streamlit as st
import pandas as pd
import datetime
import json
import logging
from typing import Dict, Any, Optional
from db_utils import fetch_all_expenses, fetch_expense_by_id, update_expense, delete_expense

@st.cache_data
def load_metadata() -> Optional[Dict[str, Any]]:
    try:
        with open("expense_metadata.json", "r") as f:
            return json.load(f)
    except Exception as e:
        st.error("Could not load metadata.")
        logging.error(f"Metadata load error: {e}")
        return None

@st.cache_data
def convert_df_to_csv(df: pd.DataFrame) -> bytes:
    try:
        return df.to_csv(index=False).encode("utf-8")
    except Exception as e:
        logging.error(f"CSV conversion failed: {e}")
        return b""

def render():
    st.session_state.setdefault("edit_mode", False)
    st.session_state.setdefault("delete_confirm", False)
    st.session_state.setdefault("selected_expense_id", None)

    metadata = load_metadata()
    if metadata is None:
        return

    if st.session_state.edit_mode:
        if st.session_state.selected_expense_id:
            expense = fetch_expense_by_id(st.session_state.selected_expense_id)
            if expense:
                display_edit_form(expense, metadata)
            else:
                st.error("Could not load expense to edit.")
            return
    elif st.session_state.delete_confirm:
        if st.session_state.selected_expense_id:
            expense = fetch_expense_by_id(st.session_state.selected_expense_id)
            if expense:
                display_delete_confirmation(expense)
            else:
                st.error("Could not load expense to delete.")
            return

    render_report_view(metadata)

def render_report_view(metadata: Dict[str, Any]):
    st.subheader("Expense Report")

    df_all = fetch_all_expenses()
    if df_all.empty:
        st.info("No expense data available.")
        return

    df_all["month"] = df_all["date"].dt.strftime("%Y-%m")
    all_accounts = metadata["Account"]
    all_categories = sorted(metadata["categories"].keys())
    all_users = sorted(set(metadata["User"].values()))

    # --- Filter Layout ---
    month_selected = st.selectbox("Select Month", ["All"] + sorted(df_all["month"].unique(), reverse=True))

    col1, col2 = st.columns(2)
    with col1:
        accounts = st.multiselect("Account", ["All"] + all_accounts, default=["All"])
        categories = st.multiselect("Category", ["All"] + all_categories, default=["All"])
    with col2:
        users = st.multiselect("User", ["All"] + all_users, default=["All"])
        selected_categories = categories if "All" not in categories else all_categories
        available_subcats = sorted({sub for cat in selected_categories for sub in metadata["categories"][cat]})
        subcategory = st.selectbox("Sub-category", ["All"] + available_subcats)

    # --- Apply Filters ---
    df = df_all.copy()
    if month_selected != "All":
        df = df[df["month"] == month_selected]
    if "All" not in accounts:
        df = df[df["account"].isin(accounts)]
    if "All" not in categories:
        df = df[df["category"].isin(categories)]
    if subcategory != "All":
        df = df[df["sub_category"] == subcategory]
    if "All" not in users:
        df = df[df["user"].isin(users)]

    # --- Summary Stats ---
    total = df["amount"].sum()
    st.markdown(f"### Total Expense (Filtered): ₹{total:,.2f}")

    if not df.empty:
        st.markdown("#### Summary Statistics")
        txns = len(df)
        avg_amt = df["amount"].mean()
        top_cat = df.groupby("category")["amount"].sum().nlargest(1)
        top_cat_display = f"{top_cat.index[0]} (₹{top_cat.values[0]:,.0f})" if not top_cat.empty else "N/A"

        col1, col2, col3 = st.columns(3)
        col1.metric("Transactions", f"{txns:,}")
        col2.metric("Avg. Transaction", f"₹{avg_amt:,.2f}")
        col3.metric("Top Category", top_cat_display)

    # --- Section Title + Refresh Button ---
    col_left, col_spacer, col_right = st.columns([5, 1, 1])
    with col_left:
        st.markdown("### Detailed Transactions")
    with col_right:
        if st.button("🔄 Refresh Data", help="Click to reload data from database"):
            st.session_state["force_refresh"] = True

    if st.session_state.get("force_refresh", False):
        st.session_state["force_refresh"] = False
        st.rerun()

    # --- Table Display ---
    display_df = df.drop(columns=["id", "year", "week", "day_of_week", "month"], errors="ignore").rename(columns={
        "date": "Date",
        "account": "Account",
        "category": "Category",
        "sub_category": "Sub Category",
        "type": "Type",
        "user": "User",
        "amount": "Amount"
    }).sort_values("Date", ascending=False)

    st.dataframe(
        display_df.style.format({"Date": "{:%Y-%m-%d}", "Amount": "₹{:.2f}"}),
        use_container_width=True,
        height=400,
        hide_index=True
    )

    # --- Edit / Delete Controls ---
    if not df.empty:
        st.markdown("#### Edit / Delete Expense")
        df = df.sort_values("date", ascending=False).head(500)
        df["display"] = df.apply(lambda row: f"{row['date'].strftime('%Y-%m-%d')} {row['account']} {row['category']} {row['sub_category'][:15]} ₹{row['amount']:.0f}", axis=1)
        selector_map = {row["display"]: row["id"] for row in df[["display", "id"]].to_dict("records")}
        selector_map = {"-- Select expense --": None, **selector_map}

        selected_label = st.selectbox("Select Expense to Modify", list(selector_map.keys()))
        selected_id = selector_map[selected_label]

        col1, col2 = st.columns([1, 1])
        if col1.button("Edit Selected", disabled=not selected_id):
            st.session_state.selected_expense_id = selected_id
            st.session_state.edit_mode = True
            st.rerun()
        if col2.button("Delete Selected", disabled=not selected_id):
            st.session_state.selected_expense_id = selected_id
            st.session_state.delete_confirm = True
            st.rerun()

        csv = convert_df_to_csv(display_df)
        st.download_button("📥 Export to CSV", csv, "filtered_expenses.csv", "text/csv")

def display_edit_form(expense_data: Dict[str, Any], metadata: Dict[str, Any]):
    st.subheader("Edit Expense")
    all_categories = sorted(metadata["categories"].keys())
    all_accounts = metadata["Account"]
    user_map = metadata["User"]
    category_map = metadata["categories"]

    default_date = pd.to_datetime(expense_data["date"]).date()
    default_category = expense_data["category"]
    subcats = sorted(category_map.get(default_category, []))

    with st.form("edit_form"):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date", value=default_date)
            account = st.selectbox("Account", all_accounts, index=all_accounts.index(expense_data["account"]))
            category = st.selectbox("Category", all_categories, index=all_categories.index(default_category))
        with col2:
            subcat = st.selectbox("Sub-category", subcats, index=subcats.index(expense_data["sub_category"]))
            type_ = st.text_input("Type", value=expense_data["type"])
            user = user_map[account]
            amount = st.number_input("Amount (INR)", value=float(expense_data["amount"]), min_value=0.01)

        if st.form_submit_button("Save Changes"):
            update_expense(expense_data["id"], {
                "date": date.strftime("%Y-%m-%d"),
                "account": account,
                "category": category,
                "sub_category": subcat,
                "type": type_,
                "user": user,
                "amount": amount
            })
            st.success("Expense updated.")
            st.session_state.edit_mode = False
            st.rerun()

def display_delete_confirmation(expense_data: Dict[str, Any]):
    st.warning("⚠️ Are you sure you want to delete this expense?")
    st.write(expense_data)
    col1, col2 = st.columns(2)
    if col1.button("Yes, Delete"):
        delete_expense(expense_data["id"])
        st.success("Deleted successfully.")
        st.session_state.delete_confirm = False
        st.rerun()
    if col2.button("Cancel"):
        st.session_state.delete_confirm = False
        st.rerun()
