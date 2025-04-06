from agents import Agent, Runner, function_tool
import sys
import os

# Add the parent directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import db_utils

# Define function tools for the agents to use
@function_tool
def get_daily_data(date: str = None):
    """
    Get daily supply chain data from the database.
    
    Args:
        date: Optional date string in DD-MM-YYYY format. If provided, only data for that date is returned.
    
    Returns:
        List of dictionaries containing the daily data.
    """
    return db_utils.get_daily_data(date)

@function_tool
def update_production_plan(date: str, production_plan: int):
    """
    Update the production plan for a specific date.
    
    Args:
        date: Date string in DD-MM-YYYY format.
        production_plan: New production plan value.
    
    Returns:
        Success or error message.
    """
    return db_utils.update_production_plan(date, production_plan)

@function_tool
def get_production_summary():
    """
    Get a summary of production data.
    
    Returns:
        Dictionary with production summary statistics.
    """
    return db_utils.get_production_summary()

@function_tool
def get_demand_summary():
    """
    Get a summary of demand data.
    
    Returns:
        Dictionary with demand summary statistics.
    """
    return db_utils.get_demand_summary()

@function_tool
def get_inventory_summary():
    """
    Get a summary of inventory data.
    
    Returns:
        Dictionary with inventory summary statistics.
    """
    return db_utils.get_inventory_summary()

# Create the production planner agent with the database tools
production_planner = Agent(
    name="production_planner",
    instructions="""
    You are a production planning assistant. You help users understand and modify the production plan.
    Use the provided tools to:
    1. Get daily data to understand the current production plan
    2. Update the production plan when requested
    3. Provide summaries and insights about production
    
    Always explain your reasoning and provide context for your recommendations but be concise.
    """,
    model="gpt-4o",
    tools=[get_daily_data, update_production_plan, get_production_summary, get_inventory_summary]
)

# Create the demand planner agent with the database tools
demand_planner = Agent(
    name="demand_planner",
    instructions="""
    You are a demand planning assistant. You help users understand demand patterns and trends.
    Use the provided tools to:
    1. Get daily data to understand the current demand
    2. Provide summaries and insights about demand patterns
    3. Analyze the relationship between demand and inventory
    
    Always explain your reasoning and provide context for your insights but be concise
    """,
    model="gpt-4o",
    tools=[get_daily_data, get_demand_summary, get_inventory_summary]
)

# Create the triage agent that routes to the appropriate specialist
triage_agent = Agent(
    name="triage_agent",
    instructions="""
    You determine which specialist agent to use based on the user's question:
    
    - Route to the production_planner for questions about production plans, 
      modifying production values, or production capacity.
      
    - Route to the demand_planner for questions about demand patterns, 
      forecasts, or demand analysis.
      
    If the question involves both areas, choose the most relevant specialist.
    """,
    handoffs=[production_planner, demand_planner]
)

async def main():
    msg = input("Hi! I am your supply chain assistant. How can I help? ")
    result = await Runner.run(triage_agent, msg)
    print(result.final_output)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())