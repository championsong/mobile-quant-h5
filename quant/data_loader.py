from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class PriceBar:
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


REQUIRED_FIELDS = {"date", "close"}


def _to_float(value: str, default: float = 0.0) -> float:
    text = (value or "").strip()
    return float(text) if text else default


def load_price_data(csv_path: str | Path) -> list[PriceBar]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"找不到数据文件: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fields = set(reader.fieldnames or [])
        missing = REQUIRED_FIELDS - fields
        if missing:
            raise ValueError(f"CSV 缺少必要字段: {', '.join(sorted(missing))}")

        bars: list[PriceBar] = []
        for row in reader:
            raw_date = (row.get("date") or "").strip()
            if not raw_date:
                continue

            bars.append(
                PriceBar(
                    date=datetime.fromisoformat(raw_date),
                    open=_to_float(row.get("open", ""), 0.0),
                    high=_to_float(row.get("high", ""), 0.0),
                    low=_to_float(row.get("low", ""), 0.0),
                    close=_to_float(row.get("close", ""), 0.0),
                    volume=_to_float(row.get("volume", ""), 0.0),
                )
            )

    if not bars:
        raise ValueError("CSV 中没有可用行情数据")

    bars.sort(key=lambda item: item.date)
    return bars
