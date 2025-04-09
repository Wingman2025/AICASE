import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import sqlite3
import sys
import os
from datetime import datetime

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

# Define the layout with a navigation bar, styled table, footer, and chat components
app.layout = html.Div([
    # Navigation bar
    html.Div([
        html.H1("Supply Chain Dashboard", style={'textAlign': 'center', 'color': '#007bff'}),
        html.Hr(style={'border': '1px solid #007bff'}),
    ], style={'padding': '10px', 'backgroundColor': '#f9f9f9'}),

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
    font_awesome
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

# Register the chatbot callbacks
chatbot.register_callbacks(app)

if __name__ == '__main__':
    # Use standard configuration for local development
    app.run(debug=True)
