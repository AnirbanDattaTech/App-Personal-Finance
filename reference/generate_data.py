# reference/create_file_data.py
"""
Generates realistic expense data based on predefined rules and constraints.

Reads rules from 'sample_data_generation.csv' (in project root) and
outputs transactions to 'dummy_expenses_generated.csv' (in project root)
covering the period from 2023-01-01 to 2025-04-20.
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from pathlib import Path
import logging
from tqdm import tqdm # For progress bar
from typing import List, Dict, Any, Optional

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- File Paths (CRITICAL CHANGE) ---
# Get the directory where THIS script lives (reference/)
SCRIPT_DIR = Path(__file__).parent
# Get the parent directory (project root: app-personal-finance/)
PROJECT_ROOT = SCRIPT_DIR.parent

# Define paths relative to the PROJECT_ROOT
RULES_FILE = PROJECT_ROOT / "sample_data_generation.csv"
OUTPUT_FILE = PROJECT_ROOT / "dummy_expenses_generated.csv"
METADATA_FILE = PROJECT_ROOT / "expense_metadata.json" # Optional, for validation/reference

# Date Range
START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2025, 4, 20)

# Constraints
MONTHLY_MIN_TOTAL = 60000
MONTHLY_MAX_TOTAL = 120000
MONTHLY_MAX_ROWS = 100

# Ad-hoc Transaction Generation Parameters
AVG_ADHOC_PER_DAY = 4 # Average number of ad-hoc transactions per day
ADHOC_RANGE = (1, 7) # Min/Max ad-hoc transactions per day (adjust as needed)

# --- Helper Functions (No changes needed inside functions) ---

def load_rules(filepath: Path) -> Optional[pd.DataFrame]:
    """Loads and preprocesses the ruleset CSV."""
    if not filepath.exists():
        logging.error(f"Rules file not found: {filepath}")
        return None
    try:
        df_rules = pd.read_csv(filepath)
        df_rules.columns = [col.strip() for col in df_rules.columns]
        df_rules['Valid-expense-types'] = df_rules['Valid-expense-types'].str.split('|')
        for col in ['Min-expenses-amount', 'Max-expenses-amount', 'Max-times-per-month']:
            df_rules[col] = pd.to_numeric(df_rules[col], errors='coerce')
        df_rules['Max-times-per-month'].fillna(5, inplace=True)
        df_rules['Max-times-per-month'] = df_rules['Max-times-per-month'].astype(int)
        df_rules.dropna(subset=['Category', 'Sub-category', 'User', 'Account', 'Expense-Frequency', 'Min-expenses-amount', 'Max-expenses-amount'], inplace=True)
        logging.info(f"Loaded {len(df_rules)} rules from {filepath}")
        return df_rules
    except Exception as e:
        logging.error(f"Error loading or processing rules file {filepath}: {e}", exc_info=True)
        return None

def get_date_parts(date_obj: datetime) -> Dict[str, Any]:
    """Calculates derived date columns."""
    return {
        "date_dt": date_obj,
        "date": date_obj.strftime('%d-%m-%Y'),
        "year": date_obj.year,
        "month": date_obj.strftime('%Y-%m'),
        "week": date_obj.strftime('%Y-W%V'),
        "day_of_week": date_obj.strftime('%A')
    }

def generate_fixed_transaction(rule: pd.Series, date_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generates a dictionary for a fixed transaction based on a rule."""
    if rule['Min-expenses-amount'] != rule['Max-expenses-amount']:
        logging.warning(f"Rule marked as fixed frequency but Min!=Max: {rule.to_dict()}")
        return None
    amount = rule['Min-expenses-amount']
    valid_types = rule['Valid-expense-types']
    selected_type = valid_types[0] if isinstance(valid_types, list) and valid_types else "Fixed Expense"
    return {
        **date_info, "account": rule['Account'], "category": rule['Category'],
        "sub_category": rule['Sub-category'], "type": selected_type,
        "user": rule['User'], "amount": amount
    }

def generate_adhoc_transaction(rule: pd.Series, date_info: Dict[str, Any]) -> Dict[str, Any]:
    """Generates a dictionary for an ad-hoc transaction based on a rule."""
    amount = round(random.uniform(rule['Min-expenses-amount'], rule['Max-expenses-amount']), 2)
    selected_type = random.choice(rule['Valid-expense-types']) if isinstance(rule['Valid-expense-types'], list) and rule['Valid-expense-types'] else "Ad-hoc Expense"
    return {
        **date_info, "account": rule['Account'], "category": rule['Category'],
        "sub_category": rule['Sub-category'], "type": selected_type,
        "user": rule['User'], "amount": amount
    }

def check_fixed_conditions(rule: pd.Series, current_date: datetime) -> bool:
    """Checks if a fixed/recurring rule should trigger on the current date."""
    freq = rule['Expense-Frequency']
    day = current_date.day
    month = current_date.month

    if freq == 'monthly':
        if rule['Category'] == 'Rent' and day == 1: return True
        if rule['Category'] == 'Household' and rule['Sub-category'] == 'Maid' and day == 1: return True
        if rule['Category'] == 'Investment' and rule['Sub-category'] == 'SIP' and day == 5: return True
        if rule['Category'] == 'Insurance Premium' and rule['Sub-category'] == 'ULIP' and day == 10: return True
        if rule['Category'] == 'Insurance Premium' and rule['Sub-category'] == 'Health Insurance' and day == 15: return True
        if rule['Category'] == 'Connectivity' and rule['Sub-category'] == 'Netflix' and day == 20: return True # Example day for monthly connectivity
        if rule['Category'] == 'Utilities' and rule['Sub-category'] == 'Water' and day == 7: return True # Example day
        if rule['Category'] == 'Utilities' and rule['Sub-category'] == 'Maintenance' and day == 6: return True # Example day
        if rule['Category'] == 'Utilities' and rule['Sub-category'] == 'Garbage Collection' and day == 3: return True # Example day
        return False
    elif freq == 'bi-monthly': # Odd months, day 2
        return month % 2 != 0 and day == 2
    elif freq == 'once every 3 months': # Jan, Apr, Jul, Oct, day 3
        return month in [1, 4, 7, 10] and day == 3
    elif freq == 'once every 6 months': # Jan, Jul, day 4
        return month in [1, 7] and day == 4
    elif freq == 'bi-annually': # Mar 20, Sep 20
        return (month == 3 and day == 20) or (month == 9 and day == 20)
    elif freq == 'annually': # Jan 15
         # Handle specific annual items
        if rule['Category'] == 'Insurance Premium' and rule['Sub-category'] == 'Vehicle Insurance': return month == 2 and day == 25 # Example Date
        if rule['Category'] == 'Connectivity' and rule['Sub-category'] == 'Prime Video': return month == 1 and day == 15 # Example Date
        if rule['Category'] == 'Connectivity' and rule['Sub-category'] == 'Disney+ Hotstar': return month == 1 and day == 16 # Example Date
        return False # Only trigger specific annuals
    return False

# --- Main Generation Logic (No changes needed inside function) ---
def generate_data():
    """Main function to generate the expense data."""
    logging.info("--- Starting Data Generation ---")
    logging.info(f"Looking for rules file at: {RULES_FILE}")
    logging.info(f"Output will be saved to: {OUTPUT_FILE}")

    df_rules = load_rules(RULES_FILE)
    if df_rules is None:
        return

    fixed_rules = df_rules[df_rules['Expense-Frequency'] != 'ad-hoc'].copy()
    adhoc_rules = df_rules[df_rules['Expense-Frequency'] == 'ad-hoc'].copy()

    all_transactions = []
    current_date = START_DATE
    total_days = (END_DATE - START_DATE).days + 1
    pbar = tqdm(total=total_days, desc="Generating Daily Transactions")

    current_month_str = ""
    current_month_total = 0.0
    current_month_rows = 0
    monthly_rule_counts: Dict[int, int] = {}

    while current_date <= END_DATE:
        date_info = get_date_parts(current_date)

        if date_info['month'] != current_month_str:
            if current_month_str:
                logging.info(f"Month {current_month_str} Summary: Rows={current_month_rows}, Total=₹{current_month_total:.2f}")
                if current_month_total < MONTHLY_MIN_TOTAL: logging.warning(f"Month {current_month_str} total ₹{current_month_total:.2f} BELOW target minimum ₹{MONTHLY_MIN_TOTAL}")
                if current_month_total > MONTHLY_MAX_TOTAL: logging.warning(f"Month {current_month_str} total ₹{current_month_total:.2f} ABOVE target maximum ₹{MONTHLY_MAX_TOTAL}")
                if current_month_rows > MONTHLY_MAX_ROWS: logging.warning(f"Month {current_month_str} rows {current_month_rows} EXCEEDED target maximum {MONTHLY_MAX_ROWS}")
            current_month_str = date_info['month']
            current_month_total = 0.0; current_month_rows = 0; monthly_rule_counts = {}
            logging.debug(f"Starting generation for month: {current_month_str}")

        # 1. Generate Fixed Transactions
        for index, rule in fixed_rules.iterrows():
            if check_fixed_conditions(rule, current_date):
                transaction = generate_fixed_transaction(rule, date_info)
                if transaction and current_month_rows < MONTHLY_MAX_ROWS + 5:
                     all_transactions.append(transaction)
                     current_month_total += transaction['amount']
                     current_month_rows += 1
                     monthly_rule_counts[index] = monthly_rule_counts.get(index, 0) + 1
                     logging.debug(f"Generated fixed: {transaction['category']}/{transaction['sub_category']} on {date_info['date']}")
                elif transaction:
                     logging.warning(f"Skipped fixed {rule['Category']}/{rule['Sub-category']} on {date_info['date']} (Monthly row limit: {current_month_rows})")

        # 2. Generate Ad-hoc Transactions
        num_adhoc_today = random.randint(ADHOC_RANGE[0], ADHOC_RANGE[1])
        adhoc_added_today = 0
        weights = adhoc_rules['Account'].apply(lambda x: 1.5 if x in ['Anirban-ICICI', 'Puspita-SBI'] else 1.0).values
        if weights.sum() > 0: weights = weights / weights.sum()
        else: weights = None

        for _ in range(num_adhoc_today):
            if current_month_total >= MONTHLY_MAX_TOTAL or current_month_rows >= MONTHLY_MAX_ROWS:
                logging.debug(f"Stopping ad-hoc for {date_info['date']} due to limits.")
                break
            if weights is None or adhoc_rules.empty: continue

            rule_selected = False
            for attempt in range(5):
                 try:
                     selected_rule_series = adhoc_rules.sample(n=1, weights=weights).iloc[0]
                     rule_index = selected_rule_series.name
                 except ValueError as e: logging.warning(f"Adhoc sample error: {e}"); continue

                 current_rule_count = monthly_rule_counts.get(rule_index, 0)
                 max_allowed = selected_rule_series['Max-times-per-month']

                 if current_rule_count < max_allowed:
                     transaction = generate_adhoc_transaction(selected_rule_series, date_info)
                     # Further check if adding this exceeds monthly total *drastically*
                     if current_month_total + transaction['amount'] <= MONTHLY_MAX_TOTAL * 1.05: # Allow slight overshoot
                         all_transactions.append(transaction)
                         current_month_total += transaction['amount']
                         current_month_rows += 1
                         monthly_rule_counts[rule_index] = current_rule_count + 1
                         adhoc_added_today += 1
                         rule_selected = True
                         logging.debug(f"Generated adhoc: {transaction['category']}/{transaction['sub_category']} on {date_info['date']}")
                         break # Exit retry loop
                     else:
                         logging.debug(f"Skipping adhoc {selected_rule_series['Category']}/{selected_rule_series['Sub-category']} to avoid exceeding monthly total drastically.")
                         # Don't break, allow trying another rule maybe
                 else:
                     logging.debug(f"Rule {rule_index} hit monthly limit ({max_allowed}). Retrying...")

            if not rule_selected: logging.debug(f"Could not find valid ad-hoc rule for {date_info['date']} after retries.")

        current_date += timedelta(days=1)
        pbar.update(1)

    pbar.close()
    # Log summary for the very last month
    if current_month_str:
        logging.info(f"Month {current_month_str} Summary: Rows={current_month_rows}, Total=₹{current_month_total:.2f}")
        if current_month_total < MONTHLY_MIN_TOTAL: logging.warning(f"Month {current_month_str} total ₹{current_month_total:.2f} BELOW target minimum ₹{MONTHLY_MIN_TOTAL}")
        if current_month_total > MONTHLY_MAX_TOTAL: logging.warning(f"Month {current_month_str} total ₹{current_month_total:.2f} ABOVE target maximum ₹{MONTHLY_MAX_TOTAL}")
        if current_month_rows > MONTHLY_MAX_ROWS: logging.warning(f"Month {current_month_str} rows {current_month_rows} EXCEEDED target maximum {MONTHLY_MAX_ROWS}")


    if not all_transactions:
        logging.warning("No transactions were generated.")
        return

    df_final = pd.DataFrame(all_transactions)
    output_columns = ['date', 'year', 'month', 'week', 'day_of_week', 'account', 'category', 'sub_category', 'type', 'user', 'amount']
    df_final = df_final[output_columns]

    logging.info(f"--- Data Generation Complete ---")
    logging.info(f"Total transactions generated: {len(df_final)}")

    try:
        df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
        logging.info(f"Successfully saved generated data to: {OUTPUT_FILE}")
    except Exception as e:
        logging.error(f"Error saving output CSV file {OUTPUT_FILE}: {e}", exc_info=True)

# --- Execution Guard ---
if __name__ == "__main__":
    generate_data()