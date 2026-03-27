# 个人量化交易股票小程序

这是一个轻量级的本地股票量化小程序，适合个人学习、研究和回测使用。

当前版本支持：

- 通过股票代码下载真实 A 股历史数据 CSV
- 导入本地股票历史数据 CSV
- 支持双均线、RSI 反转、唐奇安突破三种策略
- 进行简单回测并输出收益、胜率、最大回撤、年化收益、超额收益、盈亏比
- 用本地图形界面查看结果、交易信号、成交记录与图表分析

## 运行环境

- Python 3.10+
- 图形回测默认只依赖标准库
- 若需下载真实 A 股历史数据，需要安装：

```bash
python -m pip install akshare pandas
```

## 启动方式

```bash
python app.py
```

## 手机版 Web 端

如果你要做成适配手机的版本，当前仓库已经新增一套响应式 Web 应用：

- 入口文件：`web_app.py`
- 后端目录：`mobile_web/`
- 支持模块：行情榜单、涨跌分区、策略详情页、注册登录、我的页面、移动端回测

启动方式：

```bash
python web_app.py
```

启动后访问：

```text
http://127.0.0.1:8000
```

体验账号：

```text
momo / momo123
guest / guest123
```

数据持久化：

- 用户注册和登录信息会写入本地 SQLite 数据库 `momo_quant.db`
- 线上正式环境可通过 `DATABASE_URL` 切换到 PostgreSQL

示例：

```bash
DATABASE_URL=postgresql://user:password@host:5432/momo_quant
```

当前还支持：

- 持久化保存“我的自选”
- 持久化保存“我的策略收藏”
- K 线图周期切换、均线叠加、买卖点标记
- K 线图缩放、拖动、十字线与成交量面板

建议安装依赖：

```bash
python -m pip install -r requirements.txt
```

## GitHub 与线上部署

如果要让手机通过公网访问，推荐流程是：

1. 代码推送到 GitHub
2. 使用 Render 等平台连接 GitHub 仓库
3. 平台按 `render.yaml` 自动安装依赖并启动 `web_app.py`

仓库中已添加：

- `.gitignore`
- `render.yaml`

这样推送后可以直接用于 Render 部署。

如果你在 Windows 上想直接双击运行，也可以使用：

```bash
start.bat
```

命令行回测方式：

```bash
python app.py --cli --file sample_data/demo_stock.csv --short 5 --long 20 --capital 100000 --position 0.95
```

## CSV 数据格式

程序支持以下表头：

```csv
date,open,high,low,close,volume
2025-01-02,10.12,10.50,9.98,10.33,123456
2025-01-03,10.35,10.60,10.20,10.55,118000
```

要求：

- `date` 为日期
- `close` 为收盘价
- 其余列可选，但建议保留
- 日期按从早到晚排序，若未排序程序会自动排序

## 功能说明

默认策略为：

- 短期均线向上突破长期均线时买入
- 短期均线向下跌破长期均线时卖出
- RSI 策略在脱离超卖区时买入，跌出超买区时卖出
- 唐奇安策略在突破区间高点时买入，跌破区间低点时卖出
- 可在界面中修改不同策略参数、初始资金、单次仓位比例

图表分析页支持：

- 价格走势折线
- 买卖点标记
- 资金曲线

## 示例数据

仓库内提供了一个示例文件：

- `sample_data/demo_stock.csv`

你可以先用它体验，再替换成自己的股票历史数据。

## 下载真实 A 股数据

图形界面顶部新增了“A 股历史数据下载”区域，可输入：

- 6 位股票代码，例如 `000001`
- 开始日期，例如 `2025-01-01`
- 结束日期，例如 `2026-03-27`
- 复权方式：不复权、前复权、后复权

点击“下载并填入”后，程序会把 CSV 保存到：

- `data_downloads/`

也可以用命令行下载并回测：

```bash
python app.py --cli --download-symbol 000001 --start-date 2025-01-01 --end-date 2026-03-27 --adjust qfq --strategy ma_cross
```

## 免责声明

本项目仅用于学习和研究，不构成投资建议，也不建议直接接入真实资金后未经验证地自动交易。
