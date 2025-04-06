import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import asyncio
from datetime import datetime
import sys
import os

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
    
    # Add custom CSS for chat messages
    custom_css = html.Style("""
        .user-message {
            background-color: #e9f5ff;
            border-radius: 18px 18px 0 18px;
            padding: 10px 15px;
            margin: 5px 0;
            max-width: 80%;
            align-self: flex-end;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            word-break: break-word;
        }
        
        .assistant-message {
            background-color: #f1f1f1;
            border-radius: 18px 18px 18px 0;
            padding: 10px 15px;
            margin: 5px 0;
            max-width: 80%;
            align-self: flex-start;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            word-break: break-word;
        }
        
        .chat-timestamp {
            font-size: 0.7rem;
            color: #6c757d;
            margin-top: 2px;
        }
        
        /* Animaciones */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .user-message, .assistant-message {
            animation: fadeIn 0.3s ease-out;
        }
        
        /* Hover effect for the chat button */
        #open-chat-button:hover {
            transform: scale(1.05);
            box-shadow: 0 6px 16px rgba(0,0,0,0.4);
        }
    """)
    
    return chat_button, chat_modal, chat_store, font_awesome, custom_css

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
            # Añadir una animación de entrada
            current_style.update({"animation": "fadeIn 0.3s ease-out"})
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
    async def process_user_message(n_clicks, n_submit, user_input, conversation_data):
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
        
        # Create the user message UI component
        user_message_component = html.Div([
            html.Div(user_input, className="user-message"),
            html.Div(timestamp, className="chat-timestamp text-end")
        ], className="d-flex flex-column align-items-end mb-3")
        
        # Update the UI with the user message
        chat_history = messages_to_components(messages)
        
        # Process the message with the agent
        try:
            # Pass the entire conversation history to the agent
            conversation_history = [{"role": msg["role"], "content": msg["content"]} for msg in messages]
            result = await Runner.run(triage_agent, input=conversation_history)
            assistant_response = result.final_output
            
            # Add assistant response to conversation history
            assistant_message = {
                "role": "assistant",
                "content": assistant_response,
                "time": datetime.now().strftime("%H:%M")
            }
            messages.append(assistant_message)
            
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
                html.Div(message["content"], className="user-message"),
                html.Div(message["time"], className="chat-timestamp text-end")
            ], className="d-flex flex-column align-items-end mb-3")
        else:
            component = html.Div([
                html.Div([
                    html.I(className="fas fa-robot me-2 text-primary", style={"fontSize": "0.9rem"}),
                    message["content"]
                ], className="assistant-message"),
                html.Div(message["time"], className="chat-timestamp")
            ], className="d-flex flex-column align-items-start mb-3")
        
        components.append(component)
    
    return components
