from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    func,
    insert,
    select,
)
from sqlalchemy.engine import Engine, RowMapping
from werkzeug.security import check_password_hash, generate_password_hash


SQLITE_PATH = Path(__file__).resolve().parent.parent / "momo_quant.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{SQLITE_PATH}")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

ENGINE: Engine = create_engine(DATABASE_URL, future=True)
METADATA = MetaData()

USERS = Table(
    "users",
    METADATA,
    Column("id", Integer, primary_key=True),
    Column("username", String(64), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("display_name", String(64), nullable=False),
    Column("membership", String(32), nullable=False, server_default="体验版"),
    Column("risk_level", String(32), nullable=False, server_default="平衡型"),
    Column("intro", Text, nullable=False, server_default=""),
    Column("phone_mask", String(32), nullable=False, server_default=""),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
)

WATCHLISTS = Table(
    "watchlists",
    METADATA,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("symbol", String(16), nullable=False),
    Column("name", String(64), nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    UniqueConstraint("user_id", "symbol", name="uq_watchlists_user_symbol"),
)

FAVORITES = Table(
    "favorites",
    METADATA,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("strategy_code", String(64), nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    UniqueConstraint("user_id", "strategy_code", name="uq_favorites_user_strategy"),
)

ORDERS = Table(
    "orders",
    METADATA,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("symbol", String(16), nullable=False),
    Column("side", String(16), nullable=False),
    Column("order_type", String(16), nullable=False),
    Column("price", String(32), nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("status", String(32), nullable=False, server_default="submitted"),
    Column("note", Text, nullable=False, server_default=""),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
)

CONDITIONAL_ORDERS = Table(
    "conditional_orders",
    METADATA,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("symbol", String(16), nullable=False),
    Column("trigger_type", String(32), nullable=False),
    Column("trigger_price", String(32), nullable=False),
    Column("order_side", String(16), nullable=False),
    Column("order_price", String(32), nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("status", String(32), nullable=False, server_default="armed"),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
)

RISK_PROFILES = Table(
    "risk_profiles",
    METADATA,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
    Column("max_position_pct", Integer, nullable=False, server_default="25"),
    Column("max_daily_loss_pct", Integer, nullable=False, server_default="3"),
    Column("max_drawdown_pct", Integer, nullable=False, server_default="12"),
    Column("auto_stop_loss_pct", Integer, nullable=False, server_default="5"),
    Column("auto_take_profit_pct", Integer, nullable=False, server_default="12"),
    Column("updated_at", DateTime, nullable=False, server_default=func.now()),
)


DEMO_USERS = [
    {
        "username": "momo",
        "password": "momo123",
        "display_name": "momo研究员",
        "membership": "专业版",
        "risk_level": "平衡型",
        "intro": "偏好趋势和波段策略组合，关注移动端量化执行体验。",
        "phone_mask": "138****6677",
    },
    {
        "username": "guest",
        "password": "guest123",
        "display_name": "访客体验官",
        "membership": "体验版",
        "risk_level": "稳健型",
        "intro": "主要体验策略广场、行情榜单和移动端回测能力。",
        "phone_mask": "139****8899",
    },
]


def _serialize_user(row: RowMapping | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "membership": row["membership"],
        "risk_level": row["risk_level"],
        "intro": row["intro"],
        "phone_mask": row["phone_mask"],
    }


def init_db() -> None:
    METADATA.create_all(ENGINE)

    with ENGINE.begin() as connection:
        for user in DEMO_USERS:
            existing = connection.execute(
                select(USERS.c.id).where(USERS.c.username == user["username"])
            ).first()
            if existing:
                continue

            connection.execute(
                insert(USERS).values(
                    username=user["username"],
                    password_hash=generate_password_hash(user["password"]),
                    display_name=user["display_name"],
                    membership=user["membership"],
                    risk_level=user["risk_level"],
                    intro=user["intro"],
                    phone_mask=user["phone_mask"],
                )
            )

        momo = connection.execute(
            select(USERS.c.id).where(USERS.c.username == "momo")
        ).first()
        if momo:
            for item in [
                {"symbol": "000001", "name": "平安银行"},
                {"symbol": "600519", "name": "贵州茅台"},
                {"symbol": "300750", "name": "宁德时代"},
            ]:
                exists = connection.execute(
                    select(WATCHLISTS.c.id).where(
                        (WATCHLISTS.c.user_id == momo.id) & (WATCHLISTS.c.symbol == item["symbol"])
                    )
                ).first()
                if not exists:
                    connection.execute(
                        insert(WATCHLISTS).values(user_id=momo.id, symbol=item["symbol"], name=item["name"])
                    )

            for strategy_code in ["beichen_ma_fast", "poxiao_breakout_20"]:
                exists = connection.execute(
                    select(FAVORITES.c.id).where(
                        (FAVORITES.c.user_id == momo.id) & (FAVORITES.c.strategy_code == strategy_code)
                    )
                ).first()
                if not exists:
                    connection.execute(
                        insert(FAVORITES).values(user_id=momo.id, strategy_code=strategy_code)
                    )
            risk_exists = connection.execute(
                select(RISK_PROFILES.c.id).where(RISK_PROFILES.c.user_id == momo.id)
            ).first()
            if not risk_exists:
                connection.execute(
                    insert(RISK_PROFILES).values(
                        user_id=momo.id,
                        max_position_pct=30,
                        max_daily_loss_pct=3,
                        max_drawdown_pct=12,
                        auto_stop_loss_pct=5,
                        auto_take_profit_pct=14,
                    )
                )

            order_exists = connection.execute(
                select(ORDERS.c.id).where(ORDERS.c.user_id == momo.id)
            ).first()
            if not order_exists:
                connection.execute(
                    insert(ORDERS),
                    [
                        {
                            "user_id": momo.id,
                            "symbol": "000001",
                            "side": "buy",
                            "order_type": "limit",
                            "price": "11.02",
                            "quantity": 1200,
                            "status": "submitted",
                            "note": "趋势策略联动下单",
                        },
                        {
                            "user_id": momo.id,
                            "symbol": "600519",
                            "side": "sell",
                            "order_type": "market",
                            "price": "0",
                            "quantity": 100,
                            "status": "filled",
                            "note": "风控减仓",
                        },
                    ],
                )

            conditional_exists = connection.execute(
                select(CONDITIONAL_ORDERS.c.id).where(CONDITIONAL_ORDERS.c.user_id == momo.id)
            ).first()
            if not conditional_exists:
                connection.execute(
                    insert(CONDITIONAL_ORDERS),
                    [
                        {
                            "user_id": momo.id,
                            "symbol": "000001",
                            "trigger_type": "breakout_up",
                            "trigger_price": "11.20",
                            "order_side": "buy",
                            "order_price": "11.22",
                            "quantity": 1000,
                            "status": "armed",
                        },
                        {
                            "user_id": momo.id,
                            "symbol": "600519",
                            "trigger_type": "stop_loss",
                            "trigger_price": "1498.00",
                            "order_side": "sell",
                            "order_price": "1497.50",
                            "quantity": 100,
                            "status": "armed",
                        },
                    ],
                )


def get_user_row(username: str) -> RowMapping | None:
    with ENGINE.begin() as connection:
        row = connection.execute(
            select(USERS).where(USERS.c.username == username)
        ).mappings().first()
    return row


def get_user_by_username(username: str) -> dict | None:
    return _serialize_user(get_user_row(username))


def register_user(username: str, password: str, display_name: str) -> dict:
    with ENGINE.begin() as connection:
        existing = connection.execute(
            select(USERS.c.id).where(USERS.c.username == username)
        ).first()
        if existing:
            raise ValueError("用户名已存在")

        phone_mask = f"13{len(username):01d}****{len(display_name):04d}"[:11]
        connection.execute(
            insert(USERS).values(
                username=username,
                password_hash=generate_password_hash(password),
                display_name=display_name,
                membership="体验版",
                risk_level="平衡型",
                intro=f"我是 {display_name}，正在使用 momo量化 探索移动端量化交易。",
                phone_mask=phone_mask,
            )
        )

    user = get_user_by_username(username)
    if user is None:
        raise ValueError("注册失败")
    return user


def authenticate_user(username: str, password: str) -> dict | None:
    row = get_user_row(username)
    if row is None:
        return None
    if not check_password_hash(row["password_hash"], password):
        return None
    return _serialize_user(row)


def list_watchlist(username: str) -> list[dict]:
    user = get_user_by_username(username)
    if user is None:
        return []
    with ENGINE.begin() as connection:
        rows = connection.execute(
            select(WATCHLISTS).where(WATCHLISTS.c.user_id == user["id"]).order_by(WATCHLISTS.c.created_at.desc())
        ).mappings().all()
    return [{"symbol": row["symbol"], "name": row["name"]} for row in rows]


def add_watchlist_item(username: str, symbol: str, name: str) -> list[dict]:
    user = get_user_by_username(username)
    if user is None:
        raise ValueError("用户不存在")
    with ENGINE.begin() as connection:
        exists = connection.execute(
            select(WATCHLISTS.c.id).where(
                (WATCHLISTS.c.user_id == user["id"]) & (WATCHLISTS.c.symbol == symbol)
            )
        ).first()
        if not exists:
            connection.execute(
                insert(WATCHLISTS).values(user_id=user["id"], symbol=symbol, name=name)
            )
    return list_watchlist(username)


def remove_watchlist_item(username: str, symbol: str) -> list[dict]:
    user = get_user_by_username(username)
    if user is None:
        return []
    with ENGINE.begin() as connection:
        connection.execute(
            delete(WATCHLISTS).where(
                (WATCHLISTS.c.user_id == user["id"]) & (WATCHLISTS.c.symbol == symbol)
            )
        )
    return list_watchlist(username)


def list_favorites(username: str) -> list[str]:
    user = get_user_by_username(username)
    if user is None:
        return []
    with ENGINE.begin() as connection:
        rows = connection.execute(
            select(FAVORITES.c.strategy_code).where(FAVORITES.c.user_id == user["id"])
        ).all()
    return [row[0] for row in rows]


def add_favorite(username: str, strategy_code: str) -> list[str]:
    user = get_user_by_username(username)
    if user is None:
        raise ValueError("用户不存在")
    with ENGINE.begin() as connection:
        exists = connection.execute(
            select(FAVORITES.c.id).where(
                (FAVORITES.c.user_id == user["id"]) & (FAVORITES.c.strategy_code == strategy_code)
            )
        ).first()
        if not exists:
            connection.execute(
                insert(FAVORITES).values(user_id=user["id"], strategy_code=strategy_code)
            )
    return list_favorites(username)


def remove_favorite(username: str, strategy_code: str) -> list[str]:
    user = get_user_by_username(username)
    if user is None:
        return []
    with ENGINE.begin() as connection:
        connection.execute(
            delete(FAVORITES).where(
                (FAVORITES.c.user_id == user["id"]) & (FAVORITES.c.strategy_code == strategy_code)
            )
        )
    return list_favorites(username)


def _resolve_user_id(username: str) -> int:
    user = get_user_by_username(username)
    if user is None:
        raise ValueError("用户不存在")
    return int(user["id"])


def get_risk_profile(username: str) -> dict:
    user_id = _resolve_user_id(username)
    with ENGINE.begin() as connection:
        row = connection.execute(
            select(RISK_PROFILES).where(RISK_PROFILES.c.user_id == user_id)
        ).mappings().first()
        if row is None:
            connection.execute(insert(RISK_PROFILES).values(user_id=user_id))
            row = connection.execute(
                select(RISK_PROFILES).where(RISK_PROFILES.c.user_id == user_id)
            ).mappings().first()
    return {
        "max_position_pct": int(row["max_position_pct"]),
        "max_daily_loss_pct": int(row["max_daily_loss_pct"]),
        "max_drawdown_pct": int(row["max_drawdown_pct"]),
        "auto_stop_loss_pct": int(row["auto_stop_loss_pct"]),
        "auto_take_profit_pct": int(row["auto_take_profit_pct"]),
    }


def update_risk_profile(username: str, payload: dict) -> dict:
    user_id = _resolve_user_id(username)
    values = {
        "max_position_pct": int(payload.get("max_position_pct", 25)),
        "max_daily_loss_pct": int(payload.get("max_daily_loss_pct", 3)),
        "max_drawdown_pct": int(payload.get("max_drawdown_pct", 12)),
        "auto_stop_loss_pct": int(payload.get("auto_stop_loss_pct", 5)),
        "auto_take_profit_pct": int(payload.get("auto_take_profit_pct", 12)),
    }
    with ENGINE.begin() as connection:
        row = connection.execute(
            select(RISK_PROFILES.c.id).where(RISK_PROFILES.c.user_id == user_id)
        ).first()
        if row is None:
            connection.execute(insert(RISK_PROFILES).values(user_id=user_id, **values))
        else:
            connection.execute(
                RISK_PROFILES.update().where(RISK_PROFILES.c.user_id == user_id).values(**values)
            )
    return get_risk_profile(username)


def list_orders(username: str) -> list[dict]:
    user_id = _resolve_user_id(username)
    with ENGINE.begin() as connection:
        rows = connection.execute(
            select(ORDERS)
            .where(ORDERS.c.user_id == user_id)
            .order_by(ORDERS.c.created_at.desc(), ORDERS.c.id.desc())
        ).mappings().all()
    return [
        {
            "id": row["id"],
            "symbol": row["symbol"],
            "side": row["side"],
            "order_type": row["order_type"],
            "price": row["price"],
            "quantity": int(row["quantity"]),
            "status": row["status"],
            "note": row["note"],
        }
        for row in rows
    ]


def create_order(username: str, payload: dict) -> list[dict]:
    user_id = _resolve_user_id(username)
    with ENGINE.begin() as connection:
        connection.execute(
            insert(ORDERS).values(
                user_id=user_id,
                symbol=str(payload.get("symbol", "")).strip(),
                side=str(payload.get("side", "buy")).strip(),
                order_type=str(payload.get("order_type", "limit")).strip(),
                price=str(payload.get("price", "0")).strip(),
                quantity=int(payload.get("quantity", 0)),
                status="submitted",
                note=str(payload.get("note", "")).strip(),
            )
        )
    return list_orders(username)


def list_conditional_orders(username: str) -> list[dict]:
    user_id = _resolve_user_id(username)
    with ENGINE.begin() as connection:
        rows = connection.execute(
            select(CONDITIONAL_ORDERS)
            .where(CONDITIONAL_ORDERS.c.user_id == user_id)
            .order_by(CONDITIONAL_ORDERS.c.created_at.desc(), CONDITIONAL_ORDERS.c.id.desc())
        ).mappings().all()
    return [
        {
            "id": row["id"],
            "symbol": row["symbol"],
            "trigger_type": row["trigger_type"],
            "trigger_price": row["trigger_price"],
            "order_side": row["order_side"],
            "order_price": row["order_price"],
            "quantity": int(row["quantity"]),
            "status": row["status"],
        }
        for row in rows
    ]


def create_conditional_order(username: str, payload: dict) -> list[dict]:
    user_id = _resolve_user_id(username)
    with ENGINE.begin() as connection:
        connection.execute(
            insert(CONDITIONAL_ORDERS).values(
                user_id=user_id,
                symbol=str(payload.get("symbol", "")).strip(),
                trigger_type=str(payload.get("trigger_type", "breakout_up")).strip(),
                trigger_price=str(payload.get("trigger_price", "0")).strip(),
                order_side=str(payload.get("order_side", "buy")).strip(),
                order_price=str(payload.get("order_price", "0")).strip(),
                quantity=int(payload.get("quantity", 0)),
                status="armed",
            )
        )
    return list_conditional_orders(username)
