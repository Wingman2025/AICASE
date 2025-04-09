import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta

def create_date_range(start, end):
    """Generate a date range from start to end dates."""
    return pd.date_range(start, end)

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
    """Update the production plan for a specific date."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # First, get the current demand for this date
    cursor.execute("SELECT demand FROM daily_data WHERE date = ?", (date,))
    result = cursor.fetchone()
    
    if result is None:
        conn.close()
        return f"No record found for date {date}."
        
    demand = result[0]
    
    # Calculate new inventory value
    new_inventory = production_plan - demand
    
    # Update both production_plan and inventory
    cursor.execute(
        "UPDATE daily_data SET production_plan = ?, inventory = ? WHERE date = ?", 
        (production_plan, new_inventory, date)
    )
    
    conn.commit()
    conn.close()
    
    return f"Production plan for {date} updated successfully to {production_plan}. Inventory recalculated to {new_inventory}."

def update_demand(db_path, date, demand):
    """Update the demand for a specific date."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # First, get the current production_plan for this date
    cursor.execute("SELECT production_plan FROM daily_data WHERE date = ?", (date,))
    result = cursor.fetchone()
    
    if result is None:
        conn.close()
        return f"No record found for date {date}."
        
    production_plan = result[0]
    
    # Calculate new inventory value
    new_inventory = production_plan - demand
    
    # Update both demand and inventory
    cursor.execute(
        "UPDATE daily_data SET demand = ?, inventory = ? WHERE date = ?", 
        (demand, new_inventory, date)
    )
    
    conn.commit()
    conn.close()
    
    return f"Demand for {date} updated successfully to {demand}. Inventory recalculated to {new_inventory}."

if __name__ == "__main__":
    # Example usage
    start_date = datetime(2025, 4, 1)
    days = 30
    
    # Generate daily data
    daily_data_df = generate_daily_data(start_date, days)
    
    # Create database directory if it doesn't exist
    import os
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    
    # Populate database
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "supply_chain.db")
    populate_database(db_path, daily_data_df)
    
    print("Sample data generated and saved to database.")
