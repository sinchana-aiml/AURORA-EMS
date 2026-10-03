"""Flask entry point for the AURORA-EMS dashboard API."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

from flask import Flask, jsonify, request, send_from_directory

from .dashboard_service import build_dashboard_payload
from .chat_service import answer_chat


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/api/health")
    def health() -> tuple[object, int]:
        return jsonify({"status": "ok"}), 200

    @app.post("/api/chat")
    def chat() -> tuple[object, int]:
        body = request.get_json(silent=True) or {}
        message = str(body.get("message", "")).strip()
        if not message:
            return jsonify({"error": "message is required"}), 400
        if len(message) > 1000:
            return jsonify({"error": "message too long (max 1000 chars)"}), 400
        history = body.get("history", [])
        if not isinstance(history, list):
            history = []
        history = history[-8:]  # limit history
        try:
            dashboard_data = build_dashboard_payload(scenario="normal", horizon_hours=24)
        except Exception:
            dashboard_data = {}
        try:
            result = answer_chat(message, history, dashboard_data)
            return jsonify(result), 200
        except Exception as error:
            return jsonify({"error": f"Chat service error: {error}"}), 500

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
