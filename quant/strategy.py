from __future__ import annotations

from dataclasses import dataclass

from quant.data_loader import PriceBar


BUY = "BUY"
SELL = "SELL"

STRATEGY_MA_CROSS = "ma_cross"
STRATEGY_RSI_REVERSAL = "rsi_reversal"
STRATEGY_DONCHIAN_BREAKOUT = "donchian_breakout"

STRATEGY_LABELS = {
    STRATEGY_MA_CROSS: "双均线",
    STRATEGY_RSI_REVERSAL: "RSI 反转",
    STRATEGY_DONCHIAN_BREAKOUT: "唐奇安突破",
}


@dataclass(slots=True)
class StrategySignal:
    date: str
    signal: str
    price: float
    note: str


def moving_average(values: list[float], window: int) -> list[float | None]:
    if window <= 0:
        raise ValueError("均线周期必须大于 0")

    result: list[float | None] = []
    rolling_sum = 0.0
    for index, value in enumerate(values):
        rolling_sum += value
        if index >= window:
            rolling_sum -= values[index - window]

        if index + 1 < window:
            result.append(None)
        else:
            result.append(rolling_sum / window)
    return result


def rolling_high(values: list[float], window: int) -> list[float | None]:
    if window <= 1:
        raise ValueError("突破周期必须大于 1")

    result: list[float | None] = []
    for index in range(len(values)):
        if index < window:
            result.append(None)
        else:
            result.append(max(values[index - window : index]))
    return result


def rolling_low(values: list[float], window: int) -> list[float | None]:
    if window <= 1:
        raise ValueError("突破周期必须大于 1")

    result: list[float | None] = []
    for index in range(len(values)):
        if index < window:
            result.append(None)
        else:
            result.append(min(values[index - window : index]))
    return result


def compute_rsi(values: list[float], window: int) -> list[float | None]:
    if window <= 1:
        raise ValueError("RSI 周期必须大于 1")
    if len(values) < 2:
        return [None for _ in values]

    gains = [0.0]
    losses = [0.0]
    for index in range(1, len(values)):
        change = values[index] - values[index - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    avg_gain = moving_average(gains, window)
    avg_loss = moving_average(losses, window)
    rsi_values: list[float | None] = []
    for gain, loss in zip(avg_gain, avg_loss):
        if gain is None or loss is None:
            rsi_values.append(None)
        elif loss == 0:
            rsi_values.append(100.0)
        else:
            rs = gain / loss
            rsi_values.append(100 - (100 / (1 + rs)))
    return rsi_values


def generate_ma_cross_signals(
    bars: list[PriceBar], short_window: int, long_window: int
) -> list[StrategySignal]:
    if short_window >= long_window:
        raise ValueError("短均线周期必须小于长均线周期")

    closes = [bar.close for bar in bars]
    short_ma = moving_average(closes, short_window)
    long_ma = moving_average(closes, long_window)
    signals: list[StrategySignal] = []

    for index in range(1, len(bars)):
        prev_short = short_ma[index - 1]
        prev_long = long_ma[index - 1]
        curr_short = short_ma[index]
        curr_long = long_ma[index]

        if None in (prev_short, prev_long, curr_short, curr_long):
            continue

        bar = bars[index]
        if prev_short <= prev_long and curr_short > curr_long:
            signals.append(
                StrategySignal(
                    date=bar.date.date().isoformat(),
                    signal=BUY,
                    price=bar.close,
                    note=f"短均线 {curr_short:.2f} 上穿长均线 {curr_long:.2f}",
                )
            )
        elif prev_short >= prev_long and curr_short < curr_long:
            signals.append(
                StrategySignal(
                    date=bar.date.date().isoformat(),
                    signal=SELL,
                    price=bar.close,
                    note=f"短均线 {curr_short:.2f} 下破长均线 {curr_long:.2f}",
                )
            )
    return signals


def generate_rsi_reversal_signals(
    bars: list[PriceBar], rsi_window: int, oversold: float, overbought: float
) -> list[StrategySignal]:
    if oversold >= overbought:
        raise ValueError("RSI 超卖阈值必须小于超买阈值")
    if oversold <= 0 or overbought >= 100:
        raise ValueError("RSI 阈值必须落在 0 到 100 之间")

    closes = [bar.close for bar in bars]
    rsi_values = compute_rsi(closes, rsi_window)
    signals: list[StrategySignal] = []

    for index in range(1, len(bars)):
        prev_rsi = rsi_values[index - 1]
        curr_rsi = rsi_values[index]
        if prev_rsi is None or curr_rsi is None:
            continue

        bar = bars[index]
        if prev_rsi <= oversold and curr_rsi > oversold:
            signals.append(
                StrategySignal(
                    date=bar.date.date().isoformat(),
                    signal=BUY,
                    price=bar.close,
                    note=f"RSI {curr_rsi:.2f} 向上脱离超卖区",
                )
            )
        elif prev_rsi >= overbought and curr_rsi < overbought:
            signals.append(
                StrategySignal(
                    date=bar.date.date().isoformat(),
                    signal=SELL,
                    price=bar.close,
                    note=f"RSI {curr_rsi:.2f} 向下跌出超买区",
                )
            )
    return signals


def generate_donchian_breakout_signals(
    bars: list[PriceBar], breakout_window: int
) -> list[StrategySignal]:
    highs = [bar.high if bar.high > 0 else bar.close for bar in bars]
    lows = [bar.low if bar.low > 0 else bar.close for bar in bars]
    upper_band = rolling_high(highs, breakout_window)
    lower_band = rolling_low(lows, breakout_window)
    signals: list[StrategySignal] = []

    in_position = False
    for index, bar in enumerate(bars):
        upper = upper_band[index]
        lower = lower_band[index]
        if upper is None or lower is None:
            continue

        if not in_position and bar.close > upper:
            in_position = True
            signals.append(
                StrategySignal(
                    date=bar.date.date().isoformat(),
                    signal=BUY,
                    price=bar.close,
                    note=f"收盘价突破 {breakout_window} 日高点 {upper:.2f}",
                )
            )
        elif in_position and bar.close < lower:
            in_position = False
            signals.append(
                StrategySignal(
                    date=bar.date.date().isoformat(),
                    signal=SELL,
                    price=bar.close,
                    note=f"收盘价跌破 {breakout_window} 日低点 {lower:.2f}",
                )
            )
    return signals


def generate_signals(
    bars: list[PriceBar],
    strategy_name: str,
    short_window: int,
    long_window: int,
    rsi_window: int,
    rsi_oversold: float,
    rsi_overbought: float,
    breakout_window: int,
) -> list[StrategySignal]:
    if strategy_name == STRATEGY_MA_CROSS:
        return generate_ma_cross_signals(bars, short_window, long_window)
    if strategy_name == STRATEGY_RSI_REVERSAL:
        return generate_rsi_reversal_signals(bars, rsi_window, rsi_oversold, rsi_overbought)
    if strategy_name == STRATEGY_DONCHIAN_BREAKOUT:
        return generate_donchian_breakout_signals(bars, breakout_window)
    raise ValueError(f"不支持的策略: {strategy_name}")
