import pandas as pd
from typing import List
from statsmodels.tsa.holtwinters import SimpleExpSmoothing
import db_utils


def get_demand_series() -> pd.Series:
    """Return the demand series from the database."""
    data = db_utils.get_daily_data()
    if not data:
        return pd.Series(dtype=float)
    return pd.Series([row["demand"] for row in data])


def moving_average_forecast(window: int = 3, periods: int = 7) -> List[float]:
    """Return a simple moving average forecast."""
    series = get_demand_series()
    if series.empty:
        return []
    if len(series) < window:
        window = len(series)
    last_ma = series.rolling(window=window).mean().iloc[-1]
    return [round(last_ma, 2)] * periods


def exponential_smoothing_forecast(alpha: float = 0.5, periods: int = 7) -> List[float]:
    """Return an exponential smoothing forecast."""
    series = get_demand_series()
    if series.empty:
        return []
    model = SimpleExpSmoothing(series, initialization_method="heuristic").fit(
        smoothing_level=alpha, optimized=False
    )
    forecast = model.forecast(periods)
    return [round(val, 2) for val in forecast.tolist()]
