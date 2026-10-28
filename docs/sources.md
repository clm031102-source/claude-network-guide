# 参考资料与版本依据

[目录](tutorial.md) · [来源声明](../NOTICE.md)

整理日期：2026-10-28。软件和政策会变化，执行安装或购买前重新检查官网、实际脚本与当时生效的条款。本项目不缓存第三方价格，不将历史库存写成当前可购买。

## 引入的完整项目

固定 commit、许可证、原始文件路径和 SHA-256 记录在 [NOTICE.md](../NOTICE.md) 与 [UPSTREAM.json](../UPSTREAM.json)。本项目不是把旧仓库链接换个名字后声称全部原创：新增主线教程和工作台，模块保留第三方版权与适配关系。

- VPS 模块的部署结构、命令与维护逻辑，依据本仓库实际 `modules/vps/skills/claude-network-guide/scripts/`。
- 切换器模块的高级功能，依据本仓库实际 `modules/switcher/` 的源码和平台文档。
- 主教程与源模块历史描述冲突时，先核对实现；默认范围以根目录教程为准，不能用历史营销描述覆盖检测限制。

## 官方技术入口

| 主题 | 来源 | 本教程用来核对什么 |
|---|---|---|
| Anthropic 支持地区 | [官方政策入口](https://www.anthropic.com/supported-countries) | 使用资格需按当时生效条款核对，代理出口不是资格证明 |
| Xray SOCKS 出站 | [Project X](https://xtls.github.io/en/config/outbounds/socks.html) | 住宅 SOCKS 出站字段 |
| Xray 路由 | [Project X](https://xtls.github.io/en/config/routing.html) | 入站标签到出站的路由结构 |
| 3x-ui | [官方仓库](https://github.com/MHSanaei/3x-ui) | 服务器面板与发布入口 |
| Mihomo DNS | [官方配置文档](https://wiki.metacubex.one/config/dns/) | fake-IP、解析策略、respect-rules 与代理服务器解析 |
| Mihomo TUN | [官方配置文档](https://wiki.metacubex.one/config/inbound/tun/) | 路由接管、DNS 劫持、strict-route 及平台差异 |
| Clash Verge Rev | [官方发布页](https://github.com/clash-verge-rev/clash-verge-rev/releases) | 客户端来源与当前版本 |
| OpenClash | [官方仓库](https://github.com/vernesong/OpenClash) | 路由器适配与发布入口 |
| Let's Encrypt IP 证书 | [官方说明](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability) | IP 证书与短期有效期、自动续期必要性 |

本次读取 Anthropic 支持地区入口时，它重定向到一个标注 **2026-11-12 生效**的政策页面，晚于本教程整理日期。因此这里不把该页面的未来条款写成已经生效的规则；请在实际使用日期核对当时适用版本。

## 证据层级

官方文档描述能力或条款；源代码描述实现；隔离测试证明特定输入输出；真实客户端和服务器测试证明当时环境中的实际行为。商家的采购承诺、ASN 分类与用户体验分别保存，不互相冒充。

本项目没有获得“住宅 IP 保号”“评分阈值保安全”“语言或字体必然触发限制”等可验证官方依据，因此不把这些说法写入新主线。
