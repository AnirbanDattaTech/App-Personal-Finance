# streamlit/tabs/budget.py
"""
Renders the static 'Budget' tab UI based on predefined mock data.
Includes placeholders for Start/End Balance.
Uses a grid layout for metrics.
Replaces inline edit buttons with a single placeholder "Edit" button per account,
intended to trigger a popover/form in the functional version.
"""
import streamlit as st
import plotly.graph_objects as go
import datetime
import pandas as pd # Using pandas for easy bar chart data creation

# --- Helper Function for Bar Chart (Remains the same) ---
def create_budget_bar_chart(budget: float, spend: float, title: str) -> go.Figure:
    """Creates a simple Plotly bar chart comparing budget vs spend."""
    display_budget_for_range = max(budget, 1.0) # Use at least 1 for y-axis range

    df = pd.DataFrame({
        'Category': ['Budget', 'Current Spend'],
        'Amount': [budget, spend]
    })

    fig = go.Figure()

    # Budget Bar
    fig.add_trace(go.Bar(
        x=['Budget'],
        y=[budget],
        name='Budget',
        marker_color='lightblue',
        text=f"₹{budget:,.0f}",
        textposition='outside',
        hoverinfo='name+y'
    ))

    # Spend Bar
    fig.add_trace(go.Bar(
        x=['Current Spend'],
        y=[spend],
        name='Current Spend',
        marker_color='salmon',
        text=f"₹{spend:,.0f}",
        textposition='outside',
        hoverinfo='name+y'
    ))

    # Customize layout
    fig.update_layout(
        title=dict(text=title, x=0.5, font_size=16),
        yaxis_title="Amount (INR)",
        xaxis_title=None,
        xaxis=dict(showticklabels=False),
        yaxis=dict(range=[0, max(display_budget_for_range, spend) * 1.2]),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        bargap=0.4,
        margin=dict(l=40, r=20, t=50, b=90),
        height=350
    )
    fig.update_yaxes(hoverformat = ".2f")

    return fig


# --- Main Render Function ---
def render():
    """Renders the Budget page mock UI with cleaned-up metric display and placeholder edit buttons."""
    st.subheader("Monthly Budget Overview")

    # --- Get Current Month ---
    current_date = datetime.date.today()
    current_month_str = current_date.strftime("%B %Y")

    # --- Mock Data ---
    mock_data = {
        "Anirban-ICICI": {
            "budget": 50000.0,
            "spend": 30000.0,
            "start_balance": 60000.0,
            "end_balance": 20000.0
        },
        "Anirban-SBI": {
            "budget": 0.0,
            "spend": 4000.0,
            "start_balance": 15000.0,
            "end_balance": 5000.0
        }
    }

    # --- Main Layout ---
    col_icici, col_sbi = st.columns(2)

    # --- Process Each Account Column ---
    accounts = {"Anirban-ICICI": col_icici, "Anirban-SBI": col_sbi}

    for account_name, column in accounts.items():
        with column:
            budget = mock_data[account_name]["budget"]
            spend = mock_data[account_name]["spend"]
            start_balance = mock_data[account_name]["start_balance"]
            end_balance = mock_data[account_name]["end_balance"]
            remaining = budget - spend
            percent_remaining = (remaining / budget) * 100 if budget > 0 else (-100 if spend > 0 else 0)

            st.markdown(f"#### {account_name}")
            st.markdown(f"**Month:** {current_month_str}")
            st.divider()

            # --- Grid Layout for Metrics (No inline buttons) ---

            # Row 1: Budget
            st.metric(label="Budget", value=f"₹{budget:,.2f}")

            # Row 2: Current Spend & Remaining
            row2_col1, row2_col2 = st.columns(2)
            with row2_col1:
                st.metric(label="Current Spend", value=f"₹{spend:,.2f}")
            with row2_col2:
                st.metric(label="Remaining (Budget)", value=f"₹{remaining:,.2f}", delta=f"{percent_remaining:.1f}%")

            # Row 3: Start & End Balance
            row3_col1, row3_col2 = st.columns(2)
            with row3_col1:
                st.metric(label="Starting Balance", value=f"₹{start_balance:,.2f}")
            with row3_col2:
                 st.metric(label="Ending Balance", value=f"₹{end_balance:,.2f}")

            # --- Placeholder Edit Button (Below metrics grid) ---
            st.button(
                "Edit Budget & Balances",
                key=f"edit_all_{account_name}",
                help="Set Budget, Starting Balance, and Ending Balance for Current Month (Feature coming soon!)",
                disabled=True # Disabled for mock
            )

            # --- Progress Bar ---
            progress_value = 1.0 if spend > 0 and budget == 0 else (spend / budget if budget > 0 else 0)
            st.progress(progress_value)

            st.divider() # Separator before chart

            # --- Bar Chart ---
            chart = create_budget_bar_chart(budget, spend, f"{account_name} Budget vs Spend")
            st.plotly_chart(chart, use_container_width=True)

    # --- 'Update Spend Details' Button (Below Columns) ---
    st.divider()
    _, center_col, _ = st.columns([1, 1, 1]) # Centering column
    with center_col:
        st.button(
            "🔄 Update Spend Details",
            key="update_spend_button",
            help="Fetch latest spend data for the current month (Feature coming soon!)",
            disabled=True # Disabled for mock
        )