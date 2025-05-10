# streamlit/db_utils.py
# ADDED DETAILED LOGGING FOR DEBUGGING BUDGET API FLOW
import sqlite3
import pandas as pd
from uuid import uuid4
from pathlib import Path
import logging
from typing import Optional, Dict, Any, List
import datetime
import sys

# --- Path Setup & Import Config ---
try:
    CURRENT_FILE_DIR = Path(__file__).resolve().parent
    STREAMLIT_DIR = CURRENT_FILE_DIR
    PROJECT_ROOT = STREAMLIT_DIR.parent
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
        logging.info(f"Added project root ({PROJECT_ROOT}) to sys.path for config import.")
    from config.settings import DB_FULL_PATH # Now try importing
    if not isinstance(DB_FULL_PATH, Path): raise TypeError("DB_FULL_PATH is not Path")
    logging.info(f"Successfully imported DB_FULL_PATH: {DB_FULL_PATH}")
except Exception as e:
    logging.error(f"CRITICAL: Failed during path setup or config import: {e}", exc_info=True)
    FALLBACK_ROOT = Path(__file__).parent.parent
    DB_FULL_PATH = FALLBACK_ROOT / "data" / "IMPORT_ERROR_expenses.db"
    logging.error(f"Using fallback DB path: {DB_FULL_PATH}")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s') # Added line number

if not DB_FULL_PATH.exists():
    logging.error(f"CONFIGURED DATABASE NOT FOUND at: {DB_FULL_PATH.resolve()}")
else:
    logging.info(f"Using configured database at: {DB_FULL_PATH.resolve()}")

def get_connection() -> Optional[sqlite3.Connection]:
    """Establishes a connection to the SQLite database specified by DB_FULL_PATH."""
    global DB_FULL_PATH
    # <<< ADDED LOGGING HERE >>>
    logging.info(f"[get_connection] Attempting to connect to: {DB_FULL_PATH.resolve()}")
    try:
        conn = sqlite3.connect(DB_FULL_PATH, check_same_thread=False, timeout=10) # Added timeout
        conn.row_factory = sqlite3.Row
        logging.info(f"[get_connection] Connection successful to {DB_FULL_PATH.resolve()}")
        return conn
    except Exception as e:
        logging.error(f"[get_connection] Connection error to {DB_FULL_PATH.resolve()}: {e}", exc_info=True)
        return None

# --- Budget Feature DB Logic ---

def calculate_current_spend(year_month: str, account: str) -> float:
    """Calculates the total spend for a given account in a specific month."""
    # <<< ADDED LOGGING HERE >>>
    logging.info(f"[calculate_current_spend] Calculating for account='{account}', year_month='{year_month}'")
    conn = get_connection()
    if conn is None:
        logging.error(f"[calculate_current_spend] DB connection failed.")
        return 0.0
    sql = "SELECT SUM(amount) FROM expenses WHERE account = ? AND month = ?;"
    total_spend = 0.0
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (account, year_month))
        result = cursor.fetchone()
        # <<< ADDED LOGGING HERE >>>
        logging.info(f"[calculate_current_spend] Raw DB result for SUM(amount): {result}")
        if result is not None and result[0] is not None:
            total_spend = float(result[0])
            logging.info(f"[calculate_current_spend] Calculated spend: {total_spend:.2f}")
        else:
            logging.info(f"[calculate_current_spend] No spend found (result was None or sum was None).")
            total_spend = 0.0
    except Exception as e:
        logging.error(f"[calculate_current_spend] Error: {e}", exc_info=True)
        total_spend = 0.0
    finally:
        if conn: conn.close()
    logging.info(f"[calculate_current_spend] Returning total_spend: {total_spend}")
    return total_spend

def get_budget_data(year_month: str, account: str) -> Dict[str, Any]:
    """Fetches budget details for a specific account and month."""
    # <<< ADDED LOGGING HERE >>>
    logging.info(f"[get_budget_data] Fetching for account='{account}', year_month='{year_month}'")
    conn = get_connection()
    default_budget_val = 50000.0 if account == "Anirban-ICICI" else 0.0
    budget_details = {"budget_amount": default_budget_val, "start_balance": 0.0, "end_balance": 0.0}
    if conn is None:
        logging.error(f"[get_budget_data] DB connection failed. Returning defaults: {budget_details}")
        return budget_details
    sql = "SELECT budget_amount, start_balance, end_balance FROM monthly_budgets WHERE year_month = ? AND account = ?;"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (year_month, account))
        record = cursor.fetchone()
        # <<< ADDED LOGGING HERE >>>
        logging.info(f"[get_budget_data] Raw DB record fetched: {record}")
        if record:
            fetched_dict = dict(record)
            budget_details["budget_amount"] = float(fetched_dict.get("budget_amount", default_budget_val))
            budget_details["start_balance"] = float(fetched_dict.get("start_balance", 0.0) or 0.0)
            budget_details["end_balance"] = float(fetched_dict.get("end_balance", 0.0) or 0.0)
            logging.info(f"[get_budget_data] Parsed record: {budget_details}")
        else:
            logging.info(f"[get_budget_data] No record found. Using defaults: {budget_details}")
    except Exception as e:
        logging.error(f"[get_budget_data] Error: {e}", exc_info=True)
        logging.warning(f"[get_budget_data] Returning default data due to error: {budget_details}")
    finally:
        if conn: conn.close()
    logging.info(f"[get_budget_data] Returning budget_details: {budget_details}")
    return budget_details

def get_all_budget_data_for_month(year_month: str) -> Dict[str, Dict[str, Any]]:
    """Fetches all relevant budget data for all relevant accounts for a specific month."""
    # <<< ADDED LOGGING HERE >>>
    logging.info(f"[get_all_budget_data_for_month] Fetching for month: {year_month}")
    accounts_to_process = ["Anirban-ICICI", "Anirban-SBI"]
    all_account_data: Dict[str, Dict[str, Any]] = {}
    try:
        for account in accounts_to_process:
            logging.info(f"[get_all_budget_data_for_month] Processing account: {account}")
            budget_data = get_budget_data(year_month, account) # This now has internal logging
            current_spend = calculate_current_spend(year_month, account) # This now has internal logging
            all_account_data[account] = {
                "budget_amount": budget_data.get("budget_amount", 0.0),
                "start_balance": budget_data.get("start_balance", 0.0),
                "end_balance": budget_data.get("end_balance", 0.0),
                "current_spend": current_spend
            }
            logging.info(f"[get_all_budget_data_for_month] Assembled data for {account}: {all_account_data[account]}")
    except Exception as e:
        logging.error(f"[get_all_budget_data_for_month] Failed: {e}", exc_info=True)
        return {}
    logging.info(f"[get_all_budget_data_for_month] Returning final data: {all_account_data}")
    return all_account_data

# --- Other functions (fetch_all_expenses, etc.) remain below ---
# (No changes needed to the rest of the functions like fetch_all_expenses, insert_expense etc.)
def fetch_all_expenses() -> pd.DataFrame:
    conn = get_connection()
    if conn is None: return pd.DataFrame()
    try:
        query = "SELECT id, date, year, month, week, day_of_week, account, category, sub_category, type, user, amount FROM expenses ORDER BY date DESC"
        df = pd.read_sql(query, conn)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        # logging.info(f"Fetched {len(df)} expenses.") # Reduced verbosity
        return df
    except Exception as e:
        logging.error(f"Error fetching all expenses: {e}", exc_info=True)
        return pd.DataFrame()
    finally:
        if conn: conn.close()

def fetch_expense_by_id(expense_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    if conn is None: return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
        record = cursor.fetchone()
        return dict(record) if record else None
    except Exception as e:
        logging.error(f"Error fetching expense by ID {expense_id}: {e}", exc_info=True)
        return None
    finally:
        if conn: conn.close()

def insert_expense(data: Dict[str, Any]) -> bool:
    conn = get_connection()
    if conn is None: return False
    required_fields = ['date', 'year', 'month', 'week', 'day_of_week', 'account', 'category', 'sub_category', 'type', 'user', 'amount']
    if any(field not in data for field in required_fields):
        logging.error(f"Missing required fields for insert.")
        return False
    sql = "INSERT INTO expenses (id, date, year, month, week, day_of_week, account, category, sub_category, type, user, amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    try:
        cursor = conn.cursor()
        new_id = str(uuid4())
        values = (new_id, data['date'], int(data['year']), data['month'], data['week'], data['day_of_week'], data['account'], data['category'], data.get('sub_category', ''), data['type'], data['user'], float(data['amount']))
        cursor.execute(sql, values)
        conn.commit()
        logging.info(f"✅ Expense inserted with ID: {new_id}")
        return True
    except Exception as e:
        logging.error(f"Error inserting expense: {e}", exc_info=True)
        conn.rollback()
        return False
    finally:
        if conn: conn.close()

def update_expense(expense_id: str, data: Dict[str, Any]) -> bool:
    conn = get_connection()
    if conn is None: return False
    updatable_fields = ['date', 'year', 'month', 'week', 'day_of_week', 'account', 'category', 'sub_category', 'type', 'user', 'amount']
    set_parts = []
    values = []
    for field in updatable_fields:
        if field in data:
            set_parts.append(f"{field} = ?")
            if field in ['year']: values.append(int(data[field]))
            elif field in ['amount']: values.append(float(data[field]))
            else: values.append(data[field])
    if not set_parts: return False
    set_clause = ", ".join(set_parts)
    sql = f"UPDATE expenses SET {set_clause} WHERE id = ?"
    values.append(expense_id)
    try:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(values))
        conn.commit()
        if cursor.rowcount == 0: return False
        logging.info(f"Expense {expense_id} updated successfully.")
        return True
    except Exception as e:
        logging.error(f"Error updating expense {expense_id}: {e}", exc_info=True)
        conn.rollback()
        return False
    finally:
        if conn: conn.close()

def delete_expense(expense_id: str) -> bool:
    conn = get_connection()
    if conn is None: return False
    sql = "DELETE FROM expenses WHERE id = ?"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (expense_id,))
        conn.commit()
        if cursor.rowcount == 0: return False
        logging.info(f"Expense {expense_id} deleted successfully.")
        return True
    except Exception as e:
        logging.error(f"Error deleting expense {expense_id}: {e}", exc_info=True)
        conn.rollback()
        return False
    finally:
        if conn: conn.close()

def fetch_last_expenses(n: int = 10) -> pd.DataFrame:
    conn = get_connection()
    if conn is None: return pd.DataFrame()
    try:
        query = f"SELECT id, date, year, month, week, day_of_week, account, category, sub_category, type, user, amount FROM expenses ORDER BY date DESC, rowid DESC LIMIT ?"
        df = pd.read_sql(query, conn, params=(n,))
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        # logging.info(f"Fetched last {len(df)} expenses.") # Reduced verbosity
        return df
    except Exception as e:
        logging.error(f"Error fetching last {n} expenses: {e}", exc_info=True)
        return pd.DataFrame()
    finally:
        if conn: conn.close()

def update_budget_data(year_month: str, account: str, data: Dict[str, Any]) -> bool:
    # <<< ADDED LOGGING HERE >>>
    logging.info(f"[update_budget_data] Updating for account='{account}', year_month='{year_month}', data={data}")
    conn = get_connection()
    if conn is None: return False
    current_month_str = datetime.date.today().strftime("%Y-%m")
    if year_month != current_month_str:
        logging.warning(f"[update_budget_data] Month mismatch. Current: {current_month_str}, Provided: {year_month}. Skipping update.")
        return False
    try:
        budget_amount = float(data.get("budget_amount", 0.0))
        start_balance = float(v) if (v := data.get("start_balance")) is not None else None
        end_balance = float(v) if (v := data.get("end_balance")) is not None else None
    except Exception as e:
        logging.error(f"[update_budget_data] Invalid data types: {e}")
        return False
    sql = "INSERT INTO monthly_budgets (year_month, account, budget_amount, start_balance, end_balance, updated_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP) ON CONFLICT(year_month, account) DO UPDATE SET budget_amount=excluded.budget_amount, start_balance=excluded.start_balance, end_balance=excluded.end_balance, updated_at=CURRENT_TIMESTAMP;"
    try:
        cursor = conn.cursor()
        values = (year_month, account, budget_amount, start_balance, end_balance)
        cursor.execute(sql, values)
        conn.commit()
        logging.info(f"[update_budget_data] Upsert successful for {account} in {year_month}.")
        return True
    except Exception as e:
        logging.error(f"[update_budget_data] Error: {e}", exc_info=True)
        conn.rollback()
        return False
    finally:
        if conn: conn.close()