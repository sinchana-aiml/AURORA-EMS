"""Flask entry point for the AURORA-EMS dashboard API."""

from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from .dashboard_service import build_dashboard_payload


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


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
            return jsonify(
                build_dashboard_payload(
                    scenario=scenario,
                    horizon_hours=horizon_hours,
                )
            ), 200
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        except Exception as error:
            return jsonify(
                {"error": f"Unable to build dashboard data: {error}"}
            ), 500

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def frontend(path: str):
        if not FRONTEND_DIST.exists():
            return jsonify(
                {
                    "error": "Frontend build not found. "
                    "Run `npm run build` inside frontend/."
                }
            ), 503

        requested_file = FRONTEND_DIST / path

        if path and requested_file.is_file():
            return send_from_directory(FRONTEND_DIST, path)

        return send_from_directory(FRONTEND_DIST, "index.html")

    return app


app = create_app()
