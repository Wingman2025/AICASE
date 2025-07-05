import os
import sqlite3
import sys
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output, State
from flask_login import UserMixin, login_user, current_user, LoginManager, logout_user
import pandas as pd
import plotly.graph_objects as go
import forecast_utils

# Try to import Railway-specific packages, but continue if not available
try:
    import dj_database_url
    from dotenv import load_dotenv
    # Load environment variables from .env file if it exists
    load_dotenv()
    RAILWAY_DEPLOYMENT = True
except ImportError:
    dj_database_url = None
    load_dotenv = None
    RAILWAY_DEPLOYMENT = False

# Add the project root to the Python path
dashboard_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(dashboard_dir)
sys.path.append(project_root)

# Import the chatbot module
import chatbot
import db_utils
import uuid
import traceback

# Función para migrar la tabla de usuarios de ID entero a UUID
def migrate_users_table_if_needed():
    """Migrar la tabla de usuarios de ID entero a UUID si es necesario."""
    if not RAILWAY_DEPLOYMENT:
        return  # Solo ejecutar en Railway
    
    try:
        conn = db_utils.get_connection()
        cursor = conn.cursor()
        
        # Verificar si la tabla users existe y tiene la columna id como entero
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'id'
        """)
        
        column_info = cursor.fetchone()
        
        # Si la columna id existe y es de tipo integer o bigint, necesitamos migrar
        if column_info and column_info[1].lower() in ('integer', 'bigint'):
            print("Iniciando migración de la tabla de usuarios...")
            
            # Crear tabla temporal con la nueva estructura
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
            
            conn.commit()
            print("Migración completada con éxito.")
        
        conn.close()
    except Exception as e:
        print(f"Error durante la verificación/migración de la tabla de usuarios: {str(e)}")
        traceback.print_exc()

# Initialize the Dash app with Bootstrap
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Supply Chain Dashboard"
server = app.server  # Expose Flask server for Gunicorn

# Configurar Flask-Login
server.config['SECRET_KEY'] = 'supply-chain-dashboard-secret-key-2025'  # Clave secreta para las sesiones
login_manager = LoginManager()
login_manager.init_app(server)
login_manager.login_view = '/login'

# Definir la clase User
class User(UserMixin):
    def __init__(self, user_dict):
        self.id = user_dict["id"]
        self.display_name = user_dict["display_name"]

@login_manager.user_loader
def load_user(user_id):
    # Cargar usuario desde la base de datos
    conn = db_utils.get_connection()
    cursor = conn.cursor()
    
    if db_utils.IS_RAILWAY:
        cursor.execute("SELECT id, username, display_name FROM users WHERE id = %s", (user_id,))
    else:
        cursor.execute("SELECT id, username, display_name FROM users WHERE id = ?", (user_id,))
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        user_dict = {
            "id": user[0],
            "username": user[1],
            "display_name": user[2] or user[1]
        }
        return User(user_dict)
    
    return None

# Configure static file serving for production
if RAILWAY_DEPLOYMENT and 'RAILWAY_STATIC_URL' in os.environ:
    try:
        from whitenoise import WhiteNoise
        server.wsgi_app = WhiteNoise(server.wsgi_app)
        # Verificar si el directorio de assets existe antes de añadirlo
        assets_path = os.path.join(project_root, 'assets')
        if os.path.exists(assets_path):
            server.wsgi_app.add_files(assets_path, prefix='assets/')
        else:
            print(f"Directorio de assets no encontrado en: {assets_path}")
            # Crear el directorio de assets si no existe
            os.makedirs(assets_path, exist_ok=True)
            print(f"Directorio de assets creado en: {assets_path}")
    except ImportError as e:
        WhiteNoise = None
        print(f"Error al importar WhiteNoise: {str(e)}")
    except Exception as e:
        print(f"Error al configurar WhiteNoise: {str(e)}")

# Get chat components from the chatbot module
chat_button, chat_modal, chat_store, session_store, debug_store, font_awesome = chatbot.create_chat_components()

# Set global styles for message components in chatbot module
chatbot.USER_MESSAGE_STYLE = {'textAlign': 'left', 'margin': '5px'}
chatbot.ASSISTANT_MESSAGE_STYLE = {'textAlign': 'right', 'margin': '5px'}
chatbot.TIMESTAMP_STYLE = {'textAlign': 'center', 'margin': '5px'}

# Login form
login_form = dbc.Card(
    [
        html.H4("Iniciar Sesión", className="card-title text-center mb-4"),
        dbc.Input(id="login-username", placeholder="Nombre de usuario o email", type="text", className="mb-3"),
        dbc.Button("Iniciar Sesión", id="login-button", color="primary", className="w-100"),
        html.Div(id="login-feedback", className="mt-3 text-danger")
    ],
    body=True,
    className="shadow-sm"
)

# Componente para seleccionar sesiones anteriores
def create_session_selector(user_id):
    # Obtener todas las sesiones del usuario
    sessions = db_utils.get_user_sessions(user_id)
    
    if not sessions:
        return html.Div("No hay sesiones anteriores", className="text-muted text-center my-2")
    
    # Crear opciones para el dropdown
    options = [{"label": f"Sesión del {get_session_date(session_id)}", "value": session_id} for session_id in sessions]
    
    # Añadir opción para nueva sesión
    options.insert(0, {"label": "Nueva conversación", "value": "new"})
    
    return html.Div([
        html.H6("Seleccionar conversación:", className="mb-2"),
        dcc.Dropdown(
            id="session-selector",
            options=options,
            value="new",
            clearable=False,
            className="mb-3"
        )
    ])

def get_session_date(session_id):
    """Obtener la fecha de la primera interacción en una sesión"""
    conn = db_utils.get_connection()
    cursor = conn.cursor()
    
    if db_utils.IS_RAILWAY:
        cursor.execute(
            "SELECT timestamp FROM conversation_history WHERE session_id = %s ORDER BY id ASC LIMIT 1",
            (session_id,)
        )
    else:
        cursor.execute(
            "SELECT timestamp FROM conversation_history WHERE session_id = ? ORDER BY id ASC LIMIT 1",
            (session_id,)
        )
    
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        # Convertir el timestamp a formato legible
        try:
            timestamp_str = str(result[0])
            
            # Intentar diferentes formatos de fecha
            for date_format in [
                "%Y-%m-%d %H:%M:%S.%f",  # Formato SQLite con microsegundos
                "%Y-%m-%d %H:%M:%S",     # Formato SQLite sin microsegundos
                "%Y-%m-%dT%H:%M:%S.%f",  # Formato ISO con microsegundos
                "%Y-%m-%dT%H:%M:%S",     # Formato ISO sin microsegundos
                "%d-%m-%Y %H:%M:%S"      # Formato DD-MM-YYYY
            ]:
                try:
                    timestamp = datetime.strptime(timestamp_str, date_format)
                    return timestamp.strftime("%d/%m/%Y %H:%M")
                except ValueError:
                    continue
            
            # Si ninguno de los formatos anteriores funciona, intentar extraer la fecha del UUID de la sesión
            # Los UUIDs tienen un componente de tiempo que podemos usar como fallback
            if len(session_id) == 36:  # Longitud estándar de UUID
                try:
                    # Extraer los primeros 8 caracteres que representan el timestamp
                    timestamp = datetime.now()
                    return timestamp.strftime("%d/%m/%Y %H:%M")
                except:
                    pass
            
            return "fecha desconocida"
        except Exception as e:
            print(f"Error al procesar fecha de sesión: {str(e)}")
            return f"sesión {session_id[:8]}"
    
    return "nueva sesión"

# Navbar with login/logout and session selector
def get_navbar():
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        user_menu = dbc.DropdownMenu(
            label=f"Hola, {current_user.display_name}",
            children=[
                dbc.DropdownMenuItem("Cerrar Sesión", id="logout-button"),
            ],
            nav=True,
            in_navbar=True,
        )
    else:
        user_menu = dbc.NavItem(dbc.NavLink("Iniciar Sesión", href="/login"))
    
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand("Supply Chain Dashboard", href="/"),
                dbc.NavbarToggler(id="navbar-toggler"),
                dbc.Collapse(
                    dbc.Nav(
                        [
                            dbc.NavItem(dbc.NavLink("Dashboard", href="/")),
                            user_menu,
                        ],
                        className="ms-auto",
                        navbar=True
                    ),
                    id="navbar-collapse",
                    navbar=True,
                ),
            ]
        ),
        color="primary",
        dark=True,
        className="mb-4",
    )

# Define the layout with a navigation bar, styled table, footer, and chat components
app.layout = html.Div([
    # URL Location component - needed for navigation
    dcc.Location(id='url', refresh=True),
    
    # Navigation bar
    get_navbar(),
    
    # Login form
    html.Div(id="login-form", children=[login_form], style={'display': 'block'}),
    
    # Session selector
    html.Div(id="session-selector-container", style={'display': 'none'}),
    
    # Tabs for navigation
    dcc.Tabs(id='tabs-example', value='tab-1', children=[
        dcc.Tab(label='Daily Data', value='tab-1', style={'padding': '10px'}),
        dcc.Tab(label='Inventory Analysis', value='tab-2', style={'padding': '10px'}),
        dcc.Tab(label='Demand Forecast', value='tab-3', style={'padding': '10px'}),
    ], style={'margin': '10px', 'display': 'none'}),
    
    # Refresh button and notification
    html.Div([
        dbc.Button("Actualizar Datos", id="refresh-button", color="primary", className="mr-1"),
        html.Div(id="refresh-notification", style={'color': 'green', 'marginTop': '5px'})
    ], style={'textAlign': 'center'}),

    # Content area
    html.Div(id='tabs-content-example', style={'padding': '20px'}),

    # Footer
    html.Div([
        html.Hr(style={'border': '1px solid #007bff'}),
        html.P(" 2025 Supply Chain Analytics | All Rights Reserved", style={'textAlign': 'center', 'color': '#888'}),
    ], style={'padding': '10px', 'backgroundColor': '#f9f9f9'}),
    
    # Chat components
    chat_button,
    chat_modal,
    chat_store,
    session_store,
    debug_store,
    font_awesome,
    
    # Hidden store to store user data
    dcc.Store(id="user-store", data={}),
    
    # Hidden div to store session data (ya incluido en chat_components)
    # html.Div(id="session-store", style={"display": "none"}),
    
    # Hidden div to store session data
    # html.Div(id="session-store", style={"display": "none"}),
])

# Database connection function
def get_db_connection():
    # Check if we have Railway deployment and DATABASE_URL environment variable
    if RAILWAY_DEPLOYMENT and os.getenv('DATABASE_URL'):
        try:
            # Parse the DATABASE_URL and return a PostgreSQL connection
            db_config = dj_database_url.parse(os.getenv('DATABASE_URL'))
            import psycopg2
            return psycopg2.connect(
                host=db_config['HOST'],
                database=db_config['NAME'],
                user=db_config['USER'],
                password=db_config['PASSWORD'],
                port=db_config['PORT']
            )
        except (ImportError, Exception):
            # Fall back to SQLite if there's any issue with PostgreSQL
            pass
    
    # Default SQLite connection for local development
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to the project root, then to the data directory
    data_dir = os.path.join(os.path.dirname(script_dir), 'data')
    # Path to the database file
    db_path = os.path.join(data_dir, 'supply_chain.db')
    return sqlite3.connect(db_path)

# Callback to update content based on selected tab
@app.callback(Output('tabs-content-example', 'children'),
              [Input('tabs-example', 'value'), Input('refresh-button', 'n_clicks')])
def render_content(tab, n_clicks):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if tab == 'tab-1':
            # Modified SQL query to specify column order including forecast
            cursor.execute(
                "SELECT date, demand, production_plan, forecast, inventory "
                "FROM daily_data ORDER BY date"
            )
            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]


            # Fetch summary metrics
            prod_summary = db_utils.get_production_summary()
            demand_summary = db_utils.get_demand_summary()
            inv_summary = db_utils.get_inventory_summary()
            projected_inventory = db_utils.get_latest_inventory()

            metrics = dbc.Row([
                dbc.Col(
                    dbc.Card([
                        dbc.CardHeader("Total Production"),
                        dbc.CardBody(html.Div(prod_summary.get("total_production", 0), className="metric-number"))
                    ], body=True, className="text-center"),
                    md=4
                ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardHeader("Total Demand"),
                        dbc.CardBody(html.Div(demand_summary.get("total_demand", 0), className="metric-number"))
                    ], body=True, className="text-center"),
                    md=4
                ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardHeader("Projected Inventory"),
                        dbc.CardBody(html.Div(projected_inventory, className="metric-number"))
                    ], body=True, className="text-center"),
                    md=4
                )
            ], className="mb-4")

            return html.Div([
                metrics,
                html.H3('Daily Data', style={'textAlign': 'center', 'color': '#4CAF50'}),
                html.Table([
                    html.Thead(html.Tr([html.Th(col, style={'padding': '10px', 'border': '1px solid #ddd', 'backgroundColor': '#f2f2f2'}) for col in columns])),
                    html.Tbody([
                        html.Tr([
                            html.Td(cell, style={'padding': '10px', 'border': '1px solid #ddd', 'textAlign': 'center', 'color': 'blue' if col == 'production_plan' else 'black'})
                            for col, cell in zip(columns, row)
                        ]) for row in data
                    ])
                ], style={'width': '100%', 'borderCollapse': 'collapse', 'margin': '20px auto'}),
            ])
        elif tab == 'tab-3':
            df = pd.DataFrame(db_utils.get_daily_data())
            if df.empty:
                return html.Div("No data available")
            demand_series = df['demand']
            forecast = forecast_utils.exponential_smoothing_forecast(periods=5)

            last_date = pd.to_datetime(df['date'].iloc[-1], format='%Y-%m-%d')
            future_dates = [
                (last_date + pd.Timedelta(days=i)).strftime('%Y-%m-%d')
                for i in range(1, len(forecast) + 1)
            ]

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['date'], y=demand_series, mode='lines+markers', name='Historical Demand'))
            fig.add_trace(go.Scatter(x=future_dates, y=forecast, mode='lines+markers', name='Forecast'))

            return html.Div([
                dcc.Graph(figure=fig),
                html.H5('Forecast Values'),
                html.Ul([html.Li(f"{d}: {v}") for d, v in zip(future_dates, forecast)])
            ])
        else:
            return html.Div("Tab not implemented")
    finally:
        conn.close()

# Callback for refresh notification
@app.callback(
    Output('refresh-notification', 'children'),
    [Input('refresh-button', 'n_clicks')],
    prevent_initial_call=True
)
def show_refresh_notification(n_clicks):
    if n_clicks:
        current_time = datetime.now().strftime("%H:%M:%S")
        return f"Datos actualizados a las {current_time}"
    return ""

# Callback para manejar el inicio de sesión
@app.callback(
    [Output('login-feedback', 'children'),
     Output('user-store', 'data'),
     Output('url', 'pathname')],
    [Input('login-button', 'n_clicks')],
    [State('login-username', 'value')]
)
def handle_login(n_clicks, username):
    if n_clicks is None or not username:
        return "", None, dash.no_update
    
    # Obtener o crear usuario
    try:
        user_dict = db_utils.get_or_create_user(username)
        user = User(user_dict)
        login_user(user)
        
        return "", user_dict, "/"
    except Exception as e:
        print(f"Error al iniciar sesión: {str(e)}")
        return f"Error al iniciar sesión: {str(e)}", None, dash.no_update

# Callback para seleccionar una sesión
@app.callback(
    Output('session-store', 'data'),
    [Input('session-selector', 'value')],
    [State('user-store', 'data')]
)
def handle_session_selection(session_id, user_data):
    if not session_id or not user_data:
        return dash.no_update
    
    if session_id == "new":
        # Crear una nueva sesión
        return {"session_id": str(uuid.uuid4())}
    else:
        # Usar la sesión seleccionada
        return {"session_id": session_id}

# Callback para mostrar el selector de sesiones
@app.callback(
    Output('session-selector-container', 'children'),
    [Input('user-store', 'data')]
)
def show_session_selector(user_data):
    if not user_data:
        return dash.no_update
    
    return create_session_selector(user_data["id"])

# Callback para manejar el cierre de sesión
@app.callback(
    [Output('user-store', 'data', allow_duplicate=True),
     Output('url', 'pathname', allow_duplicate=True)],
    [Input('logout-button', 'n_clicks')],
    prevent_initial_call=True
)
def handle_logout(n_clicks):
    if n_clicks:
        logout_user()
        return None, "/login"
    return dash.no_update, dash.no_update

# Callback para mostrar/ocultar componentes según el estado de autenticación
@app.callback(
    [Output('login-form', 'style'),
     Output('session-selector-container', 'style'),
     Output('tabs-example', 'style')],
    [Input('url', 'pathname'),
     Input('user-store', 'data')]
)
def update_ui_based_on_auth(pathname, user_data):
    # Si el usuario está autenticado
    if user_data:
        return {'display': 'none'}, {'display': 'block'}, {'display': 'block', 'margin': '10px'}
    # Si el usuario no está autenticado
    else:
        return {'display': 'block'}, {'display': 'none'}, {'display': 'none'}

# Register the chatbot callbacks
chatbot.register_callbacks(app)

# Ejecutar la migración de usuarios automáticamente al iniciar la aplicación en Railway
migrate_users_table_if_needed()
# Ejecutar la migración de la tabla conversation_history para añadir la columna user_id si no existe
db_utils.migrate_conversation_history_table()
db_utils.ensure_forecast_column()

if __name__ == '__main__':
    # Use standard configuration for local development
    app.run(debug=True)
