# Windows 本地程序

**下载、解压、双击 ClaudeNetworkGuide.exe，直接看体检结果。** 日常使用不需要安装 Python，不需要填写代理端口、住宅 IP 或 Claude 路径。

[下载 Windows x64 便携包](https://github.com/clm031102-source/claude-network-guide/releases/latest/download/ClaudeNetworkGuide-Windows-x64.zip) · [所有版本与校验值](https://github.com/clm031102-source/claude-network-guide/releases) · [完整保姆指南](beginner-guide.md)

## 第一次打开

1. 下载 ZIP，在资源管理器中选择“全部解压缩”。保留包内程序和依赖目录，不只复制其中一个 exe。
2. 双击 `ClaudeNetworkGuide.exe`，独立窗口打开后自动进行一次只读体检。
3. 等待结束，先看自动识别出的电脑、代理、TUN 和 Claude，再看每项结果与建议。
4. 网络变化后点“重新检测”。只有点击启动按钮，才会在重检后尝试打开官方 Claude。

界面和检测内核都在自己的电脑上运行。窗口内部只连接本机回环服务，没有云端检测后台，不把配置上传给维护者。公网出口和连通性测试会访问固定外部目标，对方能看到实际请求源地址。

Windows 版需要 .NET Framework 4.6.2 或更新版本，并使用 Microsoft Edge WebView2 显示界面。缺少组件时，按程序提示通过 Windows 更新、[微软 .NET 下载页](https://dotnet.microsoft.com/download/dotnet-framework)或 [WebView2 官方页面](https://developer.microsoft.com/microsoft-edge/webview2/)补齐对应组件。不要从论坛下载不明补丁，也无需关闭系统防护。

## 自动识别与可选覆盖

默认读取系统代理、已知客户端与监听端口、活动网卡和路由、DNS、时区语言以及 Claude 安装记录，并尝试取得支持的客户端运行时信息。权限不足、读取失败或不支持的客户端会显示未验证，不会用猜测补成通过。

高级设置仅用于覆盖自动发现，留空即自动识别。指定预期出口后，会额外比对实测地址；未指定时展示实测出口与通道一致性。采购声明不作为检测门槛。自动读取不能确认商家的独享承诺、订单归属或完整 IP 历史，这些由采购记录说明。

## 关闭与排障

关闭窗口会关闭自己的本地服务，不改系统代理、时区、语言、DNS、IPv6 或防火墙，也不结束已有客户端和其他本地服务。

无法打开时，确认已经完整解压、系统为 Windows x64、WebView2 可用。记录具体错误与版本，通过[本项目反馈](https://github.com/clm031102-source/claude-network-guide/issues)求助；不要附带订阅、账号或密钥。

完整范围与启动行为见[检测说明](04-preflight-check.md)。普通读者直接使用便携包；源码运行和打包步骤供维护者使用。
