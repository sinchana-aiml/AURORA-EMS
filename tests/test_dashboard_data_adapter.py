"""Focused checks for the dashboard-only Digital Twin data adapter."""

from dashboard.data_adapter import DASHBOARD_COLUMNS, load_digital_twin_sample


def test_empty_fuel_adapter_uses_digital_twin_outputs():
    data = load_digital_twin_sample(initial_fuel_litres=0.0)

    assert list(data.columns) == DASHBOARD_COLUMNS
    assert len(data) == 24
    assert (data["fuel_litres"] == 0.0).all()
    assert (data["generator_kw"] == 0.0).all()
    assert (data["unmet_load_kw"] > 0.0).any()
    assert data.attrs["initial_fuel_litres"] == 0.0
