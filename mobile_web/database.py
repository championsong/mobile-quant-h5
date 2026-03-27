from __future__ import annotations

import sqlite3
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash


DB_PATH = Path(__file__).resolve().parent.parent / "momo_quant.db"


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


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                membership TEXT NOT NULL DEFAULT '体验版',
                risk_level TEXT NOT NULL DEFAULT '平衡型',
                intro TEXT NOT NULL DEFAULT '',
                phone_mask TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        for user in DEMO_USERS:
            connection.execute(
                """
                INSERT INTO users (
                    username, password_hash, display_name, membership, risk_level, intro, phone_mask
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO NOTHING
                """,
                (
                    user["username"],
                    generate_password_hash(user["password"]),
                    user["display_name"],
                    user["membership"],
                    user["risk_level"],
                    user["intro"],
                    user["phone_mask"],
                ),
            )


def serialize_user(row: sqlite3.Row | None) -> dict | None:
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


def get_user_by_username(username: str) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    return serialize_user(row)


def get_user_row(username: str) -> sqlite3.Row | None:
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()


def register_user(username: str, password: str, display_name: str) -> dict:
    with get_connection() as connection:
        existing = connection.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if existing:
            raise ValueError("用户名已存在")

        phone_mask = f"13{len(username):01d}****{len(display_name):04d}"[:11]
        connection.execute(
            """
            INSERT INTO users (
                username, password_hash, display_name, membership, risk_level, intro, phone_mask
            )
            VALUES (?, ?, ?, '体验版', '平衡型', ?, ?)
            """,
            (
                username,
                generate_password_hash(password),
                display_name,
                f"我是 {display_name}，正在使用 momo量化 探索移动端量化交易。",
                phone_mask,
            ),
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
    return serialize_user(row)
