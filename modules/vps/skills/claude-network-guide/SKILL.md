---
name: claude-network-guide
description: 用户明确要求用 claude-network-guide 部署或复核其指定 VPS 时使用。默认仅处理个人网络入口、证书、订阅、固定独享住宅出口、备份和验收。CLIProxyAPI 是独立选择；阅读仓库、购买咨询或启动本地检测工作台不触发远程部署。
---

# Claude Network Guide · VPS 部署与维护

项目：https://github.com/clm031102-source/claude-network-guide

本模块保留上游完整部署脚本，并按本项目重写执行范围。内部 `xxd-vps` 服务名和路径用于兼容，不需要用户寻找另一个教程仓库。版权与固定来源见根目录 `NOTICE.md`、`UPSTREAM.json`。

## 开始前

先阅读根目录 `AGENTS.md`、`docs/03-network-setup.md`、`docs/validation.md`。当前 skill 位于 `modules/vps/skills/claude-network-guide`，不要误把模块根目录当成项目根目录。

仅在用户已经要求操作指定服务器时执行。阅读说明、研究源码、编写教程或检查本机工作台不授权连接 VPS 或安装系统服务。已有信息不要重复询问；缺少目标机器、登录方式、关键拓扑或必要范围时，先完成独立准备再补问。

## 执行边界

1. 只操作本次指定服务器；核对主机身份和实际目标。已有 SSH 别名、其他业务和用户配置不得覆盖。
2. 本项目要求用户本人购买并控制固定独享住宅 IP。先确认住宅 VPS 直出，还是普通 VPS + 独立住宅出口；普通 VPS 默认机房出口不满足这一配置要求。
3. 密码、私钥、订阅地址、UUID、面板凭据和 API Key 不在对话、日志、公开文件或命令参数中出现。优先终端交互输入或私有文件，不复制真实秘密到示例命令。
4. 先验证新终端密钥登录，再关闭密码登录；保留救援入口和现有会话。
5. 默认网络范围不运行 `all` / `cliproxy` / 完整 `maint`。不安装本机切换器，不读取登录态，不改本机时区、地区、IPv6 或 DNS。
6. 阶段失败先检查原因，修复后重试该阶段；不跳过有效性检查，不以删除服务器或重装已有业务解决普通问题。
7. 保留固定的 3x-ui / Xray 兼容组合；升级需要独立回归验证，不擅自改版本或校验值。
8. 住宅来源、独享性和历史不能由 ASN 标签或第三方分数证明。不承诺不封号，不用分数阈值决定“安全”或强制退购。

## 第一步：记录本次参数

```text
服务器公网 IP：
SSH 用户名 / 端口：
SSH 别名：
登录方式：本机密钥路径 / 终端交互输入初始密码
系统版本及是否已有业务：
线路结构：住宅 VPS 直出 / 普通 VPS + 本人另购住宅出口
预期住宅公网 IPv4：
住宅出站协议、认证方式与 UDP 能力：
住宅凭据所在本机私有文件路径：
服务器日志时区、流量额度、计费方向与重置日：
```

未提供非关键计费参数时，不虚构商家额度。服务器时区采用用户指定或明确说明的日志时区；不是为了伪造地理位置而改本机设置。

## 第二步：建立 SSH

本机部署脚本需要 Bash、OpenSSH 与必要的解压工具；Windows 在 WSL 中使用。新检测工作台本身不需要 WSL。

下面 `$VPS_SKILL` 指当前 skill 目录，所有占位符须替换为本次参数。密码由用户在自己的终端输入：

```bash
bash "$VPS_SKILL/scripts/local/connect.sh" \
  --alias my-vps --host VPS_PUBLIC_IP --port 22 --user root --password-prompt
```

密钥模式二选一：

```bash
bash "$VPS_SKILL/scripts/local/connect.sh" \
  --alias my-vps --host VPS_PUBLIC_IP --port 22 --user root --key /private/path/server-key
```

确认别名未指向其他机器，再验证第二个 SSH 会话。现有 `base` 检查 root 的 `authorized_keys`，使用 sudo 用户时先审查这个前提，不绕过检查。

## 第三步：分阶段部署网络

```bash
VPS_REMOTE="$VPS_SKILL/scripts/local/remote.sh"
bash "$VPS_REMOTE" my-vps upload
bash "$VPS_REMOTE" my-vps init --ip VPS_PUBLIC_IP --alias my-vps --timezone Etc/UTC
bash "$VPS_REMOTE" my-vps base
bash "$VPS_REMOTE" my-vps cert
bash "$VPS_REMOTE" my-vps xui
bash "$VPS_REMOTE" my-vps sub
bash "$VPS_REMOTE" my-vps backup
```

`Etc/UTC` 是示例；流量参数按订单填写 `--quota-gb` 与 `--reset-day`。逐段执行和验证。

必须处理完整脚本的副作用：

- `base` 会创建 API 服务用户并开放 API 8318；`cert` 会准备其 Nginx 入口。网络方案须关闭 8318 公网访问并去掉未用 API 入口，验证 Nginx 后重载。
- 管理面板端口应限制管理来源或通过 SSH 隧道访问；随机路径不是访问控制。
- 证书申请失败就处理外部 TCP 80、ACME、时钟等原因，不用自签名证书或关闭证书校验凑合。
- 不运行完整 `maint`。按根 `docs/maintenance.md` 单独设置规则刷新和备份定时器；保留 `cert` 已创建的续期定时器。
- 网络方案不能直接以完整 `verify` 的全绿作为交付条件，不为满足它而安装 API。

## 第四步：把住宅 IP 接为最终出口

住宅 VPS 直出：从真实客户端分别经 REALITY 和 TLS 查询出口，均须匹配预期住宅 IPv4。

普通 VPS 中转：默认 Xray 出站是 VPS 本身，需要添加住宅出站，并将两条真实入站标签的流量都绑定它。使用服务商支持的协议和安全传输方式；凭据只存权限受限文件。

不要只修改运行时文件而让面板重启覆盖。保留已有私网阻断，检查规则顺序，不设置住宅失败后回退 VPS / 本地直连。UDP 每段都须支持；不支持时明确阻断并说明功能影响。

配置校验 → 重载 → 主备实测 → 住宅故障演练 → 恢复验证。最终 IP 相同只是条件之一，DNS / UDP / IPv6 仍分别验收。

## 第五步：网络验收与交付

按根 `docs/validation.md` 完成服务、端口、SSH、证书、订阅、规则、备份、真实客户端与故障演练。区分 pass / warning / fail / unknown，未测到不能写通过。

Clash Verge Rev / OpenClash 使用 Clash 订阅；Shadowrocket 使用对应订阅。必须核对运行配置和目标连接；文件中有规则不能证明内核已加载。

`save` / `export` 的既有流程面向完整服务栈，并检查完整阶段。纯网络交付不能硬调用后伪造 API 验收。由操作者在本机私有交付文件中保存必要订阅与管理字段，写明 API 未部署；不要把内容打印给模型或放入公开目录。

交付包括：SSH 别名、私有文件路径、版本、备份路径、两个入口的住宅出口验收摘要、仍未验证的事项。完整 IP 和秘密留在私有记录，公开摘要脱敏。

## 明确选择后：CLIProxyAPI 完整服务栈

CLIProxyAPI 不是 Claude 检测的依赖。本项目不提供把 Claude 消费订阅登录态 / OAuth 接进该服务的流程。其他提供商也要核对当时有效授权方式及条款。

用户明确选择完整栈后，审查端口和管理来源，避免与网络定时器重复，再执行：

```bash
bash "$VPS_REMOTE" my-vps cliproxy
bash "$VPS_REMOTE" my-vps maint
bash "$VPS_REMOTE" my-vps verify --full
bash "$VPS_REMOTE" my-vps save --lang zh
```

完整栈验收失败要如实报告。`verify --full` 包含证书续期演练和重载钩子，不应描述成完全没有外部请求或服务影响的只读检查。导出文件只告知路径，不读取其中秘密到聊天。

`traffic` 和 `kiwivm` 是可选流量校准，参数与私有 Key 按脚本处理；需要才启用，不将服务商适配等同采购推荐。

## 以后检查和修复

纯检查先查看部署记录与状态，不自动 `upload`、重启、更新或执行 `fix`。网络方案用根验收文档；完整栈状态检查也须区分写状态与证书演练。

修复在用户授权范围内进行：先备份，明确修改目标，验证后保留回滚版本。3x-ui / Xray 升级前做实际客户端兼容测试。住宅属性、平台政策、价格、库存与余额在相关操作时重新核对。

排障参考：`references/troubleshooting.md` 和根 `docs/maintenance.md`。历史模块文字与当前范围冲突时，以当前目标、根规则和实际脚本为准，不机械执行旧默认安装流程。
