// 从 paldb 地图数据中提取钓点标记 (含世界坐标)。
// 用法: node tools_extract_fishing.mjs <paldb_map_data.js> <out.json>
import { readFileSync, writeFileSync } from 'node:fs';

const src = readFileSync(process.argv[2], 'utf8');
(0, eval)(src);

// 收集所有全局数组里带 type 的标记
const found = [];
const seenTypes = new Map();
for (const key of Object.keys(globalThis)) {
  const v = globalThis[key];
  if (!Array.isArray(v)) continue;
  for (const e of v) {
    if (!e || typeof e !== 'object') continue;
    const t = e.type;
    if (typeof t !== 'string') continue;
    seenTypes.set(t, (seenTypes.get(t) || 0) + 1);
    if (t === 'Fishing Spot' || t === 'Rare Fishing Spot') {
      found.push({ ...e, __from: key });
    }
  }
}

console.log('数组来源统计:', [...new Set(found.map(f => f.__from))].join(', '));
console.log('钓点标记总数:', found.length);
const byType = {};
for (const f of found) byType[f.type] = (byType[f.type] || 0) + 1;
console.log('按类型:', byType);

// 字段盘点
const fieldCount = {};
for (const f of found) for (const k of Object.keys(f)) fieldCount[k] = (fieldCount[k] || 0) + 1;
console.log('字段出现次数:', fieldCount);

console.log('\n前 8 条:');
for (const f of found.slice(0, 8)) console.log('  ', JSON.stringify(f));

// 位置来源: pos(世界坐标) 还是 ipos(像素)
const hasPos = found.filter(f => f.pos).length;
const hasIpos = found.filter(f => f.ipos).length;
console.log(`\n带 pos(世界坐标): ${hasPos}   带 ipos(地图像素): ${hasIpos}`);

// href / item 分布 (看能否与 DataTable 的钓点类型对上)
const hrefs = {};
for (const f of found) hrefs[f.href ?? '(无)'] = (hrefs[f.href ?? '(无)'] || 0) + 1;
console.log('href 取值:', hrefs);

writeFileSync(process.argv[3], JSON.stringify(found, null, 1));
console.log('\n已写入', process.argv[3]);
