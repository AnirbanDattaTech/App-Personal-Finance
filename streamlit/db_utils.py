# streamlit/db_utils.py
import sqlite3
import pandas as pd
from uuid import uuid4
from pathlib import Path # Use pathlib
import logging
from typing import Optional, Dict, Any, List

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- ✅ Define DB Path relative to the project root ---
# This assumes db_utils.py is in 'app-personal-finance/streamlit/'
# Path(__file__) gives the path to db_utils.py
# .parent gives 'app-personal-finance/streamlit/'
# .parent gives 'app-personal-finance/'
# Then we navigate to 'data/expenses.db'
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "expenses.db"

# --- Optional: Check if DB exists and log ---
if not DB_PATH.exists():
    logging.error(f"DATABASE NOT FOUND at expected location: {DB_PATH.resolve()}")
    # Indicate the expected path based on calculation
    logging.error(f"(Calculated from: {__file__})")
    # You might want to raise an error or handle this case differently in a real app
else:
    # Print statement removed as logging is now configured
    logging.info(f"Using database at: {DB_PATH.resolve()}")
# ---

def get_connection() -> Optional[sqlite3.Connection]:
    """
    Establishes a connection to the SQLite database.

    Returns:
        Optional[sqlite3.Connection]: A connection object or None if connection fails.
    """
    try:
        # Ensure the path is passed as a string or Path object
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Return rows as dictionary-like objects
        logging.debug(f"Database connection established to {DB_PATH.resolve()}")
        return conn
    except sqlite3.Error as e:
        # Use logging correctly
        logging.error(f"Database connection error to {DB_PATH.resolve()}: {e}", exc_info=True)
        return None

def fetch_all_expenses() -> pd.DataFrame:
    """Fetches all expenses, ordered by date descending."""
    conn = get_connection()
    if conn is None:
        logging.error("Cannot fetch expenses: Database connection failed.")
        return pd.DataFrame()
    try:
        # Explicitly select columns for clarity and potential future changes
        query = "SELECT id, date, year, month, week, day_of_week, account, category, sub_category, type, user, amount FROM expenses ORDER BY date DESC"
        df = pd.read_sql(query, conn)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        logging.info(f"Fetched {len(df)} expenses.")
        return df
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        logging.error(f"Error fetching all expenses: {e}", exc_info=True)
        return pd.DataFrame()
    finally:
        if conn: conn.close()

def fetch_expense_by_id(expense_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single expense by its ID."""
    conn = get_connection()
    if conn is None:
        logging.error(f"Cannot fetch expense {expense_id}: Database connection failed.")
        return None
    try:
        cursor = conn.cursor()
        # Use parameter binding for safety
        cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
        record = cursor.fetchone()
        logging.debug(f"Fetched expense for ID {expense_id}: {'Found' if record else 'Not Found'}")
        # Convert sqlite3.Row to dict if found
        return dict(record) if record else None
    except sqlite3.Error as e:
        logging.error(f"Error fetching expense by ID {expense_id}: {e}", exc_info=True)
        return None
    finally:
        if conn: conn.close()

def insert_expense(data: Dict[str, Any]) -> bool:
    """
    Inserts a new expense record into the database.

    Args:
        data (Dict[str, Any]): Dictionary containing expense details.
                               Must include all required fields.

    Returns:
        bool: True if insertion was successful, False otherwise.
    """
    conn = get_connection()
    if conn is None:
        logging.error("Cannot insert expense: Database connection failed.")
        return False

    # Define expected columns explicitly based on the SQL statement below
    required_fields = ['date', 'year', 'month', 'week', 'day_of_week',
                       'account', 'category', 'sub_category', 'type',
                       'user', 'amount']

    # Check for missing fields *before* trying to insert
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        logging.error(f"Missing required fields for inserting expense: {', '.join(missing_fields)}. Data provided: {list(data.keys())}")
        return False

    sql = """
    INSERT INTO expenses (
        id, date, year, month, week, day_of_week,
        account, category, sub_category, type, user, amount
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    try:
        cursor = conn.cursor()
        new_id = str(uuid4()) # Generate UUID here
        # Prepare values in the correct order, ensuring types
        values = (
            new_id,
            data['date'], # Assume already string in 'YYYY-MM-DD' format
            int(data['year']),
            data['month'],
            data['week'],
            data['day_of_week'],
            data['account'],
            data['category'],
            # Handle potentially missing/empty sub_category gracefully
            data.get('sub_category', ''), # Use .get for optional fields if applicable
            data['type'],
            data['user'],
            float(data['amount'])
        )
        cursor.execute(sql, values)
        conn.commit()
        logging.info(f"✅ Expense inserted with ID: {new_id}")
        return True
    except (sqlite3.Error, ValueError, TypeError) as e: # Catch potential type errors too
        logging.error(f"Error inserting expense: {e}", exc_info=True)
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def update_expense(expense_id: str, data: Dict[str, Any]) -> bool:
    """Updates an existing expense based on its ID."""
    conn = get_connection()
    if conn is None:
        logging.error(f"Cannot update expense {expense_id}: Database connection failed.")
        return False

    # Define fields allowed for update (excluding id, maybe others)
    updatable_fields = ['date', 'year', 'month', 'week', 'day_of_week', 'account', 'category', 'sub_category', 'type', 'user', 'amount']
    # Construct SET clause dynamically from provided data, only using allowed fields
    set_parts = []
    values = []
    for field in updatable_fields:
        if field in data:
            set_parts.append(f"{field} = ?")
            # Basic type conversion/validation (more robust needed for production)
            if field in ['year']:
                values.append(int(data[field]))
            elif field in ['amount']:
                values.append(float(data[field]))
            else:
                values.append(data[field])

    if not set_parts:
        logging.warning(f"No valid fields provided for updating expense ID {expense_id}.")
        return False

    set_clause = ", ".join(set_parts)
    sql = f"UPDATE expenses SET {set_clause} WHERE id = ?"
    values.append(expense_id) # Add the ID for the WHERE clause

    try:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(values))
        conn.commit()
        if cursor.rowcount == 0:
            logging.warning(f"No expense found with ID {expense_id} to update.")
            return False
        logging.info(f"Expense {expense_id} updated successfully.")
        return True
    except (sqlite3.Error, ValueError, TypeError) as e:
        logging.error(f"Error updating expense {expense_id}: {e}", exc_info=True)
        conn.rollback()
        return False
    finally:
        if conn: conn.close()

def delete_expense(expense_id: str) -> bool:
    """Deletes an expense record by its ID."""
    conn = get_connection()
    if conn is None:
        logging.error(f"Cannot delete expense {expense_id}: Database connection failed.")
        return False

    sql = "DELETE FROM expenses WHERE id = ?"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (expense_id,))
        conn.commit()
        if cursor.rowcount == 0:
            logging.warning(f"No expense found with ID {expense_id} to delete.")
            return False
        logging.info(f"Expense {expense_id} deleted successfully.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Error deleting expense {expense_id}: {e}", exc_info=True)
        conn.rollback()
        return False
    finally:
        if conn: conn.close()

def fetch_last_expenses(n: int = 10) -> pd.DataFrame:
    """Fetches the last N expenses, ordered by date then rowid descending."""
    conn = get_connection()
    if conn is None:
        logging.error(f"Cannot fetch last {n} expenses: Database connection failed.")
        return pd.DataFrame()
    try:
        # Order by date descending first, then rowid descending as a tie-breaker
        # Explicitly list columns
        query = f"""
            SELECT id, date, year, month, week, day_of_week, account, category, sub_category, type, user, amount
            FROM expenses
            ORDER BY date DESC, rowid DESC
            LIMIT ?
        """
        df = pd.read_sql(query, conn, params=(n,))
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        logging.info(f"Fetched last {len(df)} expenses (requested {n}).")
        return df
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        logging.error(f"Error fetching last {n} expenses: {e}", exc_info=True)
        return pd.DataFrame()
    finally:
        if conn: conn.close()