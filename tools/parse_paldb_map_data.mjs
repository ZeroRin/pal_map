// 解析 paldb 地图数据: 用成对的 pos(世界坐标cm) / ipos(地图像素) 反推坐标变换
import { readFileSync, writeFileSync } from 'node:fs';

const src = readFileSync(process.argv[2], 'utf8');

// 间接 eval 在全局作用域执行; 文件里是 var 声明, 执行后可从 globalThis 取
(0, eval)(src);
const config = globalThis.config;
console.log('config =', JSON.stringify(config));
const names = Object.keys(globalThis).filter(k => /Data|config|Lookup|Dungeon|region/i.test(k));
console.log('可用的全局变量:', names.join(', '));

// 扫描所有含 pos 的对象, 找同时带 ipos 的条目
const re = /\{[^{}]*"pos":\{"X":(-?\d+),"Y":(-?\d+)\}[^{}]*\}/g;
const pairs = [];
let m;
while ((m = re.exec(src))) {
  const ip = m[0].match(/"ipos":\{"X":(-?[\d.]+),"Y":(-?[\d.]+)\}/);
  if (ip) pairs.push({ px: +m[1], py: +m[2], ix: +ip[1], iy: +ip[2] });
}
console.log('\n同时含 pos 与 ipos 的条目:', pairs.length);
for (const p of pairs.slice(0, 6)) console.log('  ', JSON.stringify(p));

if (pairs.length >= 2) {
  const fit = (getP, getI) => {
    const n = pairs.length;
    let sx = 0, sy = 0, sxx = 0, sxy = 0;
    for (const p of pairs) { const x = getP(p), y = getI(p); sx += x; sy += y; sxx += x * x; sxy += x * y; }
    const a = (n * sxy - sx * sy) / (n * sxx - sx * sx);
    const b = (sy - a * sx) / n;
    let maxr = 0;
    for (const p of pairs) maxr = Math.max(maxr, Math.abs(a * getP(p) + b - getI(p)));
    return { a, b, maxr };
  };
  const fx = fit(p => p.px, p => p.ix);
  const fy = fit(p => p.py, p => p.iy);
  console.log('\nipos.X = %s * pos.X + %s   (max残差 %s)', fx.a, fx.b.toFixed(3), fx.maxr.toFixed(3));
  console.log('ipos.Y = %s * pos.Y + %s   (max残差 %s)', fy.a, fy.b.toFixed(3), fy.maxr.toFixed(3));
  console.log('=> 1 像素 = %s cm (两个方向应一致)', (1 / fx.a).toFixed(4));

  // 用 config 推导理论值做交叉验证
  const c = config;
  const spanX = c.landScapeRealPositionMax.X - c.landScapeRealPositionMin.X;
  const perPx = spanX / (c.minMapTextureBlockSize.X / 2 ** 4);   // 8192px / 16 tiles... 直接用 8192
  console.log('\nconfig 理论: 世界跨度 %d cm, 纹理 %d px => %s cm/px',
    spanX, c.minMapTextureBlockSize.X, (spanX / c.minMapTextureBlockSize.X).toFixed(4));
  console.log('   世界 X 范围 [%d, %d] -> 像素 [0, %d]', c.landScapeRealPositionMin.X,
    c.landScapeRealPositionMax.X, c.minMapTextureBlockSize.X);
  console.log('   用拟合式: pos.X=%d -> ipos.X=%s ; pos.X=%d -> ipos.X=%s',
    c.landScapeRealPositionMin.X, (fx.a * c.landScapeRealPositionMin.X + fx.b).toFixed(1),
    c.landScapeRealPositionMax.X, (fx.a * c.landScapeRealPositionMax.X + fx.b).toFixed(1));
  console.log('   世界 Y 范围 [%d, %d] -> ipos.Y: %s / %s', c.landScapeRealPositionMin.Y,
    c.landScapeRealPositionMax.Y,
    (fy.a * c.landScapeRealPositionMin.Y + fy.b).toFixed(1),
    (fy.a * c.landScapeRealPositionMax.Y + fy.b).toFixed(1));

  writeFileSync(process.argv[3] || 'src/paldb/paldb_transform.json',
    JSON.stringify({ config, fitX: fx, fitY: fy, samples: pairs.length }, null, 1));
  console.log('\n已写入', process.argv[3] || 'src/paldb/paldb_transform.json');
}
