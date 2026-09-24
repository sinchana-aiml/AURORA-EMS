"""Flask entry point for the AURORA-EMS dashboard API."""

from __future__ import annotations

from flask import Flask, jsonify, request

from .dashboard_service import build_dashboard_payload


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/api/health")
    def health() -> tuple[object, int]:
        return jsonify({"status": "ok"}), 200

    @app.get("/api/dashboard")
    def dashboard() -> tuple[object, int]:
        scenario = request.args.get("scenario", "normal")
        try:
            horizon_hours = int(request.args.get("horizon_hours", "24"))
            return jsonify(build_dashboard_payload(scenario=scenario, horizon_hours=horizon_hours)), 200
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        except Exception as error:  # Core Twin failures must be visible to the frontend.
            return jsonify({"error": f"Unable to build dashboard data: {error}"}), 500

    return app


app = create_app()
