import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import asyncio
from datetime import datetime
import sys
import os
import re

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
agents_dir = os.path.join(current_dir, 'agents')
sys.path.insert(0, agents_dir)

# Import the modules using the correct path
import agentsscm
from agentsscm import triage_agent, Runner

# Create the chat components that will be imported into the dashboard
def create_chat_components():
    """Create and return the chat button, modal, and store components."""
    
    # Define styles for chat components
    user_message_style = {
        "backgroundColor": "#e9f5ff",
        "color": "#333333",
        "padding": "10px 15px",
        "borderRadius": "18px 18px 0 18px",
        "maxWidth": "80%",
        "boxShadow": "0 1px 2px rgba(0,0,0,0.1)",
        "marginBottom": "5px",
        "wordWrap": "break-word"
    }
    
    assistant_message_style = {
        "backgroundColor": "#007bff",
        "color": "white",
        "padding": "10px 15px",
        "borderRadius": "18px 18px 18px 0",
        "maxWidth": "80%",
        "boxShadow": "0 1px 2px rgba(0,0,0,0.1)",
        "marginBottom": "5px",
        "wordWrap": "break-word"
    }
    
    timestamp_style = {
        "fontSize": "0.7rem",
        "color": "#999",
        "marginTop": "3px"
    }
    
    # Chat button that will trigger the chat modal
    chat_button = html.Div([
        dbc.Button(
            html.I(className="fas fa-robot", style={"fontSize": "1.5rem"}),
            id="open-chat-button",
            color="primary",
            className="position-fixed",
            style={
                "bottom": "20px",
                "right": "20px",
                "zIndex": "1000",
                "borderRadius": "50%",
                "width": "60px",
                "height": "60px",
                "display": "flex",
                "justifyContent": "center",
                "alignItems": "center",
                "boxShadow": "0 4px 12px rgba(0,0,0,0.3)",
                "transition": "all 0.3s ease",
            },
        ),
    ])

    # Chat modal component - now with improved styling
    chat_modal = html.Div(
        [
            html.Div([
                # Header
                html.Div([
                    html.Div([
                        html.I(className="fas fa-robot me-2", style={"fontSize": "1.2rem"}),
                        html.H5("Supply Chain Assistant", className="m-0 fw-bold"),
                    ], className="d-flex align-items-center"),
                    html.Button(
                        "×",
                        id="close-chat",
                        className="btn-close btn-close-white",
                        style={"fontSize": "1.5rem"}
                    ),
                ], className="d-flex justify-content-between align-items-center p-3 bg-primary text-white rounded-top"),
                
                # Chat history display
                html.Div(id="chat-history", className="p-3", 
                        style={
                            "height": "350px", 
                            "overflowY": "auto",
                            "backgroundColor": "#f8f9fa",
                            "borderLeft": "1px solid #dee2e6",
                            "borderRight": "1px solid #dee2e6",
                        }),
                
                # Input area
                html.Div([
                    dbc.InputGroup([
                        dbc.Input(
                            id="user-input", 
                            placeholder="Escribe tu pregunta aquí...", 
                            type="text",
                            className="border-primary",
                            style={
                                "borderRadius": "20px 0 0 20px",
                                "padding": "10px 15px",
                                "fontSize": "0.95rem"
                            }
                        ),
                        dbc.Button(
                            html.I(className="fas fa-paper-plane"), 
                            id="send-button", 
                            color="primary", 
                            style={
                                "borderRadius": "0 20px 20px 0",
                                "padding": "10px 15px"
                            }
                        ),
                    ]),
                    
                    # Loading indicator
                    dcc.Loading(
                        id="loading",
                        type="circle",
                        color="#007bff",
                        children=html.Div(id="loading-output")
                    ),
                ], className="p-3 bg-white rounded-bottom border-bottom border-left border-right"),
            ], 
            className="rounded shadow",
            style={
                "position": "fixed",
                "bottom": "90px",
                "right": "20px",
                "width": "350px",
                "maxWidth": "90vw",
                "zIndex": "1000",
                "display": "none",  # Initially hidden
                "transition": "all 0.3s ease",
                "overflow": "hidden",
                "border": "1px solid #dee2e6",
            },
            id="chat-modal"
            ),
        ],
    )

    # Store component for chat history
    chat_store = dcc.Store(id="conversation-store", data={"messages": []})
    
    # Font Awesome for icons - updated to newer version
    font_awesome = html.Link(
        rel="stylesheet",
        href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
    )
    
    # Define global styles
    global USER_MESSAGE_STYLE, ASSISTANT_MESSAGE_STYLE, TIMESTAMP_STYLE
    USER_MESSAGE_STYLE = user_message_style
    ASSISTANT_MESSAGE_STYLE = assistant_message_style
    TIMESTAMP_STYLE = timestamp_style
    
    return chat_button, chat_modal, chat_store, font_awesome

def register_callbacks(app):
    """Register the chat-related callbacks with the provided Dash app."""
    
    @app.callback(
        Output("chat-modal", "style"),
        [Input("open-chat-button", "n_clicks"), 
         Input("close-chat", "n_clicks")],
        [State("chat-modal", "style")],
        prevent_initial_call=True
    )
    def toggle_chat_modal(open_clicks, close_clicks, current_style):
        """Toggle the visibility of the chat modal."""
        ctx = dash.callback_context
        if not ctx.triggered:
            return current_style
        
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if button_id == "open-chat-button":
            current_style.update({"display": "block"})
        else:
            current_style.update({"display": "none"})
        
        return current_style
    
    @app.callback(
        [Output("chat-history", "children"),
         Output("user-input", "value"),
         Output("conversation-store", "data"),
         Output("loading-output", "children")],
        [Input("send-button", "n_clicks"),
         Input("user-input", "n_submit")],
        [State("user-input", "value"),
         State("conversation-store", "data")],
        prevent_initial_call=True
    )
    def process_user_message(n_clicks, n_submit, user_input, conversation_data):
        """Process the user's message and update the chat history."""
        if not user_input or (not n_clicks and not n_submit):
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Get current time for timestamp
        timestamp = datetime.now().strftime("%H:%M")
        
        # Add user message to conversation history
        messages = conversation_data.get("messages", [])
        user_message = {
            "role": "user",
            "content": user_input,
            "time": timestamp
        }
        messages.append(user_message)
        
        # Update the UI with the user message
        chat_history = messages_to_components(messages)
        
        # Process the message with the agent
        try:
            # Create a placeholder for the agent's response
            assistant_message = {
                "role": "assistant",
                "content": "Procesando tu consulta...",
                "time": datetime.now().strftime("%H:%M")
            }
            messages.append(assistant_message)
            
            # Run the agent in a separate thread to not block the UI
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Pass the entire conversation history to the agent
            conversation_history = [{"role": msg["role"], "content": msg["content"]} for msg in messages[:-1]]  # Exclude the placeholder
            result = loop.run_until_complete(Runner.run(triage_agent, input=conversation_history))
            loop.close()
            
            # Update the placeholder with the actual response
            messages[-1]["content"] = result.final_output
            messages[-1]["time"] = datetime.now().strftime("%H:%M")
            
            # Update the UI with both messages
            chat_history = messages_to_components(messages)
            
            return chat_history, "", {"messages": messages}, ""
        except Exception as e:
            # Handle errors
            error_message = {
                "role": "assistant",
                "content": f"Lo siento, ha ocurrido un error: {str(e)}",
                "time": datetime.now().strftime("%H:%M")
            }
            messages.append(error_message)
            chat_history = messages_to_components(messages)
            
            return chat_history, "", {"messages": messages}, ""

def messages_to_components(messages):
    """Convert message objects to Dash components."""
    components = []
    
    for message in messages:
        if message["role"] == "user":
            component = html.Div([
                html.Div(message["content"], 
                         className="d-inline-block", 
                         style=USER_MESSAGE_STYLE),
                html.Div(message["time"], 
                         className="text-end", 
                         style=TIMESTAMP_STYLE)
            ], className="d-flex flex-column align-items-end mb-3")
        else:
            # Procesar el texto para convertir markdown a HTML
            content = process_markdown(message["content"])
            
            component = html.Div([
                html.Div([
                    html.I(className="fas fa-robot me-2 text-primary", style={"fontSize": "0.9rem"}),
                    html.Div(content, style={"display": "inline"})
                ], className="d-inline-block", 
                   style=ASSISTANT_MESSAGE_STYLE),
                html.Div(message["time"], style=TIMESTAMP_STYLE)
            ], className="d-flex flex-column align-items-start mb-3")
        
        components.append(component)
    
    return components

def process_markdown(text):
    """
    Procesa texto en formato markdown y lo convierte a componentes Dash HTML.
    Soporta: negrita, cursiva, listas y saltos de línea.
    """
    # Patrones para diferentes elementos de Markdown
    bold_pattern = r'\*\*(.*?)\*\*'
    italic_pattern = r'\*(.*?)\*'
    list_item_pattern = r'^\s*[-*]\s+(.*?)$'
    
    # Crear componentes para cada parte del texto
    components = []
    last_end = 0
    
    # Primero procesamos negrita
    for match in re.finditer(bold_pattern, text):
        # Añadir texto normal antes del formato
        if match.start() > last_end:
            components.append(text[last_end:match.start()])
        
        # Añadir texto en negrita
        bold_text = match.group(1)
        components.append(html.Strong(bold_text))
        
        last_end = match.end()
    
    # Añadir el resto del texto después del último formato
    if last_end < len(text):
        components.append(text[last_end:])
    
    # Ahora procesamos cursiva en los componentes de texto
    processed_components = []
    for component in components:
        if isinstance(component, str):
            # Procesar cursiva
            italic_components = []
            last_end = 0
            
            for match in re.finditer(italic_pattern, component):
                # Añadir texto normal antes del formato
                if match.start() > last_end:
                    italic_components.append(component[last_end:match.start()])
                
                # Añadir texto en cursiva
                italic_text = match.group(1)
                italic_components.append(html.Em(italic_text))
                
                last_end = match.end()
            
            # Añadir el resto del texto
            if last_end < len(component):
                italic_components.append(component[last_end:])
            
            processed_components.extend(italic_components)
        else:
            processed_components.append(component)
    
    # Procesar saltos de línea y listas
    final_components = []
    lines = []
    current_line = []
    
    for component in processed_components:
        if isinstance(component, str):
            # Dividir por saltos de línea
            parts = component.split('\n')
            for i, part in enumerate(parts):
                if i > 0:  # Si no es la primera parte, es un salto de línea
                    lines.append(current_line)
                    current_line = []
                if part:  # Si no está vacío
                    current_line.append(part)
        else:
            current_line.append(component)
    
    if current_line:
        lines.append(current_line)
    
    # Procesar cada línea para detectar elementos de lista
    in_list = False
    list_items = []
    
    for line in lines:
        # Convertir componentes de la línea a texto para verificar si es un elemento de lista
        line_text = ''.join([c if isinstance(c, str) else '' for c in line])
        list_match = re.match(list_item_pattern, line_text)
        
        if list_match:
            # Es un elemento de lista
            if not in_list:
                # Iniciar una nueva lista
                in_list = True
                list_items = []
            
            # Añadir el elemento a la lista actual
            list_content = []
            found_marker = False
            
            for component in line:
                if isinstance(component, str) and not found_marker:
                    # Buscar y eliminar el marcador de lista
                    marker_match = re.search(r'^\s*[-*]\s+', component)
                    if marker_match:
                        found_marker = True
                        rest = component[marker_match.end():]
                        if rest:
                            list_content.append(rest)
                    else:
                        list_content.append(component)
                else:
                    list_content.append(component)
            
            list_items.append(html.Li(list_content))
        else:
            # No es un elemento de lista
            if in_list:
                # Finalizar la lista anterior
                final_components.append(html.Ul(list_items, style={"marginLeft": "20px"}))
                in_list = False
            
            # Añadir la línea normal
            if line:
                final_components.append(html.Div(line))
                final_components.append(html.Br())
    
    # Finalizar la última lista si existe
    if in_list:
        final_components.append(html.Ul(list_items, style={"marginLeft": "20px"}))
    
    # Eliminar el último <br> si existe
    if final_components and isinstance(final_components[-1], html.Br):
        final_components.pop()
    
    return final_components
