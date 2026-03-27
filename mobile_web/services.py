from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from mobile_web.database import get_user_by_username
from quant.backtest import BacktestResult, run_backtest
from quant.data_loader import load_price_data
from quant.downloader import default_end_date, default_start_date, download_a_share_history
from quant.strategy import moving_average


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
    hero: str
    philosophy: str
    strengths: list[str]
    warnings: list[str]
    steps: list[str]
    params: dict[str, float | int]


BROKER_CONNECTORS = [
    BrokerConnector(
        code="sim",
        name="模拟交易账户",
        status="ready",
        description="默认启用，负责演示资金面板、持仓变化、策略下单和风控联动。",
        features=["资金总览", "模拟持仓", "策略联动", "风控演示"],
    ),
    BrokerConnector(
        code="qmt",
        name="QMT 交易终端",
        status="config_required",
        description="为本地量化终端预留，可同步账户、委托和成交回报。",
        features=["实盘下单", "持仓同步", "委托回报", "账户查询"],
    ),
    BrokerConnector(
        code="opend",
        name="OpenD 网关",
        status="config_required",
        description="适合扩展多市场能力，便于后续接入更丰富的券商能力。",
        features=["账户连接", "行情订阅", "交易下单", "订单跟踪"],
    ),
]


STRATEGY_PRESETS = [
    StrategyPreset(
        code="beichen_ma_fast",
        title="北辰趋势快线",
        strategist="北辰趋势研究员",
        engine="ma_cross",
        description="用 5 日和 20 日均线捕捉趋势启动，适合热点轮动中的快速跟随。",
        fit_for="震荡转趋势、热点切换、轻仓试错",
        risk_level="中",
        tags=["双均线", "趋势跟随", "A股"],
        hero="更适合想要在趋势刚启动时介入、又不想把持仓拉得太久的用户。",
        philosophy="先确认趋势，再参与波段，宁可慢一步，也要避免频繁在噪音里追涨杀跌。",
        strengths=["信号清晰", "参数直观", "适合手机端快速选择"],
        warnings=["震荡行情容易来回打脸", "不适合极短线日内搏杀"],
        steps=["短均线上穿长均线时买入", "短均线跌破长均线时卖出", "严格控制单次仓位"],
        params={"short_window": 5, "long_window": 20},
    ),
    StrategyPreset(
        code="lanyue_ma_steady",
        title="岚月稳健均线",
        strategist="岚月波段交易师",
        engine="ma_cross",
        description="使用 10 日和 30 日均线过滤噪音，交易频率更低，更偏中线。",
        fit_for="主升浪跟随、慢牛结构、低频波段",
        risk_level="中低",
        tags=["双均线", "稳健", "中线"],
        hero="更适合对回撤容忍度一般、希望少做决策但保持纪律的用户。",
        philosophy="把交易次数降下来，用更长周期换更稳定的趋势确认。",
        strengths=["更稳健", "换手率较低", "更适合持有型用户"],
        warnings=["启动信号更慢", "可能错过早期加速段"],
        steps=["10 日均线上穿 30 日均线买入", "10 日均线下破 30 日均线卖出", "持仓中减少频繁调参"],
        params={"short_window": 10, "long_window": 30},
    ),
    StrategyPreset(
        code="bailu_rsi_reversal",
        title="白露超跌反弹",
        strategist="白露逆势交易师",
        engine="rsi_reversal",
        description="关注 RSI 从超卖区回升的反转信号，适合超跌修复与情绪回暖阶段。",
        fit_for="情绪冰点修复、短期技术反弹、逆势捕捉",
        risk_level="中高",
        tags=["RSI", "反转", "短线"],
        hero="更适合愿意捕捉修复性机会、接受更高噪音和更高判断门槛的用户。",
        philosophy="在极端悲观后等待资金回流，拿最先被修复的一段利润。",
        strengths=["切入点灵敏", "适合反弹交易", "和趋势策略形成互补"],
        warnings=["容易出现假反弹", "止损纪律要求更高"],
        steps=["RSI 低于超卖阈值后重新站回阈值上方买入", "RSI 从超买区回落时卖出", "避免在单边下跌中连续抄底"],
        params={"rsi_window": 14, "rsi_oversold": 30, "rsi_overbought": 70},
    ),
    StrategyPreset(
        code="chi_xiao_rsi_aggressive",
        title="赤霄动量反转",
        strategist="赤霄日内交易师",
        engine="rsi_reversal",
        description="缩短 RSI 周期并提高阈值敏感度，适合激进型用户做快速切换。",
        fit_for="高波动标的、快进快出、激进风格",
        risk_level="高",
        tags=["RSI", "激进", "高波动"],
        hero="更适合接受高频信号和更高回撤的用户，不建议重仓使用。",
        philosophy="在波动里找节奏，靠速度和纪律，不靠重仓死扛。",
        strengths=["反应更快", "更适合高波动环境", "信号密集"],
        warnings=["误触发更多", "不适合没有止损习惯的用户"],
        steps=["更短周期追踪 RSI", "出现敏感反转即执行", "更依赖仓位和风控"],
        params={"rsi_window": 9, "rsi_oversold": 25, "rsi_overbought": 75},
    ),
    StrategyPreset(
        code="poxiao_breakout_20",
        title="破晓 20 日突破",
        strategist="破晓趋势交易师",
        engine="donchian_breakout",
        description="当价格突破 20 日高点时参与趋势扩张，强调顺势、强势和纪律退出。",
        fit_for="放量突破、强趋势板块、龙头跟随",
        risk_level="中高",
        tags=["唐奇安", "突破", "趋势"],
        hero="更适合强势市场环境，面对突破后快速拉升时有较好执行体验。",
        philosophy="不在底部猜测，只在强势确认后参与，拿一段最干净的趋势。",
        strengths=["顺势清晰", "突破结构易理解", "适合热点板块"],
        warnings=["假突破风险高", "追涨时点位要求严格"],
        steps=["收盘价突破 20 日高点买入", "跌破区间低点退出", "避免在无量突破中重仓"],
        params={"breakout_window": 20},
    ),
    StrategyPreset(
        code="yuanhang_breakout_55",
        title="远航长波段突破",
        strategist="远航 CTA 交易师",
        engine="donchian_breakout",
        description="把突破周期拉长到 55 日，降低噪音和交易频率，更像大级别趋势策略。",
        fit_for="低频交易、长波段持有、耐心型用户",
        risk_level="中",
        tags=["唐奇安", "低频", "长趋势"],
        hero="更适合不想频繁盯盘、偏好趋势大段落的人群。",
        philosophy="用时间换确定性，让真正的大趋势自己展开。",
        strengths=["低频省心", "趋势过滤能力更强", "适合组合中的中枢策略"],
        warnings=["等待时间更长", "短期收益体验可能偏弱"],
        steps=["突破 55 日高点买入", "跌破 55 日低点退出", "保持耐心，不轻易中途干预"],
        params={"breakout_window": 55},
    ),
]


MARKET_BOARD = {
    "indices": [
        {"name": "上证指数", "value": "3,268.14", "change_pct": "+0.62%"},
        {"name": "深证成指", "value": "10,412.55", "change_pct": "+1.08%"},
        {"name": "创业板指", "value": "2,145.72", "change_pct": "+1.46%"},
    ],
    "gainers": [
        {"symbol": "300750", "name": "宁德时代", "price": "212.42", "change_pct": "+7.84%"},
        {"symbol": "002594", "name": "比亚迪", "price": "248.10", "change_pct": "+6.13%"},
        {"symbol": "601127", "name": "赛力斯", "price": "87.36", "change_pct": "+5.72%"},
        {"symbol": "603019", "name": "中科曙光", "price": "56.92", "change_pct": "+5.48%"},
    ],
    "losers": [
        {"symbol": "600276", "name": "恒瑞医药", "price": "44.23", "change_pct": "-3.26%"},
        {"symbol": "000333", "name": "美的集团", "price": "66.51", "change_pct": "-2.94%"},
        {"symbol": "600036", "name": "招商银行", "price": "32.80", "change_pct": "-2.41%"},
        {"symbol": "601318", "name": "中国平安", "price": "41.29", "change_pct": "-2.18%"},
    ],
}


def get_dashboard_payload(username: str | None = None) -> dict:
    user = get_user_by_username(username or "") or get_user_by_username("guest")
    if user is None:
        raise ValueError("未初始化默认用户")
    return {
        "profile": {
            "nickname": user["display_name"],
            "membership": user["membership"],
            "risk_level": user["risk_level"],
            "intro": user["intro"],
            "phone_mask": user["phone_mask"],
        },
        "summary_cards": [
            {"label": "总资产", "value": "1,286,530", "delta": "+2.14%"},
            {"label": "今日盈亏", "value": "+12,460", "delta": "+0.98%"},
            {"label": "策略数量", "value": str(len(STRATEGY_PRESETS)), "delta": "6 位交易师"},
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
        "market_board": MARKET_BOARD,
    }


def get_strategy_payload() -> list[dict]:
    return [
        {
            "code": item.code,
            "title": item.title,
            "strategist": item.strategist,
            "engine": item.engine,
            "description": item.description,
            "fit_for": item.fit_for,
            "risk_level": item.risk_level,
            "tags": item.tags,
            "hero": item.hero,
        }
        for item in STRATEGY_PRESETS
    ]


def get_strategy_preset(code: str) -> StrategyPreset:
    for item in STRATEGY_PRESETS:
        if item.code == code:
            return item
    raise ValueError(f"未找到策略: {code}")


def get_strategy_detail(code: str) -> dict:
    item = get_strategy_preset(code)
    return asdict(item)

def serialize_backtest_result(result: BacktestResult, bars: list) -> dict:
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
        "candles": [
            {
                "date": bar.date.date().isoformat(),
                "open": round(bar.open or bar.close, 2),
                "high": round(bar.high or bar.close, 2),
                "low": round(bar.low or bar.close, 2),
                "close": round(bar.close, 2),
            }
            for bar in bars[-90:]
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

    payload = serialize_backtest_result(result, bars)
    closes = [bar.close for bar in bars[-90:]]
    short_window = int(params.get("short_window", 5))
    long_window = int(params.get("long_window", 20))
    short_ma = moving_average(closes, short_window)
    long_ma = moving_average(closes, long_window)
    payload["strategy_title"] = preset.title
    payload["strategist"] = preset.strategist
    payload["symbol"] = symbol
    payload["csv_path"] = str(Path(csv_path))
    payload["moving_averages"] = {
        "short_label": f"MA{short_window}",
        "long_label": f"MA{long_window}",
        "short": [round(item, 2) if item is not None else None for item in short_ma],
        "long": [round(item, 2) if item is not None else None for item in long_ma],
    }
    return payload
