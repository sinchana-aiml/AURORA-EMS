"""
Simple demonstration of the AURORA-EMS forecasting service.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.forecasting.service import get_forecast


def main():
    forecast = get_forecast(
        current_timestamp="2024-07-01T00:00:00+00:00",
        horizon_hours=24,
    )

    print("\nAURORA-EMS Forecast Demo")
    print("=" * 60)

    print(f"Forecast rows: {len(forecast)}")
    print(f"Forecast mode: {forecast['forecast_mode'].iloc[0]}")

    print("\nFirst 5 forecast steps:")
    print(
        forecast[
            [
                "timestamp",
                "solar_power_kw_p50",
                "wind_power_kw_p50",
                "total_load_kw_p50",
                "net_load_kw_p50",
                "storm_risk_flag",
                "turbine_cutout_risk",
            ]
        ].head().to_string(index=False)
    )

    print("\nForecast completed successfully.")


if __name__ == "__main__":
    main()