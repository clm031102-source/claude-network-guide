# Claude 网络指南 账号工具 · Windows 版 (Beta)

> 本目录是独立保留的高级组件源码参考，来源见 [NOTICE](../../../NOTICE.md)。主流程请使用[根目录的本地检测工作台](../../../README.md)。本仓库尚未发布 Windows 原生安装包；不要将保留的构建与更新能力理解为已有可下载版本。

> ⚠️ **本版本为 Beta,未经大规模真机测试**。核心逻辑移植自 macOS 稳定版,但 Windows 环境差异大,遇到问题请到 [Issues](https://github.com/clm031102-source/claude-network-guide/issues) 反馈。

## 系统要求

- Windows 10 / 11 (64 位)
- PowerShell 5.1+（Windows 自带,无需安装）
- 代理客户端（需支持 TUN 模式），安装器会自动探测并写入 `$PROXY_MODE`:
  - **Clash Verge** —— 存在配置目录即识别，可由「一键修复」按当前模式配置置顶规则
  - **sing-box / ClashX / Surge / WireGuard** —— 按进程或服务识别
  - **其他 TUN 客户端**（Astrill / OpenVPN / Tailscale 等）—— 安装时选 `other`
  - **auto** —— 任一已知进程/服务命中即视为在线（未识别到客户端时的默认选项）
- Claude 桌面版 Windows
- 安装时需要**管理员权限**一次（注册守护任务 / 锁定时区 / 关闭 IPv6）

> 代理模式同时写入 `%USERPROFILE%\.claude-switcher\proxy-mode.txt`，保镖按这个文件分派检测逻辑；缺失时按旧版 Clash Verge 行为处理。

## 安装

1. 先开启代理（TUN 模式）。安装器会检查出口不能是 `CN`，并按当前出口国家写入 `$COUNTRY_TARGET`；需要美国出口时请先把节点切到美国。地区识别会依次尝试 ipinfo / ipapi / ifconfig / Cloudflare trace，全部失败时可手动选择国家；也可设 `$env:FORCE=1` 强制按 US 继续
2. 进入完整仓库的 `modules/switcher/windows/` 目录，阅读安装影响后，按需右键该目录的 `install.ps1` →「使用 PowerShell 运行」，或在管理员 PowerShell 中执行
3. 如果提示禁止运行脚本,先执行一次:
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   ```
4. 按提示确认/选择代理客户端，走完流程后桌面会出现「Claude网络指南账号工具」快捷方式

## 更新

本仓库目前没有发布本组件的原生 Release，因此当前没有可下载安装的更新。检查到 GitHub 的“尚无 Release”响应时，界面会显示“暂无可用原生更新”。本版本使用源码安装；未来只有发布了匹配的 Windows 压缩包和校验清单，下面保留的更新流程才有可用资产。

更新机制源码保留了以下能力：

- **自动检查**：启动后后台调用 `check-update`，不阻塞界面；24 小时缓存命中时直接显示提示条，不重复打扰
- **一键更新**：点「一键更新」后自动下载 Windows zip 与 `SHA256SUMS-release.txt`，SHA256 校验通过才替换 `%USERPROFILE%\.claude-switcher` 下的 `claude-switch.ps1` / `claude-bodyguard.ps1` / `SwitcherUI.ps1`
- **保留配置**：更新前读取旧脚本的 `$PROXY_MODE` / `$COUNTRY_TARGET` / `$TZ_TARGET` / `$PROXY_GROUP`，写入新脚本对应行
- **备份与回滚**：替换前备份到 `backup-<当前版本>-<时间戳>\`；任一步失败会自动回滚并提示原因，旧版本继续可用
- **无需管理员**：更新只改当前用户目录，不弹 UAC；替换后重启 `ClaudeBodyguard` 计划任务并自动重启界面
- **稍后与手动检查**：点「稍后」会隐藏提示条，24 小时内不再自动提示；底部「检查更新」会清除缓存并立即检查一次

正式打包时，版本号来自 zip 根目录的 `VERSION` 文件，安装后保存在 `%USERPROFILE%\.claude-switcher\version.txt`。组件内嵌套的 release 工作流是参考文件，当前不会自动在本仓库发布安装包。**该更新流程尚未经过 Windows 真机验证**，遇到问题请到 Issues 反馈。

## 多代理客户端支持

| 客户端 | `$PROXY_MODE` | 存活判定 | 说明 |
|---|---|---|---|
| Clash Verge | `clash-verge` | `verge-mihomo` 进程 + TUN | 按 Clash 模式自动配置规则（全局/直连跳过） |
| sing-box | `sing-box` | `sing-box` 进程 + TUN | 置顶规则需自行配置 |
| ClashX | `clashx` | `ClashX` 进程 + TUN | 置顶规则需自行配置 |
| Surge | `surge` | `Surge` 进程 + TUN | 置顶规则需自行配置 |
| WireGuard | `wireguard` | `WireGuardTunnel*` 服务 + TUN | 置顶规则需自行配置 |
| 其他 TUN 客户端 | `other` | 仅 TUN | 不要求特定进程，避免误杀 |
| 自动 | `auto` | 任一已知进程/服务 + TUN | 保镖在 `auto` 下同样只查 TUN |

TUN 判定顺序：先看是否存在 `198.18.x.x` 假 IP（Clash 系 fake-ip）；没有则回退到任意处于 `Up` 状态、描述匹配 `TAP/TUN/WireGuard/Wintun/VPN/Tailscale` 的虚拟网卡。198.18 命中时保持原来的 `TUN网卡=ok`；回退命中时显示 `TUN网卡=ok:通用虚拟网卡`。

## Clash 规则与全局模式

「一键修复」会先识别 Clash 当前模式（Mihomo API `/configs`，失败再读 `clash-verge.yaml` / `verge.yaml` 的 `mode:`），再决定是否动规则：

- **全局 / 直连模式**：规则本来就不生效，修复不写 `Merge.yaml`，也不写 `Script.js`；只有发现旧版遗留的 Merge 规则时才清理并重启一次 Clash。没有遗留时不改动任何配置。
- **规则模式**：只写 `profiles\Script.js` 的托管块（`// >>> claude-switcher managed rules >>>`），不再写 `Merge.yaml`。写入前备份，重启后通过内核 `/rules` 验证前 16 条规则；验证失败会自动从备份回滚 `Script.js`。规则模式需要在 Clash Verge 中启用「全局扩展脚本」，否则验证会失败并回滚。
- **无法识别模式**：跳过规则修改，避免误伤。
- 安装器不再写任何规则；安装完成后请打开切换器点一次「一键修复」完成配置。

旧版切换器写进 `Merge.yaml` 的 `prepend-rules`、单独成行的 `---` 和重复顶层键会被自动备份并清理，不会再写回。全局模式下如果 TUN 已经被旧配置破坏，清理后的那次重启通常即可恢复。

「一键修复」的规则模式/清理结果会显示在界面 Banner；检查列表的「规则置顶」也会同步显示 `ok` / `warn` / `fail`。

## 与 macOS 版的差异（注意事项）

> macOS 版支持 Clash Verge / Shadowrocket / sing-box / ClashX / Surge 与地区自适应（按出口国家自动锁定时区+地区格式，换节点后 `set-region` 一键重配）。Windows 版已对齐多客户端检测，但 **Shadowrocket 仅 macOS 可用**；Windows 的时区映射表目前覆盖美国主要时区、加拿大多伦多/温哥华、日本、韩国、新加坡、台湾、香港、英国、德国、法国、澳大利亚（悉尼/墨尔本），其他时区会回退到 `Eastern Standard Time`，可在脚本头部手动修改 `$TZ_TARGET`。`地区` 检查目前仍固定为 `en-US`，不随出口国家调整。换国家后 Windows 版暂无 `set-region`，需要重跑安装器（会重新写入 `$COUNTRY_TARGET` / `$TZ_TARGET`）或手动修改脚本头部。macOS 的 `update` 命令与 12 小时自动检查、48 小时 IP 审查未移植到 Windows；Windows 另有一套启动检查 + 一键更新，见上文「更新」。

| 项目 | 说明 |
|---|---|
| 时区名称 | Windows 用 `Eastern Standard Time` 这类 ID,安装器会自动把 IP 城市映射过去 |
| 保镖频率 | 计划任务登录启动,隐藏窗口常驻,每 10 秒巡检(与 Mac 一致) |
| 保镖判定 | 显式客户端模式按「客户端进程/服务 + TUN」；`auto` / `other` 只查 TUN |
| IPv6 | 关闭的是所有网卡的 ms_tcpip6 绑定;要恢复: `Enable-NetAdapterBinding -ComponentID ms_tcpip6` |
| SmartScreen | 首次运行可能弹"Windows 已保护你的电脑" → 点「更多信息」→「仍要运行」 |
| 账号数据目录 | Windows 版在 `%APPDATA%\Claude`(与 macOS 路径不同,逻辑相同) |
| 卸载 | 计划任务里删掉 ClaudeBodyguard,删除 `%USERPROFILE%\.claude-switcher` 和桌面快捷方式即可 |

## 已知限制

- 设备指纹体检（`fingerprint`）与 Web 检测页为 macOS/浏览器能力，Windows 版暂未内置，可用 Web 版检查 Canvas/WebGL。
- 界面是 WPF 重写的第一版,样式以 Mac 版为准对齐,细节可能有出入
- Clash Verge 的 TUN 开关在 Windows 上如果被更新重置,目前需要手动在设置里重新打开(一键修复会提示)
- 账号快照切换前请确保 Claude 已完全退出(托盘图标也要退出)
- 旧版切换器可能在 `Merge.yaml` 留下 `prepend-rules` / 多文档 `---`，导致 Clash 报 `Merge.yaml ... containing more than one document` 或 TUN 异常。当前「一键修复」会自动备份并清理这些遗留内容，规则模式改用 `Script.js`，不再写 `Merge.yaml`；全局/直连模式跳过规则，只在需要清理旧 Merge 时重启一次
- 「一键修复」在规则模式写入/清理后会重启 Clash Verge（任务栏/托盘图标会短暂消失，属正常）；全局模式仅在清理历史 Merge 时重启。规则模式重启后会验证内核 `/rules` 前 16 条，失败自动回滚 `Script.js`；控制接口不可用时只提示“无法验证”，不会谎报成功
- **`auto` / `other` 的 TUN 判定是通用启发式**:只要有一块处于 `Up` 状态、描述里带 `TAP/TUN/WireGuard/Wintun/VPN/Tailscale` 的网卡就会判定 TUN 在线,无法区分"代理隧道已接管"还是"某块虚拟网卡只是存在"。可能误判(例如虚拟网卡残留、其他 VPN 适配器),此时请把 `$PROXY_MODE` 改成实际客户端后重跑安装器;若仍不稳定,可在计划任务中暂停 `ClaudeBodyguard`
- **非 Clash 客户端**:保镖已按客户端模式分派,不再因缺少 `verge-mihomo` 每 10 秒误杀 Claude;但 `规则置顶` 检查只在 Clash Verge 下按模式判定（全局/直连 ok、规则模式验证 `Script.js` 与内核），非 Clash 用户需要自行在客户端里为 `claude.ai` / `anthropic.com` 等域名配置置顶/直连规则。`DNS` 检查也按 `198.18.x.x` 判断,使用非 fake-ip TUN 时可能显示 `fail`,不代表代理不可用
- 系统区域为 zh-CN(控制台代码页 936/GBK)时,界面通过读取核心脚本落盘的 `last-check.txt`(UTF-8)展示检查结果,不受代码页影响;若你看到"检测输出不完整(3/14)"且用的是旧版界面,请更新到最新版
