import os
import sqlite3
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Verificar si estamos en Railway (tiene DATABASE_URL configurado)
IS_RAILWAY = os.getenv("DATABASE_URL") is not None

def get_db_path():
    """
    Get the path to the SQLite database file.
    Only used in local development with SQLite.
    """
    if IS_RAILWAY:
        return None  # No se usa en Railway
        
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "data", "supply_chain.db")
    return db_path

def get_connection():
    """
    Get a connection to the database.
    Returns SQLite connection locally and PostgreSQL connection on Railway.
    """
    if IS_RAILWAY:
        # Importar psycopg2 solo si estamos en Railway
        import psycopg2
        
        db_url = os.getenv("DATABASE_URL")
        return psycopg2.connect(db_url)
    else:
        db_path = get_db_path()
        print(f"Using database at: {db_path}")
        return sqlite3.connect(db_path)

def get_daily_data(date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get daily supply chain data from the database.
    
    Args:
        date: Optional date string in DD-MM-YYYY format. If provided, only data for that date is returned.
        
    Returns:
        List of dictionaries containing the daily data.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        if date:
            if IS_RAILWAY:
                query = "SELECT date, demand, inventory, production_plan FROM daily_data WHERE date = %s"
            else:
                query = "SELECT date, demand, inventory, production_plan FROM daily_data WHERE date = ?"
            cursor.execute(query, (date,))
        else:
            query = "SELECT date, demand, inventory, production_plan FROM daily_data ORDER BY date"
            cursor.execute(query)
            
        columns = [column[0] for column in cursor.description]
        result = []
        
        for row in cursor.fetchall():
            result.append(dict(zip(columns, row)))
        
        return result
    finally:
        conn.close()

def update_production_plan(date: str, production_plan: int) -> str:
    """
    Update the production plan for a specific date and recalculate inventory.
    
    Args:
        date: Date string in DD-MM-YYYY format.
        production_plan: New production plan value.
        
    Returns:
        Success or error message.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # First, get the current demand for this date
        if IS_RAILWAY:
            cursor.execute("SELECT demand FROM daily_data WHERE date = %s", (date,))
        else:
            cursor.execute("SELECT demand FROM daily_data WHERE date = ?", (date,))
        
        result = cursor.fetchone()
        
        if result is None:
            return f"No record found for date {date}."
            
        demand = result[0]
        
        # Calculate new inventory value
        new_inventory = production_plan - demand
        
        # Update both production_plan and inventory
        if IS_RAILWAY:
            cursor.execute(
                "UPDATE daily_data SET production_plan = %s, inventory = %s WHERE date = %s", 
                (production_plan, new_inventory, date)
            )
        else:
            cursor.execute(
                "UPDATE daily_data SET production_plan = ?, inventory = ? WHERE date = ?", 
                (production_plan, new_inventory, date)
            )
        
        conn.commit()
        
        if cursor.rowcount == 0:
            return f"No record found for date {date}."
        return f"Production plan for {date} updated successfully to {production_plan}. Inventory recalculated to {new_inventory}."
    except Exception as e:
        return f"Error updating record: {str(e)}"
    finally:
        conn.close()

def update_demand(date: str, demand: int) -> str:
    """
    Update the demand for a specific date and recalculate inventory.
    
    Args:
        date: Date string in DD-MM-YYYY format.
        demand: New demand value.
        
    Returns:
        Success or error message.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # First, get the current production_plan for this date
        if IS_RAILWAY:
            cursor.execute("SELECT production_plan FROM daily_data WHERE date = %s", (date,))
        else:
            cursor.execute("SELECT production_plan FROM daily_data WHERE date = ?", (date,))
        
        result = cursor.fetchone()
        
        if result is None:
            return f"No record found for date {date}."
            
        production_plan = result[0]
        
        # Calculate new inventory value
        new_inventory = production_plan - demand
        
        # Update both demand and inventory
        if IS_RAILWAY:
            cursor.execute(
                "UPDATE daily_data SET demand = %s, inventory = %s WHERE date = %s", 
                (demand, new_inventory, date)
            )
        else:
            cursor.execute(
                "UPDATE daily_data SET demand = ?, inventory = ? WHERE date = ?", 
                (demand, new_inventory, date)
            )
        
        conn.commit()
        
        if cursor.rowcount == 0:
            return f"No record found for date {date}."
        return f"Demand for {date} updated successfully to {demand}. Inventory recalculated to {new_inventory}."
    except Exception as e:
        return f"Error updating record: {str(e)}"
    finally:
        conn.close()

def get_production_summary():
    """
    Get a summary of production data.
    
    Returns:
        Dictionary with production summary statistics.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Get total, average, min, and max production plan
        if IS_RAILWAY:
            cursor.execute("SELECT SUM(production_plan), AVG(production_plan), MIN(production_plan), MAX(production_plan) FROM daily_data")
        else:
            cursor.execute("SELECT SUM(production_plan), AVG(production_plan), MIN(production_plan), MAX(production_plan) FROM daily_data")
        
        total, avg, min_val, max_val = cursor.fetchone()
        
        return {
            "total_production": total,
            "average_production": round(avg, 2) if avg else 0,
            "min_production": min_val,
            "max_production": max_val
        }
    finally:
        conn.close()

def get_demand_summary():
    """
    Get a summary of demand data.
    
    Returns:
        Dictionary with demand summary statistics.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Get total, average, min, and max demand
        if IS_RAILWAY:
            cursor.execute("SELECT SUM(demand), AVG(demand), MIN(demand), MAX(demand) FROM daily_data")
        else:
            cursor.execute("SELECT SUM(demand), AVG(demand), MIN(demand), MAX(demand) FROM daily_data")
        
        total, avg, min_val, max_val = cursor.fetchone()
        
        return {
            "total_demand": total,
            "average_demand": round(avg, 2) if avg else 0,
            "min_demand": min_val,
            "max_demand": max_val
        }
    finally:
        conn.close()

def get_inventory_summary():
    """
    Get a summary of inventory data.
    
    Returns:
        Dictionary with inventory summary statistics.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Get total, average, min, and max inventory
        if IS_RAILWAY:
            cursor.execute("SELECT SUM(inventory), AVG(inventory), MIN(inventory), MAX(inventory) FROM daily_data")
        else:
            cursor.execute("SELECT SUM(inventory), AVG(inventory), MIN(inventory), MAX(inventory) FROM daily_data")
        
        total, avg, min_val, max_val = cursor.fetchone()
        
        return {
            "total_inventory": total,
            "average_inventory": round(avg, 2) if avg else 0,
            "min_inventory": min_val,
            "max_inventory": max_val
        }
    finally:
        conn.close()