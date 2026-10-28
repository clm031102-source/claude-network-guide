// 构建后处理：把主线、How-to、Wiki 每篇正文按小节（h2/h3）切开，生成全文搜索数据
// dist/search-sections.json（中文）和 dist/en/search-sections.json（英文）。
// 搜索框打开时才加载；结果是「文章 › 小节」，点了跳到那一节（锚点用页面右侧「本页」目录里的同一个）。
// 在 base-links.mjs 之前运行：这里的 href 不带子路径前缀，由页面脚本按 BASE_URL 补。
import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join, sep } from "node:path";

const walk = (dir) => readdirSync(dir).flatMap((f) => (statSync(join(dir, f)).isDirectory() ? walk(join(dir, f)) : [join(dir, f)]));
const ENT = { amp: "&", lt: "<", gt: ">", quot: '"', "#39": "'", nbsp: " " };
const text = (html) => html
  .replace(/<(script|style|button|svg)[\s\S]*?<\/\1>/g, " ")
  .replace(/<[^>]+>/g, " ")
  .replace(/&(#x?[0-9a-f]+|\w+);/gi, (m, e) => ENT[e] ?? (e[0] === "#" ? String.fromCodePoint(e[1] === "x" ? parseInt(e.slice(2), 16) : +e.slice(1)) : m))
  .replace(/\s+/g, " ").trim();
const KIND = {
  zh: { guide: "主线", howto: "How-to", wiki: "Wiki", section: "小节" },
  en: { guide: "Guide", howto: "How-to", wiki: "Wiki", section: "Section" },
};
const out = { zh: [], en: [] };
for (const file of walk("dist").filter((f) => f.endsWith("index.html"))) {
  const path = "/" + file.slice("dist/".length).split(sep).join("/").replace(/index\.html$/, "");
  const lang = path.startsWith("/en/") ? "en" : "zh";
  const kind = path.replace(/^\/en\//, "/").split("/")[1];
  if (!["guide", "howto", "wiki"].includes(kind) || path.replace(/^\/en\//, "/") === `/${kind}/`) continue;
  const html = readFileSync(file, "utf8");
  const art = html.match(/<article class="xxd-prose[^"]*"[^>]*>([\s\S]*?)<\/article>/)?.[1];
  if (!art) continue;
  const title = text(html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/)?.[1] ?? "");
  // 「本页」目录：标题文字 → 锚点
  const toc = new Map();
  for (const [, slug, t] of html.matchAll(/<a[^>]+href="#([^"]+)"[^>]*>([\s\S]*?)<\/a>/g)) if (slug !== "main") toc.set(text(t), decodeURIComponent(slug));
  const parts = art.split(/(?=<h[23][\s>])/);
  for (const part of parts) {
    const h = part.match(/^<h[23][^>]*>([\s\S]*?)<\/h[23]>/);
    if (!h) continue;
    const heading = text(h[1]);
    const body = text(part.slice(h[0].length)).slice(0, 600);
    const slug = h[0].match(/^<h[23][^>]*\sid="([^"]+)"/)?.[1] ?? toc.get(heading);
    const K = KIND[lang];
    out[lang].push({ label: `${title} › ${heading}`, hint: `${K[kind]} · ${K.section}`, keywords: body, href: path + (slug ? "#" + slug : "") });
  }
}
writeFileSync("dist/search-sections.json", JSON.stringify(out.zh));
writeFileSync("dist/en/search-sections.json", JSON.stringify(out.en));
console.log(`✓ 全文搜索：中文 ${out.zh.length} 个小节，英文 ${out.en.length} 个小节`);
