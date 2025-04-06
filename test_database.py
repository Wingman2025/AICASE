import os
import sys
import sqlite3
from datetime import datetime, timedelta

# Asegurarse de que podemos importar db_utils
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import db_utils

def print_separator():
    print("\n" + "="*50 + "\n")

# 1. Verificar la ruta de la base de datos
db_path = db_utils.get_db_path()
print(f"Ruta de la base de datos: {db_path}")
print(f"¿Existe el archivo? {'Sí' if os.path.exists(db_path) else 'No'}")

print_separator()

# 2. Verificar si la tabla daily_data existe
try:
    conn = db_utils.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_data'")
    table_exists = cursor.fetchone() is not None
    print(f"¿Existe la tabla 'daily_data'? {'Sí' if table_exists else 'No'}")
    
    if table_exists:
        # 3. Contar cuántos registros hay
        cursor.execute("SELECT COUNT(*) FROM daily_data")
        count = cursor.fetchone()[0]
        print(f"Número total de registros: {count}")
        
        # 4. Mostrar las fechas disponibles
        cursor.execute("SELECT date FROM daily_data ORDER BY date")
        dates = [row[0] for row in cursor.fetchall()]
        print(f"Fechas disponibles: {dates}")
        
        # 5. Mostrar algunos ejemplos de datos
        print("\nEjemplos de datos:")
        cursor.execute("SELECT * FROM daily_data LIMIT 3")
        columns = [desc[0] for desc in cursor.description]
        print(f"Columnas: {columns}")
        
        rows = cursor.fetchall()
        for i, row in enumerate(rows):
            print(f"Registro {i+1}: {dict(zip(columns, row))}")
    
    conn.close()
except Exception as e:
    print(f"Error al verificar la base de datos: {str(e)}")

print_separator()

# 6. Probar la función get_daily_data
print("Probando la función get_daily_data:")

# 6.1 Sin fecha (todos los registros)
all_data = db_utils.get_daily_data()
print(f"Número de registros recuperados (sin filtro de fecha): {len(all_data)}")
if all_data:
    print(f"Primer registro: {all_data[0]}")

# 6.2 Con fecha específica
today = datetime.now()
today_str = today.strftime('%d-%m-%Y')
yesterday_str = (today - timedelta(days=1)).strftime('%d-%m-%Y')
tomorrow_str = (today + timedelta(days=1)).strftime('%d-%m-%Y')

print(f"\nBuscando datos para hoy ({today_str}):")
today_data = db_utils.get_daily_data(today_str)
print(f"Registros encontrados: {len(today_data)}")
for item in today_data:
    print(item)

print(f"\nBuscando datos para ayer ({yesterday_str}):")
yesterday_data = db_utils.get_daily_data(yesterday_str)
print(f"Registros encontrados: {len(yesterday_data)}")

print(f"\nBuscando datos para mañana ({tomorrow_str}):")
tomorrow_data = db_utils.get_daily_data(tomorrow_str)
print(f"Registros encontrados: {len(tomorrow_data)}")

print_separator()

# 7. Verificar las fechas generadas por generate_data.py
print("Fechas que deberían estar en la base de datos según generate_data.py:")
start_date = datetime(2025, 4, 3)  # Fecha inicial en generate_data.py
for i in range(15):  # 15 días de datos
    date_str = (start_date + timedelta(days=i)).strftime('%d-%m-%Y')
    data = db_utils.get_daily_data(date_str)
    print(f"  {date_str}: {'✓' if data else '✗'} ({len(data)} registros)")

if __name__ == "__main__":
    print("Script de prueba completado.")
