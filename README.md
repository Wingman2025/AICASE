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

## Project Structure

- `agents/` - Contains the AI agent definitions
  - `agentsscm.py` - Defines the supply chain management agents
- `dashboard/` - Dashboard application
  - [dashboard.py](cci:7://file:///c:/Users/Jorge/cascade%20projects/AICASE/dashboard/dashboard.py:0:0-0:0) - Main dashboard application
- [data/](cci:1://file:///c:/Users/Jorge/cascade%20projects/AICASE/db_utils.py:19:0-48:20) - Database and data files
- `chatbot.py` - Chat interface components and callbacks
- [db_utils.py](cci:7://file:///c:/Users/Jorge/cascade%20projects/AICASE/db_utils.py:0:0-0:0) - Database utility functions


## Installation

1. Clone this repository
2. Install the required dependencies:
   pip install -r requirements.txt

3. Set up your OpenAI API key in an environment variable or .env file:


## Usage

1. Start the dashboard application:
2. Access the dashboard in your web browser at [http://127.0.0.1](http://127.0.0.1):8050/
3. Use the chat interface to interact with the AI assistant

## AI Agents

The system uses multiple specialized AI agents:

- **Triage Agent**: Routes queries to the appropriate specialist agent
- **Production Planner**: Handles production planning and optimization
- **Demand Planner**: Analyzes demand patterns and forecasts

## Database

The application uses SQLite to store supply chain data. The database includes:
- Daily demand data
- Production plans
- Inventory levels

## License

[Your license information here]