// 从 paldb CDN 抓取赏金首 NPC 图标: node fetch_boss_icons.mjs
// 图标路径来自 Character/DT_PalBossNPCIcon.json 的 AssetPathName
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { join, basename } from 'node:path';

const ROOT = process.argv[2] ?? '.';
const ICON_JSON = join(ROOT, 'exports/Pal/Content/Pal/DataTable/Character/DT_PalBossNPCIcon.json');
const OUT = join(ROOT, 'pal_spawner_map/src/npc_icons');
mkdirSync(OUT, { recursive: true });

const rows = JSON.parse(readFileSync(ICON_JSON, 'utf8'))[0].Rows;
const jobs = [];
for (const [k, v] of Object.entries(rows)) {
  const ap = v?.Icon?.AssetPathName;
  if (!ap) continue;
  const asset = ap.includes('.') ? ap.split('.')[0] : ap;         // /Game/Pal/Texture/PalIcon/NPC/T_BOSS_NPC_Hunter
  const rel = asset.replace('/Game/', '');                        // Pal/Texture/PalIcon/NPC/T_BOSS_NPC_Hunter
  jobs.push({ key: k, url: `https://cdn.paldb.cc/image/${rel}.webp`, file: join(OUT, basename(asset) + '.webp') });
}
console.log(`需要抓取 ${jobs.length} 张图标`);

let ok = 0, skip = 0, fail = [];
for (const j of jobs) {
  if (existsSync(j.file)) { skip++; continue; }
  try {
    const res = await fetch(j.url, { headers: { 'User-Agent': 'Mozilla/5.0', 'Referer': 'https://paldb.cc/' } });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    writeFileSync(j.file, Buffer.from(await res.arrayBuffer()));
    ok++;
  } catch (e) {
    fail.push(`${j.key}: ${e.message}`);
  }
}
console.log(`完成: 新下载 ${ok}, 已存在 ${skip}, 失败 ${fail.length}`);
if (fail.length) console.log(fail.join('\n'));
