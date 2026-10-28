# Claude 网络指南 教程站

把 claude-network-guide 方案讲给第一次接触的人：主线教程（按顺序 0–7 步）、How-to（具体怎么做）、Wiki（这是什么）、常见问题。
这是独立保留的教程站源码参考，当前本仓库没有发布 Cloudflare 主站或 GitHub Pages 备用站。[页面源码](src/pages/)用于阅读；首次使用请从[主教程及本地检测工作台](../../../README.md)开始。界面使用 [xxd-ui-kit](https://github.com/nevertoday/xxd-ui-kit)（MIT），保留其许可证。

```bash
cd claude-network-guide/modules/vps/site
npm install
npm run dev        # http://localhost:4410
npm run build      # 输出到 dist/
```

## 中英双语

中文在根路径，英文在 `/en/` 下，页面一一对应（构建时检查过）。语言看路径（`data/nav.js` 的 `langOf`），切换按钮在顶栏。

- 主线和 How-to：中文 `src/pages/guide|howto/*.mdx`，英文 `src/pages/en/guide|howto/*.mdx`，**改一边要同步改另一边**。
- Wiki、常见问题：中文 `data/wiki.js`、`data/faq.js`，英文 `data/wiki.en.js`、`data/faq.en.js`。
- 首页、Wiki 页、常见问题页、How-to 目录：`src/views/` 里一份，中英文路由共用。
- 步骤、How-to 标题、术语：`data/nav.js` 里每项的 `en` 字段。

## 怎么改

- **站点结构**只在 `src/data/nav.js` 改：主线 7 步、How-to 和 Wiki 清单、术语解释（`GLOSSARY`）。步骤写完后把 `ready` 改成 `true`，导航和首页会自动给它加链接。
- **主线教程**每一步是 `src/pages/guide/<n>-<slug>.mdx`，开头写 `layout: ../../layouts/Guide.astro` 和 `step: n`。
- **教程组件**（在 MDX 里 import）：
  - `Callout`：提示框，`type` 是 `ok`（你应该看到）/ `warn`（注意）/ `no`（别这样做）/ `tip`（小提示）
  - `Term`：术语，悬停出一句话解释，`k` 对应 `GLOSSARY` 里的词
  - `Checkpoint`：步骤结尾的检查点，可以打勾，打勾记在读者自己的浏览器里
  - `Q`：「卡住了？」里的一条，可以展开
  - `Tabs`：按设备或路线切换（`items={[["win","Windows"],["mac","Mac"]]}`，内容放在 `<div slot="win">` 里）
  - `Copy`：带复制按钮的命令或话术块
  - `Shot`：配图（`public/img/`），自动带截图日期。截图里的 IP、账号、所在地一律打码或换成示例地址 `203.0.113.10`，只截不用登录的公开页面
  - 每一步和每篇 How-to 末尾自动带反馈入口（`Feedback`），在 GitHub 上新建一条带模板的 Issue
- **How-to** 是 `src/pages/howto/<slug>.mdx`（`layout: ../../layouts/HowTo.astro`，`slug` 要和 `HOWTO` 里一致）；**Wiki** 和 **常见问题** 只改数据：`src/data/wiki.js`、`src/data/faq.js`。
- **搜索**（⌘K）自动收录主线每一步、每篇 How-to、每个 Wiki 条目和每条常见问题。
- **xxd-ui-kit 的 CSS 和 JS** 在 `public/xxd/` 里自带一份，不走 CDN（国内打开不会卡在外部资源上）。升级时在 xxd-ui-kit 里先 `pnpm xxd:build`，再在这里跑 `npm run sync-xxd`。

## 部署

- 当前状态：没有部署到 Cloudflare 或 GitHub Pages，也没有可供读者直接访问的站点 URL。
- Cloudflare：`npm run release` 保留构建后调用 `wrangler deploy` 的能力。实际发布前需在自己的 Cloudflare 账户中配置项目、域名与 `wrangler.jsonc`，并完成授权。不要把保留的配置值视为已开通资源。
- GitHub Pages：`modules/vps/.github/workflows/site-pages.yml` 是嵌套的参考文件，不会因推送 main 自动运行。需要部署时，应在仓库根单独配置工作流，并将构建目录修正为 `modules/vps/site/`，以实际站点的 base 路径验收链接。

## 新手实测

按 [TESTING.md](./TESTING.md) 的规程找人试用；每次大改后都要做一遍。

## 写作规矩

- 站在第一次接触的人的角度：先说这一步做什么、要多久，再说怎么做，最后说应该看到什么。
- 截图里的 IP、订阅地址、密码一律打码；示例 IP 用文档专用的 `203.0.113.x`。
- 价格、库存、付款方式这类会变的信息不写死，写「以官网为准」。
