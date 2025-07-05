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


def forecast_from_date(
    start_date: str,
    periods: int,
    method: str = "exponential_smoothing",
    alpha: float = 0.5,
    window: int = 3,
) -> List[float]:
    """Forecast demand beginning from ``start_date`` using the chosen method.

    The forecast uses all data up to and including ``start_date`` as the
    history. Supported methods are ``"exponential_smoothing"`` (default) and
    ``"moving_average"``.
    """

    data = db_utils.get_daily_data()
    if not data:
        return []

    try:
        iso_date = db_utils.parse_date(start_date)
    except ValueError:
        return []

    earliest_date = min(str(row["date"]) for row in data)
    if iso_date < earliest_date:
        iso_date = earliest_date
        history = [row["demand"] for row in data]
    else:
        history = [
            row["demand"] for row in data if str(row["date"]) <= iso_date
        ]
    if not history:
        return []
    series = pd.Series(history)

    if method == "moving_average":
        if len(series) < window:
            window = len(series)
        last_ma = series.rolling(window=window).mean().iloc[-1]
        forecast = [round(last_ma, 2)] * periods
    else:
        model = SimpleExpSmoothing(series, initialization_method="heuristic").fit(
            smoothing_level=alpha, optimized=False
        )
        forecast = [round(val, 2) for val in model.forecast(periods).tolist()]

    return forecast

