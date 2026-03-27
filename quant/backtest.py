from __future__ import annotations

from dataclasses import dataclass

from quant.data_loader import PriceBar
from quant.strategy import BUY, SELL, StrategySignal, generate_signals


@dataclass(slots=True)
class EquityPoint:
    date: str
    close: float
    equity: float


@dataclass(slots=True)
class TradeRecord:
    buy_date: str
    buy_price: float
    sell_date: str
    sell_price: float
    shares: int
    profit: float
    return_pct: float
    holding_days: int


@dataclass(slots=True)
class BacktestResult:
    strategy_name: str
    initial_capital: float
    ending_capital: float
    total_return_pct: float
    annualized_return_pct: float
    buy_hold_return_pct: float
    alpha_vs_hold_pct: float
    max_drawdown_pct: float
    win_rate_pct: float
    profit_factor: float
    average_holding_days: float
    trade_count: int
    signals: list[StrategySignal]
    trades: list[TradeRecord]
    equity_curve: list[EquityPoint]


def _compute_max_drawdown(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0

    peak = equity_curve[0]
    max_drawdown = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak <= 0:
            continue
        drawdown = (peak - value) / peak
        max_drawdown = max(max_drawdown, drawdown)
    return max_drawdown * 100


def _annualized_return(total_return_ratio: float, day_count: int) -> float:
    if day_count <= 0:
        return 0.0
    years = day_count / 252
    if years <= 0:
        return 0.0
    return ((1 + total_return_ratio) ** (1 / years) - 1) * 100


def _profit_factor(trades: list[TradeRecord]) -> float:
    gross_profit = sum(trade.profit for trade in trades if trade.profit > 0)
    gross_loss = abs(sum(trade.profit for trade in trades if trade.profit < 0))
    if gross_loss == 0:
        return gross_profit if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def run_backtest(
    bars: list[PriceBar],
    strategy_name: str = "ma_cross",
    short_window: int = 5,
    long_window: int = 20,
    rsi_window: int = 14,
    rsi_oversold: float = 30.0,
    rsi_overbought: float = 70.0,
    breakout_window: int = 20,
    initial_capital: float = 100000.0,
    position_ratio: float = 0.95,
) -> BacktestResult:
    if initial_capital <= 0:
        raise ValueError("初始资金必须大于 0")
    if not 0 < position_ratio <= 1:
        raise ValueError("仓位比例必须在 0 到 1 之间")
    if len(bars) < 2:
        raise ValueError("至少需要 2 条行情数据")

    signals = generate_signals(
        bars=bars,
        strategy_name=strategy_name,
        short_window=short_window,
        long_window=long_window,
        rsi_window=rsi_window,
        rsi_oversold=rsi_oversold,
        rsi_overbought=rsi_overbought,
        breakout_window=breakout_window,
    )
    signal_map = {signal.date: signal for signal in signals}

    cash = initial_capital
    shares = 0
    buy_price = 0.0
    buy_date = ""
    buy_index = -1
    trades: list[TradeRecord] = []
    equity_values: list[float] = []
    equity_curve: list[EquityPoint] = []

    for index, bar in enumerate(bars):
        signal = signal_map.get(bar.date.date().isoformat())
        if signal and signal.signal == BUY and shares == 0:
            budget = cash * position_ratio
            lot = int(budget // bar.close)
            if lot > 0:
                cash -= lot * bar.close
                shares = lot
                buy_price = bar.close
                buy_date = bar.date.date().isoformat()
                buy_index = index

        elif signal and signal.signal == SELL and shares > 0:
            proceeds = shares * bar.close
            cash += proceeds
            profit = (bar.close - buy_price) * shares
            trades.append(
                TradeRecord(
                    buy_date=buy_date,
                    buy_price=buy_price,
                    sell_date=bar.date.date().isoformat(),
                    sell_price=bar.close,
                    shares=shares,
                    profit=profit,
                    return_pct=((bar.close / buy_price) - 1) * 100,
                    holding_days=index - buy_index,
                )
            )
            shares = 0
            buy_price = 0.0
            buy_date = ""
            buy_index = -1

        equity = cash + shares * bar.close
        equity_values.append(equity)
        equity_curve.append(
            EquityPoint(
                date=bar.date.date().isoformat(),
                close=bar.close,
                equity=equity,
            )
        )

    if shares > 0:
        last_index = len(bars) - 1
        last_bar = bars[last_index]
        proceeds = shares * last_bar.close
        cash += proceeds
        profit = (last_bar.close - buy_price) * shares
        trades.append(
            TradeRecord(
                buy_date=buy_date,
                buy_price=buy_price,
                sell_date=last_bar.date.date().isoformat(),
                sell_price=last_bar.close,
                shares=shares,
                profit=profit,
                return_pct=((last_bar.close / buy_price) - 1) * 100,
                holding_days=last_index - buy_index,
            )
        )
        equity_values[-1] = cash
        equity_curve[-1] = EquityPoint(
            date=last_bar.date.date().isoformat(),
            close=last_bar.close,
            equity=cash,
        )

    wins = sum(1 for trade in trades if trade.profit > 0)
    ending_capital = cash
    total_return_ratio = (ending_capital / initial_capital) - 1
    buy_hold_return_pct = ((bars[-1].close / bars[0].close) - 1) * 100
    avg_holding_days = (
        sum(trade.holding_days for trade in trades) / len(trades) if trades else 0.0
    )

    return BacktestResult(
        strategy_name=strategy_name,
        initial_capital=initial_capital,
        ending_capital=ending_capital,
        total_return_pct=total_return_ratio * 100,
        annualized_return_pct=_annualized_return(total_return_ratio, len(bars)),
        buy_hold_return_pct=buy_hold_return_pct,
        alpha_vs_hold_pct=total_return_ratio * 100 - buy_hold_return_pct,
        max_drawdown_pct=_compute_max_drawdown(equity_values),
        win_rate_pct=(wins / len(trades) * 100) if trades else 0.0,
        profit_factor=_profit_factor(trades),
        average_holding_days=avg_holding_days,
        trade_count=len(trades),
        signals=signals,
        trades=trades,
        equity_curve=equity_curve,
    )
