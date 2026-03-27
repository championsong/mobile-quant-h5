const state = {
  strategies: [],
  activeStrategy: "beichen_ma_fast",
  lastCurve: [],
};

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "请求失败");
  }
  return response.json();
}

function renderProfile(data) {
  const profileBlock = document.getElementById("profile-block");
  const summaryCards = document.getElementById("summary-cards");
  const positions = document.getElementById("positions");
  const watchlist = document.getElementById("watchlist");
  const brokerList = document.getElementById("broker-list");

  profileBlock.innerHTML = `
    <h3 class="profile-title">${data.profile.nickname}</h3>
    <p class="profile-sub">${data.profile.membership} · ${data.profile.risk_level}</p>
    <p class="profile-sub">${data.profile.intro}</p>
  `;

  summaryCards.innerHTML = data.summary_cards.map(item => `
    <article class="metric-card">
      <p>${item.label}</p>
      <div class="value">${item.value}</div>
      <div class="delta">${item.delta}</div>
    </article>
  `).join("");

  positions.innerHTML = data.positions.map(item => `
    <article class="position-card">
      <strong>${item.symbol} ${item.name}</strong>
      <p class="helper-text">仓位 ${item.weight}</p>
      <p class="delta">${item.pnl}</p>
    </article>
  `).join("");

  watchlist.innerHTML = data.watchlist.map(item => `<li>${item}</li>`).join("");

  brokerList.innerHTML = data.brokers.map(item => `
    <article class="broker-card">
      <div class="strategy-meta">
        <strong>${item.name}</strong>
        <span class="broker-status ${item.status === "ready" ? "broker-status--ready" : ""}">
          ${item.status === "ready" ? "已就绪" : "待配置"}
        </span>
      </div>
      <p class="helper-text">${item.description}</p>
      <div class="features">${item.features.map(feature => `<span>${feature}</span>`).join("")}</div>
    </article>
  `).join("");
}

function renderSelectedStrategy() {
  const target = document.getElementById("selected-strategy");
  const strategy = state.strategies.find(item => item.code === state.activeStrategy);
  if (!strategy) {
    target.innerHTML = "<p class='helper-text'>请选择一个策略。</p>";
    return;
  }

  document.getElementById("strategy-code").value = strategy.code;
  target.innerHTML = `
    <div class="strategy-meta">
      <div>
        <strong>${strategy.title}</strong>
        <div class="strategist">${strategy.strategist}</div>
      </div>
      <span class="risk">${strategy.risk_level}风险</span>
    </div>
    <p class="helper-text">${strategy.description}</p>
    <p class="helper-text">适用场景：${strategy.fit_for}</p>
  `;
}

function renderStrategies(items) {
  const container = document.getElementById("strategy-list");
  state.strategies = items;
  container.innerHTML = items.map(item => `
    <article class="strategy-card ${item.code === state.activeStrategy ? "active" : ""}" data-code="${item.code}">
      <div class="strategy-meta">
        <div>
          <strong>${item.title}</strong>
          <div class="strategist">${item.strategist}</div>
        </div>
        <span class="risk">${item.risk_level}风险</span>
      </div>
      <p class="helper-text">${item.description}</p>
      <p class="helper-text">适用场景：${item.fit_for}</p>
      <div class="tag-row">${item.tags.map(tag => `<span>${tag}</span>`).join("")}</div>
    </article>
  `).join("");

  container.querySelectorAll(".strategy-card").forEach(card => {
    card.addEventListener("click", () => {
      state.activeStrategy = card.dataset.code;
      renderStrategies(state.strategies);
      renderSelectedStrategy();
      document.getElementById("trade").scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  renderSelectedStrategy();
}

function renderBacktestResult(result) {
  const summary = document.getElementById("result-summary");
  const signalList = document.getElementById("signal-list");
  summary.innerHTML = `
    <strong>${result.strategy_title}</strong>
    <p>${result.strategist} · 股票 ${result.symbol}</p>
    <p>总收益率 ${result.total_return_pct}% · 年化 ${result.annualized_return_pct}% · 最大回撤 ${result.max_drawdown_pct}%</p>
    <p>超额收益 ${result.alpha_vs_hold_pct}% · 胜率 ${result.win_rate_pct}% · 盈亏比 ${result.profit_factor}</p>
    <p>结束资金 ${result.ending_capital} · 交易次数 ${result.trade_count}</p>
  `;

  signalList.innerHTML = result.signals.map(item => `
    <article class="signal-card">
      <strong>${item.date} ${item.signal}</strong>
      <p class="helper-text">价格 ${item.price}</p>
      <p class="helper-text">${item.note}</p>
    </article>
  `).join("");

  state.lastCurve = result.equity_curve || [];
  drawEquityChart(state.lastCurve);
}

function drawEquityChart(points) {
  const canvas = document.getElementById("equity-chart");
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(rect.width, 280);
  const height = 220;
  const scale = window.devicePixelRatio || 1;
  canvas.width = width * scale;
  canvas.height = height * scale;

  const ctx = canvas.getContext("2d");
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  ctx.clearRect(0, 0, width, height);

  if (!points || !points.length) {
    return;
  }

  const values = points.map(item => item.equity);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const padX = 18;
  const padY = 20;
  const usableWidth = width - padX * 2;
  const usableHeight = height - padY * 2;

  ctx.strokeStyle = "#eadfce";
  ctx.lineWidth = 1;
  [0, 0.5, 1].forEach(ratio => {
    const y = padY + usableHeight * ratio;
    ctx.beginPath();
    ctx.moveTo(padX, y);
    ctx.lineTo(width - padX, y);
    ctx.stroke();
  });

  ctx.strokeStyle = "#14805c";
  ctx.lineWidth = 2.4;
  ctx.beginPath();
  points.forEach((point, index) => {
    const x = padX + (usableWidth * index) / Math.max(points.length - 1, 1);
    const normalized = max === min ? 0.5 : (point.equity - min) / (max - min);
    const y = height - padY - normalized * usableHeight;
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  ctx.fillStyle = "#68727d";
  ctx.font = "12px Microsoft YaHei UI";
  ctx.fillText(points[0].date, padX, height - 6);
  const last = points[points.length - 1].date;
  const textWidth = ctx.measureText(last).width;
  ctx.fillText(last, width - padX - textWidth, height - 6);
}

function bindBottomNav() {
  const links = [...document.querySelectorAll(".bottom-link")];
  const sections = links
    .map(link => document.querySelector(link.getAttribute("href")))
    .filter(Boolean);

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) {
        return;
      }
      const activeId = `#${entry.target.id}`;
      links.forEach(link => link.classList.toggle("active", link.getAttribute("href") === activeId));
    });
  }, { rootMargin: "-35% 0px -45% 0px", threshold: 0.05 });

  sections.forEach(section => observer.observe(section));
}

async function loadInitialData() {
  const [dashboard, strategyResponse] = await Promise.all([
    fetchJson("/api/dashboard"),
    fetchJson("/api/strategies"),
  ]);
  renderProfile(dashboard);
  renderStrategies(strategyResponse.items);
}

document.getElementById("backtest-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const payload = Object.fromEntries(formData.entries());
  payload.strategy_code = state.activeStrategy;

  const summary = document.getElementById("result-summary");
  summary.innerHTML = "<p>正在下载行情并运行回测，请稍候...</p>";

  try {
    const result = await fetchJson("/api/backtest", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderBacktestResult(result);
  } catch (error) {
    summary.innerHTML = `<p>${error.message}</p>`;
  }
});

window.addEventListener("resize", () => {
  if (state.lastCurve.length) {
    drawEquityChart(state.lastCurve);
  }
});

bindBottomNav();
loadInitialData().catch((error) => {
  document.getElementById("result-summary").innerHTML = `<p>${error.message}</p>`;
});
