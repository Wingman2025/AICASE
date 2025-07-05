import os
import sqlite3
import traceback
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import dateparser
import re
import numpy as np
import psycopg2
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Verificar si estamos en Railway (PostgreSQL) o local (SQLite)
IS_RAILWAY = 'DATABASE_URL' in os.environ

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
    Obtiene una conexión a la base de datos, ya sea SQLite (local) o PostgreSQL (Railway).
    
    Returns:
        Objeto de conexión a la base de datos
    """
    if IS_RAILWAY:
        # Conexión a PostgreSQL en Railway
        DATABASE_URL = os.environ['DATABASE_URL']
        conn = psycopg2.connect(DATABASE_URL)
    else:
        # Conexión a SQLite local
        db_path = get_db_path()
        print(f"Using database at: {db_path}")
        conn = sqlite3.connect(db_path)
    
    return conn


def parse_date(date_str: str) -> str:
    """
    Parses a date string in any format or natural language and returns it
    in the correct format for the database.

    Returns:
        Date string in the `YYYY-MM-DD` format for both PostgreSQL and SQLite.
    """
    # Explicitly specify DD-MM-YYYY format as the preferred input format,
    # but allow dateparser to handle natural language as well. If the input
    # is just a month name (optionally followed by a year), parse it
    # separately so the day defaults to the first of that month.
    month_only = re.fullmatch(r"[A-Za-z]+(?:\s+\d{4})?", date_str.strip())
    if month_only:
        parsed = dateparser.parse(
            date_str,
            settings={"PREFER_DAY_OF_MONTH": "first"},
        )
    else:
        parsed = dateparser.parse(
            date_str,
            date_formats=["%d-%m-%Y", "%d/%m/%Y"],
            settings={"PREFER_DAY_OF_MONTH": "first"},
        )
    if not parsed:
        raise ValueError(f"No se pudo interpretar la fecha: {date_str}")

    # Always return ISO format regardless of the database backend
    return parsed.strftime("%Y-%m-%d")

def get_daily_data(date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get daily supply chain data from the database.
    
    Args:
        date: Optional date string in `YYYY-MM-DD` format. If provided, only data for that date is returned.
        
    Returns:
        List of dictionaries containing the daily data.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        if date:
            # Use the parse_date function to handle any date format
            try:
                formatted_date = parse_date(date)
                print(f"Buscando datos para la fecha: {formatted_date}")
                
                if IS_RAILWAY:
                    query = "SELECT date, demand, production_plan, forecast, inventory FROM daily_data WHERE date = %s"
                else:
                    query = "SELECT date, demand, production_plan, forecast, inventory FROM daily_data WHERE date = ?"
                cursor.execute(query, (formatted_date,))
            except ValueError as e:
                print(f"Error al procesar la fecha: {e}")
                return []
        else:
            query = "SELECT date, demand, production_plan, forecast, inventory FROM daily_data ORDER BY date"
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
    """Update the production plan for a specific date and recalculate cumulative inventory."""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        if IS_RAILWAY:
            cursor.execute("UPDATE daily_data SET production_plan = %s WHERE date = %s", (int(production_plan), date))
        else:
            cursor.execute("UPDATE daily_data SET production_plan = ? WHERE date = ?", (int(production_plan), date))

        conn.commit()

        if cursor.rowcount == 0:
            return f"No record found for date {date}."

        recalculate_inventory_from(date)
        return f"Production plan for {date} updated successfully to {production_plan}. Inventory recalculated cumulatively."
    except Exception as e:
        return f"Error updating record: {str(e)}"
    finally:
        conn.close()

def update_demand(date: str, demand: int) -> str:
    """Update the demand for a specific date and recalculate cumulative inventory."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if IS_RAILWAY:
            cursor.execute("UPDATE daily_data SET demand = %s WHERE date = %s", (int(demand), date))
        else:
            cursor.execute("UPDATE daily_data SET demand = ? WHERE date = ?", (int(demand), date))
        conn.commit()
        if cursor.rowcount == 0:
            return f"No record found for date {date}."
        recalculate_inventory_from(date)
        return f"Demand for {date} updated successfully to {demand}. Inventory recalculated cumulatively."
    except Exception as e:
        return f"Error updating record: {str(e)}"
    finally:
        conn.close()

def increase_all_demand(offset: int) -> str:
    """Increase demand for every existing record by a constant offset and recalculate inventory cumulatively.

    Args:
        offset: Integer to add to each demand value (can be negative).

    Returns:
        Success or error message.
    """
    if offset == 0:
        return "Offset is zero; no changes made."

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT date, demand FROM daily_data ORDER BY date")
        rows = cursor.fetchall()
        if not rows:
            return "No data available to update."

        for date_val, demand in rows:
            new_demand = int(demand) + int(offset)
            if IS_RAILWAY:
                cursor.execute("UPDATE daily_data SET demand = %s WHERE date = %s", (new_demand, date_val))
            else:
                cursor.execute("UPDATE daily_data SET demand = ? WHERE date = ?", (new_demand, date_val))

        conn.commit()

        # Recalculate inventory once starting from first date
        first_date = rows[0][0]
        recalculate_inventory_from(first_date)
        return f"Demand increased by {offset} units for {len(rows)} days. Inventory recalculated cumulatively."
    except Exception as e:
        conn.rollback()
        return f"Error increasing demand: {str(e)}"
    finally:
        conn.close()


def update_forecast(date: str, forecast_value: int) -> str:
    """Update the forecast value for a specific date."""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        if IS_RAILWAY:
            cursor.execute(
                "UPDATE daily_data SET forecast = %s WHERE date = %s",
                (int(forecast_value), date),
            )
        else:
            cursor.execute(
                "UPDATE daily_data SET forecast = ? WHERE date = ?",
                (int(forecast_value), date),
            )

        conn.commit()

        if cursor.rowcount == 0:
            return f"No record found for date {date}."
        return f"Forecast for {date} updated successfully to {forecast_value}."
    except Exception as e:
        return f"Error updating record: {str(e)}"
    finally:
        conn.close()

def clear_all_forecast() -> str:
    """Clear the forecast column for every row without deleting data."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Set forecast to NULL (works both PostgreSQL and SQLite)
        cursor.execute("UPDATE daily_data SET forecast = NULL")
        conn.commit()
        return "All forecast values cleared."
    except Exception as e:
        conn.rollback()
        return f"Error clearing forecast values: {str(e)}"
    finally:
        conn.close()


def clear_forecast_range(start_date: str, end_date: Optional[str] = None) -> str:
    """Clear forecast values for a given date range.

    ``start_date`` and ``end_date`` may be provided in any parsable format. All
    rows with a ``date`` greater than or equal to ``start_date`` and, if
    ``end_date`` is given, less than or equal to ``end_date`` will have their
    ``forecast`` column set to ``NULL``.
    """

    try:
        iso_start = parse_date(start_date)
        iso_end = parse_date(end_date) if end_date else None
    except ValueError as e:
        return f"Error processing date: {e}"

    conn = get_connection()
    try:
        cursor = conn.cursor()
        if iso_end:
            if IS_RAILWAY:
                cursor.execute(
                    "UPDATE daily_data SET forecast = NULL WHERE date >= %s AND date <= %s",
                    (iso_start, iso_end),
                )
            else:
                cursor.execute(
                    "UPDATE daily_data SET forecast = NULL WHERE date >= ? AND date <= ?",
                    (iso_start, iso_end),
                )
        else:
            if IS_RAILWAY:
                cursor.execute(
                    "UPDATE daily_data SET forecast = NULL WHERE date >= %s",
                    (iso_start,),
                )
            else:
                cursor.execute(
                    "UPDATE daily_data SET forecast = NULL WHERE date >= ?",
                    (iso_start,),
                )

        conn.commit()
        if cursor.rowcount == 0:
            return "No rows matched the specified date range."
        if iso_end:
            return f"Forecast cleared from {iso_start} to {iso_end}."
        return f"Forecast cleared on or after {iso_start}."
    except Exception as e:
        conn.rollback()
        return f"Error clearing forecast values: {str(e)}"
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
            "total_production": int(total) if total is not None else 0,
            "average_production": round(float(avg), 2) if avg is not None else 0,
            "min_production": int(min_val) if min_val is not None else 0,
            "max_production": int(max_val) if max_val is not None else 0
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
            "total_demand": int(total) if total is not None else 0,
            "average_demand": round(float(avg), 2) if avg is not None else 0,
            "min_demand": int(min_val) if min_val is not None else 0,
            "max_demand": int(max_val) if max_val is not None else 0
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
            "total_inventory": int(total) if total is not None else 0,
            "average_inventory": round(float(avg), 2) if avg is not None else 0,
            "min_inventory": int(min_val) if min_val is not None else 0,
            "max_inventory": int(max_val) if max_val is not None else 0
        }
    finally:
        conn.close()

def get_latest_inventory() -> int:
    """Return the inventory value for the most recent date."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT inventory FROM daily_data ORDER BY date DESC LIMIT 1")
        row = cursor.fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()

def get_stockouts() -> List[Dict[str, Any]]:
    """Retrieve rows where inventory is zero or negative."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = (
            "SELECT date, demand, production_plan, inventory FROM daily_data "
            "WHERE inventory <= 0 ORDER BY date"
        )
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()

def propose_production_plan_for_stockouts() -> List[Dict[str, Any]]:
    """Propose a production plan equal to demand for each stockout day."""
    stockouts = get_stockouts()
    proposals = []
    for row in stockouts:
        date = row["date"]
        demand = int(row["demand"])
        current_plan = int(row["production_plan"])
        proposed_plan = demand
        resulting_inventory = proposed_plan - demand
        proposals.append(
            {
                "date": date,
                "demand": demand,
                "current_production_plan": current_plan,
                "proposed_production_plan": proposed_plan,
                "resulting_inventory": resulting_inventory,
            }
        )
    return proposals

def recalculate_inventory_from(start_date: str) -> None:
    """Recompute cumulative inventory from a given date onward."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if IS_RAILWAY:
            cursor.execute("SELECT inventory FROM daily_data WHERE date < %s ORDER BY date DESC LIMIT 1", (start_date,))
        else:
            cursor.execute("SELECT inventory FROM daily_data WHERE date < ? ORDER BY date DESC LIMIT 1", (start_date,))
        prev = cursor.fetchone()
        running_inventory = int(prev[0]) if prev else 0
        if IS_RAILWAY:
            cursor.execute("SELECT date, production_plan, demand FROM daily_data WHERE date >= %s ORDER BY date", (start_date,))
        else:
            cursor.execute("SELECT date, production_plan, demand FROM daily_data WHERE date >= ? ORDER BY date", (start_date,))
        rows = cursor.fetchall()
        for date_val, plan, demand in rows:
            running_inventory += int(plan) - int(demand)
            if IS_RAILWAY:
                cursor.execute("UPDATE daily_data SET inventory = %s WHERE date = %s", (running_inventory, date_val))
            else:
                cursor.execute("UPDATE daily_data SET inventory = ? WHERE date = ?", (running_inventory, date_val))
        conn.commit()
    finally:
        conn.close()

def generate_future_data(start_date: str, days: int) -> str:
    """

    Generate random data for future dates and save to database.
    
    Args:
        start_date: Start date in any format or natural language
        days: Number of days to generate data for
        
    Returns:
        Success or error message
    """
    try:
        # Parse start date using parse_date function
        print(f"Generando datos desde {start_date} para {days} días")
        try:
            # First parse the date to get it in the right format
            formatted_start_date = parse_date(start_date)
            
            # Convert it to a datetime object for date arithmetic
            start_date_obj = datetime.strptime(formatted_start_date, "%Y-%m-%d")
            
            # Generate random data
            dates = [start_date_obj + timedelta(days=i) for i in range(days)]
            demand = np.random.randint(50, 150, size=days)
            production_plan = np.random.randint(50, 150, size=days)
            forecast = np.random.randint(50, 150, size=days)

            # Calculate cumulative inventory
            conn = get_connection()
            cursor = conn.cursor()
            if IS_RAILWAY:
                cursor.execute("SELECT inventory FROM daily_data WHERE date < %s ORDER BY date DESC LIMIT 1", (formatted_start_date,))
            else:
                cursor.execute("SELECT inventory FROM daily_data WHERE date < ? ORDER BY date DESC LIMIT 1", (formatted_start_date,))
            row = cursor.fetchone()
            running_inventory = int(row[0]) if row else 0
            inventory = []
            for i in range(days):
                running_inventory += int(production_plan[i]) - int(demand[i])
                inventory.append(running_inventory)
            conn.close()
            
            # Format dates for database (always YYYY-MM-DD)
            formatted_dates = [date.strftime("%Y-%m-%d") for date in dates]
            print(f"Fechas generadas: {formatted_dates}")
            
            # Connect to database
            conn = get_connection()
            cursor = conn.cursor()
            
            # Insert data into database
            for i in range(days):
                # Check if data already exists for this date
                if IS_RAILWAY:
                    cursor.execute("SELECT COUNT(*) FROM daily_data WHERE date = %s", (formatted_dates[i],))
                else:
                    cursor.execute("SELECT COUNT(*) FROM daily_data WHERE date = ?", (formatted_dates[i],))
                
                count = cursor.fetchone()[0]
                
                if count > 0:
                    # Update existing record
                    if IS_RAILWAY:
                        cursor.execute(
                            "UPDATE daily_data SET demand = %s, production_plan = %s, forecast = %s, inventory = %s WHERE date = %s",
                            (int(demand[i]), int(production_plan[i]), int(forecast[i]), int(inventory[i]), formatted_dates[i])
                        )
                    else:
                        cursor.execute(
                            "UPDATE daily_data SET demand = ?, production_plan = ?, forecast = ?, inventory = ? WHERE date = ?",
                            (int(demand[i]), int(production_plan[i]), int(forecast[i]), int(inventory[i]), formatted_dates[i])
                        )
                else:
                    # Insert new record
                    if IS_RAILWAY:
                        cursor.execute(
                            "INSERT INTO daily_data (date, demand, production_plan, forecast, inventory) VALUES (%s, %s, %s, %s, %s)",
                            (formatted_dates[i], int(demand[i]), int(production_plan[i]), int(forecast[i]), int(inventory[i]))
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO daily_data (date, demand, production_plan, forecast, inventory) VALUES (?, ?, ?, ?, ?)",
                            (formatted_dates[i], int(demand[i]), int(production_plan[i]), int(forecast[i]), int(inventory[i]))
                        )
            
            conn.commit()
            conn.close()
            
            return f"Generados datos aleatorios para {days} días a partir de {start_date}."
        except ValueError as e:
            return f"Error with date format: {str(e)}"
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Error: {str(e)}")
        print(traceback_str)
        return f"Error generando datos: {str(e)}"

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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id SERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        # SQLite
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Verificar si la columna user_id existe en SQLite
        cursor.execute("PRAGMA table_info(conversation_history)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'user_id' not in column_names:
            cursor.execute("ALTER TABLE conversation_history ADD COLUMN user_id TEXT")
            print("Columna user_id añadida a la tabla conversation_history en SQLite")
    
    conn.commit()
    conn.close()

def get_user_sessions(user_id):
    """
    Obtiene todas las sesiones únicas de un usuario.
    
    Args:
        user_id (str): ID del usuario
        
    Returns:
        list: Lista de IDs de sesión
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        if IS_RAILWAY:
            try:
                # En PostgreSQL, usamos una subconsulta para poder ordenar por MIN(timestamp)
                cursor.execute("""
                    SELECT session_id 
                    FROM (
                        SELECT session_id, MIN(timestamp) as min_time 
                        FROM conversation_history 
                        WHERE user_id = %s 
                        GROUP BY session_id
                    ) AS subquery 
                    ORDER BY min_time DESC
                """, (user_id,))
            except Exception as e:
                if "column \"user_id\" does not exist" in str(e):
                    # Si la columna no existe, ejecutar la migración y retornar una lista vacía
                    print("La columna user_id no existe. Ejecutando migración...")
                    migrate_conversation_history_table()
                    return []
                else:
                    # Si es otro tipo de error, relanzarlo
                    raise e
        else:
            cursor.execute(
                "SELECT DISTINCT session_id FROM conversation_history WHERE user_id = ? GROUP BY session_id ORDER BY MIN(timestamp) DESC",
                (user_id,)
            )
        
        sessions = [row[0] for row in cursor.fetchall()]
        return sessions
    except Exception as e:
        print(f"Error al obtener sesiones del usuario: {str(e)}")
        traceback.print_exc()  # Imprimir el traceback completo para depuración
        return []
    finally:
        conn.close()

def get_or_create_user(username):
    """
    Obtiene un usuario por su nombre de usuario o lo crea si no existe.
    
    Args:
        username (str): Nombre de usuario
        
    Returns:
        dict: Datos del usuario
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Buscar usuario existente
    if IS_RAILWAY:
        cursor.execute("SELECT id, username, display_name FROM users WHERE username = %s", (username,))
    else:
        cursor.execute("SELECT id, username, display_name FROM users WHERE username = ?", (username,))
    
    user = cursor.fetchone()
    
    if user:
        user_dict = {
            "id": user[0],
            "username": user[1],
            "display_name": user[2] or user[1]
        }
    else:
        # Crear tabla de usuarios si no existe
        if IS_RAILWAY:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    display_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    display_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        # Crear nuevo usuario
        user_id = str(uuid.uuid4())
        if IS_RAILWAY:
            cursor.execute(
                "INSERT INTO users (id, username) VALUES (%s, %s)",
                (user_id, username)
            )
        else:
            cursor.execute(
                "INSERT INTO users (id, username) VALUES (?, ?)",
                (user_id, username)
            )
        
        user_dict = {
            "id": user_id,
            "username": username,
            "display_name": username
        }
    
    conn.commit()
    conn.close()
    
    return user_dict

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

def create_users_table():
    """
    Crea la tabla para almacenar usuarios si no existe.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if IS_RAILWAY:
        # PostgreSQL
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        # SQLite
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

def update_user_display_name(user_id, display_name):
    """
    Actualiza el nombre de visualización de un usuario.
    
    Args:
        user_id: ID del usuario
        display_name: Nuevo nombre de visualización
        
    Returns:
        Mensaje de éxito o error
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if IS_RAILWAY:
            cursor.execute("UPDATE users SET display_name = %s WHERE id = %s", (display_name, user_id))
        else:
            cursor.execute("UPDATE users SET display_name = ? WHERE id = ?", (display_name, user_id))
        
        conn.commit()
        conn.close()
        
        return f"Nombre de visualización actualizado a {display_name}"
    except Exception as e:
        conn.close()
        return f"Error al actualizar el nombre de visualización: {str(e)}"

def save_message_with_user(user_id, session_id, role, content):
    """
    Guarda un mensaje en el historial de conversaciones con ID de usuario.
    
    Args:
        user_id: ID del usuario
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
            "INSERT INTO conversation_history (session_id, role, content, user_id) VALUES (%s, %s, %s, %s) RETURNING id",
            (session_id, role, content, user_id)
        )
        message_id = cursor.fetchone()[0]
    else:
        # SQLite
        cursor.execute(
            "INSERT INTO conversation_history (session_id, role, content, user_id) VALUES (?, ?, ?, ?)",
            (session_id, role, content, user_id)
        )
        message_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return message_id

def get_user_conversation_history(user_id, session_id):
    """
    Obtiene el historial de conversación para un usuario y sesión específicos.
    
    Args:
        user_id: ID del usuario
        session_id: Identificador único de la sesión
        
    Returns:
        Lista de diccionarios con los mensajes de la conversación
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if IS_RAILWAY:
        cursor.execute(
            "SELECT role, content FROM conversation_history WHERE user_id = %s AND session_id = %s ORDER BY id ASC",
            (user_id, session_id)
        )
    else:
        cursor.execute(
            "SELECT role, content FROM conversation_history WHERE user_id = ? AND session_id = ? ORDER BY id ASC",
            (user_id, session_id)
        )
    
    messages = []
    for row in cursor.fetchall():
        messages.append({
            "role": row[0],
            "content": row[1]
        })
    
    conn.close()
    return messages

def migrate_conversation_history_table():
    """
    Verifica si la tabla conversation_history tiene la columna user_id y la añade si no existe.
    Esta función debe ejecutarse al inicio de la aplicación en Railway.
    """
    if not IS_RAILWAY:
        return  # Solo es necesario en Railway (PostgreSQL)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar si la columna user_id existe en PostgreSQL
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'conversation_history' 
            AND column_name = 'user_id'
        """)
        
        column_exists = cursor.fetchone()
        
        if not column_exists:
            print("Añadiendo columna user_id a la tabla conversation_history en PostgreSQL...")
            cursor.execute("ALTER TABLE conversation_history ADD COLUMN user_id TEXT")
            conn.commit()
            print("Columna user_id añadida correctamente a la tabla conversation_history")
        else:
            print("La columna user_id ya existe en la tabla conversation_history")
            
    except Exception as e:
        print(f"Error al verificar/añadir la columna user_id: {str(e)}")
    finally:
        conn.close()

def ensure_forecast_column():
    """Ensure the daily_data table has a forecast column."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if IS_RAILWAY:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'daily_data' AND column_name = 'forecast'
                """
            )
            exists = cursor.fetchone()
            if not exists:
                print("Añadiendo columna forecast a la tabla daily_data en PostgreSQL...")
                cursor.execute("ALTER TABLE daily_data ADD COLUMN forecast INTEGER DEFAULT 0")
                conn.commit()
        else:
            cursor.execute("PRAGMA table_info(daily_data)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'forecast' not in columns:
                print("Añadiendo columna forecast a la tabla daily_data en SQLite...")
                cursor.execute("ALTER TABLE daily_data ADD COLUMN forecast INTEGER DEFAULT 0")
                conn.commit()
    except Exception as e:
        print(f"Error al verificar/añadir la columna forecast: {str(e)}")
    finally:
        conn.close()


def convert_sqlite_date_format():
    """Convert existing `daily_data.date` values from `DD-MM-YYYY` to `YYYY-MM-DD`.

    This helper should be executed once after upgrading to the unified date
    format. It has no effect when running against PostgreSQL.
    """
    if IS_RAILWAY:
        print("Date conversion is not required for PostgreSQL.")
        return

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT date FROM daily_data")
        dates = [row[0] for row in cursor.fetchall()]

        for old_date in dates:
            try:
                # Skip if the date is already in ISO format
                datetime.strptime(old_date, "%Y-%m-%d")
                continue
            except ValueError:
                pass

            try:
                new_date = datetime.strptime(old_date, "%d-%m-%Y").strftime("%Y-%m-%d")
                cursor.execute(
                    "UPDATE daily_data SET date = ? WHERE date = ?",
                    (new_date, old_date),
                )
            except Exception as e:
                print(f"No se pudo convertir la fecha {old_date}: {e}")

        conn.commit()
        print("Conversión de fechas completada.")
    finally:
        conn.close()
