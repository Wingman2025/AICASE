import os
import sqlite3
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
import numpy as np

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
            # Asegurarse de que la fecha esté en el formato correcto DD-MM-YYYY
            try:
                # Intentar parsear la fecha para validarla
                date_obj = datetime.strptime(date, "%d-%m-%Y")
                formatted_date = date_obj.strftime("%d-%m-%Y")
                print(f"Buscando datos para la fecha: {formatted_date}")
                
                if IS_RAILWAY:
                    query = "SELECT date, demand, inventory, production_plan FROM daily_data WHERE date = %s"
                else:
                    query = "SELECT date, demand, inventory, production_plan FROM daily_data WHERE date = ?"
                cursor.execute(query, (formatted_date,))
            except ValueError:
                print(f"Formato de fecha inválido: {date}. Debe ser DD-MM-YYYY")
                return []
        else:
            query = "SELECT date, demand, inventory, production_plan FROM daily_data ORDER BY date"
            cursor.execute(query)
            
        columns = [column[0] for column in cursor.description]
        result = []
        
        rows = cursor.fetchall()
        print(f"Filas encontradas: {len(rows)}")
        
        for row in rows:
            result.append(dict(zip(columns, row)))
        
        # Si no se encontraron resultados para una fecha específica, imprimir todas las fechas disponibles
        if date and len(result) == 0:
            print("No se encontraron datos para la fecha especificada. Verificando fechas disponibles...")
            cursor.execute("SELECT date FROM daily_data ORDER BY date")
            available_dates = [row[0] for row in cursor.fetchall()]
            print(f"Fechas disponibles en la base de datos: {available_dates}")
        
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

def generate_future_data(start_date: str, days: int) -> str:
    """
    Generate random data for future dates and save to database.
    
    Args:
        start_date: Start date in DD-MM-YYYY format
        days: Number of days to generate data for
        
    Returns:
        Success or error message
    """
    try:
        # Parse start date
        print(f"Generando datos desde {start_date} para {days} días")
        start_date_obj = datetime.strptime(start_date, "%d-%m-%Y")
        
        # Generate random data
        dates = [start_date_obj + timedelta(days=i) for i in range(days)]
        demand = np.random.randint(50, 150, size=days)
        production_plan = np.random.randint(50, 150, size=days)
        
        # Calculate inventory as production_plan - demand
        inventory = [production_plan[i] - demand[i] for i in range(days)]
        
        # Format dates for database
        formatted_dates = [date.strftime("%d-%m-%Y") for date in dates]
        print(f"Fechas generadas: {formatted_dates}")
        
        # Connect to database
        conn = get_connection()
        cursor = conn.cursor()
        
        # Insert data for each date
        inserted_count = 0
        updated_count = 0
        
        for i in range(days):
            # Check if date already exists
            if IS_RAILWAY:
                cursor.execute("SELECT COUNT(*) FROM daily_data WHERE date = %s", (formatted_dates[i],))
            else:
                cursor.execute("SELECT COUNT(*) FROM daily_data WHERE date = ?", (formatted_dates[i],))
                
            exists = cursor.fetchone()[0] > 0
            
            if exists:
                # Update existing record
                if IS_RAILWAY:
                    cursor.execute(
                        "UPDATE daily_data SET demand = %s, production_plan = %s, inventory = %s WHERE date = %s",
                        (int(demand[i]), int(production_plan[i]), int(inventory[i]), formatted_dates[i])
                    )
                else:
                    cursor.execute(
                        "UPDATE daily_data SET demand = ?, production_plan = ?, inventory = ? WHERE date = ?",
                        (int(demand[i]), int(production_plan[i]), int(inventory[i]), formatted_dates[i])
                    )
                updated_count += 1
                print(f"Actualizado registro para {formatted_dates[i]}: demanda={int(demand[i])}, producción={int(production_plan[i])}, inventario={int(inventory[i])}")
            else:
                # Insert new record
                if IS_RAILWAY:
                    cursor.execute(
                        "INSERT INTO daily_data (date, demand, production_plan, inventory) VALUES (%s, %s, %s, %s)",
                        (formatted_dates[i], int(demand[i]), int(production_plan[i]), int(inventory[i]))
                    )
                else:
                    cursor.execute(
                        "INSERT INTO daily_data (date, demand, production_plan, inventory) VALUES (?, ?, ?, ?)",
                        (formatted_dates[i], int(demand[i]), int(production_plan[i]), int(inventory[i]))
                    )
                inserted_count += 1
                print(f"Insertado nuevo registro para {formatted_dates[i]}: demanda={int(demand[i])}, producción={int(production_plan[i])}, inventario={int(inventory[i])}")
        
        # Verificar que los datos se hayan guardado correctamente
        if IS_RAILWAY:
            cursor.execute("SELECT date, demand FROM daily_data WHERE date = %s", (formatted_dates[0],))
        else:
            cursor.execute("SELECT date, demand FROM daily_data WHERE date = ?", (formatted_dates[0],))
        
        first_record = cursor.fetchone()
        print(f"Verificación del primer registro: {first_record}")
        
        conn.commit()
        conn.close()
        
        return f"Successfully generated data for {days} days starting from {start_date}. Inserted {inserted_count} new records and updated {updated_count} existing records."
    
    except Exception as e:
        print(f"Error en generate_future_data: {str(e)}")
        return f"Error generating future data: {str(e)}"

def delete_all_data() -> str:
    """
    Elimina todos los datos de la tabla daily_data para comenzar desde cero.
    
    Returns:
        Mensaje indicando el éxito o error de la operación.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Obtener el número de registros antes de eliminar
        cursor.execute("SELECT COUNT(*) FROM daily_data")
        count_before = cursor.fetchone()[0]
        
        # Eliminar todos los registros
        cursor.execute("DELETE FROM daily_data")
        
        # Verificar que todos los registros se hayan eliminado
        cursor.execute("SELECT COUNT(*) FROM daily_data")
        count_after = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        return f"Se han eliminado correctamente {count_before} registros de la base de datos. La tabla ahora está vacía y lista para comenzar desde cero."
    
    except Exception as e:
        print(f"Error al eliminar los datos: {str(e)}")
        return f"Error al eliminar los datos: {str(e)}"

def create_conversation_history_table():
    """
    Crea la tabla para almacenar el historial de conversaciones si no existe.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if IS_RAILWAY:
        # PostgreSQL
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_history (
            id SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
    else:
        # SQLite
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
    
    conn.commit()
    conn.close()
    
def save_message(session_id, role, content):
    """
    Guarda un mensaje en el historial de conversaciones.
    
    Args:
        session_id: Identificador único de la sesión
        role: Rol del mensaje ('user' o 'assistant')
        content: Contenido del mensaje
        
    Returns:
        ID del mensaje guardado
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if IS_RAILWAY:
        # PostgreSQL
        cursor.execute(
            "INSERT INTO conversation_history (session_id, role, content) VALUES (%s, %s, %s) RETURNING id",
            (session_id, role, content)
        )
        message_id = cursor.fetchone()[0]
    else:
        # SQLite
        cursor.execute(
            "INSERT INTO conversation_history (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )
        message_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return message_id

def get_conversation_history(session_id):
    """
    Recupera el historial de conversación para una sesión específica.
    
    Args:
        session_id: Identificador único de la sesión
        
    Returns:
        Lista de diccionarios con los mensajes de la conversación
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT role, content FROM conversation_history WHERE session_id = ? ORDER BY id ASC",
        (session_id,)
    )
    
    # Convertir los resultados a una lista de diccionarios
    history = [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]
    
    conn.close()
    
    return history

def clear_conversation_history(session_id):
    """
    Elimina el historial de conversación para una sesión específica.
    
    Args:
        session_id: Identificador único de la sesión
        
    Returns:
        Mensaje indicando el éxito o error de la operación
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "DELETE FROM conversation_history WHERE session_id = ?",
        (session_id,)
    )
    
    conn.commit()
    conn.close()
    
    return f"Historial de conversación eliminado para la sesión {session_id}"