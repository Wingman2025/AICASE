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
            html.I(className="fas fa-comments"),
            id="open-chat-button",
            color="success",
            className="position-fixed",
            style={
                "bottom": "20px",
                "right": "20px",
                "zIndex": "1000",
                "borderRadius": "50%",
                "width": "50px",
                "height": "50px",
                "display": "flex",
                "justifyContent": "center",
                "alignItems": "center",
                "boxShadow": "0 4px 8px rgba(0,0,0,0.2)"
            },
        ),
    ])

    # Chat modal component - now smaller and positioned on the right
    chat_modal = html.Div(
        [
            html.Div([
                # Header
                html.Div([
                    html.H5("Supply Chain Assistant", className="m-0"),
                    html.Button(
                        "×",
                        id="close-chat",
                        className="btn-close",
                        style={"fontSize": "1.5rem"}
                    ),
                ], className="d-flex justify-content-between align-items-center p-2 bg-success text-white"),
                
                # Chat history display
                html.Div(id="chat-history", className="p-2 border-bottom", 
                        style={"height": "250px", "overflowY": "auto"}),
                
                # Input area
                html.Div([
                    dbc.InputGroup([
                        dbc.Input(id="user-input", placeholder="Ask a question...", 
                                type="text", size="sm"),
                        dbc.Button(
                            html.I(className="fas fa-paper-plane"), 
                            id="send-button", 
                            color="primary", 
                            size="sm",
                            className="ms-1"
                        ),
                    ]),
                    
                    # Loading indicator
                    dcc.Loading(
                        id="loading",
                        type="circle",
                        children=html.Div(id="loading-output")
                    ),
                ], className="p-2"),
            ], 
            className="border rounded bg-white shadow",
            style={
                "position": "fixed",
                "bottom": "80px",
                "right": "20px",
                "width": "300px",
                "zIndex": "1000",
                "display": "none"  # Initially hidden
            },
            id="chat-modal"
            ),
        ],
    )

    # Store component for chat history
    chat_store = dcc.Store(id="conversation-store", data={"messages": []})
    
    # Font Awesome for icons
    font_awesome = html.Link(
        rel="stylesheet",
        href="https://use.fontawesome.com/releases/v5.15.4/css/all.css"
    )
    
    return chat_button, chat_modal, chat_store, font_awesome

def register_callbacks(app):
    """Register the chat-related callbacks with the provided Dash app."""
    
    # Callback to open/close the chat modal
    @app.callback(
        Output("chat-modal", "style"),
        [Input("open-chat-button", "n_clicks"), Input("close-chat", "n_clicks")],
        [State("chat-modal", "style")],
        prevent_initial_call=True
    )
    def toggle_chat_modal(open_clicks, close_clicks, style):
        ctx = dash.callback_context
        if not ctx.triggered:
            return style
        
        # Create a copy of the current style
        new_style = dict(style) if style else {
            "position": "fixed",
            "bottom": "80px",
            "right": "20px",
            "width": "300px",
            "zIndex": "1000"
        }
        
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if button_id == "open-chat-button":
            new_style["display"] = "block"
        elif button_id == "close-chat":
            new_style["display"] = "none"
        
        return new_style

    # Callback to handle sending messages and getting responses
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
    def send_message(n_clicks, n_submit, user_input, conversation_data):
        # Check if there's a trigger and input
        if not (n_clicks or n_submit) or not user_input:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Add user message to conversation
        conversation_data["messages"].append({"role": "user", "content": user_input, "time": datetime.now().strftime("%H:%M")})
        
        # Get response from agent (run in a separate thread to not block the UI)
        try:
            # Create a placeholder for the agent's response
            conversation_data["messages"].append({"role": "assistant", "content": "Thinking...", "time": datetime.now().strftime("%H:%M")})
            
            # Run the agent in the background
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(Runner.run(triage_agent, user_input))
            loop.close()
            
            # Update the placeholder with the actual response
            conversation_data["messages"][-1]["content"] = result.final_output
            
        except Exception as e:
            # Handle errors gracefully
            conversation_data["messages"][-1]["content"] = f"I'm sorry, I encountered an error: {str(e)}"
        
        # Render the chat history with more compact styling
        chat_history = []
        for msg in conversation_data["messages"]:
            if msg["role"] == "user":
                # User message styling - more compact
                chat_history.append(html.Div([
                    html.Div(
                        msg["content"],
                        className="px-2 py-1 mb-1 rounded bg-primary text-white",
                        style={"maxWidth": "85%", "marginLeft": "auto", "fontSize": "0.9rem"}
                    ),
                    html.Small(
                        msg["time"],
                        className="d-block text-end text-muted",
                        style={"fontSize": "0.7rem"}
                    )
                ], className="d-flex flex-column mb-1"))
            else:
                # Assistant message styling - more compact
                chat_history.append(html.Div([
                    html.Div(
                        msg["content"],
                        className="px-2 py-1 mb-1 rounded bg-light",
                        style={"maxWidth": "85%", "fontSize": "0.9rem"}
                    ),
                    html.Small(
                        msg["time"],
                        className="d-block text-muted",
                        style={"fontSize": "0.7rem"}
                    )
                ], className="d-flex flex-column mb-1"))
        
        # Return updated chat history, clear input, updated conversation data, and empty loading output
        return chat_history, "", conversation_data, ""
