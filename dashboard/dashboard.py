import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import sqlite3
import sys
import os
from datetime import datetime
import uuid
from flask_login import UserMixin, login_user, current_user

# Try to import Railway-specific packages, but continue if not available
try:
    import dj_database_url
    from dotenv import load_dotenv
    # Load environment variables from .env file if it exists
    load_dotenv()
    RAILWAY_DEPLOYMENT = True
except ImportError:
    RAILWAY_DEPLOYMENT = False

# Add the project root to the Python path
dashboard_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(dashboard_dir)
sys.path.append(project_root)

# Import the chatbot module
import chatbot

# Initialize the Dash app with Bootstrap
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Supply Chain Dashboard"
server = app.server  # Expose Flask server for Gunicorn

# Configure static file serving for production
if RAILWAY_DEPLOYMENT and 'RAILWAY_STATIC_URL' in os.environ:
    try:
        from whitenoise import WhiteNoise
        server.wsgi_app = WhiteNoise(server.wsgi_app)
        server.wsgi_app.add_files(os.path.join(project_root, 'assets'), prefix='assets/')
    except ImportError:
        pass  # Continue without whitenoise if not installed

# Get chat components from the chatbot module
chat_button, chat_modal, chat_store, font_awesome = chatbot.create_chat_components()

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
    
    if result:
        # Convertir el timestamp a formato legible
        try:
            timestamp = datetime.strptime(str(result[0]), "%Y-%m-%d %H:%M:%S.%f")
            return timestamp.strftime("%d/%m/%Y %H:%M")
        except:
            return "fecha desconocida"
    
    return "fecha desconocida"

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
    # Navigation bar
    get_navbar(),
    
    # Login form
    login_form,
    
    # Session selector
    html.Div(id="session-selector-container"),
    
    # Tabs for navigation
    dcc.Tabs(id='tabs-example', value='tab-1', children=[
        dcc.Tab(label='Daily Data', value='tab-1', style={'padding': '10px'}),
    ], style={'fontSize': '18px', 'fontWeight': 'bold'}),

    # Refresh button
    html.Div([
        dbc.Button(
            [html.I(className="fas fa-sync-alt me-2"), "Actualizar Datos"],
            id="refresh-button",
            color="success",
            className="mb-3",
            style={'marginTop': '10px'}
        ),
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
    font_awesome,
    
    # Hidden div to store user data
    html.Div(id="user-store", style={"display": "none"}),
    
    # Hidden div to store session data
    html.Div(id="session-store", style={"display": "none"}),
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
            # Modified SQL query to specify column order with inventory at the end
            cursor.execute("SELECT date, demand, production_plan, inventory FROM daily_data")
            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return html.Div([
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

# Register the chatbot callbacks
chatbot.register_callbacks(app)

class User(UserMixin):
    def __init__(self, user_dict):
        self.id = user_dict["id"]
        self.display_name = user_dict["display_name"]

if __name__ == '__main__':
    # Use standard configuration for local development
    app.run(debug=True)
