# tabs/visuals.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import datetime
from db_utils import fetch_all_expenses
from typing import Dict, Any, Optional
import logging

@st.cache_data
def load_metadata() -> Optional[Dict[str, Any]]:
    """Loads metadata from the expense_metadata.json file."""
    try:
        with open("expense_metadata.json", "r") as f:
            return json.load(f)
    except Exception as e:
        st.error("Error loading metadata.")
        logging.exception(e)
        return None

def get_common_layout_args(chart_title: str, show_legend: bool = False) -> Dict[str, Any]:
    return {
        "title_text": chart_title,
        "title_font_size": 16,
        "title_x": 0.5,
        "margin": dict(l=10, r=10, t=40, b=100 if show_legend else 60),
        "legend": dict(
            orientation="h",
            yanchor="top",
            y=-0.3,
            xanchor="center",
            x=0.5
        ),
        "hovermode": "closest",
        "showlegend": show_legend
    }


def render():
    """Renders the 'Visualizations' page with a 2x2 grid of charts."""
    st.subheader("Expense Visualizations")
    metadata = load_metadata()
    if metadata is None:
        return

    df_all = fetch_all_expenses()
    if df_all.empty:
        st.info("No expense data available.")
        return

    df_all['date'] = pd.to_datetime(df_all['date'], errors='raise')
    df_all['YearMonth'] = df_all['date'].dt.strftime('%Y-%m')
    min_date = df_all['date'].min().date()
    max_date = df_all['date'].max().date()
    all_months = ["All"] + sorted(df_all['YearMonth'].unique(), reverse=True)
    all_categories = ["All"] + sorted(list(metadata.get("categories", {}).keys()))
    all_users = ["All"] + sorted(list(set(metadata.get("User", {}).values())))
    all_accounts = ["All"] + metadata.get("Account", [])

    # Initialize session state for legend visibility
    if 'legends' not in st.session_state:
        st.session_state.legends = {
            'pie': False,
            'bar': False,
            'line': False,
            'top': False
        }

    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    # PIE CHART
    with col1:
        st.markdown("#### By Category (Proportion)")
        with st.expander("Filters", expanded=False):
            pie_month = st.selectbox("Month", all_months, 0, key="pie_month")
            pie_cats = st.multiselect("Category", all_categories, ["All"], key="pie_cat")
            pie_accounts = st.multiselect("Account", all_accounts, ["All"], key="pie_account")
            pie_users = st.multiselect("User", all_users, ["All"], key="pie_user")
        
        # Compact toggle button
        cols = st.columns([1,4])
        with cols[0]:
            if st.button("Toggle Legend", key="pie_legend_btn"):
                st.session_state.legends['pie'] = not st.session_state.legends['pie']

        pie_df = df_all.copy()
        if pie_month != "All":
            pie_df = pie_df[pie_df['YearMonth'] == pie_month]
        if "All" not in pie_cats:
            pie_df = pie_df[pie_df['category'].isin(pie_cats)]
        if "All" not in pie_accounts:
            pie_df = pie_df[pie_df['account'].isin(pie_accounts)]
        if "All" not in pie_users:
            pie_df = pie_df[pie_df['user'].isin(pie_users)]

        pie_data = pie_df.groupby('category')['amount'].sum().reset_index()
        if not pie_data.empty:
            fig = px.pie(pie_data, values='amount', names='category', hole=0.4)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(**get_common_layout_args("Spending by Category", st.session_state.legends['pie']))
            st.plotly_chart(fig, use_container_width=True)

    # BAR CHART
    with col2:
        st.markdown("#### By Category (Absolute)")
        with st.expander("Filters", expanded=False):
            bar_start = st.date_input("Start Date", min_date, key="bar_start")
            bar_end = st.date_input("End Date", max_date, key="bar_end")
            bar_accounts = st.multiselect("Account", all_accounts, ["All"], key="bar_account")
            bar_users = st.multiselect("User", all_users, ["All"], key="bar_user")
        
        cols = st.columns([1,4])
        with cols[0]:
            if st.button("Toggle Legend", key="bar_legend_btn"):
                st.session_state.legends['bar'] = not st.session_state.legends['bar']

        bar_df = df_all[(df_all['date'].dt.date >= bar_start) & (df_all['date'].dt.date <= bar_end)]
        if "All" not in bar_accounts:
            bar_df = bar_df[bar_df['account'].isin(bar_accounts)]
        if "All" not in bar_users:
            bar_df = bar_df[bar_df['user'].isin(bar_users)]

        bar_data = bar_df.groupby('category')['amount'].sum().reset_index()
        if not bar_data.empty:
            fig = px.bar(bar_data, x='category', y='amount', color='category')
            layout = get_common_layout_args("Total Spending by Category", st.session_state.legends['bar'])
            layout["yaxis_title"] = "Amount (INR)"
            layout["xaxis"] = dict(categoryorder='total descending')
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True)

    # LINE CHART
    with col3:
        st.markdown("#### Trend Over Time")
        with st.expander("Filters", expanded=False):
            line_start = st.date_input("Start Date", min_date, key="line_start")
            line_end = st.date_input("End Date", max_date, key="line_end")
            line_cats = st.multiselect("Category", all_categories, ["All"], key="line_cat")
            line_accounts = st.multiselect("Account", all_accounts, ["All"], key="line_account")
            line_users = st.multiselect("User", all_users, ["All"], key="line_user")
            line_mode = st.radio("View", ["Daily", "Cumulative"], 0, horizontal=True, key="line_mode")
        
        cols = st.columns([1,4])
        with cols[0]:
            if st.button("Toggle Legend", key="line_legend_btn"):
                st.session_state.legends['line'] = not st.session_state.legends['line']

        line_df = df_all[(df_all['date'].dt.date >= line_start) & (df_all['date'].dt.date <= line_end)]
        if "All" not in line_cats:
            line_df = line_df[line_df['category'].isin(line_cats)]
        if "All" not in line_accounts:
            line_df = line_df[line_df['account'].isin(line_accounts)]
        if "All" not in line_users:
            line_df = line_df[line_df['user'].isin(line_users)]

        trend = line_df.groupby('date')['amount'].sum().reset_index()
        fig = go.Figure()
        if not trend.empty:
            if line_mode == "Daily":
                fig.add_trace(go.Scatter(x=trend['date'], y=trend['amount'], mode='lines+markers'))
            else:
                trend['cumulative'] = trend['amount'].cumsum()
                fig.add_trace(go.Scatter(x=trend['date'], y=trend['cumulative'], mode='lines+markers', line=dict(dash='dot')))
            layout = get_common_layout_args("Spending Trend", st.session_state.legends['line'])
            layout["yaxis_title"] = "Amount (INR)"
            layout["xaxis"] = dict(rangeslider=dict(visible=True), type="date")
            layout["hovermode"] = "x unified"
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True)

    # TOP 10 TYPE
    with col4:
        st.markdown("#### Top 10 Expenses by Type")
        with st.expander("Filters", expanded=False):
            top_start = st.date_input("Start Date", min_date, key="top_start")
            top_end = st.date_input("End Date", max_date, key="top_end")
            top_accounts = st.multiselect("Account", all_accounts, ["All"], key="top_account")
            top_users = st.multiselect("User", all_users, ["All"], key="top_user")
        
        cols = st.columns([1,4])
        with cols[0]:
            if st.button("Toggle Legend", key="top_legend_btn"):
                st.session_state.legends['top'] = not st.session_state.legends['top']

        top_df = df_all[(df_all['date'].dt.date >= top_start) & (df_all['date'].dt.date <= top_end)]
        if "All" not in top_accounts:
            top_df = top_df[top_df['account'].isin(top_accounts)]
        if "All" not in top_users:
            top_df = top_df[top_df[top_users]]

        top_data = top_df.groupby('type')['amount'].sum().reset_index().sort_values('amount', ascending=False).head(10)
        if not top_data.empty:
            fig = px.bar(top_data, x='amount', y='type', orientation='h', text='amount', color='type')
            layout = get_common_layout_args("Top 10 Expense Types", st.session_state.legends['top'])
            layout["xaxis_title"] = "Amount (INR)"
            layout["yaxis_title"] = ""
            fig.update_layout(**layout)
            fig.update_traces(texttemplate="₹%{x:,.0f}", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)