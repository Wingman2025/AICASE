import os
import sqlite3
import pandas as pd
from typing import List, Dict, Any, Optional

def get_db_path():
    """Get the absolute path to the database file."""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Path to the data directory
    data_dir = os.path.join(script_dir, 'data')
    # Path to the database file
    return os.path.join(data_dir, 'supply_chain.db')

def get_connection():
    """Create and return a connection to the database."""
    db_path = get_db_path()
    return sqlite3.connect(db_path)

def get_daily_data(date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get daily data from the database.
    
    Args:
        date: Optional date string in DD-MM-YYYY format. If provided, only data for that date is returned.
        
    Returns:
        List of dictionaries containing the daily data.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if date:
            cursor.execute("SELECT * FROM daily_data WHERE date = ?", (date,))
        else:
            cursor.execute("SELECT * FROM daily_data")
        
        # Get column names
        columns = [desc[0] for desc in cursor.description]
        
        # Fetch all rows and convert to list of dictionaries
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append(dict(zip(columns, row)))
        
        return result
    finally:
        conn.close()

def update_production_plan(date: str, production_plan: int) -> str:
    """
    Update the production plan for a specific date.
    
    Args:
        date: Date string in DD-MM-YYYY format.
        production_plan: New production plan value.
        
    Returns:
        Success or error message.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE daily_data SET production_plan = ? WHERE date = ?", 
                      (production_plan, date))
        conn.commit()
        
        if cursor.rowcount == 0:
            return f"No record found for date {date}."
        return f"Production plan for {date} updated successfully to {production_plan}."
    except Exception as e:
        return f"Error updating record: {str(e)}"
    finally:
        conn.close()

def get_production_summary() -> Dict[str, Any]:
    """
    Get a summary of production data.
    
    Returns:
        Dictionary with production summary statistics.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                AVG(production_plan) as avg_production,
                MAX(production_plan) as max_production,
                MIN(production_plan) as min_production,
                SUM(production_plan) as total_production
            FROM daily_data
        """)
        
        row = cursor.fetchone()
        return {
            "average_production": row[0],
            "maximum_production": row[1],
            "minimum_production": row[2],
            "total_production": row[3]
        }
    finally:
        conn.close()

def get_demand_summary() -> Dict[str, Any]:
    """
    Get a summary of demand data.
    
    Returns:
        Dictionary with demand summary statistics.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                AVG(demand) as avg_demand,
                MAX(demand) as max_demand,
                MIN(demand) as min_demand,
                SUM(demand) as total_demand
            FROM daily_data
        """)
        
        row = cursor.fetchone()
        return {
            "average_demand": row[0],
            "maximum_demand": row[1],
            "minimum_demand": row[2],
            "total_demand": row[3]
        }
    finally:
        conn.close()

def get_inventory_summary() -> Dict[str, Any]:
    """
    Get a summary of inventory data.
    
    Returns:
        Dictionary with inventory summary statistics.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                AVG(inventory) as avg_inventory,
                MAX(inventory) as max_inventory,
                MIN(inventory) as min_inventory
            FROM daily_data
        """)
        
        row = cursor.fetchone()
        return {
            "average_inventory": row[0],
            "maximum_inventory": row[1],
            "minimum_inventory": row[2]
        }
    finally:
        conn.close()