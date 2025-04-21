import pandas as pd
import random
from datetime import datetime, timedelta
import calendar
import numpy as np
import io
import time # For timing efficiency
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any, Tuple, Literal # Import Literal

# --- Configuration ---
start_date = datetime(2023, 1, 1)
end_date = datetime(2025, 4, 20)
max_total_rows = 2450
max_rows_per_month = 95
min_monthly_spend = 60000
max_monthly_spend = 120000

accounts_map = {
    "Anirban": ["Anirban-SBI", "Anirban-ICICI"],
    "Puspita": ["Puspita-SBI", "Puspita-Bandhan"]
}

users_map = {
    "Anirban-SBI": "Anirban",
    "Anirban-ICICI": "Anirban",
    "Puspita-SBI": "Puspita",
    "Puspita-Bandhan": "Puspita"
}

categories_subcategories = {
    "Investment": ["SIP", "Mutual Funds", "Stocks", "FD/RD"],
    "Rent": ["House Rent"],
    "Travel": ["Day Trip", "Vacation", "Commute", "Cab", "Train", "Flight", "Hotel/Stay", "Parking Fee"],
    "Restaurant": ["Dine-in", "Takeaway", "Food Delivery", "Snacks", "Cafe", "Drinks"],
    "Insurance Premium": ["Life Insurance", "ULIP", "Health Insurance", "Vehicle Insurance"],
    "Household": [
        "Electricity Bill", "Plumbing", "Electrical Repairs", "Appliance Repair", "Cleaning",
        "Pest Control", "Bike Maintenance", "Car Maintenance",
        "Furniture", "Kitchen Tools", "Ironing", "Maid"
    ],
    "Connectivity": ["Airtel WiFi", "Jio Recharge", "Airtel Mobile", "Netflix", "Prime Video", "Disney+ Hotstar"],
    "Waste": ["Smoke", "Alcohol"],
    "Grocery": ["BigBasket", "Amazon", "Flipkart Grocery", "Zepto", "Local Store", "Other"],
    "Beauty": ["Nykaa", "Meesho", "Purplle", "Salon", "Makeup", "Skincare"], # Removed duplicate Salon
    "Shopping": ["Amazon", "Flipkart", "Meesho", "Nykaa", "Purple", "Lifestyle", "Max", "Myntra"],
    "Health": ["Doctor Visit", "Medicines", "Lab Test", "Health Checkup"],
    "Utilities": ["Electricity", "Water", "Gas Cylinder", "Maintenance", "Garbage Collection"],
    "Gifts & Donations": ["Family", "Friends", "Charity", "Temple"],
    "Entertainment": ["Movies", "Concerts", "Games"],
    "Education": ["Online Courses", "Books", "Workshops"]
}

# --- Pydantic Model for Validation ---
class ExpenseRecord(BaseModel):
    # Corrected 'date' field: Use base type 'str' and apply pattern via Field
    date: str = Field(..., pattern=r'^\d{2}-\d{2}-\d{4}$') # dd-mm-yyyy format

    year: int = Field(..., ge=2000, le=datetime.now().year + 5) # Basic year range check
    month: str = Field(..., pattern=r'^\d{4}-\d{2}$') # yyyy-mm format
    week: str = Field(..., pattern=r'^\d{4}-W\d{2}$') # yyyy-Www format
    day_of_week: Literal['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    account: Literal["Anirban-SBI", "Anirban-ICICI", "Puspita-SBI", "Puspita-Bandhan"]
    category: str # Can add Literal check later if list is stable
    sub_category: str # Can add Literal check later if list is stable
    type: str = Field(..., min_length=3) # Basic check for non-empty type
    user: Literal["Anirban", "Puspita"]
    amount: int = Field(..., ge=0, le=55000) # Allow up to Life Insurance amount


# --- Fixed Transaction Details (Similar structure) ---
fixed_transactions = {
    "Rent": {"User": "Anirban", "Account": "Anirban-ICICI", "Category": "Rent", "Sub-category": "House Rent", "Amount": 30000, "Day": 1},
    "Maid": {"User": "Puspita", "Account": "Puspita-SBI", "Category": "Household", "Sub-category": "Maid", "Amount": 2500, "Day": 1},
    "SIP": {"User": "Anirban", "Account": "Anirban-ICICI", "Category": "Investment", "Sub-category": "SIP", "Amount": 3000, "Day": 5},
    "ULIP": {"User": "Anirban", "Account": "Anirban-ICICI", "Category": "Insurance Premium", "Sub-category": "ULIP", "Amount": 4000, "Day_Range": (20, 25)},
    "Health Insurance": {"User": "Anirban", "Account": "Anirban-ICICI", "Category": "Insurance Premium", "Sub-category": "Health Insurance", "Amount": 1200, "Day_Range": (20, 25)},
    "Life Insurance": {"User": "Anirban", "Account": "Anirban-ICICI", "Category": "Insurance Premium", "Sub-category": "Life Insurance", "Amount": 55000, "Dates": [(3, 20), (9, 20)]} # (Month, Day)
}

# --- Realistic 'Type' Generation Helpers (Keep similar, minor tweaks if needed) ---
places = ["Home", "Office", "Airport", "Mall", "Friend Place", "Mysore", "Chennai", "Vacation", "Weekend Trip"]
grocery_stores = ["BigBasket", "Amazon Pantry", "Flipkart Grocery", "Zepto", "Local Kirana Store"]
grocery_needs = ["Quick Need", "Weekly Stock", "Monthly Topup"]
restaurants = ["Meghana Foods", "Nagarjuna", "Empire", "Third Wave Coffee", "Toit", "Truffles", "CTR", "Cafe Coffee Day", "Starbucks"]
shopping_stores = ["Amazon", "Flipkart", "Meesho", "Nykaa", "Purplle", "Lifestyle Store", "Max Fashion", "Myntra"]
shopping_items = ["Clothing", "Electronics", "Home Needs", "Books", "Skincare", "Makeup", "Haircare"]
health_items = ["Consultation", "Prescription", "Pain Relief", "Cold/Flu", "Test"]
health_places = ["Local GP", "Manipal Hospital", "Apollo Clinic", "Local Lab", "Metropolis", "Thyrocare"]
connectivity_items = ["Broadband Bill", "Mobile Recharge", "Postpaid/Prepaid", "Subscription"]
commute_methods = ["Metro Card Recharge", "Bus Ticket", "Parking"]
utility_items = ["BESCOM Bill", "BWSSB Bill", "Indane/HP Gas Booking", "Apartment Monthly Maintenance", "Monthly Waste Pickup Fee"]
repair_items = ["Local Plumber Fix", "Electrician Visit", "AC Service/Fridge Repair", "Urban Company Cleaning", "PCI Service", "Bike Maintenance", "Car Maintenance"]


def generate_realistic_type(category, sub_category, account, current_date):
    """Generates a more descriptive 'Type' based on category/sub-category."""
    month_name = calendar.month_name[current_date.month]
    year_short = current_date.strftime("%y")

    try:
        if category == "Rent" and sub_category == "House Rent":
            return f"Monthly House Rent - {month_name}"
        elif category == "Household" and sub_category == "Maid":
            return f"Monthly Maid Salary - {month_name}"
        elif category == "Investment" and sub_category == "SIP":
            return f"Monthly SIP Investment - {month_name}"
        elif category == "Insurance Premium" and sub_category == "ULIP":
            return f"Monthly ULIP Premium - {month_name}"
        elif category == "Insurance Premium" and sub_category == "Health Insurance":
             return f"Health Insurance Prem. - {month_name}-{year_short}"
        elif category == "Insurance Premium" and sub_category == "Life Insurance":
             return f"Life Insurance Premium - {month_name}-{year_short}"
        elif category == "Travel":
            if sub_category in ["Flight", "Train"]:
                company = random.choice(["Indigo", "Air India", "GoAir", "IRCTC", "Tatkal Ticket"])
                dest = random.choice([p for p in places if p != "Office"])
                return f"{company} - {dest}" if sub_category == "Flight" else f"{company} Booking - {dest}"
            elif sub_category == "Cab":
                company = random.choice(["Ola", "Uber", "Rapido Auto"])
                dest = random.choice(places)
                return f"{company} - {dest}"
            elif sub_category == "Commute":
                return f"{random.choice(commute_methods)} - {random.choice(places)}"
            elif sub_category == "Hotel/Stay":
                 hotel = random.choice(["Local Hotel", "OYO", "Treebo"])
                 trip = random.choice(["Vacation", "Weekend Trip"])
                 return f"Stay at {hotel} - {trip}"
            elif sub_category == "Parking Fee":
                 loc = random.choice(["Orion Mall", "Forum Mall", "Office Basement"])
                 return f"Parking @ {loc}"
            else: # Day Trip, Vacation
                return f"{sub_category} Expense"
        elif category == "Restaurant":
            rest = random.choice(restaurants)
            if sub_category == "Food Delivery":
                app = random.choice(["Zomato Order", "Swiggy Order"])
                return f"{app} - {rest}"
            elif sub_category == "Dine-in":
                meal = random.choice(["Lunch", "Dinner", "Snacks", "Coffee"])
                return f"{meal} @ {rest}"
            elif sub_category == "Takeaway":
                 return f"Takeaway from {rest}"
            elif sub_category == "Cafe":
                 return f"Coffee/Snack at {rest}"
            elif sub_category == "Snacks":
                 return f"Snacks from {rest}"
            elif sub_category == "Drinks":
                 return f"Drinks from {rest}"
        elif category == "Household":
            if sub_category in ["Plumbing", "Electrical Repairs", "Appliance Repair", "Cleaning", "Pest Control", "Bike Maintenance", "Car Maintenance"]:
                 possible_repairs = {
                     "Plumbing": "Local Plumber Fix", "Electrical Repairs": "Electrician Visit",
                     "Appliance Repair": "AC Service/Fridge Repair", "Cleaning": "Urban Company Cleaning",
                     "Pest Control": "PCI Service", "Bike Maintenance": "Bike Maintenance", "Car Maintenance": "Car Maintenance"
                 }
                 return possible_repairs.get(sub_category, f"{sub_category} Service")
            elif sub_category == "Furniture":
                 return "Furniture related expense"
            elif sub_category == "Kitchen Tools":
                 return "Kitchen Tools related expense"
            elif sub_category == "Ironing":
                 return "Local Presswala"
            elif sub_category == "Electricity Bill":
                 return f"Electricity Bill - {month_name}"
        elif category == "Connectivity":
             if sub_category in ["Airtel WiFi", "Prime Video", "Netflix", "Disney+ Hotstar"]:
                 return f"{sub_category} Subscription - {month_name}"
             elif sub_category in ["Jio Recharge", "Airtel Mobile"]:
                 return f"{sub_category} {'Mobile Recharge' if 'Jio' in sub_category else 'Postpaid/Prepaid'}"
        elif category == "Waste":
            return f"{sub_category} related expense"
        elif category == "Grocery":
            if sub_category == "Other":
                return "Other related expense"
            store = sub_category
            need = random.choice(grocery_needs)
            if store == "Amazon": store = "Amazon Pantry"
            if store == "Flipkart Grocery": store = "Flipkart Grocery Order"
            if store == "Zepto": store = "Zepto Quick Order"
            if store == "BigBasket": store = "BB Order"
            if store == "Local Store": store = "Local Kirana Store"
            return f"{store} - {need}"
        elif category == "Beauty":
             store = sub_category if sub_category in ["Nykaa", "Meesho", "Purplle"] else "Salon"
             item = random.choice(["Skincare", "Makeup", "Haircare"])
             if store == "Salon":
                 service = random.choice(["Facial Treatment", "Manicure @ Local Salon", "Haircut"])
                 return service
             elif store =="Meesho":
                 return f"{store} Beauty - {item}"
             elif store == "Purplle":
                 return f"Purplle Order - {item}"
             elif store == "Nykaa":
                 return f"Nykaa Order - {item}"
             else: # Fallback for Makeup/Skincare direct subcats
                 brand = random.choice(["Sephora Purchase", "Body Shop Items"])
                 return f"{brand} - {item}"
        elif category == "Shopping":
             store = sub_category
             item = random.choice(shopping_items)
             prefix = f"{store} Order" if store in ["Amazon", "Flipkart"] else f"{store} Find" if store == "Meesho" else f"Purplle Haul" if store =="Purple" else f"{store} Fashion" if store in ["Max", "Myntra"] else f"{store} Store" if store =="Lifestyle" else f"{store} Beauty" if store == "Nykaa" else store
             return f"{prefix} - {item}"
        elif category == "Health":
             if sub_category == "Doctor Visit":
                 place = random.choice(health_places[:3])
                 return f"Consultation @ {place}"
             elif sub_category == "Medicines":
                 place = random.choice(["Apollo Pharmacy / Local Chemist"])
                 reason = random.choice(health_items[1:4])
                 return f"{place} - {reason}"
             elif sub_category == "Lab Test":
                 place = random.choice(health_places[3:])
                 return f"Test at {place}"
             elif sub_category == "Health Checkup":
                 return "Health Checkup"
        elif category == "Utilities":
             if sub_category == "Electricity": return f"BESCOM Bill - {month_name}"
             if sub_category == "Water": return f"BWSSB Bill - {month_name}"
             if sub_category == "Gas Cylinder": return f"Indane/HP Gas Booking"
             if sub_category == "Maintenance": return f"Apartment Monthly Maintenance - {month_name}"
             if sub_category == "Garbage Collection": return f"Monthly Waste Pickup Fee - {month_name}"
        elif category == "Gifts & Donations":
            return f"{sub_category} related expense"
        elif category == "Entertainment":
            return f"{sub_category} related expense"
        elif category == "Education":
            return f"{sub_category} related expense"

        return f"{sub_category} transaction" # Fallback
    except Exception as e:
        # print(f"Error generating type for {category}/{sub_category}: {e}") # Debugging
        return f"{sub_category} expense" # Safe fallback


# --- Amount Generation Helpers (Keep similar) ---
def get_amount(category, sub_category, day_of_month):
    """Generates a realistic amount based on category/sub-category."""
    day_factor = 1.5 if day_of_month <= 10 else 1.0 # Early month spike

    if category == "Rent": return 30000
    if category == "Household" and sub_category == "Maid": return 2500
    if category == "Investment" and sub_category == "SIP": return 3000
    if category == "Insurance Premium":
        if sub_category == "ULIP": return 4000
        if sub_category == "Health Insurance": return 1200
        if sub_category == "Life Insurance": return 55000
        return random.randint(1000, 15000)

    if category == "Travel":
        if sub_category == "Flight": return random.randint(3000, 15000)
        if sub_category == "Hotel/Stay": return random.randint(1500, 15000)
        if sub_category == "Vacation": return random.randint(5000, 45000)
        if sub_category == "Train": return random.randint(500, 3000)
        if sub_category == "Day Trip": return random.randint(500, 3000)
        if sub_category == "Cab": return random.randint(100, 800)
        if sub_category == "Commute": return random.randint(30, 300)
        if sub_category == "Parking Fee": return random.randint(50, 250)
    if category == "Restaurant":
        if sub_category in ["Dine-in", "Food Delivery", "Takeaway"]: return random.randint(300, 2500)
        if sub_category in ["Snacks", "Cafe", "Drinks"]: return random.randint(100, 800)
    if category == "Household":
        if sub_category == "Furniture": return random.randint(5000, 45000)
        if sub_category in ["Plumbing", "Electrical Repairs", "Appliance Repair", "Bike Maintenance", "Car Maintenance"]: return random.randint(500, 10000)
        if sub_category == "Electricity Bill": return random.randint(500, 3000)
        if sub_category in ["Cleaning", "Pest Control"]: return random.randint(300, 1500)
        if sub_category == "Kitchen Tools": return random.randint(200, 2000)
        if sub_category == "Ironing": return random.randint(50, 500)
    if category == "Connectivity":
        if sub_category == "Airtel WiFi": return random.randint(600, 1500)
        if sub_category in ["Jio Recharge", "Airtel Mobile"]: return random.randint(150, 800)
        if sub_category in ["Netflix", "Prime Video", "Disney+ Hotstar"]: return random.randint(150, 800)
    if category == "Waste":
        if sub_category == "Smoke": return random.randint(50, 1000)
        if sub_category == "Alcohol": return random.randint(300, 2000)
    if category == "Grocery":
        base_amount = random.randint(100, 4000) if sub_category != "Other" else random.randint(50, 3000)
        return int(base_amount * day_factor)
    if category == "Beauty":
         if sub_category == "Salon": return random.randint(300, 5000)
         return random.randint(500, 8000)
    if category == "Shopping":
        base_amount = random.randint(500, 8000)
        return int(base_amount * day_factor)
    if category == "Health":
         if sub_category == "Health Checkup": return random.randint(2000, 8000)
         if sub_category == "Lab Test": return random.randint(500, 4000)
         if sub_category == "Doctor Visit": return random.randint(500, 1500)
         if sub_category == "Medicines": return random.randint(100, 1500)
    if category == "Utilities":
         if sub_category == "Electricity": return random.randint(500, 3500)
         if sub_category == "Maintenance": return random.randint(2000, 4000)
         if sub_category == "Gas Cylinder": return random.randint(1000, 1200)
         if sub_category == "Water": return random.randint(200, 800)
         if sub_category == "Garbage Collection": return random.randint(50, 200)
    if category == "Gifts & Donations": return random.randint(100, 5000)
    if category == "Entertainment": return random.randint(200, 3000)
    if category == "Education": return random.randint(300, 10000)

    return random.randint(50, 500) # Default fallback


# --- Weights for Random Selection (Keep similar) ---
category_weights = {
    "Grocery": 25, "Restaurant": 20, "Household": 15, "Travel": 10,
    "Shopping": 10, "Connectivity": 5, "Utilities": 5, "Health": 4,
    "Waste": 3, "Beauty": 3, "Entertainment": 2, "Gifts & Donations": 2,
    "Education": 1, "Investment": 0.1, "Insurance Premium": 0.1, "Rent": 0,
}
active_categories = [cat for cat, weight in category_weights.items() if weight > 0]
active_weights = [category_weights[cat] for cat in active_categories]
# Normalize weights for random.choices
total_weight = sum(active_weights)
normalized_weights = [w / total_weight for w in active_weights]

# --- Data Generation Loop ---
start_time = time.time()
all_transactions_dicts = [] # Store as dictionaries for easier Pydantic validation
current_date = start_date
last_payment_month = {} # Track cyclical payments
processed_dates = 0

while current_date <= end_date and len(all_transactions_dicts) < max_total_rows * 1.1: # Generate slightly more initially
    daily_transactions_dicts = []
    day_str = current_date.strftime("%d-%m-%Y")
    year_val = current_date.year
    month_str = current_date.strftime("%Y-%m")
    week_val = current_date.isocalendar()
    week_str = f"{week_val.year}-W{week_val.week:02d}"
    day_of_week = current_date.strftime('%A')
    day_of_month = current_date.day

    added_fixed_today = {} # Track (user, category, sub_category) added via fixed rules today

    # --- 1. Add Fixed Transactions ---
    for name, details in fixed_transactions.items():
        user = details["User"]
        account = details["Account"]
        category = details["Category"]
        sub_category = details["Sub-category"]
        amount = details["Amount"]
        type_desc = generate_realistic_type(category, sub_category, account, current_date)
        added_key = (user, category, sub_category)

        should_add = False
        if "Day" in details and day_of_month == details["Day"] and added_key not in added_fixed_today:
            should_add = True
        elif "Day_Range" in details and details["Day_Range"][0] <= day_of_month <= details["Day_Range"][1]:
            # Key for Day_Range includes month string
            month_key = (user, category, sub_category, month_str)
            if month_key not in last_payment_month and added_key not in added_fixed_today:
                should_add = True
                last_payment_month[month_key] = True # Mark as paid for this month using the 4-element key
        elif "Dates" in details:
             if (current_date.month, day_of_month) in details["Dates"] and added_key not in added_fixed_today:
                 should_add = True

        if should_add:
             transaction_dict = {
                 "date": day_str, "year": year_val, "month": month_str, "week": week_str,
                 "day_of_week": day_of_week, "account": account, "category": category,
                 "sub_category": sub_category, "type": type_desc, "user": user, "amount": amount
             }
             daily_transactions_dicts.append(transaction_dict)
             added_fixed_today[added_key] = True

    # --- CORRECTED Reset Logic ---
    # Reset monthly flags (specifically for Day_Range fixed payments) at the start of a new month
    if day_of_month == 1:
        # Only target the 4-element keys used by the Day_Range fixed payments for removal
        keys_to_remove = [
            k for k in last_payment_month
            if isinstance(k, tuple) and len(k) == 4 and k[3] != month_str
        ]
        for k in keys_to_remove:
            # Check if key still exists before deleting (optional safety)
            if k in last_payment_month:
                del last_payment_month[k]
        # Note: The 2-element keys for cyclical payments don't need explicit removal here.
        # Their logic checks the associated value (last paid month) when determining the next payment.

    # --- 2. Add Cyclical Utility Transactions ---
    utility_cycles = {
        ("Utilities", "Electricity"): 2, ("Utilities", "Gas Cylinder"): 2,
        ("Connectivity", "Airtel WiFi"): 6, ("Connectivity", "Jio Recharge"): 3,
        ("Connectivity", "Airtel Mobile"): 3,
    }
    for (cat, sub_cat), cycle_months in utility_cycles.items():
        # Key for tracking cyclical payments is the 2-element tuple
        last_paid_tracker_key = (cat, sub_cat)
        last_paid_month_str = last_payment_month.get(last_paid_tracker_key, None) # Get value (month str)

        needs_payment = False
        if last_paid_month_str is None: # First time ever
            if random.random() < 1.0 / (cycle_months * 28): # Chance to pay sometime in first cycle
                needs_payment = True
        else:
            try:
                # Calculate months difference robustly
                last_paid_dt = datetime.strptime(last_paid_month_str + "-01", "%Y-%m-%d")
                months_diff = (current_date.year - last_paid_dt.year) * 12 + current_date.month - last_paid_dt.month
                if months_diff >= cycle_months:
                    # Higher chance to pay once cycle is up (e.g., 10% chance per day)
                    if random.random() < 0.10:
                        needs_payment = True
            except ValueError: # Handle potential initial bad format if logic changes
                 last_payment_month[last_paid_tracker_key] = None # Reset if error
                 needs_payment = random.random() < 1.0 / (cycle_months * 28) # Retry initial chance

        if needs_payment:
             user = "Anirban" if cat == "Connectivity" else random.choice(["Anirban", "Puspita"])
             account = random.choice(accounts_map[user])
             if user == "Puspita" and account == "Puspita-Bandhan": account = "Puspita-SBI"
             if user == "Anirban" and random.random() < 0.7: account = "Anirban-ICICI"

             amount = get_amount(cat, sub_cat, day_of_month)
             type_desc = generate_realistic_type(cat, sub_cat, account, current_date)
             fixed_check_key = (user, cat, sub_cat) # Check if fixed rule added same thing today

             if fixed_check_key not in added_fixed_today:
                 transaction_dict = {
                     "date": day_str, "year": year_val, "month": month_str, "week": week_str,
                     "day_of_week": day_of_week, "account": account, "category": cat,
                     "sub_category": sub_cat, "type": type_desc, "user": user, "amount": amount
                 }
                 daily_transactions_dicts.append(transaction_dict)
                 # Update the last paid month using the 2-element tracker key
                 last_payment_month[last_paid_tracker_key] = month_str

    # --- 3. Add Random Daily Transactions ---
    num_random_transactions = random.randint(0, 18)
    anirban_had_txn = any(t['user'] == "Anirban" for t in daily_transactions_dicts)
    puspita_had_txn = any(t['user'] == "Puspita" for t in daily_transactions_dicts)
    if not anirban_had_txn: num_random_transactions = max(1, num_random_transactions)
    if not puspita_had_txn: num_random_transactions = max(1, num_random_transactions)

    generated_for_anirban = anirban_had_txn
    generated_for_puspita = puspita_had_txn

    for _ in range(num_random_transactions):
        if len(all_transactions_dicts) + len(daily_transactions_dicts) >= max_total_rows * 1.1: break

        user = "Anirban" if not generated_for_anirban else "Puspita" if not generated_for_puspita else random.choice(["Anirban", "Puspita"])

        category = random.choices(active_categories, weights=normalized_weights, k=1)[0]
        sub_category = random.choice(categories_subcategories[category])

        if user == "Anirban":
            account = random.choices(accounts_map[user], weights=[0.3, 0.7], k=1)[0]
        else:
            account = "Puspita-Bandhan" if category in ["Travel", "Beauty"] and random.random() < 0.8 else "Puspita-SBI"

        amount = get_amount(category, sub_category, day_of_month)
        amount = min(amount, 55000) # Ensure max cap (except Life Insurance handled above)

        type_desc = generate_realistic_type(category, sub_category, account, current_date)
        fixed_check_key = (user, category, sub_category)

        if fixed_check_key not in added_fixed_today:
            transaction_dict = {
                "date": day_str, "year": year_val, "month": month_str, "week": week_str,
                "day_of_week": day_of_week, "account": account, "category": category,
                "sub_category": sub_category, "type": type_desc, "user": user, "amount": amount
            }
            daily_transactions_dicts.append(transaction_dict)
            if user == "Anirban": generated_for_anirban = True
            if user == "Puspita": generated_for_puspita = True

    all_transactions_dicts.extend(daily_transactions_dicts)
    current_date += timedelta(days=1)
    processed_dates += 1
    if processed_dates % 100 == 0: # Progress indicator
         print(f"Processed {processed_dates} dates, {len(all_transactions_dicts)} records generated...")


generation_end_time = time.time()
print(f"\nRaw data generation finished in {generation_end_time - start_time:.2f} seconds.")
print(f"Generated {len(all_transactions_dicts)} raw transaction records.")

# --- Pydantic Validation ---
print("\nValidating generated data with Pydantic...")
validation_start_time = time.time()
validated_data = []
validation_errors = []

for i, record_dict in enumerate(all_transactions_dicts):
    try:
        # Ensure amount is int before validation
        record_dict['amount'] = int(record_dict['amount'])

        # Basic check for sub_category validity before Pydantic validation
        record_category = record_dict.get('category')
        record_sub_category = record_dict.get('sub_category')
        if record_category and record_category in categories_subcategories:
            if record_sub_category not in categories_subcategories[record_category]:
                 raise ValueError(f"Sub-category '{record_sub_category}' not valid for category '{record_category}'")
        elif not record_category:
            raise ValueError("Missing category field")


        validated_record = ExpenseRecord(**record_dict)
        validated_data.append(validated_record.model_dump()) # Get dict from validated model
    except (ValidationError, ValueError) as e:
        validation_errors.append({"index": i, "error": str(e), "data": record_dict})
    except Exception as e: # Catch any other unexpected error during validation
         validation_errors.append({"index": i, "error": f"Unexpected Error: {str(e)}", "data": record_dict})


validation_end_time = time.time()
print(f"Validation finished in {validation_end_time - validation_start_time:.2f} seconds.")

if validation_errors:
    print(f"\n--- Found {len(validation_errors)} Validation Errors! ---")
    # Print first few errors for debugging
    for err in validation_errors[:5]:
        print(f"Index: {err['index']}, Error: {err['error']}") # Don't print full data for brevity
        # print(f"Data: {err['data']}") # Uncomment to see data causing error
    print("Proceeding with only the successfully validated data...")
else:
    print("Pydantic validation successful for all records.")


# --- Create DataFrame from Validated Data ---
if not validated_data:
     print("No valid data to process after validation. Exiting.")
     exit()

df = pd.DataFrame(validated_data)
# Ensure amount is integer type in DataFrame, although Pydantic should enforce it
df['amount'] = df['amount'].astype(int)

print(f"\nCreated DataFrame with {len(df)} validated records.")

# --- Post-Generation Adjustments for Monthly Constraints ---
adjustment_start_time = time.time()
print("\nApplying monthly constraints...")
final_df_rows = []
# Use validated DataFrame 'df' here
grouped = df.groupby(['year', 'month'])

for name, group in grouped:
    month_spend = group['amount'].sum()
    month_rows = len(group)

    if month_spend < min_monthly_spend or month_spend > max_monthly_spend or month_rows > max_rows_per_month:
        # Separate fixed transactions
        fixed_mask = group['sub_category'].isin(["House Rent", "Maid", "SIP", "ULIP", "Health Insurance", "Life Insurance"])
        fixed_part = group[fixed_mask]
        variable_part = group[~fixed_mask].copy()

        current_spend = group['amount'].sum()
        current_rows = len(group)

        # Sort variable part by amount (ascending) to remove smallest first
        variable_part = variable_part.sort_values('amount', ascending=True)

        rows_removed_count = 0
        indices_to_drop = []

        # Remove rows if exceeding max rows OR if spend is too high
        while current_rows > max_rows_per_month or current_spend > max_monthly_spend:
             if rows_removed_count >= len(variable_part): break # Cannot remove more variable rows

             idx_to_remove = variable_part.index[rows_removed_count]
             amount_to_remove = variable_part.loc[idx_to_remove, 'amount']

             if (current_spend - amount_to_remove < min_monthly_spend) and (current_rows - 1 <= max_rows_per_month):
                 break

             indices_to_drop.append(idx_to_remove)
             current_spend -= amount_to_remove
             current_rows -= 1
             rows_removed_count += 1

        if indices_to_drop:
             variable_part = variable_part.drop(indices_to_drop)

        adjusted_group = pd.concat([fixed_part, variable_part]).sort_index()
        final_df_rows.append(adjusted_group)

    else:
        final_df_rows.append(group)

if final_df_rows:
    final_df = pd.concat(final_df_rows).reset_index(drop=True)
else:
    final_df = df

adjustment_end_time = time.time()
print(f"Monthly adjustments finished in {adjustment_end_time - adjustment_start_time:.2f} seconds.")
print(f"Total rows after monthly adjustments: {len(final_df)}")


# --- Final Trim and Saving ---
if len(final_df) > max_total_rows:
    print(f"Trimming final DataFrame from {len(final_df)} to {max_total_rows} rows...")
    try:
        final_df['date_dt'] = pd.to_datetime(final_df['date'], format='%d-%m-%Y', errors='coerce')
        final_df.dropna(subset=['date_dt'], inplace=True) # Drop rows if date format invalid
        final_df = final_df.sort_values(by='date_dt').iloc[:max_total_rows].reset_index(drop=True)
        final_df = final_df.drop(columns=['date_dt'])
        print(f"Final row count after trimming: {len(final_df)}")
    except Exception as e:
        print(f"Error during final date sorting/trimming: {e}. Skipping sort before trim.")
        final_df = final_df.iloc[:max_total_rows].reset_index(drop=True)


# Final sort and column order
try:
    final_df['date_dt'] = pd.to_datetime(final_df['date'], format='%d-%m-%Y', errors='coerce')
    final_df.dropna(subset=['date_dt'], inplace=True)
    final_df = final_df.sort_values(by='date_dt').reset_index(drop=True)
    final_df = final_df.drop(columns=['date_dt']) # Drop the temporary datetime column
except Exception as e:
    print(f"Error during final date sorting: {e}. Proceeding without final sort.")


# Define final column order explicitly
final_column_order = ['date', 'year', 'month', 'week', 'day_of_week', 'account', 'category', 'sub_category', 'type', 'user', 'amount']
# Reindex to ensure columns exist and are in order, fill missing with NaN if any (shouldn't happen)
final_df = final_df.reindex(columns=final_column_order)

# Save to CSV
output_filename = "generated_expenses_validated_2023_2025.csv"
final_df.to_csv(output_filename, index=False)

total_end_time = time.time()
print(f"\nGenerated {len(final_df)} rows of validated expense data saved to {output_filename}")
print(f"Total script execution time: {total_end_time - start_time:.2f} seconds.")

# Display sample
print("\nSample Data:")
print(final_df.head())
print("\n...")
print(final_df.tail())