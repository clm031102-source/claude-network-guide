import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";

// Claude 网络指南 教程站：静态构建，界面全部用 xxd-ui-kit（public/xxd/ 里的一份，见 scripts/sync-xxd.mjs）。
// 主站 https://github.com/clm031102-source/claude-network-guide/tree/main/modules/vps/site/src/pages/ 部署在根路径；GitHub Pages 备用地址用 SITE_URL / BASE_PATH 构建到子路径
// （组件里的链接走 data/nav.js 的 link()，正文里手写的 /xxx 链接由 scripts/base-links.mjs 在构建后补前缀）。
const site = process.env.SITE_URL || "https://clm031102-source.github.io";
const base = process.env.BASE_PATH || "/claude-network-guide/";
export default defineConfig({
  site,
  base,
  trailingSlash: "always",
  integrations: [mdx()],
  build: { format: "directory" },
});
