# AURORA-EMS Forecasting Service Contract

## Purpose

The forecasting service provides a unified interface for renewable generation and station-load forecasts.

It is designed to provide Member 4 with a stable forecasting contract for optimization and energy-management decisions.

## Entry Points

The forecasting service provides two entry points.

### Primary API

```python
from src.forecasting.service import ForecastService

service = ForecastService()

forecast = service.generate_forecast(
    current_timestamp="2024-07-01T00:00:00+00:00",
    horizon_hours=24,
)

### Secondary API

```python
from src.forecasting.service import get_forecast

forecast = get_forecast(
    current_timestamp="2024-07-01T00:00:00+00:00",
    horizon_hours=24,
)
```
