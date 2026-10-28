# Claude Network Guide · VPS

> Independent source reference for the advanced VPS component. No tutorial site is currently hosted by this repository. Start with the [main tutorial and local workbench](../../README.md); source attribution is preserved in [NOTICE](../../NOTICE.md).

[中文](./README.md) · **English** · [한국어](./README.ko.md) · [日本語](./README.ja.md) · [العربية](./README.ar.md) · [Español](./README.es.md) · [Français](./README.fr.md) · [Русский](./README.ru.md) · [Deutsch](./README.de.md) · [Português](./README.pt.md)

Travelling to a country where the internet is hard to use? Keep using the websites and AI tools you rely on.

Tutorial source (not hosted): [Chinese pages](site/src/pages/) · [English pages](site/src/pages/en/) · [local preview](site/README.md). GitHub directories do not run the website.

How it works: buy your own overseas server, let an AI set it up with this project, then import a subscription on your phone and computer. The connection is yours alone, not shared with strangers.

## What you get

- **Your own connection** for your computer, phone and router. A main node and a backup node: if one fails, it switches to the other automatically.
- **Works right after import.** Routing rules for common websites and AI tools are already set. Websites in mainland China connect directly; everything else goes through your server.
- **CLIProxyAPI**: your own API endpoint and admin panel, updated to the latest version automatically.
  - ⚠️ **Don't connect a Claude account to CLIProxyAPI**: Anthropic's policy doesn't allow it. OpenAI has said ChatGPT accounts can be used this way — I personally love using it to make images.
- **Secure**: the server only accepts the key on your computer, and uses a proper HTTPS certificate, so browsers never warn "not secure".
- **Almost no upkeep**: certificates, rules and CLIProxyAPI update themselves, and the configuration is backed up every day.

## Three steps

### 1. Buy a server

Right now, go with **BandwagonHost**. The network is stable and it's what I use myself:

**[Buy BandwagonHost](https://bandwagonhost.com/)**

The plan in this link includes **1 TB of traffic per month** — plenty for you and your family.

[DMIT](https://www.dmit.io/) is also good, but it's out of stock at the moment. No need to wait for it.

> Both are my referral links. I may earn a commission if you buy through them, and I will use that income for charitable work. Prices and stock are as shown on the official sites.

Choose **Ubuntu 24.04** as the system. Once the server is ready, write down three things from the control panel: **server IP, root password (or key file) and SSH port**.

### 2. Let an AI set it up

Open an AI tool that can run commands on your computer, such as [Codex](https://github.com/openai/codex) or [Claude Code](https://claude.com/claude-code) (on Windows, use it inside WSL). Copy the text below, fill it in and send it:

```text
Please set up my new server using the "claude-network-guide" plan.

Plan: https://github.com/clm031102-source/claude-network-guide
First download this project to my computer and read
modules/vps/skills/claude-network-guide/SKILL.md in full. Follow its steps and rules
exactly, and use the project's scripts for setup and verification.
Please talk to me in English.

My server:
- IP:
- Login: initial password (let me type it into the terminal myself)
- SSH user and port: default
- Name I want to log in with: bwg
```

You only need to change three things:

- **IP**: the server IP from the control panel.
- **Login**: if your provider gave you a key file, change it to `key file: path to the file` (a zip is fine).
- **Name**: replace `bwg` with any name you like. Afterwards, typing `ssh that-name` logs you into the server.

If the user and port are not root / 22, replace "default" with the real values.

Then wait for the AI to finish, usually 10–20 minutes. At one point it will ask you to type the server password into the terminal. **Never paste the password into the chat.** When setup is done, password login is turned off and only this computer can log in.

If the AI can't download the project, [download the ZIP](https://github.com/clm031102-source/claude-network-guide/archive/refs/heads/main.zip) yourself, unzip it, and add a line to the text above: "The project is already at: folder path".

When it's done, a new file `my-server-your-name-subscriptions-and-accounts-en.md` appears on your desktop with:

- the **Clash subscription URL** for computer and router, and the **Shadowrocket subscription URL** for iPhone;
- the 3x-ui panel address, username and password;
- the CLIProxyAPI admin address, admin login key, API address and API key.

<details>
<summary>Set up servers often? Install it as a skill and call it in one sentence</summary>

Run once in a terminal:

```bash
git clone https://github.com/clm031102-source/claude-network-guide.git
mkdir -p ~/.claude/skills ~/.codex/skills
cp -R claude-network-guide/modules/vps/skills/claude-network-guide ~/.claude/skills/
cp -R claude-network-guide/modules/vps/skills/claude-network-guide ~/.codex/skills/
```

After that, just tell the AI "use claude-network-guide to set up my new server" and it will ask you for the server details.

</details>

### 3. Import the subscription

- **Computer (Clash Verge Rev recommended)**: install [Clash Verge Rev](https://github.com/clash-verge-rev/clash-verge-rev/releases), import the Clash subscription URL, choose **Rule** mode and turn on **TUN mode** (Virtual Network Interface; install the service when prompted). With System Proxy alone, the browser's WebRTC can reveal your real IP — see the [WebRTC leak fix guide](./docs/Clash-Verge-WebRTC泄露修复手册.md) (in Chinese, written so an AI assistant can follow it step by step).
- **iPhone**: import the Shadowrocket subscription URL in Shadowrocket.
- **Router (OpenClash)**: the same Clash subscription URL works, so every device at home uses the line. Add it under Config Subscribe (don't upload the YAML file, or the usage bar won't show and rules won't auto-update), turn off online subscription conversion, and use the Meta core.
- **Already using v2rayN (Windows / Mac / Linux)**: it works, but only as a fallback. Import the subscription URL from the "Shadowrocket (iPhone)" row (not the Clash row), pick the "bypass mainland China" routing, and turn on TUN against WebRTC leaks. That subscription has only the nodes — none of the AI routing or WeChat-direct rules — so Clash Verge Rev remains the recommended desktop app. See the [v2rayN guide](https://github.com/clm031102-source/claude-network-guide/blob/main/modules/vps/site/src/pages/en/howto/v2rayn.mdx).

Then open <https://ip.net.coffee/claude/>. If it shows your server's IP, you're connected. While you're there, check two things:

1. **Leaks first**: the DNS exit is not in China, and WebRTC's UDP exit is your server's IP (check on a computer).
2. **Then the Claude AI trust score**: if it's below 70, you can email your provider (for example BandwagonHost) to cancel this server, buy a new one, deploy it and test again. Once it's 70 or above, you're set. You can copy [these email templates](https://github.com/clm031102-source/claude-network-guide/blob/main/modules/vps/site/src/pages/en/howto/refund-rebuy.mdx).

## Before you travel

- **Set everything up and test it before you leave.** Once you're on a restricted network, downloading the project or even opening AI tools may get much harder.
- Install the clients and import the subscriptions on both phone and computer, and check that both nodes connect.
- The same server can feel faster or slower depending on where you are and which carrier you use. That's normal. If it won't connect somewhere, try another network first (hotel Wi-Fi, mobile data, another carrier). If none work, the IP is probably blocked there; your provider can give you a new one.
- Keep the connection to yourself and your family. Don't share it.

## Checking your server later

Send this to the AI (replace `bwg` with your name):

```text
Please check my server using the "claude-network-guide" plan: ssh bwg

Plan: https://github.com/clm031102-source/claude-network-guide
Download the project and read the "以后的复核和维护" (later checks and
maintenance) part of modules/vps/skills/claude-network-guide/SKILL.md.
Only check first, tell me what failed and why, and fix things only after I agree.
Don't show passwords, subscription URLs or keys in the chat.
Please talk to me in English.
```

Detailed docs ([troubleshooting](./skills/claude-network-guide/references/troubleshooting.md), [design notes](./skills/claude-network-guide/references/design.md)) are currently in Chinese; your AI can read them for you.

## Feedback and suggestions



## Privacy

- This project contains no information about any real server.
- Every server's passwords, keys, subscription URLs and API keys are freshly generated during setup and stored only on the server and your own computer. The AI doesn't show them in the chat.
- Don't post your login file, subscription URLs or keys anywhere, and don't screenshot them.
- To report a security issue, see [SECURITY.md](./SECURITY.md).

## License

[MIT](./LICENSE)
