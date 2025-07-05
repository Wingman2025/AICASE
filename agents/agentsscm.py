import asyncio
import sys
import os
import uuid

# Add the parent directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import db_utils
import forecast_utils
from agents import Agent, Runner, function_tool
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

@function_tool
def get_daily_data(date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get daily supply chain data from the database.

    Args:
        date: Optional date string provided in natural language or in a common format
              (e.g., "03-04-2025", "2025-04-03", "today", "yesterday").

    Returns:
        A list of dictionaries containing the daily data, or an informative message
        if no data is found.
    """
    # Si se proporciona una fecha, se procesa y se formatea correctamente
    if date:
        try:
            # Esta función se encarga de interpretar la fecha y devolverla en el
            # formato ISO "YYYY-MM-DD" para ambos motores de base de datos
            formatted_date = db_utils.parse_date(date)
        except ValueError as e:
            return {"error": str(e)}
    else:
        formatted_date = None

    # Obtener los datos de la base de datos usando la fecha ya formateada
    result = db_utils.get_daily_data(formatted_date)

    # Si se especificó una fecha pero no se encontraron datos, se devuelve un mensaje informativo
    if formatted_date and not result:
        available = [item['date'] for item in db_utils.get_daily_data()]
        return {
            "error": f"No se encontraron datos para la fecha {formatted_date}",
            "available_dates": available,
            "message": "Estas son las fechas disponibles en la base de datos. Por favor, selecciona una de ellas."
        }

    return result

@function_tool
def update_production_plan(date: str, production_plan: int) -> Dict[str, Any]:
    """
    Update the production plan for a specific date.

    Args:
        date: A date string expressed in natural language or in a common format
              (e.g., "today", "03-04-2025", "2025-04-03").
        production_plan: New production plan value (integer).

    Returns:
        A message indicating success or failure.
    """
    # Convertir la fecha al formato adecuado para la base de datos usando parse_date
    try:
        formatted_date = db_utils.parse_date(date)
    except ValueError as e:
        return {"error": str(e)}

    # Verificar que existan datos para la fecha especificada
    data = db_utils.get_daily_data(formatted_date)
    if not data:
        return {
            "error": f"No se encontraron datos para la fecha {formatted_date}.",
            "message": "Verifica que la fecha exista en la base de datos."
        }

    # Llamar a la función de actualización en db_utils
    result_message = db_utils.update_production_plan(formatted_date, production_plan)
    return {"message": result_message}


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
def calculate_demand_forecast(
    method: str = "exponential_smoothing",
    periods: int = 7,
    start_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate demand forecast and persist it to the database.

    If ``start_date`` is provided, the forecast begins on that date using
    historical data up to and including that day. Otherwise the forecast starts
    after the latest date present in the database.
    """

    if start_date:
        try:
            formatted_start = db_utils.parse_date(start_date)
        except ValueError as e:
            return {"error": str(e)}
        forecast = forecast_utils.forecast_from_date(
            formatted_start, periods, method=method
        )
    else:
        if method == "moving_average":
            forecast = forecast_utils.moving_average_forecast(periods=periods)
        else:
            forecast = forecast_utils.exponential_smoothing_forecast(periods=periods)

    if not forecast:
        return {"error": "No demand data available for forecasting"}

    # Determine the start date for persisting the forecast
    data = db_utils.get_daily_data()
    if data:
        if start_date:
            next_date = datetime.strptime(formatted_start, "%Y-%m-%d")
        else:
            last_date_str = max(row["date"] for row in data)
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
            next_date = last_date + timedelta(days=1)

        for value in forecast:
            db_utils.update_forecast(next_date.strftime("%Y-%m-%d"), int(value))
            next_date += timedelta(days=1)

    return {"forecast": forecast}

@function_tool
def update_demand(date: str, demand: int) -> Dict[str, Any]:
    """
    Update the demand for a specific date.

    Args:
        date: A date string expressed in natural language or in a common format
              (e.g., "today", "03-04-2025", "2025-04-03").
        demand: New demand value (integer).

    Returns:
        A message indicating success or failure.
    """
    # Convertir la fecha al formato adecuado para la base de datos usando parse_date
    try:
        formatted_date = db_utils.parse_date(date)
    except ValueError as e:
        return {"error": str(e)}

    # Verificar que existan datos para la fecha especificada
    data = db_utils.get_daily_data(formatted_date)
    if not data:
        return {
            "error": f"No se encontraron datos para la fecha {formatted_date}.",
            "message": "Verifica que la fecha exista en la base de datos."
        }

    # Llamar a la función de actualización en db_utils
    result_message = db_utils.update_demand(formatted_date, demand)
    return {"message": result_message}

@function_tool
def increase_all_demand(offset: int) -> Dict[str, Any]:
    """Increase demand for every existing record by a constant offset (e.g., +50)."""
    result_message = db_utils.increase_all_demand(offset)
    return {"message": result_message}

@function_tool
def get_inventory_summary():
    """
    Get a summary of inventory data.
    """
    return db_utils.get_inventory_summary()

@function_tool
def get_stockouts():
    """Retrieve all rows with inventory at or below zero."""
    return db_utils.get_stockouts()

@function_tool
def propose_production_plan_for_stockouts():
    """Suggest a production plan equal to demand for each stockout day."""
    return db_utils.propose_production_plan_for_stockouts()

@function_tool
def clear_all_forecast() -> Dict[str, Any]:
    """Clear the forecast column for every row without deleting any data."""
    msg = db_utils.clear_all_forecast()
    return {"message": msg}


@function_tool
def clear_forecast_range(start_date: str, end_date: Optional[str] = None) -> Dict[str, Any]:
    """Clear forecast values on or after ``start_date`` (optionally until ``end_date``)."""
    msg = db_utils.clear_forecast_range(start_date, end_date)
    return {"message": msg}

@function_tool
def generate_future_data(start_date: str, days: int) -> Dict[str, Any]:
    """
    Generate random data for future dates and save to database.
    
    Args:
        start_date: A date string expressed in natural language or in a common format
                   (e.g., "today", "03-04-2025", "2025-04-03").
        days: Number of days to generate data for (integer).
        
    Returns:
        A message indicating success or failure.
    """
    # Convertir la fecha al formato adecuado para la base de datos usando parse_date
    try:
        formatted_start_date = db_utils.parse_date(start_date)
    except ValueError as e:
        return {"error": str(e)}
        
    # Llamar a la función de generación en db_utils
    result_message = db_utils.generate_future_data(formatted_start_date, days)
    return {"message": result_message}

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
      6. Retrieving all stockouts (days where inventory is zero or negative).
      7. Proposing a new production plan for those stockouts by matching the day's demand.
      8. **Before running any calculation or updating the database, draft a concise plan that lists _each_ date that will be modified and the exact new value to be written (e.g., `current + 50`). Present this plan to the user and request an explicit yes/no confirmation before executing.**
      9. When the user uses natural language date expressions (for example, "today", "tomorrow", "the next 10 days", "next week"), interpret the input using your date parsing tools.
     10. If the message contains a date range (for example, "from April 1st to April 5th", "the next 10 days"), explicitly determine the start and end of the range.
     11. IMPORTANT: You have access to the conversation history, so you can refer to previous messages
    and maintain context throughout the conversation.
    """,
    model="gpt-4o",
    tools=[get_daily_data, update_production_plan, get_production_summary, get_inventory_summary, get_stockouts, propose_production_plan_for_stockouts]
)

demand_planner = Agent(
    name="demand_planner",
    instructions="""
    You are a demand planning specialist for a supply chain management system.
    Your responsibilities include:
      1. Getting daily data to understand current demand.
      2. Providing summaries and insights about demand patterns.
      3. **Before running any forecast, modifying demand values, or clearing forecast data, create a clear plan (e.g., list of dates that will become `NULL` for forecast) and ask the user to confirm before executing.**
      4. When the user uses natural language date expressions (for example, "today", "tomorrow", "the next 10 days", "next week"), interpret the input using your date parsing tools.
      5. If the message contains a date range (for example, "from April 1st to April 5th", "the next 10 days"), explicitly determine the start and end of the range.
      6. IMPORTANT: You have access to the conversation history, so you can refer to previous messages
    and maintain context throughout the conversation.
    """,
    model="gpt-4o",
    tools=[
        get_daily_data,
        update_demand,
        increase_all_demand,
        clear_all_forecast,
        clear_forecast_range,
        get_demand_summary,
        calculate_demand_forecast,
    ]
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
      - Use the YYYY-MM-DD format for dates (e.g., "2025-04-18").
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
    - Route to demand_planner for questions about demand data, demand generation, demand analysis, or clearing forecast values.
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
