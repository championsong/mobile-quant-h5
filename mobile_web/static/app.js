const state = {
  auth: null,
  dashboard: null,
  liveMarket: null,
  strategies: [],
  activeStrategy: "beichen_ma_fast",
  strategyDetail: null,
  boardMode: "gainers",
  candlePeriod: 20,
  candleOffset: 0,
  indicatorMode: "macd",
  activeChart: "candles",
  authMode: "login",
  lastCandles: [],
  lastCurve: [],
  lastSignals: [],
  movingAverages: null,
  indicators: null,
  favorites: [],
  watchlist: [],
  orders: [],
  conditionalOrders: [],
  riskProfile: null,
  crosshairIndex: null,
  crosshairLocked: false,
  isDraggingChart: false,
  dragStartX: 0,
  dragOffsetSnapshot: 0,
  touchMode: null,
  pinchDistance: 0,
  pinchPeriodSnapshot: 20,
};

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...options,
  });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(payload.message || "请求失败");
  }
  return payload;
}

function switchScreen(screenId) {
  document.querySelectorAll(".screen").forEach((screen) => {
    screen.classList.toggle("active", screen.id === screenId);
  });
  document.querySelectorAll(".tabbar-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.screen === screenId);
  });
}

function renderAuth() {
  const entry = document.getElementById("auth-entry");
  entry.textContent = state.auth?.is_authenticated ? "退出" : "登录";
}

function renderDashboard(data) {
  state.dashboard = data;
  state.watchlist = data.watchlist || [];

  const totalAsset = data.summary_cards[0];
  const dailyPnl = data.summary_cards[1];
  document.getElementById("hero-total-asset").textContent = totalAsset?.value || "--";
  document.getElementById("hero-delta").textContent = dailyPnl?.delta || "--";
  document.getElementById("risk-level-text").textContent = data.profile.risk_level;
  document.getElementById("broker-count-text").textContent =
    `${data.brokers.filter((item) => item.status === "ready").length}/${data.brokers.length}`;
  document.getElementById("strategy-count-text").textContent = `${state.strategies.length}`;
  document.getElementById("phone-mask-text").textContent = data.profile.phone_mask;

  document.getElementById("account-profile").innerHTML = `
    <h3 class="profile-title">${data.profile.nickname}</h3>
    <p class="profile-sub">${data.profile.membership} · ${data.profile.risk_level}</p>
    <p class="profile-sub">${data.profile.intro}</p>
  `;

  document.getElementById("summary-cards").innerHTML = data.summary_cards.map((item) => `
    <article class="metric-card">
      <p>${item.label}</p>
      <div class="value">${item.value}</div>
      <div class="delta">${item.delta}</div>
    </article>
  `).join("");

  document.getElementById("positions").innerHTML = data.positions.map((item) => `
    <article class="position-card">
      <strong>${item.symbol} ${item.name}</strong>
      <p class="helper-text">仓位 ${item.weight}</p>
      <p class="${String(item.pnl).startsWith("-") ? "negative" : "positive"}">${item.pnl}</p>
    </article>
  `).join("");

  document.getElementById("watchlist").innerHTML = state.watchlist.map((item) => `
    <li>${item.symbol} ${item.name}</li>
  `).join("");

  document.getElementById("broker-list").innerHTML = data.brokers.map((item) => `
    <article class="broker-card">
      <div class="meta-row">
        <strong>${item.name}</strong>
        <span class="broker-status ${item.status === "ready" ? "broker-status--ready" : ""}">
          ${item.status === "ready" ? "已就绪" : "待配置"}
        </span>
      </div>
      <p class="helper-text">${item.description}</p>
      <div class="chip-row">${item.features.map((feature) => `<span>${feature}</span>`).join("")}</div>
    </article>
  `).join("");

  renderMarketBoard();
  renderProfessionalMarket(data.pro_market);
  renderFavorites();
}

function renderProfessionalMarket(data) {
  if (!data) {
    return;
  }
  state.liveMarket = data;
  const lastPrice = data.last_price ?? data.minute_series?.at(-1)?.price ?? "--";
  const changeClass = String(data.change_pct || "").startsWith("-") ? "negative" : "positive";
  document.getElementById("market-hero").innerHTML = `
    <div>
      <strong>${data.active_symbol} ${data.active_name}</strong>
      <p class="helper-text">分时走势、五档盘口与逐笔成交</p>
    </div>
    <div>
      <div class="${changeClass}">${lastPrice}</div>
      <p class="helper-text">${data.change_pct || "--"} · 成交额 ${data.turnover ?? "--"} 亿</p>
    </div>
  `;

  document.getElementById("order-book").innerHTML = [
    ...(data.order_book?.asks || []),
    ...(data.order_book?.bids || []),
  ].map((item) => `
    <div class="book-row">
      <span>${item.level}</span>
      <strong>${item.price}</strong>
      <span>${item.volume}</span>
    </div>
  `).join("");

  document.getElementById("tick-list").innerHTML = (data.ticks || []).map((item) => `
    <div class="tick-row">
      <span>${item.time}</span>
      <strong>${item.price}</strong>
      <span class="${String(item.side).includes("卖") ? "negative" : "positive"}">${item.side}</span>
    </div>
  `).join("");

  document.getElementById("sector-list").innerHTML = (data.sectors || []).map((item) => `
    <article class="mini-card">
      <strong>${item.name}</strong>
      <p class="helper-text">龙头 ${item.leader}</p>
      <p class="${String(item.change_pct).startsWith("-") ? "negative" : "positive"}">${item.change_pct}</p>
    </article>
  `).join("");

  drawMinuteChart(data.minute_series || []);
}

function renderMarketBoard() {
  if (!state.dashboard) {
    return;
  }
  const board = state.dashboard.market_board;
  document.getElementById("index-strip").innerHTML = board.indices.map((item) => `
    <article class="index-card">
      <strong>${item.name}</strong>
      <p>${item.value}</p>
      <span class="${String(item.change_pct).startsWith("-") ? "negative" : "positive"}">${item.change_pct}</span>
    </article>
  `).join("");

  const items = board[state.boardMode] || [];
  document.getElementById("leaderboard").innerHTML = items.map((item, index) => `
    <article class="leader-row">
      <div class="rank">${index + 1}</div>
      <div class="leader-main">
        <strong>${item.name}</strong>
        <p>${item.symbol}</p>
      </div>
      <div class="leader-side">
        <strong>${item.price}</strong>
        <p class="${String(item.change_pct).startsWith("-") ? "negative" : "positive"}">${item.change_pct}</p>
      </div>
      <button class="mini-action" type="button" data-watch-symbol="${item.symbol}" data-watch-name="${item.name}">加自选</button>
    </article>
  `).join("");

  document.querySelectorAll("[data-watch-symbol]").forEach((button) => {
    button.addEventListener("click", async () => {
      const payload = await fetchJson("/api/me/watchlist", {
        method: "POST",
        body: JSON.stringify({
          symbol: button.dataset.watchSymbol,
          name: button.dataset.watchName,
        }),
      });
      state.watchlist = payload.items || [];
      document.getElementById("watchlist").innerHTML = state.watchlist.map((item) => `
        <li>${item.symbol} ${item.name}</li>
      `).join("");
    });
  });
}

function renderSelectedStrategy() {
  const strategy = state.strategies.find((item) => item.code === state.activeStrategy);
  const target = document.getElementById("selected-strategy");
  if (!strategy) {
    target.innerHTML = "<p class='helper-text'>请选择一个策略。</p>";
    return;
  }
  document.getElementById("strategy-code").value = strategy.code;
  target.innerHTML = `
    <div class="meta-row">
      <div>
        <strong>${strategy.title}</strong>
        <div class="helper-text">${strategy.strategist}</div>
      </div>
      <span class="risk-badge">${strategy.risk_level}风险</span>
    </div>
    <p class="helper-text">${strategy.hero || strategy.description}</p>
    <div class="chip-row">${strategy.tags.map((tag) => `<span>${tag}</span>`).join("")}</div>
    <button class="mini-action" type="button" id="favorite-current">
      ${state.favorites.includes(strategy.code) ? "取消收藏" : "收藏策略"}
    </button>
  `;
  document.getElementById("favorite-current").addEventListener("click", () => toggleFavorite(strategy.code));
}

async function loadStrategyDetail(code) {
  const detail = await fetchJson(`/api/strategies/${code}`);
  state.strategyDetail = detail;
  document.getElementById("detail-title").textContent = detail.title;
  document.getElementById("detail-risk").textContent = `${detail.risk_level}风险`;
  document.getElementById("strategy-detail").innerHTML = `
    <article class="detail-hero">
      <strong>${detail.strategist}</strong>
      <p>${detail.hero}</p>
    </article>
    <div class="detail-group">
      <h4>策略介绍</h4>
      <p>${detail.description}</p>
      <p class="helper-text">适用场景：${detail.fit_for}</p>
      <p class="helper-text">交易哲学：${detail.philosophy}</p>
    </div>
    <div class="detail-group">
      <h4>策略优势</h4>
      <ul>${detail.strengths.map((item) => `<li>${item}</li>`).join("")}</ul>
    </div>
    <div class="detail-group">
      <h4>风险提示</h4>
      <ul>${detail.warnings.map((item) => `<li>${item}</li>`).join("")}</ul>
    </div>
    <div class="detail-group">
      <h4>执行步骤</h4>
      <ol>${detail.steps.map((item) => `<li>${item}</li>`).join("")}</ol>
    </div>
    <div class="chip-row">${detail.tags.map((tag) => `<span>${tag}</span>`).join("")}</div>
  `;
}

function renderStrategies(items) {
  state.strategies = items;
  document.getElementById("strategy-count-text").textContent = `${items.length}`;
  document.getElementById("strategy-list").innerHTML = items.map((item) => `
    <article class="strategy-card ${item.code === state.activeStrategy ? "active" : ""}" data-code="${item.code}">
      <div class="meta-row">
        <div>
          <strong>${item.title}</strong>
          <div class="helper-text">${item.strategist}</div>
        </div>
        <span class="risk-badge">${item.risk_level}风险</span>
      </div>
      <p class="helper-text">${item.description}</p>
      <p class="helper-text">适用场景：${item.fit_for}</p>
      <div class="chip-row">${item.tags.map((tag) => `<span>${tag}</span>`).join("")}</div>
      <button class="mini-action" type="button" data-favorite-code="${item.code}">
        ${state.favorites.includes(item.code) ? "已收藏" : "收藏"}
      </button>
    </article>
  `).join("");

  document.querySelectorAll(".strategy-card").forEach((card) => {
    card.addEventListener("click", async () => {
      state.activeStrategy = card.dataset.code;
      renderStrategies(state.strategies);
      renderSelectedStrategy();
      await loadStrategyDetail(state.activeStrategy);
    });
  });

  document.querySelectorAll("[data-favorite-code]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.stopPropagation();
      await toggleFavorite(button.dataset.favoriteCode);
    });
  });

  renderSelectedStrategy();
}

function renderFavorites() {
  const favorites = state.favorites
    .map((code) => state.strategies.find((item) => item.code === code))
    .filter(Boolean);
  document.getElementById("favorite-list").innerHTML = favorites.length
    ? favorites.map((item) => `
      <article class="mini-card">
        <strong>${item.title}</strong>
        <p class="helper-text">${item.strategist}</p>
      </article>
    `).join("")
    : "<p class='helper-text'>还没有收藏的策略。</p>";
}

async function toggleFavorite(strategyCode) {
  const exists = state.favorites.includes(strategyCode);
  const payload = await fetchJson(
    exists ? `/api/me/favorites/${strategyCode}` : "/api/me/favorites",
    exists
      ? { method: "DELETE" }
      : { method: "POST", body: JSON.stringify({ strategy_code: strategyCode }) },
  );
  state.favorites = payload.items || [];
  renderStrategies(state.strategies);
  renderFavorites();
}

function renderOrders() {
  document.getElementById("order-list").innerHTML = state.orders.length
    ? state.orders.map((item) => `
      <article class="terminal-row">
        <strong>${item.symbol} · ${item.side === "buy" ? "买入" : "卖出"} · ${item.quantity}股</strong>
        <div class="terminal-meta">
          <span>${item.order_type === "market" ? "市价" : "限价"}</span>
          <span>价格 ${item.price}</span>
          <span>状态 ${item.status}</span>
        </div>
        <p class="helper-text">${item.note || "无备注"}</p>
      </article>
    `).join("")
    : "<p class='helper-text'>暂无委托记录。</p>";
}

function renderConditionalOrders() {
  const triggerLabels = {
    breakout_up: "向上突破",
    breakout_down: "向下跌破",
    stop_loss: "止损触发",
    take_profit: "止盈触发",
  };
  document.getElementById("conditional-list").innerHTML = state.conditionalOrders.length
    ? state.conditionalOrders.map((item) => `
      <article class="terminal-row">
        <strong>${item.symbol} · ${triggerLabels[item.trigger_type] || item.trigger_type}</strong>
        <div class="terminal-meta">
          <span>触发价 ${item.trigger_price}</span>
          <span>${item.order_side === "buy" ? "买入" : "卖出"}</span>
          <span>委托价 ${item.order_price}</span>
          <span>数量 ${item.quantity}</span>
        </div>
        <p class="helper-text">状态 ${item.status}</p>
      </article>
    `).join("")
    : "<p class='helper-text'>暂无条件单。</p>";
}

function renderRiskProfile() {
  const profile = state.riskProfile;
  if (!profile) {
    return;
  }
  const form = document.getElementById("risk-form");
  Object.entries(profile).forEach(([key, value]) => {
    const input = form.elements.namedItem(key);
    if (input) {
      input.value = value;
    }
  });
  document.getElementById("risk-status").innerHTML = `
    <strong>当前风控摘要</strong>
    <span>单票上限 ${profile.max_position_pct}%</span>
    <span>日内亏损 ${profile.max_daily_loss_pct}%</span>
    <span>组合回撤 ${profile.max_drawdown_pct}%</span>
  `;
}

function renderTradingTerminal(data) {
  state.orders = data.orders || [];
  state.conditionalOrders = data.conditional_orders || [];
  state.riskProfile = data.risk_profile || null;
  renderOrders();
  renderConditionalOrders();
  renderRiskProfile();
}

function renderBacktestResult(result) {
  document.getElementById("result-summary").innerHTML = `
    <strong>${result.strategy_title}</strong>
    <p>${result.strategist} · 股票 ${result.symbol}</p>
    <p>总收益率 ${result.total_return_pct}% · 年化 ${result.annualized_return_pct}% · 最大回撤 ${result.max_drawdown_pct}%</p>
    <p>超额收益 ${result.alpha_vs_hold_pct}% · 胜率 ${result.win_rate_pct}% · 盈亏比 ${result.profit_factor}</p>
    <p>结束资金 ${result.ending_capital} · 交易次数 ${result.trade_count}</p>
  `;
  document.getElementById("signal-list").innerHTML = result.signals.map((item) => `
    <article class="signal-card">
      <strong>${item.date} ${item.signal}</strong>
      <p class="helper-text">价格 ${item.price}</p>
      <p class="helper-text">${item.note}</p>
    </article>
  `).join("");

  state.lastCurve = result.equity_curve || [];
  state.lastCandles = result.candles || [];
  state.lastSignals = result.signals || [];
  state.movingAverages = result.moving_averages || null;
  state.indicators = result.indicators || null;
  state.candleOffset = 0;
  state.crosshairIndex = null;
  renderChartLegend();
  redrawAllCharts();
}

function renderChartLegend() {
  const moving = state.movingAverages;
  const legend = document.getElementById("chart-legend");
  if (!moving) {
    legend.innerHTML = "";
    return;
  }
  legend.innerHTML = `
    <span>红柱: 阳线</span>
    <span>绿柱: 阴线</span>
    <span class="legend-short">${moving.short_label}</span>
    <span class="legend-long">${moving.long_label}</span>
    <span class="legend-boll">BOLL</span>
    <span>▲ 买点</span>
    <span>▼ 卖点</span>
  `;
}

function updateChartTooltip(candle) {
  const tooltip = document.getElementById("chart-tooltip");
  if (!candle) {
    tooltip.classList.add("hidden-tooltip");
    tooltip.innerHTML = "";
    return;
  }
  tooltip.classList.remove("hidden-tooltip");
  tooltip.innerHTML = `
    <strong>${candle.date}</strong><br>
    开 ${candle.open} 高 ${candle.high} 低 ${candle.low} 收 ${candle.close}<br>
    量 ${candle.volume ?? 0}${state.crosshairLocked ? "<br>已锁定" : ""}
  `;
}

function setupCanvas(canvas, height) {
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(rect.width, 280);
  const scale = window.devicePixelRatio || 1;
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  ctx.clearRect(0, 0, width, height);
  return { ctx, width, height };
}

function drawOverlayLine(ctx, values, length, min, max, padX, padY, usableWidth, usableHeight, color) {
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  let hasPoint = false;
  values.forEach((value, index) => {
    if (value === null || value === undefined) {
      return;
    }
    const x = padX + (usableWidth * index) / Math.max(length - 1, 1);
    const y = padY + (1 - (value - min) / Math.max(max - min, 1e-9)) * usableHeight;
    if (!hasPoint) {
      ctx.moveTo(x, y);
      hasPoint = true;
    } else {
      ctx.lineTo(x, y);
    }
  });
  if (hasPoint) {
    ctx.stroke();
  }
}

function drawLineChart(canvas, values, labels, color, height = 240) {
  const { ctx, width } = setupCanvas(canvas, height);
  if (!values.length) {
    return;
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const padX = 18;
  const padY = 18;
  const usableWidth = width - padX * 2;
  const usableHeight = height - padY * 2;

  ctx.strokeStyle = "#ece2d5";
  ctx.lineWidth = 1;
  [0, 0.5, 1].forEach((ratio) => {
    const y = padY + usableHeight * ratio;
    ctx.beginPath();
    ctx.moveTo(padX, y);
    ctx.lineTo(width - padX, y);
    ctx.stroke();
  });

  ctx.strokeStyle = color;
  ctx.lineWidth = 2.6;
  ctx.beginPath();
  values.forEach((value, index) => {
    const x = padX + (usableWidth * index) / Math.max(values.length - 1, 1);
    const y = height - padY - ((value - min) / Math.max(max - min, 1e-9)) * usableHeight;
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  if (labels.length) {
    ctx.fillStyle = "#6f7884";
    ctx.font = "12px Microsoft YaHei UI";
    ctx.fillText(labels[0], padX, height - 6);
    const last = labels[labels.length - 1];
    const textWidth = ctx.measureText(last).width;
    ctx.fillText(last, width - padX - textWidth, height - 6);
  }
}

function drawMinuteChart(series) {
  const canvas = document.getElementById("minute-chart");
  if (!series?.length) {
    setupCanvas(canvas, 220);
    return;
  }
  const prices = series.map((item) => item.price);
  const avgs = series.map((item) => item.avg);
  const { ctx, width } = setupCanvas(canvas, 220);
  const min = Math.min(...prices, ...avgs);
  const max = Math.max(...prices, ...avgs);
  const padX = 18;
  const padY = 18;
  const usableWidth = width - padX * 2;
  const usableHeight = 220 - padY * 2;

  ctx.strokeStyle = "#ece2d5";
  ctx.lineWidth = 1;
  [0, 0.5, 1].forEach((ratio) => {
    const y = padY + usableHeight * ratio;
    ctx.beginPath();
    ctx.moveTo(padX, y);
    ctx.lineTo(width - padX, y);
    ctx.stroke();
  });
  drawOverlayLine(ctx, prices, prices.length, min, max, padX, padY, usableWidth, usableHeight, "#2563eb");
  drawOverlayLine(ctx, avgs, avgs.length, min, max, padX, padY, usableWidth, usableHeight, "#f59e0b");
}

function getCandleViewport() {
  const total = state.lastCandles.length;
  const count = Math.min(state.candlePeriod, total);
  const maxOffset = Math.max(total - count, 0);
  const offset = Math.min(Math.max(state.candleOffset, 0), maxOffset);
  const end = total - offset;
  const start = Math.max(end - count, 0);
  return { start, end, candles: state.lastCandles.slice(start, end) };
}

function drawEquityChart() {
  const canvas = document.getElementById("equity-chart");
  drawLineChart(
    canvas,
    state.lastCurve.map((item) => item.equity),
    state.lastCurve.map((item) => item.date),
    "#178560",
    240,
  );
}

function drawVolumeChart() {
  const canvas = document.getElementById("volume-chart");
  const viewport = getCandleViewport();
  const candles = viewport.candles;
  const { ctx, width, height } = setupCanvas(canvas, 120);
  if (!candles.length) {
    return;
  }
  const volumes = candles.map((item) => item.volume || 0);
  const maxVolume = Math.max(...volumes, 1);
  const padX = 18;
  const padY = 16;
  const usableWidth = width - padX * 2;
  const usableHeight = height - padY * 2;
  const step = usableWidth / Math.max(candles.length, 1);
  const bodyWidth = Math.max(3, step * 0.55);

  volumes.forEach((value, index) => {
    const x = padX + step * index + step / 2;
    const item = candles[index];
    const color = item.close >= item.open ? "#dd5840" : "#178560";
    const volumeBarHeight = (value / maxVolume) * usableHeight;
    ctx.fillStyle = color;
    ctx.globalAlpha = 0.45;
    ctx.fillRect(x - bodyWidth / 2, padY + usableHeight - volumeBarHeight, bodyWidth, volumeBarHeight);
    ctx.globalAlpha = 1;
  });

  if (state.crosshairIndex !== null && candles[state.crosshairIndex]) {
    const x = padX + step * state.crosshairIndex + step / 2;
    ctx.strokeStyle = "#94a3b8";
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(x, padY);
    ctx.lineTo(x, height - padY);
    ctx.stroke();
    ctx.setLineDash([]);
  }
}

function drawCandlesChart() {
  const canvas = document.getElementById("candles-chart");
  const viewport = getCandleViewport();
  const candles = viewport.candles;
  const { ctx, width, height } = setupCanvas(canvas, 240);
  if (!candles.length) {
    return;
  }

  const highs = candles.map((item) => item.high);
  const lows = candles.map((item) => item.low);
  const min = Math.min(...lows);
  const max = Math.max(...highs);
  const padX = 18;
  const padY = 18;
  const usableWidth = width - padX * 2;
  const priceHeight = height - padY * 2;
  const step = usableWidth / Math.max(candles.length, 1);
  const bodyWidth = Math.max(3, step * 0.55);

  ctx.strokeStyle = "#ece2d5";
  ctx.lineWidth = 1;
  [0, 0.5, 1].forEach((ratio) => {
    const y = padY + priceHeight * ratio;
    ctx.beginPath();
    ctx.moveTo(padX, y);
    ctx.lineTo(width - padX, y);
    ctx.stroke();
  });

  candles.forEach((item, index) => {
    const ratio = Math.max(max - min, 1e-9);
    const x = padX + step * index + step / 2;
    const highY = padY + (1 - (item.high - min) / ratio) * priceHeight;
    const lowY = padY + (1 - (item.low - min) / ratio) * priceHeight;
    const openY = padY + (1 - (item.open - min) / ratio) * priceHeight;
    const closeY = padY + (1 - (item.close - min) / ratio) * priceHeight;
    const color = item.close >= item.open ? "#dd5840" : "#178560";
    ctx.strokeStyle = color;
    ctx.beginPath();
    ctx.moveTo(x, highY);
    ctx.lineTo(x, lowY);
    ctx.stroke();
    ctx.fillStyle = color;
    const top = Math.min(openY, closeY);
    const bodyHeight = Math.max(Math.abs(closeY - openY), 2);
    ctx.fillRect(x - bodyWidth / 2, top, bodyWidth, bodyHeight);
  });

  if (state.movingAverages) {
    drawOverlayLine(ctx, state.movingAverages.short.slice(viewport.start, viewport.end), candles.length, min, max, padX, padY, usableWidth, priceHeight, "#f59e0b");
    drawOverlayLine(ctx, state.movingAverages.long.slice(viewport.start, viewport.end), candles.length, min, max, padX, padY, usableWidth, priceHeight, "#2563eb");
  }

  if (state.indicators) {
    drawOverlayLine(ctx, state.indicators.boll_middle.slice(viewport.start, viewport.end), candles.length, min, max, padX, padY, usableWidth, priceHeight, "#7c3aed");
    drawOverlayLine(ctx, state.indicators.boll_upper.slice(viewport.start, viewport.end), candles.length, min, max, padX, padY, usableWidth, priceHeight, "#a855f7");
    drawOverlayLine(ctx, state.indicators.boll_lower.slice(viewport.start, viewport.end), candles.length, min, max, padX, padY, usableWidth, priceHeight, "#a855f7");
  }

  state.lastSignals
    .filter((signal) => candles.some((bar) => bar.date === signal.date))
    .forEach((signal) => {
      const index = candles.findIndex((item) => item.date === signal.date);
      if (index < 0) {
        return;
      }
      const x = padX + step * index + step / 2;
      const y = padY + (1 - (candles[index].close - min) / Math.max(max - min, 1e-9)) * priceHeight;
      ctx.fillStyle = signal.signal === "BUY" ? "#dc2626" : "#178560";
      ctx.font = "12px Microsoft YaHei UI";
      ctx.fillText(signal.signal === "BUY" ? "▲" : "▼", x - 4, signal.signal === "BUY" ? y - 8 : y + 18);
    });

  if (state.crosshairIndex !== null && candles[state.crosshairIndex]) {
    const item = candles[state.crosshairIndex];
    const x = padX + step * state.crosshairIndex + step / 2;
    const y = padY + (1 - (item.close - min) / Math.max(max - min, 1e-9)) * priceHeight;
    ctx.strokeStyle = "#94a3b8";
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(x, padY);
    ctx.lineTo(x, height - padY);
    ctx.moveTo(padX, y);
    ctx.lineTo(width - padX, y);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#18212b";
    ctx.font = "12px Microsoft YaHei UI";
    ctx.fillText(`${item.date} O:${item.open} H:${item.high} L:${item.low} C:${item.close}`, padX, 14);
    const priceLabel = item.close.toFixed(2);
    const labelWidth = ctx.measureText(priceLabel).width + 14;
    ctx.fillStyle = "rgba(24,33,43,0.88)";
    ctx.fillRect(width - labelWidth - 6, y - 10, labelWidth, 20);
    ctx.fillStyle = "#ffffff";
    ctx.fillText(priceLabel, width - labelWidth, y + 4);
    const timeWidth = ctx.measureText(item.date).width + 14;
    ctx.fillStyle = "rgba(24,33,43,0.88)";
    ctx.fillRect(x - timeWidth / 2, height - 26, timeWidth, 20);
    ctx.fillStyle = "#ffffff";
    ctx.fillText(item.date, x - timeWidth / 2 + 7, height - 12);
    updateChartTooltip(item);
  } else {
    updateChartTooltip(null);
  }

  ctx.fillStyle = "#6f7884";
  ctx.font = "12px Microsoft YaHei UI";
  ctx.fillText(candles[0].date, padX, height - 6);
  const last = candles[candles.length - 1].date;
  const textWidth = ctx.measureText(last).width;
  ctx.fillText(last, width - padX - textWidth, height - 6);
}

function drawIndicatorCrosshair(canvas, labels) {
  if (state.crosshairIndex === null || !labels[state.crosshairIndex]) {
    return;
  }
  const ctx = canvas.getContext("2d");
  const width = canvas.width / (window.devicePixelRatio || 1);
  const height = canvas.height / (window.devicePixelRatio || 1);
  const padX = 18;
  const usableWidth = width - padX * 2;
  const x = padX + (usableWidth * state.crosshairIndex) / Math.max(labels.length - 1, 1);
  ctx.strokeStyle = "#94a3b8";
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(x, 18);
  ctx.lineTo(x, height - 18);
  ctx.stroke();
  ctx.setLineDash([]);
}

function drawIndicatorChart() {
  const canvas = document.getElementById("indicator-chart");
  const viewport = getCandleViewport();
  const labels = viewport.candles.map((item) => item.date);
  if (!state.indicators || !labels.length) {
    setupCanvas(canvas, 160);
    return;
  }

  if (state.indicatorMode === "rsi") {
    drawLineChart(canvas, state.indicators.rsi14.slice(viewport.start, viewport.end).map((item) => item ?? 0), labels, "#7c3aed", 160);
    drawIndicatorCrosshair(canvas, labels);
    return;
  }

  if (state.indicatorMode === "boll") {
    drawLineChart(canvas, state.indicators.boll_middle.slice(viewport.start, viewport.end).map((item) => item ?? 0), labels, "#7c3aed", 160);
    drawIndicatorCrosshair(canvas, labels);
    return;
  }

  const { ctx, width, height } = setupCanvas(canvas, 160);
  const hist = state.indicators.macd_hist.slice(viewport.start, viewport.end);
  const dif = state.indicators.macd_dif.slice(viewport.start, viewport.end);
  const dea = state.indicators.macd_dea.slice(viewport.start, viewport.end);
  const numeric = [...hist, ...dif, ...dea].filter((item) => item !== null && item !== undefined);
  if (!numeric.length) {
    return;
  }
  const min = Math.min(...numeric);
  const max = Math.max(...numeric);
  const padX = 18;
  const padY = 18;
  const usableWidth = width - padX * 2;
  const usableHeight = height - padY * 2;
  const step = usableWidth / Math.max(hist.length, 1);

  hist.forEach((value, index) => {
    const x = padX + step * index + step / 2;
    const zeroY = padY + (1 - (0 - min) / Math.max(max - min, 1e-9)) * usableHeight;
    const y = padY + (1 - ((value ?? 0) - min) / Math.max(max - min, 1e-9)) * usableHeight;
    ctx.strokeStyle = (value ?? 0) >= 0 ? "#dd5840" : "#178560";
    ctx.lineWidth = Math.max(step * 0.45, 3);
    ctx.beginPath();
    ctx.moveTo(x, zeroY);
    ctx.lineTo(x, y);
    ctx.stroke();
  });

  drawOverlayLine(ctx, dif, hist.length, min, max, padX, padY, usableWidth, usableHeight, "#2563eb");
  drawOverlayLine(ctx, dea, hist.length, min, max, padX, padY, usableWidth, usableHeight, "#f59e0b");
  drawIndicatorCrosshair(canvas, labels);
}

function redrawAllCharts() {
  if (state.activeChart === "candles") {
    drawCandlesChart();
    drawVolumeChart();
    drawIndicatorChart();
    return;
  }
  drawEquityChart();
}

function syncChartVisibility() {
  document.getElementById("candles-chart").classList.toggle("hidden-chart", state.activeChart !== "candles");
  document.getElementById("volume-chart").classList.toggle("hidden-chart", state.activeChart !== "candles");
  document.getElementById("indicator-chart").classList.toggle("hidden-chart", state.activeChart !== "candles");
  document.getElementById("equity-chart").classList.toggle("hidden-chart", state.activeChart !== "equity");
}

async function loadLiveMarket(symbol) {
  const payload = await fetchJson(`/api/market/live?symbol=${encodeURIComponent(symbol)}`);
  renderProfessionalMarket(payload);
}

async function loadTradingTerminal() {
  const payload = await fetchJson("/api/trading/terminal");
  renderTradingTerminal(payload);
}

function getChartIndexFromClientX(clientX) {
  const canvas = document.getElementById("candles-chart");
  const rect = canvas.getBoundingClientRect();
  const viewport = getCandleViewport();
  if (!viewport.candles.length) {
    return null;
  }
  const ratio = Math.min(Math.max((clientX - rect.left) / rect.width, 0), 0.999);
  return Math.floor(ratio * viewport.candles.length);
}

function updateCrosshair(clientX) {
  const index = getChartIndexFromClientX(clientX);
  if (index === null) {
    return;
  }
  state.crosshairIndex = index;
  drawCandlesChart();
  drawVolumeChart();
  drawIndicatorChart();
}

function bindUi() {
  document.querySelectorAll(".tabbar-item").forEach((button) => {
    button.addEventListener("click", () => switchScreen(button.dataset.screen));
  });

  document.querySelectorAll("[data-jump]").forEach((button) => {
    button.addEventListener("click", () => switchScreen(button.dataset.jump));
  });

  document.querySelectorAll(".board-tab").forEach((button) => {
    button.addEventListener("click", () => {
      state.boardMode = button.dataset.board;
      document.querySelectorAll(".board-tab").forEach((item) => item.classList.toggle("active", item === button));
      renderMarketBoard();
    });
  });

  document.querySelectorAll(".market-tab").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".market-tab").forEach((item) => item.classList.toggle("active", item === button));
      document.querySelectorAll(".market-panel").forEach((panel) => panel.classList.remove("active"));
      document.getElementById(`${button.dataset.marketPanel}-panel`).classList.add("active");
    });
  });

  document.querySelectorAll(".chart-tab").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.chart) {
        state.activeChart = button.dataset.chart;
        document.querySelectorAll("[data-chart]").forEach((tab) => tab.classList.toggle("active", tab === button));
        syncChartVisibility();
        redrawAllCharts();
        return;
      }
      if (button.dataset.period) {
        state.candlePeriod = Number(button.dataset.period);
        state.candleOffset = 0;
        document.querySelectorAll("[data-period]").forEach((tab) => tab.classList.toggle("active", tab === button));
        drawCandlesChart();
        drawVolumeChart();
        drawIndicatorChart();
        return;
      }
      if (button.dataset.indicator) {
        state.indicatorMode = button.dataset.indicator;
        document.querySelectorAll("[data-indicator]").forEach((tab) => tab.classList.toggle("active", tab === button));
        drawIndicatorChart();
      }
    });
  });

  document.getElementById("zoom-in").addEventListener("click", () => {
    state.candlePeriod = Math.max(10, state.candlePeriod - 10);
    drawCandlesChart();
    drawVolumeChart();
    drawIndicatorChart();
  });
  document.getElementById("zoom-out").addEventListener("click", () => {
    state.candlePeriod = Math.min(90, state.candlePeriod + 10);
    drawCandlesChart();
    drawVolumeChart();
    drawIndicatorChart();
  });
  document.getElementById("reset-view").addEventListener("click", () => {
    state.candlePeriod = 20;
    state.candleOffset = 0;
    state.crosshairIndex = null;
    state.crosshairLocked = false;
    document.getElementById("lock-hint").textContent = "长按锁定十字线，双指缩放，左右拖动平移";
    redrawAllCharts();
  });

  document.getElementById("refresh-live-market").addEventListener("click", async () => {
    const symbol = document.getElementById("live-symbol").value.trim() || "000001";
    try {
      await loadLiveMarket(symbol);
    } catch (error) {
      alert(error.message);
    }
  });

  const dialog = document.getElementById("auth-dialog");
  const displayNameRow = document.getElementById("display-name-row");
  const authSubmit = document.getElementById("auth-submit");
  document.getElementById("auth-entry").addEventListener("click", async () => {
    if (state.auth?.is_authenticated) {
      await fetchJson("/api/auth/logout", { method: "POST" });
      await bootstrap();
      return;
    }
    dialog.showModal();
  });

  document.querySelectorAll(".auth-mode").forEach((button) => {
    button.addEventListener("click", () => {
      state.authMode = button.dataset.authMode;
      document.querySelectorAll(".auth-mode").forEach((item) => item.classList.toggle("active", item === button));
      const isRegister = state.authMode === "register";
      displayNameRow.classList.toggle("hidden-auth-row", !isRegister);
      authSubmit.textContent = isRegister ? "注册" : "登录";
    });
  });

  document.getElementById("auth-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.target).entries());
    try {
      await fetchJson(`/api/auth/${state.authMode}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      dialog.close();
      await bootstrap();
    } catch (error) {
      alert(error.message);
    }
  });

  document.getElementById("backtest-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.target).entries());
    payload.strategy_code = state.activeStrategy;
    document.getElementById("result-summary").innerHTML = "<p>正在下载行情并运行回测，请稍候...</p>";
    try {
      const result = await fetchJson("/api/backtest", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      renderBacktestResult(result);
    } catch (error) {
      document.getElementById("result-summary").innerHTML = `<p>${error.message}</p>`;
    }
  });

  document.getElementById("order-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.target).entries());
    payload.quantity = Number(payload.quantity);
    const result = await fetchJson("/api/trading/orders", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.orders = result.items || [];
    renderOrders();
  });

  document.getElementById("conditional-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.target).entries());
    payload.quantity = Number(payload.quantity);
    const result = await fetchJson("/api/trading/conditional-orders", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.conditionalOrders = result.items || [];
    renderConditionalOrders();
  });

  document.getElementById("risk-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.target).entries());
    Object.keys(payload).forEach((key) => {
      payload[key] = Number(payload[key]);
    });
    const result = await fetchJson("/api/trading/risk-profile", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    state.riskProfile = result.profile;
    renderRiskProfile();
  });

  const candlesCanvas = document.getElementById("candles-chart");
  const distanceBetweenTouches = (touches) => {
    if (touches.length < 2) {
      return 0;
    }
    const dx = touches[0].clientX - touches[1].clientX;
    const dy = touches[0].clientY - touches[1].clientY;
    return Math.sqrt(dx * dx + dy * dy);
  };

  candlesCanvas.addEventListener("mousemove", (event) => {
    if (state.isDraggingChart) {
      const deltaX = event.clientX - state.dragStartX;
      const stepShift = Math.round(deltaX / 10);
      state.candleOffset = Math.max(0, state.dragOffsetSnapshot - stepShift);
      drawCandlesChart();
      drawVolumeChart();
      drawIndicatorChart();
      return;
    }
    updateCrosshair(event.clientX);
  });

  candlesCanvas.addEventListener("mouseleave", () => {
    if (state.crosshairLocked) {
      return;
    }
    state.crosshairIndex = null;
    drawCandlesChart();
    drawVolumeChart();
    drawIndicatorChart();
  });

  candlesCanvas.addEventListener("mousedown", (event) => {
    state.isDraggingChart = true;
    state.dragStartX = event.clientX;
    state.dragOffsetSnapshot = state.candleOffset;
  });

  window.addEventListener("mouseup", () => {
    state.isDraggingChart = false;
  });

  candlesCanvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    state.candlePeriod = event.deltaY < 0 ? Math.max(10, state.candlePeriod - 5) : Math.min(90, state.candlePeriod + 5);
    drawCandlesChart();
    drawVolumeChart();
    drawIndicatorChart();
  }, { passive: false });

  candlesCanvas.addEventListener("touchstart", (event) => {
    if (event.touches.length >= 2) {
      state.touchMode = "pinch";
      state.pinchDistance = distanceBetweenTouches(event.touches);
      state.pinchPeriodSnapshot = state.candlePeriod;
      return;
    }
    if (event.touches.length === 1) {
      state.touchMode = "drag";
      state.dragStartX = event.touches[0].clientX;
      state.dragOffsetSnapshot = state.candleOffset;
      state.crosshairLocked = true;
      document.getElementById("lock-hint").textContent = "十字线已锁定，双指缩放，左右拖动平移";
      updateCrosshair(event.touches[0].clientX);
    }
  }, { passive: true });

  candlesCanvas.addEventListener("touchmove", (event) => {
    if (state.touchMode === "pinch" && event.touches.length >= 2) {
      const distance = distanceBetweenTouches(event.touches);
      const ratio = distance / Math.max(state.pinchDistance, 1);
      const nextPeriod = Math.round(state.pinchPeriodSnapshot / ratio);
      state.candlePeriod = Math.min(90, Math.max(10, nextPeriod));
      drawCandlesChart();
      drawVolumeChart();
      drawIndicatorChart();
      return;
    }
    if (state.touchMode === "drag" && event.touches.length === 1) {
      const deltaX = event.touches[0].clientX - state.dragStartX;
      const stepShift = Math.round(deltaX / 10);
      state.candleOffset = Math.max(0, state.dragOffsetSnapshot - stepShift);
      updateCrosshair(event.touches[0].clientX);
    }
  }, { passive: true });

  candlesCanvas.addEventListener("touchend", () => {
    state.touchMode = null;
  });

  candlesCanvas.addEventListener("dblclick", () => {
    state.crosshairLocked = !state.crosshairLocked;
    document.getElementById("lock-hint").textContent = state.crosshairLocked
      ? "十字线已锁定，双指缩放，左右拖动平移"
      : "长按锁定十字线，双指缩放，左右拖动平移";
    if (!state.crosshairLocked) {
      state.crosshairIndex = null;
      drawCandlesChart();
      drawVolumeChart();
      drawIndicatorChart();
    }
  });

  window.addEventListener("resize", () => {
    if (state.liveMarket) {
      drawMinuteChart(state.liveMarket.minute_series || []);
    }
    if (state.lastCandles.length) {
      redrawAllCharts();
    }
  });
}

async function bootstrap() {
  const [auth, dashboard, strategies, favorites, terminal] = await Promise.all([
    fetchJson("/api/auth/status"),
    fetchJson("/api/dashboard"),
    fetchJson("/api/strategies"),
    fetchJson("/api/me/favorites"),
    fetchJson("/api/trading/terminal"),
  ]);
  state.auth = auth;
  state.favorites = favorites.items || [];
  renderAuth();
  renderStrategies(strategies.items || []);
  renderDashboard(dashboard);
  renderTradingTerminal(terminal);
  syncChartVisibility();
  try {
    await loadLiveMarket(document.getElementById("live-symbol").value.trim() || "000001");
  } catch (error) {
    console.warn("live market unavailable", error);
  }
  await loadStrategyDetail(state.activeStrategy);
}

bindUi();
bootstrap().catch((error) => {
  const summary = document.getElementById("result-summary");
  if (summary) {
    summary.innerHTML = `<p>${error.message}</p>`;
  }
});
