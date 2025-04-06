import asyncio
from agents import Agent, Runner, function_tool, ConversationMemory
import sys
import os

# Add the parent directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import db_utils

@function_tool
def get_daily_data(date: str = None):
    return db_utils.get_daily_data(date)

@function_tool
def update_production_plan(date: str, production_plan: int):
    return db_utils.update_production_plan(date, production_plan)

@function_tool
def get_production_summary():
    return db_utils.get_production_summary()

@function_tool
def get_demand_summary():
    return db_utils.get_demand_summary()

@function_tool
def get_inventory_summary():
    return db_utils.get_inventory_summary()

@function_tool
def generate_future_data(start_date: str, days: int):
    return db_utils.generate_future_data(start_date, days)

# Create shared memory objects (optional if you want persistent context)
production_memory = ConversationMemory()
demand_memory = ConversationMemory()
data_generator_memory = ConversationMemory()
triage_memory = ConversationMemory()

# Define your specialist agents with memory as before
production_planner = Agent(
    name="production_planner",
    instructions="""
    You are a production planning specialist for a supply chain management system.
    
    Your responsibilities include:
    1. Get daily data to understand the current production plan
    2. Update production plans when requested
    3. Provide summaries and insights about production patterns
    
    Always explain your reasoning and provide context for your insights but be concise.
    """,
    model="gpt-4o",
    tools=[get_daily_data, update_production_plan, get_production_summary, get_inventory_summary],
    memory=production_memory
)

demand_planner = Agent(
    name="demand_planner",
    instructions="""
    You are a demand planning specialist for a supply chain management system.
    
    Your responsibilities include:
    1. Get daily data to understand current demand.
    2. Provide summaries and insights about demand patterns.
    3. Analyze the relationship between demand and inventory.
    
    Always explain your reasoning and provide context for your insights but be concise.
    """,
    model="gpt-4o",
    tools=[get_daily_data, get_demand_summary, get_inventory_summary],
    memory=demand_memory
)

data_generator = Agent(
    name="data_generator",
    instructions="""
    You are a data generation specialist for a supply chain management system.
    
    Your responsibilities include:
    1. Generate random but realistic data for future dates.
    2. Ensure data consistency and integrity.
    3. Help users understand the generated data.
    
    When asked to generate data:
    - Always confirm the start date and number of days.
    - Use the DD-MM-YYYY format for dates (e.g., "18-04-2025").
    - Explain what data was generated and how it can be used.
    
    Always be concise and helpful in your responses.
    """,
    model="gpt-4o",
    tools=[generate_future_data, get_daily_data],
    memory=data_generator_memory
)

triage_agent = Agent(
    name="triage_agent",
    instructions="""
    You determine which specialist agent to use based on the user's question:
    
    - Route to the production_planner for questions about production plans, modifying production values, or production capacity.
    - Route to the demand_planner for questions about demand patterns, forecasts, or demand analysis.
    - Route to the data_generator for requests to generate new data, create future data points, or simulate supply chain scenarios.
    
    If the question involves multiple areas, choose the most relevant specialist.
    """,
    handoffs=[production_planner, demand_planner, data_generator],
    memory=triage_memory
)

async def main():
    # Initialize an empty conversation history as a list of message dictionaries.
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
