// 批量下载 paldb 地图瓦片: node tools/fetch_tiles.mjs <zoom> <outDir> [urlTemplate]
import { writeFile, mkdir, stat } from 'node:fs/promises';
import { join } from 'node:path';

const zoom = Number(process.argv[2] ?? 4);
const outDir = process.argv[3] ?? 'src/tiles/map8';
const tpl = process.argv[4] ?? 'https://cdn.paldb.cc/image/map8/z{z}x{x}y{y}.webp';
const n = 2 ** zoom;                        // 该层级每边瓦片数
const CONC = 8;
await mkdir(outDir, { recursive: true });

const jobs = [];
for (let x = 0; x < n; x++) for (let y = 0; y < n; y++) jobs.push({ x, y });

let done = 0, skipped = 0, failed = [];
async function getOne({ x, y }) {
  const path = join(outDir, `z${zoom}x${x}y${y}.webp`);
  try {
    const s = await stat(path);
    if (s.size > 0) { skipped++; return; }
  } catch { /* 不存在, 继续下载 */ }
  const url = tpl.replace('{z}', zoom).replace('{x}', x).replace('{y}', y);
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const res = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0', 'Referer': 'https://paldb.cc/cn/Palpagos_Islands' } });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const buf = Buffer.from(await res.arrayBuffer());
      await writeFile(path, buf);
      done++;
      return;
    } catch (e) {
      if (attempt === 3) failed.push(`${x},${y}: ${e.message}`);
      else await new Promise(r => setTimeout(r, 400 * attempt));
    }
  }
}

// 简单并发池
let idx = 0;
async function worker() {
  while (idx < jobs.length) {
    const job = jobs[idx++];
    await getOne(job);
    const total = done + skipped;
    if (total % 32 === 0) console.log(`  进度 ${total}/${jobs.length}`);
  }
}
console.log(`下载 z${zoom}: ${n}x${n} = ${jobs.length} 块 -> ${outDir}`);
await Promise.all(Array.from({ length: CONC }, worker));
console.log(`完成: 新下载 ${done}, 已存在 ${skipped}, 失败 ${failed.length}`);
if (failed.length) console.log('失败明细:', failed.slice(0, 10));
