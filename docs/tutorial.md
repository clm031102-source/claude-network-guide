# 教程目录

这份教程按实际完成顺序编排。第一次配置，先打开[零基础从这里开始][beginner-guide]，跟着完整流程走；已经有线路，可以先看第 2 章确认最终出口，再进入检测。

- **[零基础从这里开始][beginner-guide]**：按步骤完成准备、购买、配置、检测和维护。
- **[下载 Word 保姆指南][word-guide]**：当前版本的离线读物，章节链接返回本仓库对应页面。
- **[复制给 AI 的完整提示词][agent-handoff]**：让 AI 按你的实际进度协助；另提供[纯文本提示词][agent-prompt]。

Word 方便离线阅读，**步骤更新以本仓库在线原文为准**。遇到与离线版本不同的内容，先通过 Word 内的章节链接核对当前说明。

| 章节 | 内容 |
|---|---|
| [零基础完整流程][beginner-guide] | 从第一步开始需要准备什么、怎么操作、每一步如何确认完成 |
| [AI 协作完整提示词][agent-handoff] | 复制入口、使用方法与按当前进度交接给 AI 的完整说明 |
| [01 · 购买 VPS](01-buy-vps.md) | VPS 与住宅 IP 的区别、配置要求、选购表、开通后要保存的信息 |
| [02 · 购买自己的住宅 IP](02-buy-residential-ip.md) | 固定、独享、住宅 / ISP 属性，协议、退款、换 IP，两个可选拓扑 |
| [03 · 配置网络](03-network-setup.md) | SSH、服务器部署、住宅出口、REALITY / TLS、订阅、Clash / Shadowrocket / OpenClash、DNS |
| [04 · 检测并启动](04-preflight-check.md) | 启动工作台、填写配置、证据状态、启动门禁、检测边界 |
| [05 · 验收](validation.md) | TCP、UDP、IPv6、DNS、运行时路由、主备切换和故障演练 |
| [06 · 日常维护](maintenance.md) | 备份、证书、规则、升级、回滚和常见故障 |
| [高级功能](advanced.md) | CLIProxyAPI、更新器、账号快照、守护进程、Web 检测、跨平台模块 |
| [核心逻辑与完整能力映射](core-logic.md) | 两套源项目做了什么，新工作台实现什么，哪些保留在模块中 |
| [资料与版本依据](sources.md) | 官方文档、项目来源、已知限制与复核方法 |

所有可复制的 AI 任务提示词均使用本仓库 `clm031102-source/claude-network-guide`。提示词中的空白字段由你填写；密码、私钥、订阅地址或登录态不要粘贴到公开 Issue 或聊天记录中。

**先买 VPS，再把自己购买的固定独享住宅 IP 接成最终出口，最后运行检测。** 服务器程序安装成功只是其中一环；客户端实际路径和故障行为仍须验收。

[返回项目首页](../README.md)

[beginner-guide]: beginner-guide.md
[word-guide]: https://github.com/clm031102-source/claude-network-guide/raw/refs/heads/main/docs/downloads/%E9%98%B2%E5%B0%81%E6%8C%87%E5%8D%97_%E4%BF%9D%E5%A7%86%E8%81%94%E5%8A%A8%E7%89%88.docx
[agent-handoff]: agent-handoff.md
[agent-prompt]: ../prompts/带我完成配置.txt
