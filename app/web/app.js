"use strict";

(() => {
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];
  const token = $('meta[name="session-token"]').content;
  const PUBLIC_REPOSITORY = "https://github.com/clm031102-source/claude-network-guide";
  const PUBLIC_RESOURCES = Object.freeze({
    beginner: { path: "docs/beginner-guide.md" },
    word: { path: "docs/downloads/防封指南_保姆联动版.docx", download: true },
    handoff: { path: "docs/agent-handoff.md" },
    prompt: { path: "prompts/带我完成配置.txt" },
  });

  function connectPublicLinks() {
    $$("[data-public-link]").forEach((link) => {
      const resource = PUBLIC_RESOURCES[link.dataset.publicLink];
      if (!resource) return;
      const path = resource.path.split("/").map(encodeURIComponent).join("/");
      const route = resource.download ? "raw/refs/heads/main" : "blob/main";
      link.href = `${PUBLIC_REPOSITORY}/${route}/${path}`;
    });
  }

  const statusNames = { pass: "已通过", warning: "需留意", fail: "未通过", unknown: "未验证" };
  const statusSymbols = { pass: "✓", warning: "!", fail: "×", unknown: "·" };
  const viewNames = { check: "本机体检", vps: "购买 VPS", residential: "购买住宅 IP", network: "配置网络", settings: "高级设置" };
  const initialChecks = [
    ["本机与代理识别", "自动读取电脑环境、代理客户端与本地连接。"],
    ["实际出口与网络归属", "报告实测出口以及可以获取的网络信息。"],
    ["TUN、DNS 与 UDP", "分别报告取得的证据，不用一种连接代替另一种。"],
    ["Claude 程序与启动条件", "核对程序位置及所有阻断条件。"],
  ];
  const state = { config: null, report: null, running: false, busy: false, loading: true, dirty: false, stale: false, autoScanAttempted: false, filter: "all", pollTimer: null, failures: 0 };
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
    document.title = view === "check" ? "Claude 本机体检" : `Claude 本机体检 · ${viewNames[view]}`;
    if (location.hash !== `#${view}`) history.replaceState(null, "", `#${view}`);
    if (focus) { $("#main-content").focus({ preventScroll: true }); window.scrollTo({ top: 0, behavior: "auto" }); }
  }

  function readForm() {
    return {
      expected_ip: $("#expected-ip").value.trim(),
      proxy_url: $("#proxy-url").value.trim(),
      claude_path: $("#claude-path").value.trim(),
      residential_ip_confirmed: false,
      require_tun: $("#require-tun").checked,
      require_udp: $("#require-udp").checked,
    };
  }

  function fillForm(config) {
    $("#expected-ip").value = config.expected_ip || "";
    $("#proxy-url").value = config.proxy_url || "";
    $("#claude-path").value = config.claude_path || "";
    $("#require-tun").checked = config.require_tun !== false;
    $("#require-udp").checked = Boolean(config.require_udp);
  }

  function formDiffers() {
    if (!state.config) return false;
    return Object.entries(readForm()).some(([key, value]) => key !== "residential_ip_confirmed" && value !== state.config[key]);
  }

  function validateSettings(config) {
    if (config.proxy_url) {
      let url;
      try { url = new URL(config.proxy_url); } catch { throw new Error("请填写完整的 HTTP 代理地址，或清空以自动识别。"); }
      if (url.protocol !== "http:") throw new Error("此处需要 http://主机:端口 格式的代理地址，或留空自动识别。");
      if (url.username || url.password) throw new Error("本地代理地址不能包含用户名或密码。请在网络客户端中管理上游凭据。");
    }
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

  function detectedString(key) {
    const value = state.report?.detected?.[key];
    return typeof value === "string" ? value.trim() : "";
  }

  function detectedList(key) {
    const value = state.report?.detected?.[key];
    return Array.isArray(value) ? value.filter((item) => typeof item === "string" && item.trim()) : [];
  }

  function renderDetected() {
    const detected = state.report?.detected || {};
    const controller = detected.controller && typeof detected.controller === "object" ? detected.controller : {};
    const awaiting = !state.report;
    const pending = state.loading || state.running ? "正在识别…" : "尚未识别";
    const adapters = detectedList("tun_adapters");
    const clients = detectedList("clients");
    $("#detected-caption").textContent = state.report ? state.stale || state.dirty || state.running ? "显示上次识别事实，等待更新" : "来自本次本机读取结果" : "读取完成后自动显示";
    $("#detected-os").textContent = detectedString("os") || (awaiting ? pending : "系统信息未知");
    $("#detected-locale").textContent = `时区：${detectedString("timezone") || "未知"} · 语言：${detectedString("language") || "未知"}`;
    $("#detected-proxy").textContent = detectedString("proxy_url") || (awaiting ? pending : "未识别到 HTTP 代理");
    $("#detected-proxy-source").textContent = detectedString("proxy_source") ? `来源：${detectedString("proxy_source")}` : awaiting ? "自动读取本机代理设置" : "没有取得可用的代理来源信息";
    $("#detected-tun").textContent = controller.tun_enabled === true ? "控制器报告已开启" : controller.tun_enabled === false ? "控制器报告未开启" : adapters.length ? "识别到 TUN 网卡" : awaiting ? pending : "TUN 状态未知";
    $("#detected-tun-detail").textContent = adapters.length ? adapters.join("、") : controller.tun_enabled === true ? "开启状态不等于应用流量已通过" : "未取得可确认的 TUN 网卡信息";
    $("#detected-claude").textContent = detectedString("claude_path") ? "已找到程序位置" : awaiting ? pending : "未识别到 Claude";
    $("#detected-claude-path").textContent = detectedString("claude_path") || (awaiting ? "自动查找本机安装位置" : "查看下方程序检查的处理建议");
    $("#detected-ip-preview").textContent = detectedString("observed_ip") ? `实测出口 ${detectedString("observed_ip")}` : awaiting ? "出口尚未检测" : "实测出口未知";
    const routes = Array.isArray(detected.default_routes) ? detected.default_routes.filter((route) => route && typeof route === "object").map((route) => {
      const part = (key) => typeof route[key] === "string" && route[key] ? route[key] : "未知";
      return `${part("destination")} → ${part("next_hop")} · ${part("interface")}${Number.isFinite(route.metric) ? ` · 优先级 ${route.metric}` : ""}`;
    }) : [];
    const transport = { named_pipe: "本机命名管道", http: "本地 HTTP" }[controller.transport] || "连接方式未知";
    const mode = { rule: "规则模式", global: "全局模式", direct: "直连模式" }[controller.mode] || "模式未知";
    const controllerText = controller.status === "connected" ? `已连接 · ${transport} · ${mode}` : "未取得可用的本机控制器信息";
    const rows = [
      ["实测出口", detectedString("observed_ip") || "未知"],
      ["识别到的客户端", clients.join("、") || "未识别"],
      ["Claude 程序位置", detectedString("claude_path") || "未识别"],
      ["DNS 服务器", detectedList("dns_servers").join("、") || "未知"],
      ["默认路由", routes.join("\n") || "未知"],
      ["本机控制器", controllerText],
      ["DNS 模式", typeof controller.dns_mode === "string" && controller.dns_mode ? controller.dns_mode : "未知"],
      ["控制器内 Claude 连接", Number.isFinite(controller.claude_connection_count) ? `${controller.claude_connection_count} 条（仅本次读取）` : "未知"],
    ];
    const list = $("#detected-details");
    list.replaceChildren();
    rows.forEach(([label, value]) => {
      const row = document.createElement("div");
      const term = document.createElement("dt"); term.textContent = label;
      const description = document.createElement("dd"); description.textContent = awaiting ? "等待读取" : value;
      row.append(term, description); list.append(row);
    });
  }

  function updateControls() {
    const locked = state.running || state.busy || state.loading;
    const canLaunch = !locked && !state.dirty && !state.stale && state.report?.can_launch === true;
    $("#scan-button").disabled = locked || state.dirty || !state.config;
    $("#scan-button").classList.toggle("is-loading", state.running);
    $("#scan-button span").textContent = state.running ? "正在检测…" : state.report || state.stale ? "重新检测" : "开始检测";
    $("#scan-hint").textContent = state.running ? "正在读取本机配置并检测网络" : state.dirty ? "保存或撤销高级设置中的修改" : "Claude 由你手动启动";
    $("#launch-button").disabled = !canLaunch;
    $("#launch-button span").textContent = state.busy ? "正在处理…" : "启动 Claude";
    $("#export-button").disabled = !state.report || locked || state.stale || state.dirty;
    $("#save-settings").disabled = locked || !state.config || !state.dirty;
    $("#reset-settings").disabled = locked || !state.dirty;
    $$("#settings-form input").forEach((input) => { input.disabled = state.running || state.busy || state.loading; });
    $("#stale-banner").hidden = !state.stale && !state.dirty;
    $("#stale-banner").textContent = state.dirty ? "高级设置有未保存的修改。保存后会重新检测，也可以撤销修改。" : state.running ? "正在获取新的检测结果。检测完成前，之前的结果不能用于启动判断。" : "当前结果已停用。请重新检测，更新启动判断。";
    $("#config-dot").classList.toggle("dirty", state.dirty);
    $("#save-state").textContent = state.loading ? "读取配置中…" : !state.config ? "暂时无法读取配置" : state.dirty ? "有未保存的修改" : "留空的项目使用自动识别";
    $("#current-proxy").textContent = detectedString("proxy_url") || (state.report ? "未识别到 HTTP 代理" : "等待自动识别");
    $("#checks-list").setAttribute("aria-busy", String(state.running));
    if (state.running) $("#launch-description").textContent = "正在检测当前环境。请等待全部结果返回。";
    else if (state.dirty || state.stale) $("#launch-description").textContent = "当前结果需要更新。保存或撤销设置修改，再重新检测。";
    else if (canLaunch) $("#launch-description").textContent = "本次检测满足启动条件。点击启动时会再做一次新检测。";
    else if (state.report) $("#launch-description").textContent = "当前未满足启动条件。请查看检测中的阻断项和处理建议。";
    else $("#launch-description").textContent = "先完成检测。只有满足启动条件，按钮才会可用。";
  }

  function renderHero() {
    const hero = $("#status-hero");
    const icon = $("#hero-status-icon");
    const counts = { pass: 0, warning: 0, fail: 0, unknown: 0 };
    getChecks().forEach((check) => { counts[validStatus(check.status)]++; });
    let mode = "idle", kicker = state.loading ? "正在连接本机服务" : "尚未取得检测结果", title = state.loading ? "准备读取本机配置" : "本机体检等待开始", detail = "自动识别当前环境，无需预先填写配置。未验证的项目会如实保留。";
    if (state.running) { mode = "running"; kicker = "正在获取本机证据"; title = "正在读取本机配置并检测网络"; detail = "自动识别电脑、代理、TUN 与 Claude，随后显示本次全部检测结果。"; }
    else if (state.stale || state.dirty) { mode = "warning"; kicker = "结果需要更新"; title = "配置已改变，请重新检测"; detail = "上一次结果不再用于启动判断。保存当前设置后，再运行一次检测。"; }
    else if (state.report) {
      if (state.report.can_launch === true) { mode = "pass"; kicker = "本次启动条件已满足"; title = "已完成检查，可以尝试启动"; detail = counts.warning || counts.unknown ? "仍有需留意或未验证项目，请先查看具体证据与建议。" : "可验证的项目已完成检查。启动时仍会重新核对当前环境。"; }
      else if (counts.fail) { mode = "fail"; kicker = "体检已完成 · 存在需要处理的项目"; title = "本机环境有待处理的问题"; detail = "识别事实与检测结果已列在下方。查看未通过项目，按建议处理后重新检测。"; }
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

  function render() { renderHero(); renderDetected(); renderChecks(); updateControls(); }

  function acceptStatus(data) {
    const wasRunning = state.running;
    state.running = data.running === true;
    if (data.report && typeof data.report === "object") state.report = data.report;
    else if (!state.running) state.report = null;
    state.stale = state.running;
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
    state.running = true;
    state.stale = true;
    render();
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
      else if (!error.status) { state.running = true; schedulePoll(1200); setConnectionError(error.message + " 正在核对本机检测状态。"); }
      else { state.running = false; notify(error.message, true); }
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
      state.stale = true;
      state.report = null;
      notify("高级设置已保存，正在按当前设置重新检测。");
      showView("check", true);
    } catch (error) { notify(error.message, true); }
    finally { state.busy = false; render(); }
    if (!state.dirty) await startScan();
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
      state.config = { expected_ip: "", proxy_url: "", claude_path: "", residential_ip_confirmed: false, require_tun: true, require_udp: false, ...config };
      fillForm(state.config);
      if (configResult.value.warning) notify(String(configResult.value.warning), true);
    } else setConnectionError(configResult.status === "rejected" ? configResult.reason.message : "本地服务没有返回有效配置。");
    if (statusResult.status === "fulfilled") { acceptStatus(statusResult.value); if (state.running) schedulePoll(); }
    else { state.stale = true; setConnectionError(statusResult.reason.message + " 当前检测状态未知，请重试或刷新页面。"); }
    render();
    if (state.config && statusResult.status === "fulfilled" && !state.running && !state.report && !state.autoScanAttempted) {
      state.autoScanAttempted = true;
      await startScan();
    }
  }

  $$("[data-view]").forEach((button) => button.addEventListener("click", () => showView(button.dataset.view, true)));
  $$("[data-filter]").forEach((button) => button.addEventListener("click", () => setFilter(button.dataset.filter)));
  $(".brand").addEventListener("click", () => showView("check", true));
  window.addEventListener("hashchange", () => showView(location.hash.slice(1)));
  $("#settings-form").addEventListener("input", () => { state.dirty = formDiffers(); renderHero(); updateControls(); });
  $("#settings-form").addEventListener("submit", saveSettings);
  $("#reset-settings").addEventListener("click", () => { if (state.config) { fillForm(state.config); state.dirty = false; render(); notify("已撤销未保存的修改。"); } });
  $("#scan-button").addEventListener("click", startScan);
  $("#launch-button").addEventListener("click", launchClaude);
  $("#export-button").addEventListener("click", exportReport);
  window.addEventListener("beforeunload", (event) => { if (state.dirty) { event.preventDefault(); event.returnValue = ""; } });
  connectPublicLinks();
  initialize();
})();
