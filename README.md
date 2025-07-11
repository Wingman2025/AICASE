# Supply Chain Management System

# Supply Chain Management AI Assistant

This project implements a supply chain management system with AI-powered assistants using the OpenAI Agents SDK framework.

## Features

- Interactive dashboard for supply chain data visualization
- AI-powered chat assistant for supply chain management
- Multiple specialized AI agents for different supply chain functions:
  - Production planning
  - Demand forecasting
  - Inventory management
- Database integration for storing and retrieving supply chain data
- Optional **Debug** mode streams each execution step in the chat

## Project Structure

- `agents/` - Contains the AI agent definitions
  - `agentsscm.py` - Defines the supply chain management agents
- `dashboard/` - Dashboard application
  - `dashboard/dashboard.py` - Main dashboard application
- `data/` - Database and data files
- `chatbot.py` - Chat interface components and callbacks
- `db_utils.py` - Database utility functions


## Tech Stack

The application relies on the following core technologies:

- **Python 3.11** – primary language
- **OpenAI Agents SDK 0.0.8** – multi-agent LLM framework
- **Dash 2.x** & **Dash Bootstrap Components** – interactive dashboard UI
- **Pandas** – data wrangling and analysis
- **dateparser** – natural-language date parsing (European preference)
- **SQLite** (dev) & **PostgreSQL** (Railway) – relational storage with automatic driver switching
- **Asyncio** – async operations inside agents & web app

## Installation

1. Clone this repository
2. Install the required dependencies:
   pip install -r requirements.txt

3. Set up your OpenAI API key in an environment variable or .env file:


## Usage

1. Run `python dashboard/dashboard.py` to start the dashboard application.
2. Access the dashboard in your web browser at [http://127.0.0.1:8050/](http://127.0.0.1:8050/)
3. Use the chat interface to interact with the AI assistant
4. When requesting forecasts or data updates, the agent summarises the chosen calculation method and parameters. If you didn't specify details like the forecasting method or number of periods, the assistant will ask follow-up questions to gather that information and then request your confirmation before executing.
5. To generate a forecast and production plan in one step, type `/forecast-plan: <your question>` in the chat.
6. Enable the **Debug** checkbox in the chat window to stream step-by-step details of the agent's execution. When using `/forecast-plan:` the debug output includes events from both planners.

## AI Agents

The system uses multiple specialized AI agents:

- **Triage Agent**: Routes queries to the appropriate specialist agent and never answers directly
- **Production Planner**: Handles production planning and optimization
- **Demand Planner**: Analyzes demand patterns and forecasts

### Technical Design of Agents (`agents/agentsscm.py`)

The AI layer is built on top of the [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/agents/) and is organised as a small **multi-agent system**.

1. **Triage Agent (`triage_agent`)**
   • Role: entry-point router.
   • This agent never answers user questions or modifies data itself—it only routes requests to specialists.
   • Model: `gpt-4o`.
   • Handoffs: `production_planner`, `demand_planner`.
   • Routing rules:  
     – Production / inventory ⇒ `production_planner`  
     – Demand analysis / updating ⇒ `demand_planner`

2. **Production Planner (`production_planner`)**
   • Tools:
      – `get_daily_data`
      – `update_production_plan`
      – `get_production_summary`
      – `get_inventory_summary`
      – `get_stockouts`
      – `propose_production_plan_for_stockouts`
  • Responsibilities: analyse production vs demand, adjust production plans, propose fixes for stockouts, and report inventory impact. Before running calculations or modifying the database, this agent summarises the intended method (such as forecasting approach and periods) and requests confirmation from the user.

3. **Demand Planner (`demand_planner`)**
   • Tools:  
     – `get_daily_data`  
     – `update_demand`  
     – `get_demand_summary`  
  • Responsibilities: monitor and update demand values and forecast demand trends. Prior to any forecast or data update, the agent explains the calculation method and parameters and asks you to confirm before proceeding.


#### Shared Function Tools

| Tool | Purpose |
|------|---------|
| `get_daily_data(date?)` | Fetches day-level demand, production and inventory. |
| `update_production_plan(date, plan)` | Modifies the production plan for a given date and recalculates inventory. |
| `update_demand(date, demand)` | Modifies demand for a given date and recalculates inventory. |
| `get_production_summary()` | Aggregated stats on production. |
| `get_demand_summary()` | Aggregated stats on demand. |
| `get_inventory_summary()` | Aggregated stats on inventory. |
| `get_stockouts()` | Retrieve all rows where inventory is zero or negative. |
| `propose_production_plan_for_stockouts()` | Suggest production plans equal to demand on stockout days. |
| `generate_future_data(start_date, days)` | Populates future records with random realistic values. |
| `increase_all_demand(offset)` | Adds an offset to demand across all dates and recalculates inventory. |
| `clear_all_forecast()` | Sets all forecast values to NULL without deleting any rows. |
| `calculate_demand_forecast(method?, periods?, start_date?)` | Compute and store a forecast. If `start_date` is omitted the forecast begins after the last known date. |
| `delete_all_data()` | Hard reset of the database. |

#### Conversation & Memory

• Every CLI session is identified by a UUID (`session_id`).  
• Message history is persisted in the **conversation_history** table via `db_utils`.  
• When the script starts it loads previous messages, giving each agent long-term conversational memory.

#### Date & Database Abstraction

All functions rely on `db_utils.parse_date()` to normalise natural-language dates
into the `YYYY-MM-DD` format for both SQLite and PostgreSQL.
Month-only phrases such as `"July 2024"` are interpreted as the first day of that month.

The database access layer automatically switches between SQLite and PostgreSQL based on the presence of the `DATABASE_URL` environment variable and adapts SQL placeholders (`?` vs `%s`) accordingly.

This section should give maintainers enough detail to understand, extend or troubleshoot the agent infrastructure.

## Database

The application uses SQLite to store supply chain data. The database includes:
- Daily demand data
- Production plans
- Inventory levels

## Recent Updates

- Agents now draft a detailed plan and request explicit confirmation before any DB write.
- Added `increase_all_demand(offset)` tool for uniform bulk demand shifts (+/-) with automatic inventory recalculation.
- Added `clear_all_forecast()` tool to purge forecast values without touching other data.
- Triage routing extended so forecast-clearing requests reach the Demand Planner.
- Unified date handling: all functions produce `YYYY-MM-DD` regardless of backend.
- Inventory recalculates cumulatively whenever production or demand is changed.
- Forecast functions can now start from a custom date via `calculate_demand_forecast(start_date=...)`.
- Added `/forecast-plan:` command to run a forecast with the Demand Planner and
  immediately hand off to the Production Planner to create the production plan.

## License

[Your license information here]
