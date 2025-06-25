import os
import sys
import sqlite3

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, 'agents'))

import db_utils
import agentsscm
import forecast_utils

DB_PATH = db_utils.get_db_path()


def setup_module(module):
    if 'DATABASE_URL' in os.environ:
        del os.environ['DATABASE_URL']
    db_utils.IS_RAILWAY = 'DATABASE_URL' in os.environ
    if DB_PATH and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    if DB_PATH:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
    else:
        conn = db_utils.get_connection()
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS daily_data")
    cur.execute(
        """
        CREATE TABLE daily_data (
            date TEXT PRIMARY KEY,
            demand INTEGER,
            production_plan INTEGER,
            forecast INTEGER,
            inventory INTEGER
        )
        """
    )
    for i in range(1, 14):
        date = f"2024-01-{i:02d}"
        demand = 100 + i
        prod = 110 + i
        inv = prod - demand
        cur.execute(
            "INSERT INTO daily_data (date, demand, production_plan, forecast, inventory) VALUES (?, ?, ?, ?, ?)",
            (date, demand, prod, 0, inv),
        )
    conn.commit()
    conn.close()


def test_calculate_demand_forecast_no_persist(monkeypatch):
    original_get_daily_data = db_utils.get_daily_data

    def limited_get_daily_data(date=None):
        data = original_get_daily_data(date)
        if date is None:
            return [row for row in data if row["date"] <= "2024-01-10"]
        return data

    monkeypatch.setattr(db_utils, "get_daily_data", limited_get_daily_data)

    conn = db_utils.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT forecast FROM daily_data WHERE date = ?", ('2024-01-11',))
    original_value = cur.fetchone()[0]
    conn.close()

    expected = forecast_utils.exponential_smoothing_forecast(periods=3)
    import json, asyncio
    result = asyncio.run(
        agentsscm.calculate_demand_forecast.on_invoke_tool(
            None,
            json.dumps({"method": "exponential_smoothing", "periods": 3}),
        )
    )
    assert result["forecast"] == expected

    conn = db_utils.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT forecast FROM daily_data WHERE date = ?", ('2024-01-11',))
    f1 = cur.fetchone()[0]
    conn.close()

    assert f1 == original_value


def test_calculate_demand_forecast_updates_future_rows(monkeypatch):
    original_get_daily_data = db_utils.get_daily_data

    def limited_get_daily_data(date=None):
        data = original_get_daily_data(date)
        if date is None:
            return [row for row in data if row['date'] <= '2024-01-10']
        return data

    monkeypatch.setattr(db_utils, "get_daily_data", limited_get_daily_data)

    expected = forecast_utils.exponential_smoothing_forecast(periods=3)
    import json, asyncio
    result = asyncio.run(
        agentsscm.calculate_demand_forecast.on_invoke_tool(
            None,
            json.dumps({"method": "exponential_smoothing", "periods": 3, "persist": True}),
        )
    )
    assert result["forecast"] == expected

    conn = db_utils.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT forecast FROM daily_data WHERE date = ?", ('2024-01-11',))
    f1 = cur.fetchone()[0]
    cur.execute("SELECT forecast FROM daily_data WHERE date = ?", ('2024-01-12',))
    f2 = cur.fetchone()[0]
    cur.execute("SELECT forecast FROM daily_data WHERE date = ?", ('2024-01-13',))
    f3 = cur.fetchone()[0]
    conn.close()

    int_expected = [int(x) for x in expected]
    assert [f1, f2, f3] == int_expected
