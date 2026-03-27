from __future__ import annotations

import os

from flask import Flask, jsonify, render_template, request
from flask import session

from mobile_web.database import (
    add_favorite,
    add_watchlist_item,
    get_user_by_username,
    init_db,
    list_favorites,
    list_watchlist,
    register_user,
    remove_favorite,
    remove_watchlist_item,
)
from mobile_web.services import (
    get_dashboard_payload,
    get_strategy_detail,
    get_strategy_payload,
    run_preset_backtest,
)
from mobile_web.database import authenticate_user


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = os.getenv("MOMO_SECRET_KEY", "momo-quant-demo-secret")
    init_db()

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
        user = get_user_by_username(session.get("username", ""))
        return jsonify(
            {
                "is_authenticated": bool(user and user["username"] != "guest"),
                "user": user or get_user_by_username("guest"),
            }
        )

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

    @app.post("/api/auth/register")
    def register():
        payload = request.get_json(force=True)
        username = payload.get("username", "").strip()
        password = payload.get("password", "").strip()
        display_name = payload.get("display_name", "").strip()
        if len(username) < 3:
            return jsonify({"message": "用户名至少 3 位"}), 400
        if len(password) < 6:
            return jsonify({"message": "密码至少 6 位"}), 400
        if len(display_name) < 2:
            return jsonify({"message": "昵称至少 2 位"}), 400
        try:
            user = register_user(username, password, display_name)
        except ValueError as exc:
            return jsonify({"message": str(exc)}), 400
        session["username"] = user["username"]
        return jsonify({"message": "注册成功", "user": user})

    @app.post("/api/auth/logout")
    def logout():
        session.pop("username", None)
        return jsonify({"message": "已退出登录"})

    @app.get("/api/me/watchlist")
    def my_watchlist():
        username = session.get("username", "guest")
        return jsonify({"items": list_watchlist(username)})

    @app.post("/api/me/watchlist")
    def add_watchlist():
        payload = request.get_json(force=True)
        username = session.get("username", "guest")
        items = add_watchlist_item(
            username=username,
            symbol=payload.get("symbol", "").strip(),
            name=payload.get("name", "").strip() or payload.get("symbol", "").strip(),
        )
        return jsonify({"items": items})

    @app.delete("/api/me/watchlist/<symbol>")
    def delete_watchlist(symbol: str):
        username = session.get("username", "guest")
        items = remove_watchlist_item(username=username, symbol=symbol)
        return jsonify({"items": items})

    @app.get("/api/me/favorites")
    def my_favorites():
        username = session.get("username", "guest")
        return jsonify({"items": list_favorites(username)})

    @app.post("/api/me/favorites")
    def create_favorite():
        payload = request.get_json(force=True)
        username = session.get("username", "guest")
        items = add_favorite(username=username, strategy_code=payload.get("strategy_code", "").strip())
        return jsonify({"items": items})

    @app.delete("/api/me/favorites/<strategy_code>")
    def delete_favorite(strategy_code: str):
        username = session.get("username", "guest")
        items = remove_favorite(username=username, strategy_code=strategy_code)
        return jsonify({"items": items})

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
