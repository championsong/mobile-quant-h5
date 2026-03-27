from __future__ import annotations

import os

from flask import Flask, jsonify, render_template, request
from flask import session

from mobile_web.services import (
    authenticate_user,
    get_auth_payload,
    get_dashboard_payload,
    get_strategy_detail,
    get_strategy_payload,
    run_preset_backtest,
)


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = os.getenv("MOMO_SECRET_KEY", "momo-quant-demo-secret")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/dashboard")
    def dashboard():
        return jsonify(get_dashboard_payload(session.get("username")))

    @app.get("/api/strategies")
    def strategies():
        return jsonify({"items": get_strategy_payload()})

    @app.get("/api/strategies/<code>")
    def strategy_detail(code: str):
        return jsonify(get_strategy_detail(code))

    @app.get("/api/auth/status")
    def auth_status():
        return jsonify(get_auth_payload(session.get("username")))

    @app.post("/api/auth/login")
    def login():
        payload = request.get_json(force=True)
        user = authenticate_user(
            username=payload.get("username", "").strip(),
            password=payload.get("password", "").strip(),
        )
        if not user:
            return jsonify({"message": "用户名或密码错误"}), 401
        session["username"] = user["username"]
        return jsonify({"message": "登录成功", "user": user})

    @app.post("/api/auth/logout")
    def logout():
        session.pop("username", None)
        return jsonify({"message": "已退出登录"})

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
