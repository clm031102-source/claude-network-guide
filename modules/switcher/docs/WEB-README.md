# Web 版环境检测

本文件说明独立保留的浏览器侧检测页源码。它是纯静态页面，无构建、无第三方 JS/CSS 依赖；可自行本地预览或部署，当前本仓库没有发布在线站点。首次使用请从[主教程和新的本地工作台](../../../README.md)开始；本页旧版检测逻辑及评分只作高级参考。

源码目录：[modules/switcher/docs](https://github.com/clm031102-source/claude-network-guide/tree/main/modules/switcher/docs)。GitHub 文件浏览页不会运行其中的检测程序。

## 检测项

| # | 检测项 | 内容 | 判定 |
|---|---|---|---|
| 01 | 出口 IP / 归属 | `ipinfo.io/json` 优先；失败回退 `www.cloudflare.com/cdn-cgi/trace` | 成功 `ok`；仅兜底成功 `warn`；全部失败 `fail` |
| 02 | 地区一致性 | 浏览器时区、UTC 偏移、`navigator.language(s)` 与出口国家比对 | 时区不符、语言不符或缺少出口时区 `warn`；国家无语言映射时仅展示 |
| 03 | WebRTC 泄漏 | 通过 Google / Cloudflare STUN 收集候选，解析 `srflx` / `relay` 等公网地址并与出口 IP 比对 | 仅出口 IP 或 mDNS 混淆 `ok`；额外公网 IP `fail`；无候选 `warn` |
| 04 | IPv6 暴露 | `api6.ipify.org` 3 秒超时探测，必要时用 ipinfo 查询 IPv6 归属 | 不可达 `ok`；可直连且归属不似代理 `fail`；归属看似代理或未知 `warn` |
| 05 | DNS 泄漏（近似） | 并行请求 `1.1.1.1/cdn-cgi/trace` 与 `dns.google/resolve` | 均为可达 `ok`，否则 `warn`；不做 `fail` |
| 06 | 浏览器指纹展示 | Canvas 哈希、WebGL vendor/renderer、屏幕、DPR、色彩深度、platform、CPU 核心、设备内存 | 仅展示，固定 `ok`，不阻断 |
| 07 | 检测结论 | 按 `fail` 数给出总评，并列出失败/注意项 | 0 fail = 环境基本合规；≥1 fail = 高风险 |

评分仅为页面内的粗略参考：`100 - fail×25 - warn×6`，最低 0 分。

## 本地预览

必须通过 HTTP 访问。`file://` 下浏览器会拦截跨域请求，页面虽能打开但检测结果不可用。

```bash
cd claude-network-guide
python3 -m http.server 8000 --bind 127.0.0.1 --directory modules/switcher/docs
# 打开 http://127.0.0.1:8000
```

## 部署到 GitHub Pages

本仓库尚未启用这个页面的公开托管。需要公开部署时，应单独配置 GitHub Pages 工作流，将 `modules/switcher/docs/` 上传为站点产物，再用 Pages 返回的实际网址验收。不要把 GitHub 文件目录 URL 当成站点地址，也不要选择不存在的 `/web` 发布目录。

本组件内保留的 `.github/workflows/` 属于源码参考；嵌套目录中的工作流不会作为仓库根工作流自动运行。本次整合没有发布此站点。

## 隐私说明

- 页面不设置 Cookie、不写 `localStorage`/`sessionStorage`、不引入分析或追踪脚本，所有状态只在当前页面内存中。
- 检测请求只发往以下公共 API：`ipinfo.io`、`www.cloudflare.com`、`1.1.1.1`、`dns.google`、`api6.ipify.org`。
- WebRTC 检测使用 `stun:stun.l.google.com:19302` 与 `stun:stun.cloudflare.com:3478` 收集候选地址。
- 上述公共服务会看到你的出口 IP，这是完成检测的必要条件；检测结果不会上传到本项目服务器。
- 所有外部文本（IP、org、DoH 结果等）均通过 `textContent` 写入 DOM；CSP 将 `script-src` 限制为 `'self'`。

## 能力边界

- 只评估**浏览器侧**信号，不替代桌面版的 14 项审计。
- 不检测 TUN 网卡、Kill-Switch 保镖、进程级泄漏、系统路由表、系统 DNS 配置、系统代理内核。
- 地区一致性只读浏览器时区与语言，不代表系统全部区域设置。
- DNS 项是近似检测：浏览器无法读取系统 DNS，DoH 可达不能证明系统 DNS 未泄漏，建议配合桌面版 Fake-IP / DNS 隧道校验。
- WebRTC / IPv6 结果会受浏览器策略、代理是否接管 UDP、节点是否支持 IPv6 影响。
- 页面不做任何自动修复，也不绕过任何服务条款。

## 文件结构

```
docs/
├── index.html   # 页面结构、CSP、静态文案
├── style.css    # 暗色 + 紫色品牌样式，移动端优先
├── app.js       # 全部检测逻辑与安全 DOM 渲染
├── favicon.svg  # 品牌图标
└── WEB-README.md # 本文件
```

修改后无需构建，刷新页面即可。浏览器要求：支持 `fetch`、`AbortController`、`RTCPeerConnection`、`Intl.DisplayNames` 的现代版本（Chrome / Edge / Safari / Firefox 近两年版本）。
