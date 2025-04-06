import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import sqlite3
import sys
import os

# Add the project root to the Python path
dashboard_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(dashboard_dir)
sys.path.append(project_root)

# Import the chatbot module
import chatbot

# Initialize the Dash app with Bootstrap
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Supply Chain Dashboard"

# Get chat components from the chatbot module
chat_button, chat_modal, chat_store, font_awesome = chatbot.create_chat_components()

# Define the layout with a navigation bar, styled table, footer, and chat components
app.layout = html.Div([
    # Navigation bar
    html.Div([
        html.H1("Supply Chain Dashboard", style={'textAlign': 'center', 'color': '#4CAF50'}),
        html.Hr(style={'border': '1px solid #4CAF50'}),
    ], style={'padding': '10px', 'backgroundColor': '#f9f9f9'}),

    # Tabs for navigation
    dcc.Tabs(id='tabs-example', value='tab-1', children=[
        dcc.Tab(label='Daily Data', value='tab-1', style={'padding': '10px'}),
    ], style={'fontSize': '18px', 'fontWeight': 'bold'}),

    # Content area
    html.Div(id='tabs-content-example', style={'padding': '20px'}),

    # Footer
    html.Div([
        html.Hr(style={'border': '1px solid #4CAF50'}),
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
    import os
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to the project root, then to the data directory
    data_dir = os.path.join(os.path.dirname(script_dir), 'data')
    # Path to the database file
    db_path = os.path.join(data_dir, 'supply_chain.db')
    return sqlite3.connect(db_path)

# Callback to update content based on selected tab
@app.callback(Output('tabs-content-example', 'children'),
              [Input('tabs-example', 'value')])
def render_content(tab):
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

# Register the chatbot callbacks
chatbot.register_callbacks(app)

if __name__ == '__main__':
    app.run(debug=True)
