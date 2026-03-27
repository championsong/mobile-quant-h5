from __future__ import annotations

from typing import Any

from mobile_web.services import PRO_MARKET


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    return int(round(_safe_float(value, default)))


def _row_value(row: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return default


def fetch_live_market(symbol: str) -> dict:
    code = (symbol or "").strip() or PRO_MARKET["active_symbol"]
    try:
        import akshare as ak

        bid_ask_df = ak.stock_bid_ask_em(symbol=code)
        intraday_df = ak.stock_intraday_em(symbol=code)
        minute_df = ak.stock_zh_a_hist_min_em(
            symbol=code,
            start_date="1979-09-01 09:30:00",
            end_date="2222-01-01 15:00:00",
            period="1",
            adjust="",
        )
        spot_df = ak.stock_zh_a_spot_em()
        spot_row = spot_df[spot_df["代码"] == code].iloc[0].to_dict()
        bid_ask_map = {str(row["item"]): row["value"] for _, row in bid_ask_df.iterrows()}

        asks = [
            {
                "level": f"卖{level}",
                "price": round(_safe_float(bid_ask_map.get(f"sell_{level}")), 2),
                "volume": _safe_int(bid_ask_map.get(f"sell_{level}_vol")),
            }
            for level in range(5, 0, -1)
        ]
        bids = [
            {
                "level": f"买{level}",
                "price": round(_safe_float(bid_ask_map.get(f"buy_{level}")), 2),
                "volume": _safe_int(bid_ask_map.get(f"buy_{level}_vol")),
            }
            for level in range(1, 6)
        ]

        minute_series = []
        running_amount = 0.0
        running_volume = 0
        for _, minute_row in minute_df.tail(60).iterrows():
            row = minute_row.to_dict()
            close_price = _safe_float(_row_value(row, "收盘", "最新价"))
            volume = _safe_int(_row_value(row, "成交量", "手数"))
            amount = _safe_float(_row_value(row, "成交额"), close_price * max(volume, 1))
            running_amount += amount
            running_volume += max(volume, 1)
            raw_time = str(_row_value(row, "时间", "日期", default=""))
            minute_series.append(
                {
                    "time": raw_time[11:16] if len(raw_time) >= 16 else raw_time[:5],
                    "price": round(close_price, 2),
                    "avg": round(running_amount / max(running_volume, 1), 2),
                    "volume": volume,
                }
            )

        ticks = []
        for _, tick_row in intraday_df.tail(20).iloc[::-1].iterrows():
            row = tick_row.to_dict()
            ticks.append(
                {
                    "time": str(_row_value(row, "时间", default="--:--:--")),
                    "price": round(_safe_float(_row_value(row, "成交价", "最新价")), 2),
                    "volume": _safe_int(_row_value(row, "手数", "成交量")),
                    "side": str(_row_value(row, "买卖盘性质", "性质", default="中性盘")),
                }
            )

        active_name = str(_row_value(spot_row, "名称", default=PRO_MARKET["active_name"]))
        last_price = round(
            _safe_float(_row_value(spot_row, "最新价"), minute_series[-1]["price"] if minute_series else 0),
            2,
        )
        prev_close = _safe_float(_row_value(spot_row, "昨收"), last_price)
        change_pct = ((last_price - prev_close) / prev_close * 100) if prev_close else 0.0
        turnover = _safe_float(_row_value(spot_row, "成交额"))
        volume_total = _safe_int(_row_value(spot_row, "成交量"))

        return {
            "active_symbol": code,
            "active_name": active_name,
            "last_price": last_price,
            "change_pct": f"{change_pct:+.2f}%",
            "turnover": round(turnover / 100000000, 2) if turnover else 0,
            "volume_total": volume_total,
            "minute_series": minute_series or PRO_MARKET["minute_series"],
            "order_book": {"asks": asks, "bids": bids},
            "ticks": ticks or PRO_MARKET["ticks"],
            "sectors": [
                {"name": "当前标的", "change_pct": f"{change_pct:+.2f}%", "leader": active_name},
                {"name": "高股息", "change_pct": "+1.42%", "leader": "中国神华"},
                {"name": "中字头", "change_pct": "+0.88%", "leader": "中国平安"},
                {"name": "AI 算力", "change_pct": "+2.31%", "leader": "中科曙光"},
            ],
        }
    except Exception:
        fallback = dict(PRO_MARKET)
        fallback["last_price"] = PRO_MARKET["minute_series"][-1]["price"]
        fallback["change_pct"] = "+1.12%"
        fallback["turnover"] = 8.41
        fallback["volume_total"] = 286400
        return fallback
