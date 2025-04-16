# db_utils.py
import sqlite3
import pandas as pd
from uuid import uuid4
import logging
from typing import Optional, Dict, Any, List # Import types for hinting

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_NAME: str = "expenses.db" # Add type hint for constant

def get_connection() -> Optional[sqlite3.Connection]:
    """
    Establishes a connection to the SQLite database.

    Returns:
        Optional[sqlite3.Connection]: A connection object or None if connection fails.
    """
    try:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
        logging.debug("Database connection established.") # Use debug level for successful connection
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        return None

def fetch_all_expenses() -> pd.DataFrame:
    """
    Fetches all expenses from the database, ordered by date descending.

    Returns:
        pd.DataFrame: DataFrame containing all expenses, empty if error or no data.
    """
    conn = get_connection()
    if conn is None: return pd.DataFrame()

    try:
        df = pd.read_sql("SELECT * FROM expenses ORDER BY date DESC", conn)
        # Coerce errors in date conversion to NaT (Not a Time)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        # Optionally drop rows where date conversion failed
        # df = df.dropna(subset=['date'])
        logging.info(f"Fetched {len(df)} expenses.")
        return df
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        logging.error(f"Error fetching all expenses: {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()

def fetch_expense_by_id(expense_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches a single expense record by its UUID.

    Args:
        expense_id (str): The UUID of the expense to fetch.

    Returns:
        Optional[Dict[str, Any]]: A dictionary representing the expense, or None if not found or error.
    """
    conn = get_connection()
    if conn is None: return None

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
        record = cursor.fetchone()
        logging.debug(f"Fetched expense for ID {expense_id}: {'Found' if record else 'Not Found'}")
        return dict(record) if record else None
    except sqlite3.Error as e:
        logging.error(f"Error fetching expense by ID {expense_id}: {e}")
        return None
    finally:
        if conn: conn.close()


def insert_expense(data: Dict[str, Any]) -> bool:
    """
    Inserts a new expense record into the database.

    Args:
        data (Dict[str, Any]): Dictionary containing expense details. Expected keys:
                               'date', 'account', 'category', 'sub_category', 'type', 'user', 'amount'.

    Returns:
        bool: True if insertion was successful, False otherwise.
    """
    conn = get_connection()
    if conn is None: return False

    required_fields = ['date', 'account', 'category', 'sub_category', 'type', 'user', 'amount']
    if not all(field in data for field in required_fields):
        logging.error(f"Missing required fields for inserting expense. Got: {data.keys()}")
        return False

    sql = """
    INSERT INTO expenses (id, date, account, category, sub_category, type, user, amount)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    try:
        cursor = conn.cursor()
        new_id = str(uuid4())
        cursor.execute(sql, (
            new_id, data['date'], data['account'], data['category'],
            data['sub_category'], data['type'], data['user'], float(data['amount']) # Ensure amount is float
        ))
        conn.commit()
        logging.info(f"Expense inserted successfully with ID: {new_id}")
        return True
    except (sqlite3.Error, ValueError) as e: # Catch potential float conversion error
        logging.error(f"Error inserting expense: {e}")
        conn.rollback()
        return False
    finally:
        if conn: conn.close()

def update_expense(expense_id: str, data: Dict[str, Any]) -> bool:
    """
    Updates an existing expense record identified by its UUID.

    Args:
        expense_id (str): The UUID of the expense to update.
        data (Dict[str, Any]): Dictionary containing the updated expense details. Expected keys:
                               'date', 'account', 'category', 'sub_category', 'type', 'user', 'amount'.

    Returns:
        bool: True if update was successful (record found and updated), False otherwise.
    """
    conn = get_connection()
    if conn is None: return False

    required_fields = ['date', 'account', 'category', 'sub_category', 'type', 'user', 'amount']
    if not all(field in data for field in required_fields):
        logging.error(f"Missing required fields for updating expense ID {expense_id}. Got: {data.keys()}")
        return False

    sql = """
    UPDATE expenses
    SET date = ?, account = ?, category = ?, sub_category = ?, type = ?, user = ?, amount = ?
    WHERE id = ?
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (
            data['date'], data['account'], data['category'], data['sub_category'],
            data['type'], data['user'], float(data['amount']), # Ensure amount is float
            expense_id
        ))
        conn.commit()
        if cursor.rowcount == 0:
            logging.warning(f"No expense found with ID {expense_id} to update.")
            return False
        logging.info(f"Expense {expense_id} updated successfully.")
        return True
    except (sqlite3.Error, ValueError) as e:
        logging.error(f"Error updating expense {expense_id}: {e}")
        conn.rollback()
        return False
    finally:
        if conn: conn.close()


def delete_expense(expense_id: str) -> bool:
    """
    Deletes an expense record by its UUID.

    Args:
        expense_id (str): The UUID of the expense to delete.

    Returns:
        bool: True if deletion was successful (record found and deleted), False otherwise.
    """
    conn = get_connection()
    if conn is None: return False

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
        logging.error(f"Error deleting expense {expense_id}: {e}")
        conn.rollback()
        return False
    finally:
        if conn: conn.close()


def fetch_last_expenses(n: int = 10) -> pd.DataFrame:
    """
    Fetches the last N expenses, ordered most recent first.

    Args:
        n (int): The number of recent expenses to fetch. Defaults to 10.

    Returns:
        pd.DataFrame: DataFrame containing the last N expenses, empty if error or no data.
    """
    conn = get_connection()
    if conn is None: return pd.DataFrame()

    try:
        # Added rowid desc as secondary sort for deterministic order if dates are identical
        df = pd.read_sql(f"SELECT * FROM expenses ORDER BY date DESC, rowid DESC LIMIT ?", conn, params=(n,))
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        logging.info(f"Fetched last {len(df)} expenses (requested {n}).")
        return df
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        logging.error(f"Error fetching last {n} expenses: {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()