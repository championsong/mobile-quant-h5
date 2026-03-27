from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from quant.backtest import BacktestResult, run_backtest
from quant.data_loader import load_price_data
from quant.downloader import default_end_date, default_start_date, download_a_share_history


@dataclass(slots=True)
class BrokerConnector:
    code: str
    name: str
    status: str
    description: str
    features: list[str]


@dataclass(slots=True)
class StrategyPreset:
    code: str
    title: str
    strategist: str
    engine: str
    description: str
    fit_for: str
    risk_level: str
    tags: list[str]
    params: dict[str, float | int]


BROKER_CONNECTORS = [
    BrokerConnector(
        code="sim",
        name="模拟交易账户",
        status="ready",
        description="默认启用，用于演示持仓、资金曲线和策略下单流程。",
        features=["资金总览", "模拟持仓", "策略联动", "风控演示"],
    ),
    BrokerConnector(
        code="qmt",
        name="QMT 网关适配",
        status="config_required",
        description="预留给本地量化终端接入，需你后续配置交易环境与账户权限。",
        features=["实盘下单", "持仓同步", "委托回报", "账户查询"],
    ),
    BrokerConnector(
        code="opend",
        name="OpenD 网关适配",
        status="config_required",
        description="适合做移动端与桌面端联动，后续可增加港美股或多市场支持。",
        features=["账户连接", "行情订阅", "交易下单", "订单跟踪"],
    ),
]


STRATEGY_PRESETS = [
    StrategyPreset(
        code="beichen_ma_fast",
        title="北辰趋势快线",
        strategist="北辰趋势研究员",
        engine="ma_cross",
        description="用 5 日和 20 日均线捕捉中短波段启动，适合想快速识别趋势切换的用户。",
        fit_for="震荡转趋势、热点轮动、轻仓试错",
        risk_level="中",
        tags=["双均线", "趋势跟随", "A股"],
        params={"short_window": 5, "long_window": 20},
    ),
    StrategyPreset(
        code="lanyue_ma_steady",
        title="岚月稳健均线",
        strategist="岚月波段交易师",
        engine="ma_cross",
        description="采用 10 日和 30 日均线过滤噪音，偏稳健，适合中线趋势持有。",
        fit_for="慢牛结构、主升浪跟随、回撤容忍度较低",
        risk_level="中低",
        tags=["双均线", "稳健", "中线"],
        params={"short_window": 10, "long_window": 30},
    ),
    StrategyPreset(
        code="bailu_rsi_reversal",
        title="白露超跌反弹",
        strategist="白露逆势交易师",
        engine="rsi_reversal",
        description="关注 RSI 脱离超卖区的反转机会，适合短线博弈超跌修复。",
        fit_for="情绪冰点后的技术修复、短期反弹",
        risk_level="中高",
        tags=["RSI", "反转", "短线"],
        params={"rsi_window": 14, "rsi_oversold": 30, "rsi_overbought": 70},
    ),
    StrategyPreset(
        code="chi_xiao_rsi_aggressive",
        title="赤霄动量反转",
        strategist="赤霄日内交易师",
        engine="rsi_reversal",
        description="缩短 RSI 周期并提高阈值敏感度，出手更快，也更容易被噪音干扰。",
        fit_for="高波动标的、激进风格、快进快出",
        risk_level="高",
        tags=["RSI", "激进", "波动"],
        params={"rsi_window": 9, "rsi_oversold": 25, "rsi_overbought": 75},
    ),
    StrategyPreset(
        code="poxiao_breakout_20",
        title="破晓 20 日突破",
        strategist="破晓趋势交易师",
        engine="donchian_breakout",
        description="当价格站上 20 日高点时参与趋势扩张，强调顺势和纪律止损。",
        fit_for="强趋势板块、放量突破、龙头跟随",
        risk_level="中高",
        tags=["唐奇安", "突破", "趋势"],
        params={"breakout_window": 20},
    ),
    StrategyPreset(
        code="yuanhang_breakout_55",
        title="远航长波段突破",
        strategist="远航CTA交易师",
        engine="donchian_breakout",
        description="扩大突破周期到 55 日，降低交易频率，偏向更大级别趋势。",
        fit_for="低频交易、长波段、耐心持有",
        risk_level="中",
        tags=["唐奇安", "低频", "长趋势"],
        params={"breakout_window": 55},
    ),
]


def get_dashboard_payload() -> dict:
    return {
        "profile": {
            "nickname": "量化指挥官",
            "membership": "专业版",
            "risk_level": "平衡型",
            "intro": "专注股票量化研究，偏好趋势与波段策略组合。",
        },
        "summary_cards": [
            {"label": "总资产", "value": "1,286,530", "delta": "+2.14%"},
            {"label": "今日盈亏", "value": "+12,460", "delta": "+0.98%"},
            {"label": "策略数", "value": str(len(STRATEGY_PRESETS)), "delta": "3 类引擎"},
            {"label": "已连券商", "value": "1/3", "delta": "可继续扩展"},
        ],
        "brokers": [asdict(item) for item in BROKER_CONNECTORS],
        "positions": [
            {"symbol": "000001", "name": "平安银行", "weight": "18%", "pnl": "+3.8%"},
            {"symbol": "600258", "name": "首旅酒店", "weight": "12%", "pnl": "-1.2%"},
            {"symbol": "600519", "name": "贵州茅台", "weight": "10%", "pnl": "+5.4%"},
        ],
        "watchlist": [
            "趋势突破组合",
            "银行低波动组合",
            "超跌修复观察池",
            "量价异动监控池",
        ],
    }


def get_strategy_payload() -> list[dict]:
    return [asdict(item) for item in STRATEGY_PRESETS]


def get_strategy_preset(code: str) -> StrategyPreset:
    for item in STRATEGY_PRESETS:
        if item.code == code:
            return item
    raise ValueError(f"未找到策略: {code}")


def serialize_backtest_result(result: BacktestResult) -> dict:
    return {
        "strategy_name": result.strategy_name,
        "initial_capital": round(result.initial_capital, 2),
        "ending_capital": round(result.ending_capital, 2),
        "total_return_pct": round(result.total_return_pct, 2),
        "annualized_return_pct": round(result.annualized_return_pct, 2),
        "buy_hold_return_pct": round(result.buy_hold_return_pct, 2),
        "alpha_vs_hold_pct": round(result.alpha_vs_hold_pct, 2),
        "max_drawdown_pct": round(result.max_drawdown_pct, 2),
        "win_rate_pct": round(result.win_rate_pct, 2),
        "profit_factor": round(result.profit_factor, 2),
        "average_holding_days": round(result.average_holding_days, 1),
        "trade_count": result.trade_count,
        "signals": [
            {
                "date": item.date,
                "signal": item.signal,
                "price": round(item.price, 2),
                "note": item.note,
            }
            for item in result.signals[-12:]
        ],
        "trades": [
            {
                "buy_date": item.buy_date,
                "buy_price": round(item.buy_price, 2),
                "sell_date": item.sell_date,
                "sell_price": round(item.sell_price, 2),
                "shares": item.shares,
                "profit": round(item.profit, 2),
                "return_pct": round(item.return_pct, 2),
                "holding_days": item.holding_days,
            }
            for item in result.trades[-12:]
        ],
        "equity_curve": [
            {"date": item.date, "close": round(item.close, 2), "equity": round(item.equity, 2)}
            for item in result.equity_curve
        ],
    }


def run_preset_backtest(
    strategy_code: str,
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: str,
    initial_capital: float,
    position_ratio: float,
) -> dict:
    preset = get_strategy_preset(strategy_code)
    csv_path = download_a_share_history(
        symbol=symbol,
        start_date=start_date or default_start_date(),
        end_date=end_date or default_end_date(),
        adjust=adjust,
    )
    bars = load_price_data(csv_path)

    params = {
        "bars": bars,
        "strategy_name": preset.engine,
        "initial_capital": initial_capital,
        "position_ratio": position_ratio,
        "short_window": 5,
        "long_window": 20,
        "rsi_window": 14,
        "rsi_oversold": 30.0,
        "rsi_overbought": 70.0,
        "breakout_window": 20,
    }
    params.update(preset.params)
    result = run_backtest(**params)

    payload = serialize_backtest_result(result)
    payload["strategy_title"] = preset.title
    payload["strategist"] = preset.strategist
    payload["symbol"] = symbol
    payload["csv_path"] = str(Path(csv_path))
    return payload
