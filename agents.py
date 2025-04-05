from agents import Agent, Runner

agent = Agent(
    name="Production_planner",
    instructions="You answer questions about the production plan and suggest action to the user to improve it",
)

agent = Agent(
    name="demand_planner",
    instructions="You answer questions about the demand and suggest action to the user to improve it",
)

triage_agent = Agent(
    name="Triage Agent",
    instructions="You determine which agent to use based on the user's question",
    handoffs=[Production_planner, demand_planner]
)

async def main():
    result = await Runner.run(triage_agent, "What is the capital of France?")
    print(result.final_output)