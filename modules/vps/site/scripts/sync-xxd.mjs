// 把 xxd-ui-kit 的构建产物复制到 public/xxd/。网站自带一份、不走 CDN：国内打开时不会卡在外部样式上。
// 用法：XXD_UI_KIT=/path/to/xxd-ui-kit node scripts/sync-xxd.mjs（缺省找同级目录 ../../xxd-ui-kit）
import { copyFileSync, existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const kit = resolve(process.env.XXD_UI_KIT || join(here, "../../../xxd-ui-kit"));
const dist = join(kit, "packages/xxd-css/dist");
if (!existsSync(join(dist, "xxd.js"))) {
  console.error(`✗ 找不到 ${dist}/xxd.js：先在 xxd-ui-kit 里跑 pnpm xxd:build，或用 XXD_UI_KIT 指定路径`);
  process.exit(1);
}
const out = join(here, "../public/xxd");
for (const f of ["boot.js", "xxd.css", "xxd.js", "icons.js"]) copyFileSync(join(dist, f), join(out, f));
const version = JSON.parse(readFileSync(join(kit, "packages/xxd-css/package.json"), "utf8")).version;
writeFileSync(join(out, "VERSION"), `xxd-ui-kit @xxd/css ${version}\nhttps://github.com/nevertoday/xxd-ui-kit (MIT)\n`);
console.log(`✓ 已复制 @xxd/css ${version} 到 public/xxd/`);
