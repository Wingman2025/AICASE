"""
Script para migrar la tabla de usuarios de ID entero a UUID.

Este script:
1. Crea una tabla temporal con la nueva estructura (id como TEXT)
2. Copia los datos de la tabla original a la temporal, convirtiendo los IDs a UUIDs
3. Elimina la tabla original
4. Renombra la tabla temporal a 'users'
"""

import os
import sys
import uuid
import psycopg2
import sqlite3
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Determinar si estamos en Railway
IS_RAILWAY = 'DATABASE_URL' in os.environ

def get_connection():
    """Obtener conexión a la base de datos según el entorno."""
    if IS_RAILWAY:
        # Conexión a PostgreSQL en Railway
        try:
            import dj_database_url
            db_config = dj_database_url.parse(os.environ['DATABASE_URL'])
            return psycopg2.connect(
                host=db_config['HOST'],
                database=db_config['NAME'],
                user=db_config['USER'],
                password=db_config['PASSWORD'],
                port=db_config['PORT']
            )
        except Exception as e:
            print(f"Error al conectar a PostgreSQL: {str(e)}")
            sys.exit(1)
    else:
        # Conexión a SQLite local
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(script_dir, 'data', 'supply_chain.db')
        return sqlite3.connect(db_path)

def migrate_users_table():
    """Migrar la tabla de usuarios de ID entero a UUID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar si la tabla users existe
        if IS_RAILWAY:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'users'
                )
            """)
        else:
            cursor.execute("""
                SELECT count(name) FROM sqlite_master 
                WHERE type='table' AND name='users'
            """)
        
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("La tabla 'users' no existe. No es necesaria la migración.")
            return
        
        # Crear tabla temporal con la nueva estructura
        if IS_RAILWAY:
            cursor.execute("""
                CREATE TABLE users_temp (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    display_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Obtener usuarios existentes
            cursor.execute("SELECT id, username, display_name, created_at FROM users")
            users = cursor.fetchall()
            
            # Insertar usuarios en la tabla temporal con UUIDs
            for user in users:
                old_id, username, display_name, created_at = user
                new_id = str(uuid.uuid4())
                
                # Actualizar referencias en conversation_history
                cursor.execute(
                    "UPDATE conversation_history SET user_id = %s WHERE user_id = %s",
                    (new_id, str(old_id))
                )
                
                # Insertar en la tabla temporal
                cursor.execute(
                    "INSERT INTO users_temp (id, username, display_name, created_at) VALUES (%s, %s, %s, %s)",
                    (new_id, username, display_name or username, created_at or 'now()')
                )
            
            # Eliminar tabla original y renombrar la temporal
            cursor.execute("DROP TABLE users")
            cursor.execute("ALTER TABLE users_temp RENAME TO users")
            
        else:
            # SQLite tiene limitaciones para renombrar columnas, así que recreamos la tabla
            cursor.execute("""
                CREATE TABLE users_temp (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    display_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Obtener usuarios existentes
            cursor.execute("SELECT id, username, display_name, created_at FROM users")
            users = cursor.fetchall()
            
            # Insertar usuarios en la tabla temporal con UUIDs
            for user in users:
                old_id, username, display_name, created_at = user
                new_id = str(uuid.uuid4())
                
                # Actualizar referencias en conversation_history
                cursor.execute(
                    "UPDATE conversation_history SET user_id = ? WHERE user_id = ?",
                    (new_id, str(old_id))
                )
                
                # Insertar en la tabla temporal
                cursor.execute(
                    "INSERT INTO users_temp (id, username, display_name, created_at) VALUES (?, ?, ?, ?)",
                    (new_id, username, display_name or username, created_at or 'CURRENT_TIMESTAMP')
                )
            
            # Eliminar tabla original y renombrar la temporal
            cursor.execute("DROP TABLE users")
            cursor.execute("ALTER TABLE users_temp RENAME TO users")
        
        conn.commit()
        print("Migración completada con éxito.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error durante la migración: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Iniciando migración de la tabla de usuarios...")
    migrate_users_table()
    print("Proceso de migración finalizado.")
