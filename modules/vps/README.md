> 本目录是独立保留的 VPS 高级组件源码参考；当前没有公开部署教程网站。首次使用请从[主教程与本地检测工作台](../../README.md)开始，来源与固定版本见 [NOTICE](../../NOTICE.md)。下文历史说明不代表本次整合已完成所有平台实测。

# Claude 网络指南

**中文** · [English](./README.en.md) · [한국어](./README.ko.md) · [日本語](./README.ja.md) · [العربية](./README.ar.md) · [Español](./README.es.md) · [Français](./README.fr.md) · [Русский](./README.ru.md) · [Deutsch](./README.de.md) · [Português](./README.pt.md)

出差到上网不方便的国家，也能正常用常用的网站和 AI 工具。

**教程站源码（尚未部署）：** [中文页面](site/src/pages/) · [英文页面](site/src/pages/en/) · [本地预览说明](site/README.md)。GitHub 目录用于阅读源码，不会运行网站。

做法很简单：自己买一台海外服务器，让 AI 按这套方案配好，手机和电脑导入订阅就能用。线路只给你自己用，不和陌生人共享。

## 配好之后你有什么

- **一条自己的线路**：电脑、手机、路由器都能用。有主、备两个节点，一个连不上自动换另一个。
- **导入就能用**：常用网站和 AI 工具的分流规则已经配好，国内网站自动直连，不用自己写规则。
- **CLIProxyAPI**：自己的 API 接口和管理后台，会自动更新到最新版。
  - ⚠️ **不要把 Claude 账号接进 CLIProxyAPI 使用**：Anthropic 的政策不允许这样用。ChatGPT 之类的 OpenAI 官方表示可以，我个人很喜欢用它来做图。
- **安全**：服务器只能用你电脑上的密钥登录；用正规 HTTPS 证书，打开不会报"不安全"。
- **基本不用管**：证书、规则、CLIProxyAPI 自动更新，配置每天自动备份。

## 三步用起来

### 1. 买一台服务器

现在推荐直接买**搬瓦工**，线路稳定，我自己一直在用：

**[购买搬瓦工 BandwagonHost](https://bandwagonhost.com/)**

这个链接里的套餐每月 **1T 流量**，个人和家人日常使用足够。

[DMIT](https://www.dmit.io/) 也不错，但现在缺货，不用等。

> 两个都是我的邀请链接，通过它们购买我可能获得佣金，这部分收入我会用于慈善相关工作。价格和库存以官网为准。

系统选 **Ubuntu 24.04**。开通后在后台记下三样东西：**服务器 IP、root 密码（或密钥文件）、SSH 端口**。

### 2. 让 AI 配置

在电脑上打开能执行命令的 AI 工具，比如 [Codex](https://github.com/openai/codex) 或 [Claude Code](https://claude.com/claude-code)（Windows 请在 WSL 里用）。复制下面这段话，填好后发给它：

```text
请按「Claude 网络指南」方案配置我新买的服务器。

方案地址：https://github.com/clm031102-source/claude-network-guide
请先把这个项目下载到本机，完整阅读 modules/vps/skills/claude-network-guide/SKILL.md，
严格按里面的步骤和规则，用项目里的脚本完成部署和验收。

我的服务器：
- IP：
- 登录方式：初始密码（请让我在终端里自己输入）
- SSH 用户名和端口：默认
- 以后想用这个名字登录：bwg
```

要改的只有三处：

- **IP**：填后台看到的服务器 IP。
- **登录方式**：如果服务商给的是密钥文件，改成 `密钥文件：文件路径`（zip 也行）。
- **名字**：`bwg` 换成你想要的名字，以后输入 `ssh 这个名字` 就能登录服务器。

用户名和端口不是 root / 22 的，把"默认"改成实际值。

接下来等 AI 跑完，一般十几分钟。中间它会请你在终端里输入一次服务器密码，**密码不要发在聊天里**。配好后服务器会关掉密码登录，以后只能从你这台电脑登录。

AI 下载不了项目时，手动[下载 ZIP](https://github.com/clm031102-source/claude-network-guide/archive/refs/heads/main.zip) 解压，然后在那段话里加一句"项目已经在：文件夹路径"。

完成后，桌面上会多一个文件 `我的服务器-你的名字-订阅和账号.md`，里面有：

- 电脑和路由器用的 **Clash 订阅地址**、iPhone 用的 **Shadowrocket 订阅地址**；
- 3x-ui 面板的地址、账号、密码；
- CLIProxyAPI 管理后台地址、登录 Key、API 地址和 API Key。

<details>
<summary>经常配服务器？可以装成 skill，以后一句话调用</summary>

在终端执行一次：

```bash
git clone https://github.com/clm031102-source/claude-network-guide.git
mkdir -p ~/.claude/skills ~/.codex/skills
cp -R claude-network-guide/modules/vps/skills/claude-network-guide ~/.claude/skills/
cp -R claude-network-guide/modules/vps/skills/claude-network-guide ~/.codex/skills/
```

以后对 AI 说"用 claude-network-guide 帮我配置新买的服务器"就行，它会自己问你要服务器信息。

</details>

### 3. 导入订阅

- **电脑（首推 Clash Verge Rev）**：安装 [Clash Verge Rev](https://github.com/clash-verge-rev/clash-verge-rev/releases)，导入 Clash 订阅地址，选 **规则模式**，打开 **虚拟网卡模式**（TUN，第一次会提示安装服务，按提示装上）。只开系统代理时，浏览器的 WebRTC 会暴露你的真实 IP，详见 [WebRTC 泄露修复手册](./docs/Clash-Verge-WebRTC泄露修复手册.md)（可以直接交给 AI 助手照做）。
- **iPhone**：在 Shadowrocket 里导入 Shadowrocket 订阅地址。
- **软路由（OpenClash）**：同一个 Clash 订阅地址就能用，家里所有设备都走这条线路。在「配置订阅」里添加地址（别上传 yaml 文件，否则看不到流量用量，规则也不会自动更新），关闭「在线订阅转换」，内核选 Meta。
- **已经在用 v2rayN（Windows / Mac / Linux）**：也能用，但只是备选。导入「Shadowrocket（iPhone）」那一行的订阅地址（不是 Clash 那一行），路由选「绕过大陆」，打开 TUN 防 WebRTC 泄露。这个订阅只有节点，没有 AI 分流、微信直连这些规则，所以电脑上仍然首推 Clash Verge Rev。详见 [v2rayN 教程](https://github.com/clm031102-source/claude-network-guide/blob/main/modules/vps/site/src/pages/howto/v2rayn.mdx)。

导入后打开 <https://ip.net.coffee/claude/>，显示的是你服务器的 IP 就说明通了。顺便看两处：

1. **先看有没有泄露**：DNS 出口不在中国，WebRTC 的 UDP 出口是你服务器的 IP（电脑上看）。
2. **再看「Claude AI 信任评分」**：低于 70 分的话，可以发邮件给服务商（比如搬瓦工）退掉这台，重新买一台，部署好再测一次，到 70 分以上就行。邮件可以直接复制 [这几段模板](https://github.com/clm031102-source/claude-network-guide/blob/main/modules/vps/site/src/pages/howto/refund-rebuy.mdx)。

更详细的设置见 [客户端与使用建议](./docs/客户端与使用建议.md)。

## 出差前的建议

- **出发前配好，并测试一遍**。到了网络受限的地方，下载项目、打开 AI 工具都可能变困难。
- 手机和电脑都装好客户端、导入订阅，确认两个节点都能连。
- 同一台服务器，换个地方、换家运营商，速度可能不一样，这很正常。哪里连不上，先换个网络试试（酒店 Wi-Fi、手机流量、换运营商）；都不行的话，多半是这个 IP 在当地被限制了，找服务商换个新 IP 就好。
- 线路只给自己和家人用，不要分享给别人。

## 以后要检查服务器

把下面这段发给 AI（`bwg` 换成你的名字）：

```text
请按「Claude 网络指南」方案检查我的服务器：ssh bwg

方案地址：https://github.com/clm031102-source/claude-network-guide
请下载项目，阅读 modules/vps/skills/claude-network-guide/SKILL.md 的"以后的复核和维护"部分，
先只做检查，把没通过的项目和原因告诉我，我同意后再修。
不要在聊天里显示密码、订阅地址或 Key。
```

遇到问题先看 [常见问题](./skills/claude-network-guide/references/troubleshooting.md)。想了解每个设计的原因，看 [方案详解](./skills/claude-network-guide/references/design.md)。

## 反馈与建议



## 隐私

- 项目里没有任何真实服务器的信息。
- 每台服务器的密码、密钥、订阅地址、Key 都是部署时新生成的，只保存在服务器和你自己的电脑上，AI 不会在聊天里显示。
- 登录信息文件、订阅地址和 Key 不要发群、截图或上传。
- 发现安全问题请看 [SECURITY.md](./SECURITY.md)。

## License

[MIT](./LICENSE)
