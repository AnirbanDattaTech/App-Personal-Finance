# FILE: assistant/finance-assistant/app/routers/budget_api.py

import logging
import datetime
import sys # <-- Import sys
from pathlib import Path # <-- Import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

# --- Path Setup to find 'streamlit' directory ---
# This calculates the project root assuming budget_api.py is in app/routers/
try:
    CURRENT_FILE_DIR = Path(__file__).resolve().parent
    ROUTERS_DIR = CURRENT_FILE_DIR
    APP_DIR = ROUTERS_DIR.parent
    FINANCE_ASSISTANT_DIR = APP_DIR.parent
    ASSISTANT_DIR = FINANCE_ASSISTANT_DIR.parent
    PROJECT_ROOT_DIR = ASSISTANT_DIR.parent # Should be 'app-personal-finance'

    if str(PROJECT_ROOT_DIR) not in sys.path:
        # Insert at the beginning to prioritize project modules
        sys.path.insert(0, str(PROJECT_ROOT_DIR))
        logging.info(f"Added {PROJECT_ROOT_DIR} to sys.path for db_utils import")
    else:
        # Use debug level if already present
        logging.debug(f"{PROJECT_ROOT_DIR} already in sys.path")

except Exception as e:
    # Log error during path calculation
    logging.error(f"Error calculating project root or modifying sys.path: {e}", exc_info=True)
    PROJECT_ROOT_DIR = None # Indicate failure

# --- Try importing db_utils ---
try:
    # Now this import should work if PROJECT_ROOT_DIR was added successfully
    from streamlit.db_utils import get_all_budget_data_for_month, update_budget_data
    logging.info("Successfully imported db_utils using sys.path adjustment.")
except ImportError as e:
    # Log critical error if import still fails
    logging.error(f"CRITICAL: Failed to import db_utils even after sys.path adjustment. Error: {e}", exc_info=True)
    # Define dummy functions to allow app to load, but endpoints will fail
    def get_all_budget_data_for_month(ym):
        logging.error("Using dummy get_all_budget_data_for_month due to import error.")
        return {}
    def update_budget_data(ym, acc, data):
        logging.error("Using dummy update_budget_data due to import error.")
        return False

# Configure logging for the rest of the module
logger = logging.getLogger(__name__)

# Define the router AFTER potential sys.path modification and imports
router = APIRouter(
    prefix="/budgets", # Add a prefix for all routes in this router
    tags=["Budget"]     # Tag for API documentation
)

# --- Pydantic Models ---
# (Keep the Pydantic models as defined before)

class BudgetDetails(BaseModel):
    """Structure for budget details of a single account."""
    budget_amount: float = Field(..., description="Configured budget amount for the month.")
    start_balance: Optional[float] = Field(None, description="Starting balance recorded for the month.")
    end_balance: Optional[float] = Field(None, description="Ending balance recorded for the month.")
    current_spend: float = Field(..., description="Total calculated spend for the month.")

class MonthlyBudgetsResponse(BaseModel):
    """Response structure for the GET /budgets/{year_month} endpoint."""
    year_month: str = Field(..., description="The requested month (YYYY-MM).")
    data: Dict[str, BudgetDetails] = Field(..., description="Dictionary mapping account names to their budget details.")
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "year_month": "2025-05",
                    "data": {
                        "Anirban-ICICI": {"budget_amount": 50000.0, "start_balance": 60000.0, "end_balance": None, "current_spend": 3250.75},
                        "Anirban-SBI": {"budget_amount": 0.0, "start_balance": 15000.0, "end_balance": None, "current_spend": 1200.0}
                    }
                }
            ]
        }
    }

class BudgetUpdateRequest(BaseModel):
    """Request body structure for the POST /budgets/{year_month}/{account} endpoint."""
    budget_amount: float = Field(..., ge=0, description="The budget amount to set.")
    start_balance: Optional[float] = Field(None, description="The starting balance to set (optional).")
    end_balance: Optional[float] = Field(None, description="The ending balance to set (optional).")
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"budget_amount": 55000.0, "start_balance": 61000.0, "end_balance": 18000.0}
            ]
        }
    }

class BudgetUpdateResponse(BaseModel):
    """Response structure for the POST /budgets/{year_month}/{account} endpoint."""
    success: bool = Field(..., description="Indicates if the update was successful.")
    message: str = Field(..., description="Status message.")
    account: str = Field(..., description="The account that was updated.")
    year_month: str = Field(..., description="The month for which data was updated.")
    model_config = {
         "json_schema_extra": {
             "examples": [
                 {"success": True, "message": "Budget data updated successfully.", "account": "Anirban-ICICI", "year_month": "2025-05"},
                 {"success": False, "message": "Budget updates only allowed for the current month.", "account": "Anirban-ICICI", "year_month": "2025-04"}
             ]
         }
    }

# --- API Endpoints ---
# (Keep the endpoint functions @router.get(...) and @router.post(...) as defined before)

@router.get("/{year_month}", response_model=MonthlyBudgetsResponse)
async def get_monthly_budget_summary(year_month: str):
    """
    Retrieves the budget, balances, and current spend for relevant accounts
    for the specified month (YYYY-MM).
    """
    logger.info(f"Received request GET /budgets/{year_month}")
    # Basic validation for year_month format (more robust can be added)
    try:
        datetime.datetime.strptime(year_month, '%Y-%m')
    except ValueError:
        logger.warning(f"Invalid year_month format received: {year_month}")
        raise HTTPException(status_code=400, detail="Invalid year_month format. Use YYYY-MM.")

    try:
        # This should now call the *real* function if import succeeded
        budget_data = get_all_budget_data_for_month(year_month)
        if not budget_data:
            # Log if the real function returned empty (maybe no data in DB yet?)
            logger.warning(f"No budget data found or generated by db_utils for {year_month}")

        logger.info(f"Successfully processed budget data fetch for {year_month}")
        return MonthlyBudgetsResponse(year_month=year_month, data=budget_data)

    except Exception as e:
        logger.exception(f"Error fetching budget data for {year_month} in API: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error fetching budget data for {year_month}.")

@router.post("/{year_month}/{account}", response_model=BudgetUpdateResponse)
async def update_monthly_budget(year_month: str, account: str, update_data: BudgetUpdateRequest):
    """
    Updates the budget, start balance, and end balance for a specific account
    and month. IMPORTANT: This operation is only allowed for the CURRENT month.
    """
    logger.info(f"Received request POST /budgets/{year_month}/{account} with data: {update_data.model_dump(exclude_unset=True)}")

    # Validate account? (Optional, depends if we trust inputs)
    valid_accounts = ["Anirban-ICICI", "Anirban-SBI"] # Example list of accounts managed by budget
    if account not in valid_accounts:
         raise HTTPException(status_code=400, detail=f"Invalid or unsupported account for budgeting: {account}")

    # --- Call db_utils function (handles current month check internally) ---
    try:
        # Pass data as a dictionary
        # This should now call the *real* function if import succeeded
        success = update_budget_data(year_month, account, update_data.model_dump())

        if success:
            logger.info(f"Successfully updated budget data for {account} in {year_month}")
            return BudgetUpdateResponse(
                success=True,
                message="Budget data updated successfully.",
                account=account,
                year_month=year_month
            )
        else:
            # update_budget_data returns False if month is wrong or DB error occurs
            # Check current month again here just to provide a specific message if needed
            current_month_str = datetime.date.today().strftime("%Y-%m")
            if year_month != current_month_str:
                 logger.warning(f"Update failed: Attempt to update non-current month {year_month}")
                 raise HTTPException(status_code=400, detail="Budget updates only allowed for the current month.")
            else:
                 # Must be a DB error within update_budget_data
                 logger.error(f"Update failed for {account} in {year_month} likely due to DB error in db_utils.")
                 raise HTTPException(status_code=500, detail="Failed to update budget data due to a database error.")

    except HTTPException:
         raise # Re-raise HTTPExceptions raised above
    except Exception as e:
         logger.exception(f"Unexpected error updating budget data for {account} in {year_month}: {e}")
         raise HTTPException(status_code=500, detail="Internal server error while updating budget data.")