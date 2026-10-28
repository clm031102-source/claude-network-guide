# Clash Verge WebRTC 泄露修复手册（给 AI 助手照做）

> **这份文档是做什么的**：在 Windows 或 Mac 上用 Clash Verge Rev 的人，如果检测网站提示「WebRTC 泄露」，并且显示的是国内 IP，就按这份手册修。修好后 WebRTC 照常可用（网页视频、语音不受影响），只是出口变成你的服务器 IP。
>
> **怎么用**：把这个文件发给你的 AI 助手（Claude、ChatGPT、Codex 等都可以），对它说「按这份手册帮我修 WebRTC 泄露」。它会一步一步告诉你点哪里、运行什么命令，并根据结果判断下一步。手册写得很细，能力一般的模型照着做也能修好。你也可以自己从第 1 节开始照做。
>
> **不需要改服务器和订阅**，所有操作都在你自己的电脑上。

> 适用：Windows / macOS 上的 **Clash Verge Rev**（按 v2.5.8 的界面文字编写）。
> 症状：检测网站显示「WebRTC 泄露」「UDP 出口异常」，并且出口 IP 的归属地是中国。

---

## 0. 给 AI 助手的规则（先读完，再开始）

1. **严格按顺序执行**：第 1 步 → 第 2 步 → …… 不跳步，不自己发明步骤。
2. **一次只让用户做一件事**。说完一步就等用户回复结果，再说下一步。
3. **按钮名称照抄本手册里「」中的文字**，不要改写，否则用户会找不到。
4. 每一步都写了「用户应该看到什么」。用户看到的和手册不一样时，去 **第 7 节 故障对照表** 找对应的一行，不要猜。
5. 能运行命令时，用附录里的命令自己检测；不能运行命令时，把命令原样发给用户，请用户运行后把输出贴回来。
6. 记录每次检测的结果（第 3 节的表格），最后要拿修复前后的结果做对比。

### 禁止事项（任何情况下都不要做）

- ❌ 不要让用户打开「DNS 覆写」。
- ❌ 不要凭感觉开关 Clash Verge 里的「IPv6」开关。它该开还是该关，只按 4.5 的检测结果决定。
- ❌ 不要修改、删除或重新导入订阅；不要改订阅里的任何规则。
- ❌ 不要让用户安装其他代理软件、加速器、VPN。
- ❌ 不要索要或复述订阅链接、密码、密钥；也不要让用户把它们贴到对话里。
- ❌ 不要把「全局模式」当成修复方法。保持「规则」模式。
- ❌ **不要禁用或限制浏览器的 WebRTC。** 本手册的目标是「WebRTC 照常可用，只是出口变成代理 IP」。不要装任何 WebRTC 限制类扩展（例如 WebRTC Network Limiter、WebRTC Leak Prevent、WebRTC Control），不要改 Firefox `about:config` 里任何 `media.peerconnection` 开头的设置，不要改 `chrome://flags`，不要在 uBlock Origin 等广告拦截扩展里勾选「防止 WebRTC 泄露」。如果检测网站显示「WebRTC 不可用」「检测不到 IP」，那不是修好了，是被禁用了，要按第 9 节恢复。

---

## 1. 先判断适不适用

问用户三个问题：

| 问题 | 答案 | 怎么办 |
|---|---|---|
| 你用的是什么设备？ | Windows 电脑 或 Mac 电脑 | 继续 |
| | iPhone / iPad（Shadowrocket） | **停止**。Shadowrocket 以 VPN 方式运行，本来就会接管 UDP，不适用本手册 |
| | 安卓、Linux、路由器 | **停止**，本手册不覆盖 |
| 你用的是什么代理软件？ | Clash Verge / Clash Verge Rev | 继续 |
| | 其他软件 | **停止**，本手册不覆盖 |
| 电脑上有没有同时开着别的 VPN、游戏加速器、公司 VPN？ | 有 | 先请用户把它们完全退出，再继续 |
| | 没有 | 继续 |

---

## 2. 原理（用这段话向用户解释，可以照念）

> Clash Verge 默认的「系统代理」只接管浏览器的网页流量（TCP）。浏览器的 WebRTC 功能会用 UDP 去问外部服务器「我的 IP 是多少」，这个 UDP 请求不走系统代理，直接从你的本地网络出去，所以网站能看到你的真实 IP。
> 修复方法是打开 Clash Verge 的「虚拟网卡模式」（也叫 TUN 模式），让所有流量（包括 UDP）都进入 Clash，再按规则分流。

---

## 3. 第 1 步：修复前检测（记录基线）

### 3.1 浏览器出口（用户来做）

请用户在**浏览器**里打开 `https://ipinfo.io`，告诉你页面上的 `ip` 和 `country`。

- `country` 是 `CN`：说明代理本身就没生效，**停止本手册**，先让用户检查节点能不能用。
- `country` 不是 `CN`：记下这个 IP，叫它 **「浏览器 IP」**。后面所有检测都要和它比。

### 3.2 三项命令检测

按用户的系统运行附录 A（Windows）或附录 B（Mac）里的三条命令，把结果填进这张表：

| 检测项 | 命令输出 | 归属国家 | 判断 |
|---|---|---|---|
| B. 命令行出口 IP | | | |
| C. WebRTC / STUN 出口 | | | |
| D. IPv6 出口 | | | |

### 3.3 怎么判断

| 结果 | 结论 | 下一步 |
|---|---|---|
| B 的国家是 `CN` | 虚拟网卡模式**没开**（只开了系统代理）。这就是泄露原因 | 去第 4 步修复 |
| B 不是 `CN`，C 是 `CN` | TUN 开了，但 UDP 没走代理 | 去第 7 节查「C 仍是中国 IP」 |
| B、C 都不是 `CN`，D 是中国 IPv6 | IPv6 绕过了 TUN | 去第 7 节查「D 是中国 IPv6」 |
| B、C 都不是 `CN`，D 也正常 | 电脑这边已经没有泄露 | 去第 8 节，检查检测网站本身 |

**怎么认中国 IP**
- IPv4：用附录里的「查国家」命令，输出 `CN` 就是中国。
- IPv6：以 `240e:`、`2408:`、`2409:` 开头的基本都是中国电信、联通、移动的地址；拿不准就用「查国家」命令。

---

## 4. 第 2 步：修复（打开虚拟网卡模式）

一次只说一小步，每步等用户确认。

### 4.1 更新订阅

> 请打开 Clash Verge，点左侧「订阅」，在你正在用的那个订阅上点右键（或点它的「⋯」菜单），选「更新」。

用户应该看到：更新成功的提示，订阅的更新时间变成刚才。

### 4.2 安装服务

> 请点左侧「设置」，在「系统设置」区域找到「虚拟网卡模式」。

- 如果它旁边提示「TUN 模式需要服务模式，请先安装服务」，或者开关是灰的：
  > 请点「安装服务」。Windows 会弹出管理员确认，点「是」；Mac 会让你输入开机密码。
  >
  用户应该看到：「已成功安装服务」。
- 如果没有这个提示：跳过这一小步。

### 4.3 打开虚拟网卡模式

> 请把「虚拟网卡模式」的开关打开。

用户应该看到：首页显示「TUN 模式已启用，应用将通过虚拟网卡访问网络」。

- 「系统代理」开关**不用动**，开着或关着都不影响这次修复。

### 4.4 打开严格路由（只有 Windows 做，Mac 跳过）

> 请点「虚拟网卡模式」旁边的设置图标（齿轮），在弹出的窗口里打开「严格路由」，其他选项都不要改，然后点保存（或确定）。

### 4.5 检查两个开关

> 请在「设置」的「Clash 设置」区域，找到「IPv6」和「DNS 覆写」这两个开关。

**「DNS 覆写」：必须关闭。** 是开的就请用户关掉。原因：订阅里已经带了 DNS 配置，覆写会把它替换掉。

**「IPv6」：先检测这个网络有没有 IPv6，再决定开还是关。** 运行附录里的 **E. 本机有没有 IPv6 地址**（附录 A 第 E 项是 Windows，附录 B 第 E 项是 Mac），按结果设置：

| E 的结果 | 「IPv6」开关 | 原因（可以照念给用户） |
|---|---|---|
| 列出了至少一个地址 | **打开** | 你的网络有 IPv6。开关关着时，IPv6 流量会绕过虚拟网卡直接出去，造成泄露 |
| 什么都没输出 | **关闭** | 你的网络没有 IPv6，本来就没有 IPv6 流量可以泄露。开关开着反而有坏处：Clash Verge 会给微信这类软件返回 IPv6 地址，它们连不上，也不会改用 IPv4。典型症状是**微信文字能发，图片和文件发不出去** |

- Clash Verge 的这个开关会**覆盖订阅里的 IPv6 设置**，所以要按检测结果设置，不能凭感觉。
- 改了「IPv6」开关后，请用户**完全退出微信、QQ 这类聊天软件再打开**（Windows：右下角托盘里也要退出；Mac：按 Command+Q）。
- **换了网络要重新检查**：比如从家里换到公司，或者连上手机热点，这个网络有没有 IPv6 可能不一样。

### 4.6 重启浏览器

> 请**完全退出**浏览器再重新打开（Windows：右下角托盘里也要退出；Mac：按 Command+Q），只关窗口不算。

---

## 5. 第 3 步：修复后复测

1. 再做一次 3.1：浏览器打开 `https://ipinfo.io`，确认 `country` 不是 `CN`。
2. 再跑一次附录里的 B、C、D 三条命令，填一张新表。

**通过标准（三条都满足才算修好）：**

| 检测项 | 通过条件 |
|---|---|
| B. 命令行出口 IP | 国家不是 `CN`（通常和「浏览器 IP」相同） |
| C. WebRTC / STUN 出口 | **必须拿到一个 IP**，并且国家不是 `CN`（通常和「浏览器 IP」相同）。输出 `STUN_EXIT=FAILED` 不算通过 |
| D. IPv6 出口 | 下面三种都算通过：输出 IPv4 地址且不是中国；报错或超时；输出 IPv6 地址但不是中国 |

- 全部通过：去第 6 节，用检测网站做最终确认。
- 有一项不通过：去第 7 节，按那一项查。

---

## 6. 第 4 步：用检测网站最终确认

请用户在浏览器里打开 `https://browserleaks.com/webrtc`，看两处：

1. **WebRTC 是否可用**：页面上方「WebRTC Support Detection」里，`RTCPeerConnection` 后面应该是 ✔。
2. **公网 IP**：「WebRTC IP Address Detection」里的「Public IP Address」应该显示一个 IP。

| 看到的情况 | 结论 | 下一步 |
|---|---|---|
| RTCPeerConnection 是 ✔，公网 IP 不是中国 IP（通常等于「浏览器 IP」） | **修复完成** | 用第 10 节的话术告诉用户 |
| RTCPeerConnection 是 ✔，公网 IP 是中国 IP | 还有泄露 | 去第 8 节 |
| RTCPeerConnection 是 ✘，或者公网 IP 一栏是空的、显示 n/a、检测不到 | **WebRTC 被禁用或限制了，不算修好** | 去第 9 节恢复，恢复后从第 5 节重新复测 |

如果用户最开始用的是别的检测网站，最后也在那个网站上再看一次，判断方法相同。

---

## 7. 故障对照表

| 现象 | 原因 | 处理 |
|---|---|---|
| 找不到「虚拟网卡模式」 | Clash Verge 版本太旧，或者装的不是 Clash Verge Rev | 请用户到官方发布页 `https://github.com/clash-verge-rev/clash-verge-rev/releases` 下载最新版覆盖安装，再从第 4 步开始 |
| 点「安装服务」失败 | 没有管理员权限，或被安全软件拦截 | Windows：右键 Clash Verge，选「以管理员身份运行」，再打开「虚拟网卡模式」（这种方式不需要安装服务）。Mac：重新点「安装服务」，密码输入正确 |
| 出现「由于服务不可用，TUN 模式已自动关闭」 | 服务没在运行 | 设置里先点「卸载服务」，再点「安装服务」，然后重新打开「虚拟网卡模式」 |
| 出现「已切换到普通模式（Sidecar），普通权限下无法使用 TUN」 | 服务拒绝以高权限运行 | 点提示里的「查看修复方法」照做；做不到时，Windows 用「以管理员身份运行」 |
| 打开 TUN 后所有网站都打不开 | 和别的 VPN、加速器冲突，或 Windows 防火墙拦截 | 退出其他 VPN 和加速器；Windows 防火墙弹窗时点「允许」；还不行就先关掉「严格路由」再试 |
| B 仍是中国 IP | TUN 没真正生效 | 确认首页显示「TUN 模式已启用」；没有就回到 4.2；有的话请用户重启电脑后再测 |
| C 仍是中国 IP（B 已正常） | UDP 没走代理 | ① 回到 4.1 重新更新订阅；② 在「代理」页面换一个节点再测；③ 打开「虚拟网卡模式」设置，把「TUN 模式堆栈」换成另一个选项（例如 Mixed 或 gVisor），保存后再测 |
| C 输出 `STUN_EXIT=FAILED` | UDP 发不出去或收不到回复。这样 WebRTC 也会用不了，**不算修好** | ① 再测一次；② 在「代理」页面换一个节点再测；③ 打开「虚拟网卡模式」设置，把「TUN 模式堆栈」换成另一个选项（例如 Mixed 或 gVisor），保存后再测；④ 仍失败，就如实告诉用户：当前网络或节点的 UDP 不通，需要换网络或联系节点提供者 |
| D 是中国 IPv6 | IPv6 绕过了虚拟网卡 | 能拿到中国 IPv6，说明网络有 IPv6，按 4.5「IPv6」开关应该是打开的，先确认它开着。仍是中国 IPv6，就在系统里关闭 IPv6：<br>**Windows**：控制面板 → 网络和共享中心 → 更改适配器设置 → 右键正在用的网卡 → 属性 → 取消勾选「Internet 协议版本 6 (TCP/IPv6)」→ 确定<br>**Mac**：系统设置 → 网络 → 正在用的 Wi-Fi 或以太网 → 详细信息 → TCP/IP →「配置 IPv6」选「仅本地链接」→ 好 |
| 开了严格路由后局域网打印机、NAS 或虚拟机连不上 | 严格路由会拦截部分本地流量 | 关掉「严格路由」。代价：Windows 偶尔可能出现 DNS 泄露 |
| 公司 VPN 和虚拟网卡模式冲突 | 两个软件都想接管网络 | 上班用公司 VPN 时临时关「虚拟网卡模式」，下班再打开 |
| 打开虚拟网卡模式后，微信文字能发，图片、文件发不出去，或朋友圈图片加载不出来 | 最常见的原因是网络没有 IPv6，「IPv6」开关却开着 | 按顺序做，每做一步就完全退出微信再打开，发一张图试试，能发了就停：<br>① 回到 4.5 重新运行 E。什么都没输出、「IPv6」开关却开着，就把它关掉<br>② 回到 4.1 更新订阅（订阅里有让微信海外服务器直连的规则）<br>③ 打开「虚拟网卡模式」设置，把「TUN 模式堆栈」换成 Mixed，保存<br>④ 只有 Windows：在同一个设置窗口里关掉「严格路由」，保存<br>⑤ 仍不行：如实告诉用户没修好。请用户打开 Clash Verge 左侧「连接」页面，发一张图，同时截下微信相关的连接，交给订阅提供者排查。**不要**用关闭虚拟网卡模式、禁用 WebRTC 的办法来代替 |

---

## 8. 命令都通过了，检测网站仍显示中国 IP

按顺序检查：

1. **浏览器没有完全退出**：回到 4.6，完全退出后再测。
2. **浏览器扩展干扰**：请用户开一个无痕窗口（Chrome/Edge：Ctrl+Shift+N；Mac：Command+Shift+N）再测。
3. **检测网站用的是国内 STUN 服务器**：有些国内检测网站会去问国内的 STUN 服务器（例如带 `miwifi`、`qq`、`bilibili`、`aliyun` 的地址）。在「规则」模式下，国内地址本来就直连，所以会显示国内 IP，这是规则的正常行为，不是软件没开好。
   - 判断方法：如果页面列出了 STUN 服务器地址，看是不是国内的；或者换 `https://browserleaks.com/webrtc` 再测。browserleaks 显示的是代理 IP，就说明修复是成功的。
   - 这种情况**到此为止**，向用户说明原因即可。**不要**为了让这类网站也显示代理 IP 而去禁用或限制 WebRTC，也不要切换成全局模式。

---

## 9. WebRTC 被禁用或限制了：怎么恢复

第 6 节显示 RTCPeerConnection 是 ✘，或者公网 IP 检测不到时，按下面检查。**以前**有人（或别的教程）可能装过扩展、改过设置来「防泄露」，要全部撤销。只撤销下面列出的项目，不要动别的设置。

**Chrome / Edge**
1. 地址栏输入 `chrome://extensions`（Edge 输入 `edge://extensions`）。
2. 找名字里带 **WebRTC** 的扩展（例如 WebRTC Network Limiter、WebRTC Leak Prevent、WebRTC Control、WebRTC Protect），点「移除」。
3. 如果装了 **uBlock Origin**：点它的图标 → 打开设置（齿轮）→ 在「隐私」里取消勾选「防止 WebRTC 泄露本地 IP 地址」。
4. 地址栏输入 `chrome://policy`（Edge：`edge://policy`）。如果列表里有 `WebRtcIPHandling` 或 `WebRtcUdpPortRange`，说明是电脑管理员或别的软件设置的策略，本手册改不了，告诉用户去找设置它的人或软件。

**Firefox**
1. 地址栏输入 `about:config`，接受风险提示。
2. 搜索 `media.peerconnection`。
3. 列表里**粗体**的行就是被改过的，逐个点行尾的「重置」按钮（↺ 箭头）。尤其注意这两项：`media.peerconnection.enabled` 应该是 `true`；`media.peerconnection.ice.proxy_only` 应该是 `false`。
4. 如果装了 WebRTC 相关扩展或 uBlock Origin，按上面 Chrome 第 2、3 条同样处理（Firefox 扩展页是 `about:addons`）。

**Safari**：Safari 没有禁用 WebRTC 的常规开关，一般不会出现这种情况。如果出现，请用户换 Chrome 测试，确认是不是 Safari 本身的问题。

做完后**完全退出浏览器再打开**，回到第 6 节重新确认：RTCPeerConnection 是 ✔，公网 IP 是代理 IP。

> 用户不能或不愿意开「虚拟网卡模式」时：如实告诉用户，在 Clash Verge 上，「WebRTC 正常可用」和「不泄露真实 IP」要同时做到，只有虚拟网卡模式这一个办法。不要改用禁用 WebRTC 的方式代替。

---

## 10. 修复完成后对用户说的话（模板）

> 已经修好了。现在 Clash Verge 用的是「虚拟网卡模式」，浏览器的 WebRTC 功能照常可用（网页视频、语音都不受影响），只是它的 UDP 流量也会走代理，检测网站看到的是代理服务器的 IP，不再是你的真实 IP。
> 以后注意三点：
> 1. 不要关「虚拟网卡模式」，关了泄露会回来；
> 2. 不要打开「DNS 覆写」；「IPv6」开关保持这次的设置，换了网络（比如从家里换到公司）要重新检查一次；
> 3. 使用公司 VPN 或游戏加速器时，它们可能和虚拟网卡模式冲突，用完记得切回来。

---

## 附录 A：Windows 检测命令

打开 **PowerShell**（开始菜单搜索「PowerShell」，打开「Windows PowerShell」）。
⚠️ 一定要写 `curl.exe`，不能只写 `curl`（PowerShell 里的 `curl` 是另一个命令）。

**B. 命令行出口 IP**（加了 `--noproxy` 后不走系统代理，只有 TUN 生效时才会显示代理 IP）

```powershell
curl.exe --noproxy "*" -s --max-time 10 https://ipinfo.io/ip; ""; curl.exe --noproxy "*" -s --max-time 10 https://ipinfo.io/country
```

输出两行：第一行是 IP，第二行是国家代码。

**C. WebRTC / STUN 出口**（整段复制，一次粘贴进 PowerShell，按回车）

```powershell
$ErrorActionPreference = 'Stop'
try {
  $u = New-Object System.Net.Sockets.UdpClient
  $u.Client.ReceiveTimeout = 6000
  $tid = New-Object byte[] 12
  (New-Object System.Random).NextBytes($tid)
  [byte[]]$req = @(0, 1, 0, 0, 0x21, 0x12, 0xA4, 0x42) + $tid
  $u.Connect('stun.l.google.com', 19302)
  [void]$u.Send($req, $req.Length)
  $ep = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Any, 0)
  $r = $u.Receive([ref]$ep)
  $i = 20; $ip = $null
  while ($i + 4 -le $r.Length) {
    $t = $r[$i] * 256 + $r[$i + 1]; $l = $r[$i + 2] * 256 + $r[$i + 3]
    if ($t -eq 0x0020 -and $r[$i + 5] -eq 1) {
      $ip = '{0}.{1}.{2}.{3}' -f ($r[$i + 8] -bxor 0x21), ($r[$i + 9] -bxor 0x12), ($r[$i + 10] -bxor 0xA4), ($r[$i + 11] -bxor 0x42)
      break
    }
    $i += 4 + $l + ((4 - $l % 4) % 4)
  }
  if ($ip) { "STUN_EXIT=$ip" } else { 'STUN_EXIT=PARSE_FAILED' }
} catch { "STUN_EXIT=FAILED ($($_.Exception.Message))" }
```

输出一行 `STUN_EXIT=某个IP`。再用下面的「查国家」命令查这个 IP 的国家。

**D. IPv6 出口**

```powershell
curl.exe --noproxy "*" -6 -s --max-time 8 https://api64.ipify.org; if ($LASTEXITCODE -ne 0) { "IPV6_TEST=FAILED_OR_NO_IPV6" }
```

**E. 本机有没有 IPv6 地址**（4.5 用；开不开虚拟网卡模式都能测）

```powershell
Get-NetIPAddress -AddressFamily IPv6 -PrefixOrigin RouterAdvertisement, Dhcp -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notmatch '^(fe80|fd|fc|2001:0:|2002:)' } | Select-Object InterfaceAlias, IPAddress
```

- 列出了一行或多行（网卡名和以 `2` 开头的地址）：这个网络**有 IPv6**。
- 什么都没输出：这个网络**没有 IPv6**。

**查国家**（把 `这里换成IP` 替换成要查的 IP）

```powershell
curl.exe -s --max-time 10 https://ipinfo.io/这里换成IP/country
```

---

## 附录 B：Mac 检测命令

打开「终端」（启动台 → 其他 → 终端，或者用 Spotlight 搜索「终端」）。

**B. 命令行出口 IP**

```bash
curl --noproxy '*' -s --max-time 10 https://ipinfo.io/ip; echo; curl --noproxy '*' -s --max-time 10 https://ipinfo.io/country
```

**C. WebRTC / STUN 出口**（整段复制粘贴，按回车）

```bash
/usr/bin/python3 - <<'EOF'
import os, socket, struct
try:
    tid = os.urandom(12)
    req = struct.pack('!HHI', 1, 0, 0x2112A442) + tid
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(6)
    s.sendto(req, ('stun.l.google.com', 19302))
    r = s.recv(2048); i = 20; ip = None
    while i + 4 <= len(r):
        t, l = struct.unpack('!HH', r[i:i + 4])
        if t == 0x20 and r[i + 5] == 1:
            ip = '.'.join(str(b ^ m) for b, m in zip(r[i + 8:i + 12], b'\x21\x12\xa4\x42')); break
        i += 4 + l + (-l % 4)
    print('STUN_EXIT=' + (ip or 'PARSE_FAILED'))
except Exception as e:
    print('STUN_EXIT=FAILED (%s)' % e)
EOF
```

- 如果弹窗提示要安装「命令行开发者工具」：让用户点「取消」，跳过 C 项，改用第 6 节的检测网站判断 WebRTC。

**D. IPv6 出口**

```bash
curl --noproxy '*' -6 -s --max-time 8 https://api64.ipify.org || echo "IPV6_TEST=FAILED_OR_NO_IPV6"
```

**E. 本机有没有 IPv6 地址**（4.5 用；开不开虚拟网卡模式都能测）

```bash
ifconfig | awk '/^[a-z]/{i=$1} $1=="inet6" && i!~/^(utun|lo|bridge|awdl|llw|gif|stf|anpi|ap)/ && $2!~/^(fe80|fd|fc|::1|2001:0:|2002:)/ {print i, $2}'
```

- 列出了一行或多行（例如 `en0: 240e:...`）：这个网络**有 IPv6**。
- 什么都没输出：这个网络**没有 IPv6**。

**查国家**

```bash
curl -s --max-time 10 https://ipinfo.io/这里换成IP/country
```

---

## 附录 C：为什么这些检测能说明问题（给 AI 助手参考）

- **B**：`--noproxy` 让 curl 不用系统代理。只开系统代理时，curl 直接从本地出去，显示真实 IP；开了 TUN 后，所有流量都被虚拟网卡接管，显示代理 IP。所以 B 是「TUN 有没有生效」的开关检测。
- **C**：WebRTC 检测网站做的事就是向 STUN 服务器发 UDP 请求，C 和它完全一样。C 显示代理 IP，就说明浏览器的 WebRTC 也会显示代理 IP（国内 STUN 服务器除外，见第 8 节）。
- **D**：检查 IPv6 有没有绕过虚拟网卡。在 TUN 模式下，这个请求被 Clash 接管后交给代理服务器，所以输出代理服务器的 IPv4 地址也是正常的。
- **E**：只看系统给真实网卡分配的公网 IPv6 地址，排除了本地链路地址（`fe80`）、内网地址（`fd`/`fc`）、老式隧道地址（`2001:0:`、`2002:`）和 Clash 自己的虚拟网卡（Mac 上是 `utun`，Windows 上它的地址不是路由器或 DHCP 分配的）。所以开没开虚拟网卡模式，结果都一样。
- **为什么「IPv6」开关要按 E 决定**：Clash Verge 的「IPv6」开关会覆盖订阅里的 `ipv6` 设置。打开虚拟网卡模式时，它还会把这个值写进 DNS 设置，并补上一段假 IPv6 地址（`fake-ip-range6`），见 Clash Verge Rev 源码 `src-tauri/src/enhance/tun.rs`。网络没有 IPv6 时开着它，软件会拿到 IPv6 地址去连，连不通。微信不会改用 IPv4，所以图片和文件发不出去。社区里的反馈见 clash-verge-rev issue #1762。
