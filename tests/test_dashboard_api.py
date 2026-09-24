"""Contract checks for the thin dashboard JSON API."""

from src.api.app import create_app


def test_health_endpoint_returns_ok():
    response = create_app().test_client().get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_dashboard_endpoint_returns_real_module_sections():
    response = create_app().test_client().get("/api/dashboard?horizon_hours=1")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["station"]["id"] == "bharati"
    assert len(payload["telemetry"]["history"]) == 24
    assert payload["telemetry"]["latest"]["total_load_kw"] >= 0
    assert "forecast" in payload
    assert "dispatch" in payload
    assert "resilience" in payload


def test_dashboard_endpoint_rejects_invalid_parameters():
    client = create_app().test_client()

    assert client.get("/api/dashboard?horizon_hours=0").status_code == 400
    assert client.get("/api/dashboard?scenario=unknown").status_code == 400
