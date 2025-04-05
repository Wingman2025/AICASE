import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta

def create_date_range(start, end):
    """Generate a date range from start to end dates."""
    return pd.date_range(start, end)

def generate_procurement_data(dates):
    """Simulate raw material procurement data."""
    return pd.DataFrame({
        'date': dates,
        'raw_material_ordered': np.random.randint(50, 150, size=len(dates)),
        'current_inventory': np.random.randint(100, 500, size=len(dates))
    })

def generate_production_data(dates):
    """Simulate production process data."""
    return pd.DataFrame({
        'date': dates,
        'planned_volume': np.random.randint(100, 300, size=len(dates)),
        'actual_volume': np.random.randint(90, 310, size=len(dates))
    })

def generate_inventory_data(dates):
    """Simulate inventory management data."""
    return pd.DataFrame({
        'date': dates,
        'stock_level': np.random.randint(50, 500, size=len(dates)),
        'reorder_threshold': 150  # Constant threshold for demonstration
    })

def generate_distribution_data(dates):
    """Simulate distribution data."""
    return pd.DataFrame({
        'date': dates,
        'orders_shipped': np.random.randint(30, 120, size=len(dates)),
        'delivery_delays': np.random.randint(0, 5, size=len(dates))
    })

def generate_daily_data(start_date, days):
    """Simulate daily data for demand, inventory, and production plan."""
    dates = [start_date + timedelta(days=i) for i in range(days)]
    demand = np.random.randint(50, 150, size=days)
    production_plan = np.random.randint(50, 150, size=days)
    
    # Calculate inventory as production_plan - demand
    inventory = [production_plan[i] - demand[i] for i in range(days)]  # Corrected formula
    
    return pd.DataFrame({
        'date': [date.strftime('%d-%m-%Y') for date in dates],  # Format date as DD-MM-YYYY
        'demand': demand,
        'inventory': inventory,
        'production_plan': production_plan
    })

def populate_database(db_path, daily_data):
    """Create and populate the SQLite database with daily data."""
    conn = sqlite3.connect(db_path)
    daily_data.to_sql('daily_data', conn, if_exists='replace', index=False)
    conn.close()
    print(f"Database created and populated at {db_path}")

def update_production_plan(db_path, date, production_plan):
    """
    Update the production plan value for a specific date in the database.

    Args:
        db_path (str): Path to the SQLite database file.
        date (str): Date of the record to update (format: DD-MM-YYYY).
        production_plan (int): New production plan value to set.

    Returns:
        str: Success message or error message.
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        # Correct column name to 'production_plan'
        cursor.execute("UPDATE daily_data SET production_plan = ? WHERE date = ?", (production_plan, date))
        conn.commit()
        if cursor.rowcount == 0:
            return f"No record found for date {date}."
        return f"Production plan for {date} updated successfully."
    except Exception as e:
        return f"Error updating record: {str(e)}"
    finally:
        conn.close()

if __name__ == '__main__':
    # Generate data for the next 15 days
    start_date = datetime(2025, 4, 3)
    days = 15
    daily_data = generate_daily_data(start_date, days)

    # Populate the SQLite database
    import os
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Create the database file path in the same directory as the script
    db_file = os.path.join(script_dir, 'supply_chain.db')
    populate_database(db_file, daily_data)

    # Example usage of update_production_plan
    date_to_update = '03-04-2025'
    new_production_plan = 180
    result = update_production_plan(db_file, date_to_update, new_production_plan)
    print(result)
