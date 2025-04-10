import asyncio
import sys
import os
import uuid

# Add the parent directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import db_utils
from agents import Agent, Runner, function_tool

@function_tool
def get_daily_data(date: str = None):
    """
    Get daily supply chain data from the database.
    
    Args:
        date: Optional date string in DD-MM-YYYY format (e.g., "03-04-2025").
             If provided, only data for that date is returned.
             
    Returns:
        A list of dictionaries containing the daily data or an informative message.
    """
    # Asegurarse de que la fecha esté en formato DD-MM-YYYY
    if date and "-" in date:
        # Si la fecha está en formato YYYY-MM-DD, convertirla a DD-MM-YYYY
        try:
            parts = date.split("-")
            if len(parts) == 3 and len(parts[0]) == 4:  # Formato YYYY-MM-DD
                date = f"{parts[2]}-{parts[1]}-{parts[0]}"
        except Exception:
            pass  # Si hay algún error, usar la fecha tal como está
    
    result = db_utils.get_daily_data(date)
    
    # Si se especificó una fecha pero no se encontraron datos, obtener fechas disponibles
    if date and not result:
        # Obtener todas las fechas disponibles
        all_dates = [item['date'] for item in db_utils.get_daily_data()]
        return {
            "error": f"No se encontraron datos para la fecha {date}",
            "available_dates": all_dates,
            "message": "Estas son las fechas disponibles en la base de datos. Por favor, selecciona una de ellas."
        }
    
    return result

@function_tool
def update_production_plan(date: str, production_plan: int):
    """
    Update the production plan for a specific date.
    
    Args:
        date: Date string in DD-MM-YYYY format (e.g., "03-04-2025").
        production_plan: New production plan value (integer).
        
    Returns:
        A message indicating success or failure.
    """
    # Asegurarse de que la fecha esté en formato DD-MM-YYYY
    if date and "-" in date:
        # Si la fecha está en formato YYYY-MM-DD, convertirla a DD-MM-YYYY
        try:
            parts = date.split("-")
            if len(parts) == 3 and len(parts[0]) == 4:  # Formato YYYY-MM-DD
                date = f"{parts[2]}-{parts[1]}-{parts[0]}"
        except Exception:
            pass  # Si hay algún error, usar la fecha tal como está
    
    # Verificar primero si existen datos para esta fecha
    data = db_utils.get_daily_data(date)
    if not data:
        return f"No se encontraron datos para la fecha {date}. Por favor, verifica que la fecha existe en la base de datos."
    
    return db_utils.update_production_plan(date, production_plan)

@function_tool
def get_production_summary():
    """
    Get a summary of production data.
    """
    return db_utils.get_production_summary()

@function_tool
def get_demand_summary():
    """
    Get a summary of demand data.
    """
    return db_utils.get_demand_summary()

@function_tool
def update_demand(date: str, demand: int):
    """
    Update the demand for a specific date.
    """
    return db_utils.update_demand(date, demand)

@function_tool
def get_inventory_summary():
    """
    Get a summary of inventory data.
    """
    return db_utils.get_inventory_summary()

@function_tool
def generate_future_data(start_date: str, days: int):
    """
    Generate random data for future dates and save to database.
    """
    return db_utils.generate_future_data(start_date, days)

@function_tool
def delete_all_data():
    """
    Elimina todos los datos de la base de datos para comenzar desde cero.
    
    Returns:
        Un mensaje indicando el éxito o error de la operación.
    """
    return db_utils.delete_all_data()

# Create specialist agents
production_planner = Agent(
    name="production_planner",
    instructions="""
    You are a production planning specialist for a supply chain management system.
    Your responsibilities include:
      1. Getting daily data to understand the current production plan.
      2. Updating production plans when requested.
      3. Providing summaries and insights about production patterns.
      4. Analyzing the relationship between demand and inventory.
      5. Updating production plan based on inventory levels.
    Always explain your reasoning and be concise.
    
    IMPORTANT: You have access to the conversation history, so you can refer to previous messages
    and maintain context throughout the conversation.
    """,
    model="gpt-4o",
    tools=[get_daily_data, update_production_plan, get_production_summary, get_inventory_summary]
)

demand_planner = Agent(
    name="demand_planner",
    instructions="""
    You are a demand planning specialist for a supply chain management system.
    Your responsibilities include:
      1. Getting daily data to understand current demand.
      2. Providing summaries and insights about demand patterns.
    Always explain your reasoning and be concise.
    
    IMPORTANT: You have access to the conversation history, so you can refer to previous messages
    and maintain context throughout the conversation.
    """,
    model="gpt-4o",
    tools=[get_daily_data, update_demand, get_demand_summary]
)

data_generator = Agent(
    name="data_generator",
    instructions="""
    You are a data generation specialist for a supply chain management system.
    Your responsibilities include:
      1. Generating random but realistic data for future dates.
      2. Ensuring data consistency and integrity.
      3. Eliminating all data when the user wants to start from scratch.
    
    When asked to generate data:
      - Confirm the start date and number of days.
      - Use the DD-MM-YYYY format for dates (e.g., "18-04-2025").
      - Explain what data was generated and how it can be used.
    
    When asked to delete all data:
      - Confirm with the user that they really want to delete all data.
      - Warn them that this action cannot be undone.
      - After deletion, suggest generating new data.
    
    Be concise and helpful.
    
    IMPORTANT: You have access to the conversation history, so you can refer to previous messages
    and maintain context throughout the conversation.
    """,
    model="gpt-4o",
    tools=[generate_future_data, get_daily_data, delete_all_data]
)

triage_agent = Agent(
    name="triage_agent",
    instructions="""
    You determine which specialist agent to use based on the user's question:
    - Route to production_planner for questions about production plans, updating production plan, inventory levels.
    - Route to demand_planner for questions about demand data, demand generation and demand analysis.
    - Route to data_generator for:
      * Requests to generate new data.
      * Requests to delete all data and start from scratch.
      * Requests to delete unused tables (procurement, production, inventory, distribution).
    
    If the question involves multiple areas, choose the most relevant specialist.
    
    IMPORTANT: You have access to the conversation history, so you can refer to previous messages
    and maintain context throughout the conversation.
    """,
    handoffs=[production_planner, demand_planner, data_generator]
)

async def main():
    # Crear la tabla de historial de conversaciones si no existe
    db_utils.create_conversation_history_table()
    
    # Generar un ID de sesión único para esta conversación
    session_id = str(uuid.uuid4())
    print(f"ID de sesión: {session_id}")
    
    # Recuperar el historial de conversación existente o inicializar uno vacío
    db_conversation = db_utils.get_conversation_history(session_id)
    
    # Inicializar el historial para el agente
    agent_messages = []
    if db_conversation:
        # Si hay conversación previa en la base de datos, cargarla para el agente
        agent_messages = [{"role": msg["role"], "content": msg["content"]} for msg in db_conversation]
    
    print("Hi! I am your supply chain assistant. Type 'exit' to quit.")
    print("Type 'clear history' to borrar el historial de esta sesión.")
    
    result = None  # Para almacenar el resultado de la ejecución anterior
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'bye', 'quit']:
            print("Goodbye!")
            break
            
        if user_input.lower() == 'clear history':
            # Limpiar el historial de conversación
            db_utils.clear_conversation_history(session_id)
            agent_messages = []
            result = None
            print("Historial de conversación eliminado.")
            continue
        
        # Guardar el mensaje del usuario en la base de datos
        db_utils.save_message(session_id, "user", user_input)
        
        # Preparar la entrada para el agente
        if result:
            # Si hay un resultado previo, usar to_input_list() para mantener el contexto
            new_input = result.to_input_list() + [{"role": "user", "content": user_input}]
        else:
            # Primera interacción o después de limpiar el historial
            if agent_messages:
                # Si hay mensajes previos en la base de datos
                new_input = agent_messages + [{"role": "user", "content": user_input}]
            else:
                # Completamente nuevo
                new_input = [{"role": "user", "content": user_input}]
        
        # Ejecutar el agente con la entrada preparada
        result = await Runner.run(triage_agent, input=new_input)
        
        # Guardar la respuesta del asistente en la base de datos
        db_utils.save_message(session_id, "assistant", result.final_output)
        
        print("Assistant:", result.final_output)

if __name__ == "__main__":
    asyncio.run(main())
