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
