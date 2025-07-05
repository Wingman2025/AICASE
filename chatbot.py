import asyncio
import os
import re
import sys
import uuid
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State
from flask_login import current_user

# Add the project root to the Python path
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)  # Add the current directory to the path

# Add the agents directory to the Python path
agents_dir = os.path.join(current_dir, 'agents')
sys.path.append(agents_dir)

# Import the modules using the correct path

import agentsscm
from agentsscm import triage_agent, orchestrate_forecast_to_plan
from agents import Runner
import db_utils

# Estilos globales que pueden ser modificados desde el dashboard
USER_MESSAGE_STYLE = {}
ASSISTANT_MESSAGE_STYLE = {}
TIMESTAMP_STYLE = {}

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
    
    # Set global styles
    global USER_MESSAGE_STYLE, ASSISTANT_MESSAGE_STYLE, TIMESTAMP_STYLE
    USER_MESSAGE_STYLE = user_message_style
    ASSISTANT_MESSAGE_STYLE = assistant_message_style
    TIMESTAMP_STYLE = timestamp_style
    
    # Create a floating button that opens the chat modal
    chat_button = html.Div(
        dbc.Button(
            html.I(className="fas fa-robot", style={"fontSize": "1.5rem"}),
            id="open-chat-button",
            color="primary",
            className="rounded-circle p-3",
            style={
                "position": "fixed",
                "bottom": "20px",
                "right": "20px",
                "width": "50px",
                "height": "50px",
                "zIndex": "1000",
                "boxShadow": "0 4px 8px rgba(0,0,0,0.2)",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "transition": "all 0.3s ease"
            }
        )
    )
    
    # Create the chat modal
    chat_modal = html.Div(
        dbc.Card(
            [
                dbc.CardHeader(
                    [
                        html.Div(
                            [
                                html.H4("Asistente de Supply Chain", className="mb-0"),
                                html.Div([
                                    dbc.Button(
                                        "Limpiar",
                                        id="clear-chat",
                                        color="link",
                                        className="me-2",
                                        style={"fontSize": "0.9rem"}
                                    ),
                                    dbc.Button(
                                        "×",
                                        id="close-chat",
                                        className="ms-2 btn-close",
                                        style={"fontSize": "1.5rem"}
                                    ),
                                ], className="d-flex align-items-center"),
                            ],
                            className="d-flex justify-content-between align-items-center"
                        ),
                    ],
                    className="bg-primary text-white"
                ),
                dbc.CardBody(
                    [
                        # Chat history container with scrolling
                        html.Div(
                            id="chat-history",
                            style={
                "height": "250px",
                                "overflowY": "auto",
                                "display": "flex",
                                "flexDirection": "column",
                                "padding": "10px"
                            }
                        ),
                        
                        # Loading indicator
                        html.Div(id="loading-output"),
                        
                        # Input area
                        dbc.InputGroup(
                            [
                                dbc.Input(
                                    id="user-input",
                                    placeholder="Escribe tu mensaje aquí...",
                                    type="text",
                                    className="border-primary",
                                    style={"borderRadius": "20px 0 0 20px"}
                                ),
                                dbc.Button(
                                    html.I(className="fas fa-paper-plane"),
                                    id="send-button",
                                    color="primary",
                                    style={"borderRadius": "0 20px 20px 0"}
                                ),
                            ],
                            className="mt-3"
                        ),
                    ]
                ),
            ],
            style={
                "position": "fixed",
                "bottom": "80px",
                "right": "30px",
                "width": "350px",
                "maxWidth": "90vw",
                "zIndex": "1001",
                "boxShadow": "0 4px 20px rgba(0,0,0,0.15)",
                "borderRadius": "15px",
                "backgroundColor": "rgba(255, 255, 255, 0.75)",
                "backdropFilter": "blur(4px)",
                "display": "none",  # Initially hidden
                "transition": "all 0.3s ease"
            },
            id="chat-modal"
        )
    )
    
    # Create a store for the conversation history
    chat_store = dcc.Store(
        id="conversation-store",
        data={"messages": []}
    )
    
    # Create a store for the session
    session_store = dcc.Store(
        id="session-store",
        data={"session_id": str(uuid.uuid4())}
    )
    
    # Include Font Awesome for icons
    font_awesome = html.Link(
        rel="stylesheet",
        href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css"
    )
    
    return chat_button, chat_modal, chat_store, session_store, font_awesome

def register_callbacks(app):
    """Register the chat-related callbacks with the provided Dash app."""
    
    # Asegurar que la tabla de historial de conversaciones existe
    db_utils.create_conversation_history_table()
    db_utils.create_users_table()
    
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
         Input("user-input", "n_submit"),
         Input("chat-modal", "style"),  # Añadido para cargar el historial cuando se abre el chat
         Input("session-store", "data")],  # Añadido para cargar el historial de la sesión seleccionada
        [State("user-input", "value"),
         State("conversation-store", "data")],
        prevent_initial_call=True
    )
    def process_user_message(n_clicks, n_submit, modal_style, session_store, user_input, conversation_data):
        """Process the user's message and update the chat history."""
        ctx = dash.callback_context
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # Verificar si el usuario está autenticado
        user_authenticated = hasattr(current_user, 'is_authenticated') and current_user.is_authenticated
        
        # Si se está abriendo el modal o se ha seleccionado una sesión, cargar el historial de la base de datos
        if trigger in ["chat-modal", "session-store"] and (modal_style.get("display") == "block" or trigger == "session-store"):
            # Si el usuario está autenticado, usar su ID
            if user_authenticated:
                user_id = current_user.id
                
                # Obtener el ID de sesión del store de sesión o crear uno nuevo
                session_id = session_store.get("session_id") if session_store else str(uuid.uuid4())
                
                # Cargar mensajes de la base de datos para este usuario y sesión
                db_messages = db_utils.get_user_conversation_history(user_id, session_id)
                
                # Añadir timestamps si no existen
                messages = []
                for msg in db_messages:
                    if "time" not in msg:
                        msg["time"] = datetime.now().strftime("%H:%M")
                    messages.append(msg)
                
                # Actualizar el store con los mensajes, el ID de sesión y el ID de usuario
                conversation_data = {
                    "messages": messages,
                    "session_id": session_id,
                    "user_id": user_id
                }
            else:
                # Si no está autenticado, usar un ID de sesión temporal
                session_id = conversation_data.get("session_id", str(uuid.uuid4()))
                messages = conversation_data.get("messages", [])
                
                # Actualizar el store con el ID de sesión
                conversation_data = {
                    "messages": messages,
                    "session_id": session_id
                }
            
            # Actualizar la UI
            chat_history = messages_to_components(messages)
            return chat_history, "", conversation_data, ""
        
        if not user_input or (not n_clicks and not n_submit) or trigger in ["chat-modal", "session-store"]:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Obtener información de la sesión y usuario
        session_id = conversation_data.get("session_id", str(uuid.uuid4()))
        user_id = conversation_data.get("user_id") if user_authenticated else None
        
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
        
        # Guardar el mensaje del usuario en la base de datos
        if user_authenticated:
            db_utils.save_message_with_user(user_id, session_id, "user", user_input)
        else:
            db_utils.save_message(session_id, "user", user_input)
        
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
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            if user_input.lower().startswith('/forecast-plan:'):
                question = user_input.split(':', 1)[1].strip()
                result_text = loop.run_until_complete(orchestrate_forecast_to_plan(question))
                loop.close()
                messages[-1]["content"] = result_text
                messages[-1]["time"] = datetime.now().strftime("%H:%M")
                if user_authenticated:
                    db_utils.save_message_with_user(user_id, session_id, "assistant", result_text)
                else:
                    db_utils.save_message(session_id, "assistant", result_text)
                chat_history = messages_to_components(messages)
                if user_authenticated:
                    conversation_data = {"messages": messages, "session_id": session_id, "user_id": user_id}
                else:
                    conversation_data = {"messages": messages, "session_id": session_id}
                return chat_history, "", conversation_data, ""

            # Pass the entire conversation history to the agent
            conversation_history = [{"role": msg["role"], "content": msg["content"]} for msg in messages[:-1]]  # Exclude the placeholder
            result = loop.run_until_complete(Runner.run(triage_agent, input=conversation_history))
            loop.close()
            
            # Update the placeholder with the actual response
            messages[-1]["content"] = result.final_output
            messages[-1]["time"] = datetime.now().strftime("%H:%M")
            
            # Guardar la respuesta del asistente en la base de datos
            if user_authenticated:
                db_utils.save_message_with_user(user_id, session_id, "assistant", result.final_output)
            else:
                db_utils.save_message(session_id, "assistant", result.final_output)
            
            # Update the UI with both messages
            chat_history = messages_to_components(messages)
            
            # Actualizar el store con los mensajes, el ID de sesión y el ID de usuario si está autenticado
            if user_authenticated:
                conversation_data = {
                    "messages": messages,
                    "session_id": session_id,
                    "user_id": user_id
                }
            else:
                conversation_data = {
                    "messages": messages,
                    "session_id": session_id
                }
            
            return chat_history, "", conversation_data, ""
        except Exception as e:
            # Handle errors
            error_message = {
                "role": "assistant",
                "content": f"Lo siento, ha ocurrido un error: {str(e)}",
                "time": datetime.now().strftime("%H:%M")
            }
            messages.append(error_message)
            
            # Guardar el mensaje de error en la base de datos
            if user_authenticated:
                db_utils.save_message_with_user(user_id, session_id, "assistant", error_message["content"])
            else:
                db_utils.save_message(session_id, "assistant", error_message["content"])
            
            chat_history = messages_to_components(messages)
            
            # Actualizar el store con los mensajes y el ID de sesión
            if user_authenticated:
                conversation_data = {
                    "messages": messages,
                    "session_id": session_id,
                    "user_id": user_id
                }
            else:
                conversation_data = {
                    "messages": messages,
                    "session_id": session_id
                }
            
            return chat_history, "", conversation_data, ""

    @app.callback(
        [Output("chat-history", "children", allow_duplicate=True),
         Output("conversation-store", "data", allow_duplicate=True)],
        [Input("clear-chat", "n_clicks")],
        [State("conversation-store", "data")],
        prevent_initial_call=True
    )
    def clear_chat_history(n_clicks, conversation_data):
        """Limpiar el historial de chat."""
        if not n_clicks:
            return dash.no_update, dash.no_update
        
        session_id = conversation_data.get("session_id")
        if session_id:
            # Limpiar el historial en la base de datos
            db_utils.clear_conversation_history(session_id)
        
        # Reiniciar el historial en la UI
        conversation_data["messages"] = []
        return [], conversation_data

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
