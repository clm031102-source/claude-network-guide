# 来源与改造说明

本项目由 `clm031102-source` 整合维护。新增中文教程、本地检测面板和 Python 检测引擎由本项目提供；下列上游代码与资料按 MIT 许可保留。

| 来源 | 固定版本 | 本项目位置 |
|---|---|---|
| [YOURSJEYO/claude-switcher](https://github.com/YOURSJEYO/claude-switcher) | `495b9952f36b8b7b7575fa0d8de48c2465dbf486` | [账号与环境管理组件](modules/switcher/) |
| [nevertoday/xiaoxiaodong-vps](https://github.com/nevertoday/xiaoxiaodong-vps) | `81daa77d33018c5a92b3a29d962f9376f41c1427` | [VPS 部署组件](modules/vps/) |

两个版本的全部已跟踪文件均已引入，原始文件路径与 SHA-256 见 [UPSTREAM.json](UPSTREAM.json)。不包含原作者 Git 历史、私有配置、开发者本地文件或用户账户资料。原项目 AGENTS 安装提示移至组件的参考文档，避免阅读仓库时误触发系统改动。

教程品牌、提示词和反馈入口已统一为本仓库。许可证和本页保留原作者名称是 MIT 许可要求，并不表示原作者为本项目背书。VPS 组件内第三方前端资源另保留其随附 LICENSE。历史内部服务名和兼容路径保留，以免破坏组件升级、备份和回滚。

新面板是独立的只读检测入口，不会自动安装原组件、不读取 OAuth 凭据、不切换账号、不更改系统区域。组件中既有安装器、账号快照、守护和服务器管理操作仅供明确选择的高级流程使用。组件的静态检查与本机新面板测试不代表已在所有操作系统完成部署测试。

原有“实战战绩”、平台风控推测和推广说明不构成本项目的验证结论。当前教程和检测边界以根 README 与 docs 为准。
