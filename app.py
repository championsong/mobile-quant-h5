from __future__ import annotations

import argparse

from quant.backtest import run_backtest
from quant.data_loader import load_price_data
from quant.downloader import default_end_date, default_start_date, download_a_share_history
from quant.gui import launch_app
from quant.strategy import STRATEGY_MA_CROSS


def main() -> None:
    parser = argparse.ArgumentParser(description="个人量化交易股票小程序")
    parser.add_argument("--cli", action="store_true", help="使用命令行模式运行回测")
    parser.add_argument("--file", help="股票历史数据 CSV 路径")
    parser.add_argument("--download-symbol", help="先下载 A 股历史数据再回测")
    parser.add_argument("--start-date", default=default_start_date(), help="下载开始日期 YYYY-MM-DD")
    parser.add_argument("--end-date", default=default_end_date(), help="下载结束日期 YYYY-MM-DD")
    parser.add_argument("--adjust", default="", help="复权方式: 空字符串、qfq、hfq")
    parser.add_argument("--download-only", action="store_true", help="只下载数据，不执行回测")
    parser.add_argument("--strategy", default=STRATEGY_MA_CROSS, help="策略名")
    parser.add_argument("--short", type=int, default=5, help="短均线周期")
    parser.add_argument("--long", type=int, default=20, help="长均线周期")
    parser.add_argument("--rsi-window", type=int, default=14, help="RSI 周期")
    parser.add_argument("--rsi-oversold", type=float, default=30.0, help="RSI 超卖阈值")
    parser.add_argument("--rsi-overbought", type=float, default=70.0, help="RSI 超买阈值")
    parser.add_argument("--breakout-window", type=int, default=20, help="突破周期")
    parser.add_argument("--capital", type=float, default=100000.0, help="初始资金")
    parser.add_argument("--position", type=float, default=0.95, help="仓位比例")
    args = parser.parse_args()

    if not args.cli:
        launch_app()
        return

    data_file = args.file
    if args.download_symbol:
        data_file = str(
            download_a_share_history(
                symbol=args.download_symbol,
                start_date=args.start_date,
                end_date=args.end_date,
                adjust=args.adjust,
            )
        )
        print(f"已下载数据到: {data_file}")
        if args.download_only:
            return

    if not data_file:
        parser.error("命令行模式下必须提供 --file，或使用 --download-symbol")

    bars = load_price_data(data_file)
    result = run_backtest(
        bars=bars,
        strategy_name=args.strategy,
        short_window=args.short,
        long_window=args.long,
        rsi_window=args.rsi_window,
        rsi_oversold=args.rsi_oversold,
        rsi_overbought=args.rsi_overbought,
        breakout_window=args.breakout_window,
        initial_capital=args.capital,
        position_ratio=args.position,
    )

    print("=== 回测结果 ===")
    print(f"策略: {result.strategy_name}")
    print(f"初始资金: {result.initial_capital:,.2f}")
    print(f"结束资金: {result.ending_capital:,.2f}")
    print(f"总收益率: {result.total_return_pct:.2f}%")
    print(f"年化收益率: {result.annualized_return_pct:.2f}%")
    print(f"买入持有收益率: {result.buy_hold_return_pct:.2f}%")
    print(f"超额收益: {result.alpha_vs_hold_pct:.2f}%")
    print(f"最大回撤: {result.max_drawdown_pct:.2f}%")
    print(f"交易次数: {result.trade_count}")
    print(f"胜率: {result.win_rate_pct:.2f}%")
    print(f"盈亏比: {result.profit_factor:.2f}")
    print(f"平均持仓天数: {result.average_holding_days:.1f}")
    print()
    print("=== 最近信号 ===")
    for signal in result.signals[-10:]:
        print(f"{signal.date} {signal.signal} price={signal.price:.2f} note={signal.note}")


if __name__ == "__main__":
    main()
