from __future__ import annotations

import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from quant.backtest import BacktestResult, run_backtest
from quant.data_loader import load_price_data
from quant.downloader import default_end_date, default_start_date, download_a_share_history
from quant.strategy import (
    STRATEGY_DONCHIAN_BREAKOUT,
    STRATEGY_LABELS,
    STRATEGY_MA_CROSS,
    STRATEGY_RSI_REVERSAL,
)


DEFAULT_DATA = Path(__file__).resolve().parent.parent / "sample_data" / "demo_stock.csv"


class QuantApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("个人量化交易股票小程序")
        self.root.geometry("1080x760")

        self.file_path = tk.StringVar(value=str(DEFAULT_DATA))
        self.download_symbol = tk.StringVar(value="000001")
        self.download_start = tk.StringVar(value=default_start_date())
        self.download_end = tk.StringVar(value=default_end_date())
        self.adjust = tk.StringVar(value="前复权")
        self.strategy_label = tk.StringVar(value=STRATEGY_LABELS[STRATEGY_MA_CROSS])
        self.short_window = tk.StringVar(value="5")
        self.long_window = tk.StringVar(value="20")
        self.rsi_window = tk.StringVar(value="14")
        self.rsi_oversold = tk.StringVar(value="30")
        self.rsi_overbought = tk.StringVar(value="70")
        self.breakout_window = tk.StringVar(value="20")
        self.initial_capital = tk.StringVar(value="100000")
        self.position_ratio = tk.StringVar(value="0.95")

        self.summary_text = tk.StringVar(value="请选择数据文件并设置参数后运行回测。")
        self._build_layout()
        self._toggle_parameter_groups()

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        download_form = ttk.LabelFrame(container, text="A 股历史数据下载", padding=12)
        download_form.pack(fill=tk.X)

        ttk.Label(download_form, text="股票代码").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(download_form, textvariable=self.download_symbol, width=14).grid(
            row=0, column=1, sticky="w", padx=8, pady=6
        )
        ttk.Label(download_form, text="开始日期").grid(row=0, column=2, sticky="w", pady=6)
        ttk.Entry(download_form, textvariable=self.download_start, width=14).grid(
            row=0, column=3, sticky="w", padx=8, pady=6
        )
        ttk.Label(download_form, text="结束日期").grid(row=0, column=4, sticky="w", pady=6)
        ttk.Entry(download_form, textvariable=self.download_end, width=14).grid(
            row=0, column=5, sticky="w", padx=8, pady=6
        )
        ttk.Label(download_form, text="复权").grid(row=0, column=6, sticky="w", pady=6)
        ttk.Combobox(
            download_form,
            state="readonly",
            textvariable=self.adjust,
            values=["不复权", "前复权", "后复权"],
            width=10,
        ).grid(row=0, column=7, sticky="w", padx=8, pady=6)
        ttk.Button(download_form, text="下载并填入", command=self.download_data).grid(
            row=0, column=8, sticky="ew", padx=(12, 0), pady=6
        )

        form = ttk.LabelFrame(container, text="回测参数", padding=12)
        form.pack(fill=tk.X, pady=(12, 0))

        ttk.Label(form, text="CSV 文件").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.file_path, width=78).grid(
            row=0, column=1, columnspan=3, sticky="ew", padx=8, pady=6
        )
        ttk.Button(form, text="浏览", command=self.choose_file).grid(row=0, column=4, pady=6)

        ttk.Label(form, text="策略").grid(row=1, column=0, sticky="w", pady=6)
        self.strategy_combo = ttk.Combobox(
            form,
            state="readonly",
            textvariable=self.strategy_label,
            values=[STRATEGY_LABELS[key] for key in STRATEGY_LABELS],
            width=16,
        )
        self.strategy_combo.grid(row=1, column=1, sticky="w", padx=8, pady=6)
        self.strategy_combo.bind("<<ComboboxSelected>>", lambda _event: self._toggle_parameter_groups())

        ttk.Label(form, text="初始资金").grid(row=1, column=2, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.initial_capital, width=18).grid(
            row=1, column=3, sticky="w", padx=8, pady=6
        )

        ttk.Label(form, text="仓位比例").grid(row=1, column=4, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.position_ratio, width=12).grid(
            row=1, column=5, sticky="w", padx=8, pady=6
        )

        self.ma_frame = ttk.LabelFrame(form, text="双均线参数", padding=10)
        self.ma_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 6))
        ttk.Label(self.ma_frame, text="短均线").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(self.ma_frame, textvariable=self.short_window, width=10).grid(
            row=0, column=1, sticky="w", padx=8, pady=4
        )
        ttk.Label(self.ma_frame, text="长均线").grid(row=0, column=2, sticky="w", pady=4)
        ttk.Entry(self.ma_frame, textvariable=self.long_window, width=10).grid(
            row=0, column=3, sticky="w", padx=8, pady=4
        )

        self.rsi_frame = ttk.LabelFrame(form, text="RSI 参数", padding=10)
        self.rsi_frame.grid(row=2, column=3, columnspan=3, sticky="ew", pady=(8, 6), padx=(10, 0))
        ttk.Label(self.rsi_frame, text="RSI 周期").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(self.rsi_frame, textvariable=self.rsi_window, width=10).grid(
            row=0, column=1, sticky="w", padx=8, pady=4
        )
        ttk.Label(self.rsi_frame, text="超卖").grid(row=0, column=2, sticky="w", pady=4)
        ttk.Entry(self.rsi_frame, textvariable=self.rsi_oversold, width=10).grid(
            row=0, column=3, sticky="w", padx=8, pady=4
        )
        ttk.Label(self.rsi_frame, text="超买").grid(row=0, column=4, sticky="w", pady=4)
        ttk.Entry(self.rsi_frame, textvariable=self.rsi_overbought, width=10).grid(
            row=0, column=5, sticky="w", padx=8, pady=4
        )

        self.breakout_frame = ttk.LabelFrame(form, text="突破参数", padding=10)
        self.breakout_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        ttk.Label(self.breakout_frame, text="突破周期").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(self.breakout_frame, textvariable=self.breakout_window, width=10).grid(
            row=0, column=1, sticky="w", padx=8, pady=4
        )

        ttk.Button(form, text="运行回测", command=self.run).grid(
            row=4, column=0, columnspan=6, sticky="ew", pady=(12, 0)
        )
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        summary = ttk.LabelFrame(container, text="结果概览", padding=12)
        summary.pack(fill=tk.X, pady=(12, 0))
        ttk.Label(summary, textvariable=self.summary_text, justify=tk.LEFT).pack(anchor="w")

        notebook = ttk.Notebook(container)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        signals_frame = ttk.Frame(notebook, padding=10)
        trades_frame = ttk.Frame(notebook, padding=10)
        chart_frame = ttk.Frame(notebook, padding=10)
        notebook.add(signals_frame, text="交易信号")
        notebook.add(trades_frame, text="成交记录")
        notebook.add(chart_frame, text="图表分析")

        self.signals_box = tk.Text(signals_frame, wrap=tk.NONE, height=18)
        self.signals_box.pack(fill=tk.BOTH, expand=True)

        self.trades_box = tk.Text(trades_frame, wrap=tk.NONE, height=18)
        self.trades_box.pack(fill=tk.BOTH, expand=True)

        self.chart_canvas = tk.Canvas(chart_frame, bg="#ffffff", highlightthickness=0)
        self.chart_canvas.pack(fill=tk.BOTH, expand=True)
        self.chart_canvas.bind("<Configure>", lambda _event: self.redraw_chart())

        self._latest_result: BacktestResult | None = None

    def _strategy_key(self) -> str:
        for key, label in STRATEGY_LABELS.items():
            if label == self.strategy_label.get():
                return key
        return STRATEGY_MA_CROSS

    def _toggle_parameter_groups(self) -> None:
        strategy_key = self._strategy_key()
        self.ma_frame.grid_remove()
        self.rsi_frame.grid_remove()
        self.breakout_frame.grid_remove()

        if strategy_key == STRATEGY_MA_CROSS:
            self.ma_frame.grid(row=2, column=0, columnspan=6, sticky="ew", pady=(8, 6))
        elif strategy_key == STRATEGY_RSI_REVERSAL:
            self.rsi_frame.grid(row=2, column=0, columnspan=6, sticky="ew", pady=(8, 6))
        elif strategy_key == STRATEGY_DONCHIAN_BREAKOUT:
            self.breakout_frame.grid(row=2, column=0, columnspan=6, sticky="ew", pady=(8, 6))

    def choose_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="选择股票历史数据 CSV",
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")],
        )
        if selected:
            self.file_path.set(selected)

    def _adjust_key(self) -> str:
        mapping = {
            "不复权": "",
            "前复权": "qfq",
            "后复权": "hfq",
        }
        return mapping.get(self.adjust.get(), "qfq")

    def download_data(self) -> None:
        try:
            output_path = download_a_share_history(
                symbol=self.download_symbol.get(),
                start_date=self.download_start.get(),
                end_date=self.download_end.get(),
                adjust=self._adjust_key(),
            )
        except Exception as exc:
            messagebox.showerror("下载失败", str(exc))
            return

        self.file_path.set(str(output_path))
        messagebox.showinfo("下载完成", f"数据已保存到:\n{output_path}")

    def run(self) -> None:
        try:
            bars = load_price_data(self.file_path.get())
            result = run_backtest(
                bars=bars,
                strategy_name=self._strategy_key(),
                short_window=int(self.short_window.get()),
                long_window=int(self.long_window.get()),
                rsi_window=int(self.rsi_window.get()),
                rsi_oversold=float(self.rsi_oversold.get()),
                rsi_overbought=float(self.rsi_overbought.get()),
                breakout_window=int(self.breakout_window.get()),
                initial_capital=float(self.initial_capital.get()),
                position_ratio=float(self.position_ratio.get()),
            )
        except Exception as exc:
            messagebox.showerror("运行失败", str(exc))
            return

        self.render_result(result)

    def render_result(self, result: BacktestResult) -> None:
        self._latest_result = result
        strategy_display = STRATEGY_LABELS.get(result.strategy_name, result.strategy_name)
        self.summary_text.set(
            "\n".join(
                [
                    f"策略: {strategy_display}",
                    f"初始资金: {result.initial_capital:,.2f}",
                    f"结束资金: {result.ending_capital:,.2f}",
                    f"总收益率: {result.total_return_pct:.2f}%",
                    f"年化收益率: {result.annualized_return_pct:.2f}%",
                    f"买入持有收益率: {result.buy_hold_return_pct:.2f}%",
                    f"超额收益: {result.alpha_vs_hold_pct:.2f}%",
                    f"最大回撤: {result.max_drawdown_pct:.2f}%",
                    f"交易次数: {result.trade_count}",
                    f"胜率: {result.win_rate_pct:.2f}%",
                    f"盈亏比: {result.profit_factor:.2f}",
                    f"平均持仓天数: {result.average_holding_days:.1f}",
                ]
            )
        )

        self.signals_box.delete("1.0", tk.END)
        self.trades_box.delete("1.0", tk.END)

        if result.signals:
            signal_lines = [
                "日期\t信号\t价格\t说明",
                *[
                    f"{item.date}\t{item.signal}\t{item.price:.2f}\t{item.note}"
                    for item in result.signals
                ],
            ]
            self.signals_box.insert(tk.END, "\n".join(signal_lines))
        else:
            self.signals_box.insert(tk.END, "没有生成交易信号。")

        if result.trades:
            trade_lines = [
                "买入日\t买入价\t卖出日\t卖出价\t股数\t盈亏\t收益率\t持仓天数",
                *[
                    f"{item.buy_date}\t{item.buy_price:.2f}\t{item.sell_date}\t"
                    f"{item.sell_price:.2f}\t{item.shares}\t{item.profit:.2f}\t"
                    f"{item.return_pct:.2f}%\t{item.holding_days}"
                    for item in result.trades
                ],
            ]
            self.trades_box.insert(tk.END, "\n".join(trade_lines))
        else:
            self.trades_box.insert(tk.END, "没有成交记录。")

        self.redraw_chart()

    def redraw_chart(self) -> None:
        self.chart_canvas.delete("all")
        if not self._latest_result or not self._latest_result.equity_curve:
            self.chart_canvas.create_text(
                24,
                24,
                anchor="nw",
                text="运行回测后，这里会显示价格走势、买卖点和资金曲线。",
                fill="#4b5563",
                font=("Microsoft YaHei UI", 11),
            )
            return

        width = max(self.chart_canvas.winfo_width(), 900)
        height = max(self.chart_canvas.winfo_height(), 520)
        self.chart_canvas.configure(scrollregion=(0, 0, width, height))

        left = 72
        right = width - 32
        top = 40
        middle = height // 2
        bottom = height - 48
        gap = 36
        price_bottom = middle - gap
        equity_top = middle + gap

        result = self._latest_result
        points = result.equity_curve
        closes = [item.close for item in points]
        equities = [item.equity for item in points]
        dates = [item.date for item in points]

        self._draw_series_panel(
            left=left,
            top=top,
            right=right,
            bottom=price_bottom,
            values=closes,
            color="#2563eb",
            title="价格走势",
            y_label="收盘价",
            dates=dates,
            signal_points=result.signals,
            mode="price",
        )
        self._draw_series_panel(
            left=left,
            top=equity_top,
            right=right,
            bottom=bottom,
            values=equities,
            color="#059669",
            title="资金曲线",
            y_label="资金",
            dates=dates,
            signal_points=[],
            mode="equity",
        )

    def _draw_series_panel(
        self,
        left: int,
        top: int,
        right: int,
        bottom: int,
        values: list[float],
        color: str,
        title: str,
        y_label: str,
        dates: list[str],
        signal_points: list,
        mode: str,
    ) -> None:
        canvas = self.chart_canvas
        canvas.create_rectangle(left, top, right, bottom, outline="#d1d5db", width=1)
        canvas.create_text(
            left,
            top - 18,
            anchor="w",
            text=title,
            fill="#111827",
            font=("Microsoft YaHei UI", 12, "bold"),
        )
        canvas.create_text(
            left - 48,
            (top + bottom) / 2,
            angle=90,
            text=y_label,
            fill="#6b7280",
            font=("Microsoft YaHei UI", 10),
        )

        if not values:
            return

        min_value = min(values)
        max_value = max(values)
        if max_value == min_value:
            max_value += 1
            min_value -= 1

        for ratio in (0.0, 0.5, 1.0):
            y = bottom - (bottom - top) * ratio
            value = min_value + (max_value - min_value) * ratio
            canvas.create_line(left, y, right, y, fill="#eef2f7", width=1)
            canvas.create_text(
                left - 8,
                y,
                anchor="e",
                text=f"{value:.2f}",
                fill="#6b7280",
                font=("Consolas", 9),
            )

        x_step = (right - left) / max(len(values) - 1, 1)
        coords: list[float] = []
        point_lookup: dict[str, tuple[float, float]] = {}
        for index, value in enumerate(values):
            x = left + index * x_step
            y = bottom - ((value - min_value) / (max_value - min_value)) * (bottom - top)
            coords.extend([x, y])
            point_lookup[dates[index]] = (x, y)

        if len(coords) >= 4:
            canvas.create_line(*coords, fill=color, width=2, smooth=True)

        canvas.create_text(
            left,
            bottom + 18,
            anchor="w",
            text=dates[0],
            fill="#6b7280",
            font=("Consolas", 9),
        )
        canvas.create_text(
            right,
            bottom + 18,
            anchor="e",
            text=dates[-1],
            fill="#6b7280",
            font=("Consolas", 9),
        )

        if mode == "price":
            for signal in signal_points:
                point = point_lookup.get(signal.date)
                if not point:
                    continue
                x, y = point
                signal_color = "#dc2626" if signal.signal == "SELL" else "#16a34a"
                marker = "v" if signal.signal == "SELL" else "^"
                canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=signal_color, outline="")
                canvas.create_text(
                    x,
                    y - 12 if signal.signal == "BUY" else y + 12,
                    text=marker,
                    fill=signal_color,
                    font=("Consolas", 10, "bold"),
                )


def launch_app() -> None:
    root = tk.Tk()
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    app = QuantApp(root)
    app.root.mainloop()
