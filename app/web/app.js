"use strict";

(() => {
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];
  const token = $('meta[name="session-token"]').content;
  const statusNames = { pass: "已通过", warning: "需留意", fail: "未通过", unknown: "未验证" };
  const statusSymbols = { pass: "✓", warning: "!", fail: "×", unknown: "·" };
  const viewNames = { check: "启动前检测", vps: "购买 VPS", residential: "购买住宅 IP", network: "配置网络", settings: "连接设置" };
  const initialChecks = [
    ["本地代理连接", "确认配置的代理地址是否可以访问。"],
    ["目标出口与网络归属", "核对实测出口、预期 IP 与可获取的网络信息。"],
    ["住宅 IP 采购声明", "记录由你确认的独立购买信息。"],
    ["TUN、DNS 与 UDP", "分别报告取得的证据，不用一种连接代替另一种。"],
    ["Claude 程序与启动条件", "核对程序位置及所有阻断条件。"],
  ];
  const state = { config: null, report: null, running: false, busy: false, loading: true, dirty: false, forceSave: false, stale: false, filter: "all", pollTimer: null, failures: 0 };
  let noticeTimer;

  function notify(message, error = false) {
    const node = $("#notice");
    node.textContent = message;
    node.classList.toggle("error", error);
    node.hidden = false;
    clearTimeout(noticeTimer);
    noticeTimer = setTimeout(() => { node.hidden = true; }, error ? 14000 : 7000);
  }

  function setConnectionError(message) {
    const node = $("#connection-alert");
    node.textContent = message;
    node.hidden = !message;
  }

  async function api(path, { method = "GET", body, timeout = 20000, raw = false } = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
      const headers = { "X-Session-Token": token };
      if (body !== undefined) headers["Content-Type"] = "application/json";
      const response = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal, cache: "no-store", credentials: "same-origin" });
      if (raw && response.ok) return response;
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const error = new Error(typeof data.error === "string" ? data.error : `请求未完成（HTTP ${response.status}）。`);
        error.status = response.status;
        error.data = data;
        throw error;
      }
      return data;
    } catch (error) {
      if (error.name === "AbortError") throw new Error("请求超时。请确认本地检测服务仍在运行，然后重试。");
      if (error instanceof TypeError) throw new Error("无法连接本地检测服务。请确认程序仍在运行，然后重试。");
      throw error;
    } finally { clearTimeout(timer); }
  }

  function showView(view, focus = false) {
    if (!Object.hasOwn(viewNames, view)) view = "check";
    $$(".view").forEach((node) => { node.hidden = node.id !== `view-${view}`; });
    $$(".sidebar [data-view]").forEach((node) => {
      const active = node.dataset.view === view;
      node.classList.toggle("active", active);
      if (active) node.setAttribute("aria-current", "page");
      else node.removeAttribute("aria-current");
    });
    $("#breadcrumb-current").textContent = viewNames[view];
    document.title = `Claude 网络指南 · ${viewNames[view]}`;
    if (location.hash !== `#${view}`) history.replaceState(null, "", `#${view}`);
    if (focus) { $("#main-content").focus({ preventScroll: true }); window.scrollTo({ top: 0, behavior: "auto" }); }
  }

  function readForm() {
    return {
      expected_ip: $("#expected-ip").value.trim(),
      proxy_url: $("#proxy-url").value.trim(),
      claude_path: $("#claude-path").value.trim(),
      residential_ip_confirmed: $("#residential-confirmed").checked,
      require_tun: $("#require-tun").checked,
      require_udp: $("#require-udp").checked,
    };
  }

  function fillForm(config) {
    $("#expected-ip").value = config.expected_ip || "";
    $("#proxy-url").value = config.proxy_url || "http://127.0.0.1:7897";
    $("#claude-path").value = config.claude_path || "";
    $("#residential-confirmed").checked = Boolean(config.residential_ip_confirmed);
    $("#require-tun").checked = config.require_tun !== false;
    $("#require-udp").checked = Boolean(config.require_udp);
  }

  function formDiffers() {
    if (!state.config) return false;
    return state.forceSave || Object.entries(readForm()).some(([key, value]) => value !== state.config[key]);
  }

  function validateSettings(config) {
    let url;
    try { url = new URL(config.proxy_url); } catch { throw new Error("请输入完整的 HTTP 代理地址，例如 http://127.0.0.1:7897。"); }
    if (url.protocol !== "http:") throw new Error("此处需要 http://主机:端口 格式的代理地址。");
    if (url.username || url.password) throw new Error("本地代理地址不能包含用户名或密码。请在网络客户端中管理上游凭据。");
    if (config.expected_ip) {
      const octets = config.expected_ip.split(".");
      if (octets.length !== 4 || octets.some((part) => !/^\d{1,3}$/.test(part) || Number(part) > 255 || (part.length > 1 && part[0] === "0"))) {
        throw new Error("预期出口应为有效的公网 IPv4，例如四段十进制地址。");
      }
    }
  }

  function formatDate(value) {
    if (!value) return "时间未提供";
    const date = typeof value === "number" ? new Date(value < 1e12 ? value * 1000 : value) : new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(date);
  }

  function stringify(value) {
    if (value === undefined || value === null) return "未提供额外证据";
    return typeof value === "string" ? value : JSON.stringify(value, null, 2);
  }

  function getChecks() {
    return state.report && Array.isArray(state.report.checks) ? state.report.checks : [];
  }

  function validStatus(value) { return Object.hasOwn(statusNames, value) ? value : "unknown"; }

  function updateControls() {
    const locked = state.running || state.busy || state.loading;
    const canLaunch = !locked && !state.dirty && !state.stale && state.report?.can_launch === true;
    $("#scan-button").disabled = locked || state.dirty || !state.config;
    $("#scan-button").classList.toggle("is-loading", state.running);
    $("#scan-button span").textContent = state.running ? "正在检测…" : state.report || state.stale ? "重新运行检测" : "运行启动前检测";
    $("#scan-hint").textContent = state.running ? "正在获取实际证据，请稍候" : state.dirty ? "请先在连接设置中保存修改" : "点击后开始，不会自动启动应用";
    $("#launch-button").disabled = !canLaunch;
    $("#launch-button span").textContent = state.busy ? "正在处理…" : "启动 Claude";
    $("#export-button").disabled = !state.report || locked || state.stale || state.dirty;
    $("#save-settings").disabled = locked || !state.config || !state.dirty;
    $("#reset-settings").disabled = locked || !state.dirty;
    $$("#settings-form input").forEach((input) => { input.disabled = state.running || state.busy || state.loading; });
    $("#stale-banner").hidden = !state.stale && !state.dirty;
    $("#stale-banner").textContent = state.dirty ? "连接设置有未保存的修改。保存设置并重新检测后，才能启动 Claude。" : state.running ? "正在获取新的检测结果。检测完成前，之前的结果不能用于启动判断。" : "当前结果已停用。请重新完成检测，更新启动判断。";
    $("#config-dot").classList.toggle("dirty", state.dirty);
    $("#save-state").textContent = state.loading ? "读取配置中…" : !state.config ? "暂时无法读取配置" : state.dirty ? "有未保存的修改" : "当前设置已保存到本机";
    $("#current-proxy").textContent = state.config?.proxy_url || "尚未读取配置";
    $("#checks-list").setAttribute("aria-busy", String(state.running));
    if (state.running) $("#launch-description").textContent = "正在检测当前环境。请等待全部结果返回。";
    else if (state.dirty || state.stale) $("#launch-description").textContent = "连接设置已更改。保存并重新检测后，才能判断是否可以启动。";
    else if (canLaunch) $("#launch-description").textContent = "本次检测满足后端启动条件。点击启动时会再做一次新检测。";
    else if (state.report) $("#launch-description").textContent = "当前未满足启动条件。请查看检测中的阻断项和处理建议。";
    else $("#launch-description").textContent = "先完成检测。只有满足启动条件，按钮才会可用。";
  }

  function renderHero() {
    const hero = $("#status-hero");
    const icon = $("#hero-status-icon");
    const counts = { pass: 0, warning: 0, fail: 0, unknown: 0 };
    getChecks().forEach((check) => { counts[validStatus(check.status)]++; });
    let mode = "idle", kicker = "尚未运行检测", title = "你的网络，现在是什么状态？", detail = "点击运行检测，读取本机的真实结果。未验证的项目会保持灰色。";
    if (state.running) { mode = "running"; kicker = "正在获取本机证据"; title = "正在检查你的连接"; detail = "逐项检查代理、出口与本机环境。检测完成前，不会启用启动按钮。"; }
    else if (state.stale || state.dirty) { mode = "warning"; kicker = "结果需要更新"; title = "配置已改变，请重新检测"; detail = "上一次结果不再用于启动判断。保存当前设置后，再运行一次检测。"; }
    else if (state.report) {
      if (state.report.can_launch === true) { mode = "pass"; kicker = "本次启动条件已满足"; title = "已完成检查，可以尝试启动"; detail = counts.warning || counts.unknown ? "仍有需留意或未验证项目，请先查看具体证据与建议。" : "可验证的项目已完成检查。启动时仍会重新核对当前环境。"; }
      else if (counts.fail) { mode = "fail"; kicker = "存在需要处理的项目"; title = "先解决问题，再启动 Claude"; detail = "当前未满足后端启动条件。查看下方未通过项目，按建议处理后重新检测。"; }
      else { mode = "warning"; kicker = "当前证据尚不足以启动"; title = "还需要确认一些连接条件"; detail = "请检查需留意与未验证项目。缺少证据时，不会把结果显示为通过。"; }
    }
    hero.dataset.state = mode;
    $("#hero-kicker").textContent = kicker;
    $("#overall-title").textContent = title;
    $("#overall-detail").textContent = detail;
    icon.replaceChildren();
    if (mode === "idle" || mode === "running") {
      for (const cls of ["radar-ring", "radar-center"]) { const span = document.createElement("span"); span.className = cls; icon.append(span); }
    } else { const glyph = document.createElement("span"); glyph.className = "state-glyph"; glyph.textContent = mode === "pass" ? "✓" : mode === "fail" ? "×" : "!"; icon.append(glyph); }
    $("#last-scan").textContent = state.report ? `${state.stale || state.dirty ? "上一次检测" : "最近检测"} ${formatDate(state.report.timestamp)}${Number.isFinite(state.report.duration_ms) ? ` · ${(state.report.duration_ms / 1000).toFixed(1)} 秒` : ""}` : "检测在本机执行 · 不收集账户密码";
    for (const status of Object.keys(counts)) $("#count-" + status).textContent = state.report && !state.stale ? String(counts[status]) : "—";
  }

  function makeCheck(check, placeholder = false) {
    const status = placeholder ? "unknown" : validStatus(check.status);
    const article = document.createElement("article"); article.className = "check-item";
    const header = document.createElement("div"); header.className = "check-header";
    const icon = document.createElement("span"); icon.className = `check-icon ${status}`; icon.textContent = statusSymbols[status]; icon.setAttribute("aria-hidden", "true");
    const content = document.createElement("div"); content.className = "check-content";
    const titleRow = document.createElement("div"); titleRow.className = "check-title-row";
    const title = document.createElement("h3"); title.className = "check-title"; title.textContent = check.title || check.id || "未命名检测项"; titleRow.append(title);
    if (!placeholder && check.blocking && status !== "pass") { const badge = document.createElement("span"); badge.className = "blocking-badge"; badge.textContent = "阻断启动"; titleRow.append(badge); }
    const detail = document.createElement("p"); detail.className = "check-detail"; const detailText = stringify(check.detail); detail.textContent = detailText.length > 150 ? detailText.slice(0, 150) + "…" : detailText;
    content.append(titleRow, detail);
    const label = document.createElement("span"); label.className = `check-status ${status}`; label.textContent = placeholder ? "等待检测" : statusNames[status];
    header.append(icon, content, label); article.append(header);
    if (!placeholder && check.action) { const action = document.createElement("p"); action.className = "check-action"; const prefix = document.createElement("strong"); prefix.textContent = "建议"; action.append(prefix, document.createTextNode(stringify(check.action))); article.append(action); }
    if (!placeholder) { const evidence = document.createElement("details"); evidence.className = "check-evidence"; const summary = document.createElement("summary"); summary.textContent = "查看检测证据"; const pre = document.createElement("pre"); pre.textContent = check.evidence !== undefined ? stringify(check.evidence) : detailText; evidence.append(summary, pre); article.append(evidence); }
    return article;
  }

  function renderChecks() {
    const list = $("#checks-list");
    const openIds = new Set([...list.querySelectorAll("details[open]")].map((node) => node.closest("article").dataset.checkId));
    list.replaceChildren();
    if (!state.report) {
      if (state.filter !== "all" && state.filter !== "unknown") { showEmpty(list, "还没有检测结果", "运行一次检测后，可按状态筛选。"); return; }
      initialChecks.forEach(([title, detail]) => list.append(makeCheck({ title, detail }, true)));
      return;
    }
    const checks = getChecks().filter((check) => state.filter === "all" || validStatus(check.status) === state.filter);
    if (!checks.length) { showEmpty(list, "没有符合此筛选的项目", getChecks().length ? "可以切换到其他状态查看。" : "检测未返回项目，请重新运行检测。"); return; }
    checks.forEach((check, index) => { const item = makeCheck(check); item.dataset.checkId = String(check.id || index); if (openIds.has(item.dataset.checkId)) item.querySelector("details").open = true; list.append(item); });
  }

  function showEmpty(list, title, detail) { const node = document.createElement("div"); node.className = "empty-list"; node.textContent = title; const caption = document.createElement("span"); caption.textContent = detail; node.append(caption); list.append(node); }

  function setFilter(filter) {
    state.filter = filter;
    $$(".filter").forEach((node) => { const active = node.dataset.filter === filter; node.classList.toggle("active", active); node.setAttribute("aria-pressed", String(active)); });
    $$(".summary-card").forEach((node) => node.classList.toggle("selected", node.dataset.filter === filter));
    renderChecks();
  }

  function render() { renderHero(); renderChecks(); updateControls(); }

  function acceptStatus(data) {
    const wasRunning = state.running;
    state.running = data.running === true;
    if (data.report && typeof data.report === "object") state.report = data.report;
    else if (!state.running) state.report = null;
    if (!state.running) state.stale = false;
    if (!state.running && wasRunning && data.report) { state.filter = "all"; setFilter("all"); notify("检测已完成。请查看本次结果与操作建议。"); }
    render();
  }

  function schedulePoll(delay = 1200) {
    clearTimeout(state.pollTimer);
    state.pollTimer = setTimeout(poll, delay);
  }

  async function poll() {
    try {
      const data = await api("/api/status", { timeout: 12000 });
      state.failures = 0;
      setConnectionError("");
      acceptStatus(data);
      if (state.running) schedulePoll();
    } catch (error) {
      state.failures++;
      state.running = true; // An unreachable service is not evidence that a scan stopped.
      state.stale = true;
      setConnectionError(error.message + " 当前结果已停用；恢复连接后会继续核对检测状态。");
      render();
      schedulePoll(Math.min(15000, 1800 * state.failures));
    }
  }

  async function startScan() {
    if (state.running || state.busy || state.loading || state.dirty || !state.config) return;
    state.busy = true;
    state.stale = true;
    updateControls();
    try {
      const data = await api("/api/scan", { method: "POST", body: {} });
      state.running = data.running !== false;
      state.filter = "all";
      setFilter("all");
      state.failures = 0;
      setConnectionError("");
      state.busy = false;
      render();
      schedulePoll(500);
    } catch (error) {
      state.busy = false;
      if (error.status === 409) { state.running = true; schedulePoll(500); notify("已有检测正在运行，正在读取它的状态。"); }
      else notify(error.message, true);
      render();
    }
  }

  async function saveSettings(event) {
    event.preventDefault();
    if (state.running || state.busy || !state.dirty) return;
    const config = readForm();
    try { validateSettings(config); } catch (error) { notify(error.message, true); return; }
    state.busy = true;
    updateControls();
    try {
      const data = await api("/api/config", { method: "POST", body: config });
      state.config = data.config;
      fillForm(state.config);
      state.dirty = false;
      state.forceSave = false;
      state.stale = true;
      state.report = null;
      notify("设置已保存。回到启动前检测，使用新配置检查连接。");
    } catch (error) { notify(error.message, true); }
    finally { state.busy = false; render(); }
  }

  async function launchClaude() {
    if (state.running || state.busy || state.loading || state.dirty || state.stale || state.report?.can_launch !== true) return;
    state.busy = true;
    updateControls();
    notify("正在重新检测当前环境，满足条件后才会启动 Claude。");
    try {
      const data = await api("/api/launch", { method: "POST", body: {}, timeout: 45000 });
      if (data.report) state.report = data.report;
      notify(data.message || (data.launched ? "已向系统发送 Claude 启动请求。" : "请求已完成，请查看应用状态。"));
    } catch (error) {
      if (error.data?.report) { state.report = error.data.report; state.stale = false; }
      else state.stale = true;
      notify(error.status === 409 ? "当前环境未通过新一轮启动检查。结果已更新，请按建议处理。" : error.message, true);
    } finally { state.busy = false; render(); }
  }

  async function exportReport() {
    if (!state.report || state.running || state.busy || state.stale || state.dirty) return;
    const button = $("#export-button"); button.disabled = true;
    try {
      const response = await api("/api/export", { raw: true });
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a"); anchor.href = url; anchor.download = `claude-network-report-${new Date().toISOString().replaceAll(":", "-").slice(0, 19)}.json`;
      document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 10000);
      notify("已导出脱敏 JSON 报告。分享前仍请确认内容符合你的预期。");
    } catch (error) { notify(error.message, true); }
    finally { updateControls(); }
  }

  async function initialize() {
    render();
    showView(location.hash.slice(1));
    const results = await Promise.allSettled([api("/api/config"), api("/api/status")]);
    const configResult = results[0], statusResult = results[1];
    state.loading = false;
    if (configResult.status === "fulfilled" && configResult.value.config) {
      const config = configResult.value.config;
      state.config = { expected_ip: "", proxy_url: "http://127.0.0.1:7897", claude_path: "", residential_ip_confirmed: false, require_tun: true, require_udp: false, ...config };
      fillForm(state.config);
      if (configResult.value.warning) { state.forceSave = true; state.dirty = true; notify(String(configResult.value.warning), true); }
    } else setConnectionError(configResult.status === "rejected" ? configResult.reason.message : "本地服务没有返回有效配置。");
    if (statusResult.status === "fulfilled") { acceptStatus(statusResult.value); if (state.running) schedulePoll(); }
    else { state.stale = true; setConnectionError(statusResult.reason.message + " 当前检测状态未知，请重试或刷新页面。"); }
    render();
  }

  $$("[data-view]").forEach((button) => button.addEventListener("click", () => showView(button.dataset.view, true)));
  $$("[data-filter]").forEach((button) => button.addEventListener("click", () => setFilter(button.dataset.filter)));
  $(".brand").addEventListener("click", () => showView("check", true));
  window.addEventListener("hashchange", () => showView(location.hash.slice(1)));
  $("#settings-form").addEventListener("input", () => { state.dirty = formDiffers(); renderHero(); updateControls(); });
  $("#settings-form").addEventListener("submit", saveSettings);
  $("#reset-settings").addEventListener("click", () => { if (state.config) { fillForm(state.config); state.dirty = state.forceSave; render(); notify(state.forceSave ? "已恢复默认值，请核对后保存配置。" : "已撤销未保存的修改。"); } });
  $("#scan-button").addEventListener("click", startScan);
  $("#launch-button").addEventListener("click", launchClaude);
  $("#export-button").addEventListener("click", exportReport);
  window.addEventListener("beforeunload", (event) => { if (state.dirty) { event.preventDefault(); event.returnValue = ""; } });
  initialize();
})();
