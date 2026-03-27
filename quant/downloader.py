from __future__ import annotations

from datetime import date, datetime
from pathlib import Path


DEFAULT_DOWNLOAD_DIR = Path(__file__).resolve().parent.parent / "data_downloads"


def normalize_date(value: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError("日期不能为空")
    try:
        return datetime.fromisoformat(text).strftime("%Y%m%d")
    except ValueError as exc:
        raise ValueError("日期格式必须为 YYYY-MM-DD") from exc


def default_start_date() -> str:
    today = date.today()
    return f"{today.year - 1:04d}-{today.month:02d}-{today.day:02d}"


def default_end_date() -> str:
    return date.today().isoformat()


def download_a_share_history(
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: str,
    target_dir: str | Path = DEFAULT_DOWNLOAD_DIR,
) -> Path:
    code = symbol.strip()
    if len(code) != 6 or not code.isdigit():
        raise ValueError("股票代码必须是 6 位数字，例如 000001")

    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError(
            "未安装 akshare。请先执行: python -m pip install akshare pandas"
        ) from exc

    start = normalize_date(start_date)
    end = normalize_date(end_date)
    df = ak.stock_zh_a_hist(
        symbol=code,
        period="daily",
        start_date=start,
        end_date=end,
        adjust=adjust,
    )
    if df is None or df.empty:
        raise ValueError(f"未获取到 {code} 在所选区间内的历史数据")

    required_columns = ["日期", "开盘", "最高", "最低", "收盘", "成交量"]
    missing = [name for name in required_columns if name not in df.columns]
    if missing:
        raise ValueError(f"下载结果缺少必要字段: {', '.join(missing)}")

    export_df = df.loc[:, required_columns].copy()
    export_df.columns = ["date", "open", "high", "low", "close", "volume"]
    export_df["date"] = export_df["date"].astype(str)

    output_dir = Path(target_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = adjust or "raw"
    output_path = output_dir / f"{code}_{start}_{end}_{suffix}.csv"
    export_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path
