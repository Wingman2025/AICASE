import asyncio
import sys
import os

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
    """
    return db_utils.get_daily_data(date)

@function_tool
def update_production_plan(date: str, production_plan: int):
    """
    Update the production plan for a specific date.
    """
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

# Create specialist agents without using ConversationMemory
production_planner = Agent(
    name="production_planner",
    instructions="""
    You are a production planning specialist for a supply chain management system.
    Your responsibilities include:
      1. Getting daily data to understand the current production plan.
      2. Updating production plans when requested.
      3. Providing summaries and insights about production patterns.
    Always explain your reasoning and be concise.
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
      3. Analyzing the relationship between demand and inventory.
    Always explain your reasoning and be concise.
    """,
    model="gpt-4o",
    tools=[get_daily_data, get_demand_summary, get_inventory_summary]
)

data_generator = Agent(
    name="data_generator",
    instructions="""
    You are a data generation specialist for a supply chain management system.
    Your responsibilities include:
      1. Generating random but realistic data for future dates.
      2. Ensuring data consistency and integrity.
      3. Helping users understand the generated data.
    When asked to generate data:
      - Confirm the start date and number of days.
      - Use the DD-MM-YYYY format for dates (e.g., "18-04-2025").
      - Explain what data was generated and how it can be used.
    Be concise and helpful.
    """,
    model="gpt-4o",
    tools=[generate_future_data, get_daily_data]
)

triage_agent = Agent(
    name="triage_agent",
    instructions="""
    You determine which specialist agent to use based on the user's question:
    - Route to production_planner for questions about production plans.
    - Route to demand_planner for questions about demand analysis.
    - Route to data_generator for requests to generate new data.
    If the question involves multiple areas, choose the most relevant specialist.
    """,
    handoffs=[production_planner, demand_planner, data_generator]
)

async def main():
    # Initialize an empty conversation history as a list of messages.
    conversation_history = []
    print("Hi! I am your supply chain assistant. Type 'exit' to quit.")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'bye', 'quit']:
            print("Goodbye!")
            break

        # Append the user's message to the conversation history.
        conversation_history.append({"role": "user", "content": user_input})

        # Pass the entire conversation history to the agent.
        result = await Runner.run(triage_agent, input=conversation_history)

        # Append the agent's response to the conversation history.
        conversation_history.append({"role": "assistant", "content": result.final_output})

        print("Assistant:", result.final_output)

if __name__ == "__main__":
    asyncio.run(main())
