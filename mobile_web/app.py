from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from mobile_web.services import (
    get_dashboard_payload,
    get_strategy_payload,
    run_preset_backtest,
)


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/dashboard")
    def dashboard():
        return jsonify(get_dashboard_payload())

    @app.get("/api/strategies")
    def strategies():
        return jsonify({"items": get_strategy_payload()})

    @app.post("/api/backtest")
    def backtest():
        payload = request.get_json(force=True)
        result = run_preset_backtest(
            strategy_code=payload.get("strategy_code", "beichen_ma_fast"),
            symbol=payload.get("symbol", "000001"),
            start_date=payload.get("start_date", ""),
            end_date=payload.get("end_date", ""),
            adjust=payload.get("adjust", "qfq"),
            initial_capital=float(payload.get("initial_capital", 100000)),
            position_ratio=float(payload.get("position_ratio", 0.95)),
        )
        return jsonify(result)

    return app
