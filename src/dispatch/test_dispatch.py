# AURORA-EMS
# Member 4 — Dispatch Tests
#
# Basic tests for the Member 4 dispatch modules.


from src.dispatch.baseline import diesel_first_dispatch
from src.dispatch.optimizer import optimized_dispatch
from src.dispatch.constraints import (
    limit_battery_discharge,
    limit_generator_output,
    calculate_unmet_load,
)
from src.dispatch.failover import dispatch_with_failover
from src.dispatch.fuel_metrics import (
    calculate_generator_fuel,
    calculate_total_fuel,
)


def test_baseline_dispatch():
    result = diesel_first_dispatch(100, 40)

    assert result["renewable_used_kw"] == 40
    assert result["generator_1_kw"] == 60
    assert result["generator_2_kw"] == 0
    assert result["unmet_load_kw"] == 0


def test_optimizer_uses_battery():
    result = optimized_dispatch(100, 40, 210)

    assert result["renewable_used_kw"] == 40
    assert result["battery_discharge_kw"] == 60
    assert result["generator_1_kw"] == 0
    assert result["generator_2_kw"] == 0
    assert result["unmet_load_kw"] == 0


def test_optimizer_uses_generators_when_needed():
    result = optimized_dispatch(200, 0, 210)

    assert result["battery_discharge_kw"] == 60
    assert result["generator_1_kw"] == 80
    assert result["generator_2_kw"] == 60
    assert result["unmet_load_kw"] == 0


def test_battery_constraint():
    result = limit_battery_discharge(100, 210)

    assert result == 60


def test_generator_constraints():
    assert limit_generator_output(100, "G1") == 80
    assert limit_generator_output(150, "G2") == 120


def test_unmet_load():
    assert calculate_unmet_load(100, 80) == 20
    assert calculate_unmet_load(100, 100) == 0


def test_generator_failover():
    result = dispatch_with_failover(100, False, True)

    assert result["generator_1_kw"] == 0
    assert result["generator_2_kw"] == 100
    assert result["unmet_load_kw"] == 0


def test_both_generators_unavailable():
    result = dispatch_with_failover(100, False, False)

    assert result["generator_1_kw"] == 0
    assert result["generator_2_kw"] == 0
    assert result["unmet_load_kw"] == 100


def test_generator_fuel():
    assert calculate_generator_fuel("G1", 60) == 18.0
    assert calculate_generator_fuel("G2", 60) == 17.8


def test_total_fuel():
    result = calculate_total_fuel(60, 60)

    assert result["generator_1_fuel_l"] == 18.0
    assert result["generator_2_fuel_l"] == 17.8
    assert result["total_fuel_l"] == 35.8