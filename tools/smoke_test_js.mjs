// 冒烟测试: 在 Node 里用最小 DOM/Canvas 桩执行成品 HTML 的脚本,
// 依次在"全图视野(应画点)"与"近景(应画头像)"下调用 draw(), 检查无异常并统计调用。
// 用法: node tools/smoke_test_js.mjs
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const ROOT = path.dirname(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')));
const html = fs.readFileSync(path.join(ROOT, 'pal_spawner_map.html'), 'utf8');

// 提取最后一个 <script> 的内容 (含 const DATA = ...)
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (!scripts.length) throw new Error('未找到 <script>');
const code = scripts[scripts.length - 1];

const calls = { drawImage: 0, arc: 0, fillText: 0, stroke: 0 };
const colors = {};   // strokeStyle 直方图 (校验红框/蓝框)
const bgRects = [];  // drawImage 的 5 参数调用 = 底图贴图矩形 (校验叠放)
function ctxStub() {
  const h = {
    get(t, k) {
      if (k in t) return t[k];
      if (k === 'canvas') return t.canvas;
      if (k === 'drawImage') {
        return (...a) => {
          calls.drawImage++;
          if (a.length >= 5) bgRects.push([+a[1], +a[2], +a[3], +a[4]]);   // 底图: (img,x,y,w,h)
        };
      }
      return (...a) => { if (calls[k] !== undefined) calls[k]++; };
    },
    set(t, k, v) {
      if (k === 'strokeStyle' && typeof v === 'string') colors[v] = (colors[v] || 0) + 1;
      t[k] = v; return true;
    },
  };
  const base = { canvas: null };
  return new Proxy(base, h);
}
const UNCHECKED = new Set(['ckRadius', 'ckUnder', 'ckGrid']);   // 与页面默认一致
function elementStub(id) {
  const el = {
    id, style: {}, dataset: {}, checked: !UNCHECKED.has(id), value: '25', innerHTML: '', textContent: '',
    width: 1920, height: 1080,
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    getContext: () => ctxStub(),
    _lis: {},                                        // 记录事件监听, 供触控手势测试派发
    addEventListener(t, f) { (this._lis[t] = this._lis[t] || []).push(f); },
    removeEventListener() {}, appendChild() {}, removeChild() {},
    querySelector: () => elementStub(id + '>*'), querySelectorAll: () => [],
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 1920, height: 1080 }),
  };
  return el;
}
const elements = {};
const documentStub = {
  getElementById(id) { return elements[id] || (elements[id] = elementStub(id)); },
  querySelectorAll() { return []; },
  createElement(tag) { const e = elementStub(tag); if (tag === 'canvas') e.width = e.height = 64; return e; },
  addEventListener() {},
};
class ImageStub {                       // 异步"加载完成", 模拟浏览器行为
  constructor() { this.width = 40; this.height = 40; this.naturalWidth = 40; this.complete = true; }
  set src(v) { this._src = v; if (this.onload) setTimeout(() => this.onload(), 0); }
  get src() { return this._src; }
}
const sandbox = {
  document: documentStub, Image: ImageStub, console,
  innerWidth: 1920, innerHeight: 1080, devicePixelRatio: 1,
  requestAnimationFrame: (f) => setTimeout(f, 0),
  addEventListener() {}, removeEventListener() {},
  setTimeout, clearTimeout, Math, JSON, Map, Set, Date, Object, Array, String, Number, RegExp,
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;

const ctx = vm.createContext(sandbox);
try {
  vm.runInContext(code, ctx, { filename: 'pal_spawner_map.html<script>' });
} catch (e) {
  console.error('脚本执行失败:', e && e.stack || e);
  process.exit(1);
}
await new Promise(r => setTimeout(r, 20));    // 让异步 onload 跑完 (初始化 + 首帧)
console.log('✓ 脚本初始化通过');
const ev = (expr) => vm.runInContext(expr, ctx);
console.log('  DATA.points =', ev('PTS.length'), ' DATA.icons =', ev('ICON_KEY.length'),
            ' 有头像的普通点 =', ev('PTS.filter(p=>p.ii!=null&&p.ii>=0).length'),
            ' 地下城点 =', ev("PTS.filter(p=>p.t==='DG').length"),
            ' 其中绘制代表 =', ev("PTS.filter(p=>p.t==='DG'&&!p.dd).length"));
const dunPts = ev("PTS.filter(p=>p.t==='DG').length");
const dunDraw = ev("PTS.filter(p=>p.t==='DG'&&!p.dd).length");
const dunRooms = ev("Object.keys(DUNGEONS).length");
console.log(`  地下城: ${dunPts} 个点位 → ${dunDraw} 个标记 (洞口 ${dunRooms})`);

function run(label, mapWidthCm) {
  for (const k in calls) calls[k] = 0;
  for (const k in colors) delete colors[k];
  bgRects.length = 0;
  let r;
  try {
    r = ev(`(function(){ view.s = 1920/${mapWidthCm}; draw();
              return {on: palIconsOn, ipx: iconPxPal(), bpx: iconPxBoss(), sprites: SPRITES.size}; })()`);
  } catch (e) {
    console.error(`✗ draw() 在 ${label} 抛错:`, e && e.stack || e);
    process.exit(1);
  }
  console.log(`  ${label}: 普通点${r.ipx}px Boss${r.bpx}px 头像层=${r.on ? '开' : '关'} ` +
              `精灵缓存=${r.sprites} drawImage=${calls.drawImage} arc=${calls.arc}`);
  return { ...r, ...calls, colors: { ...colors }, bgRects: bgRects.map(a => [...a]) };
}

console.log('✓ 渲染测试');
const wide = run('全图视野 15km', 1500000);
const mid = run('中景 8km', 800000);
const near = run('近景 5km', 500000);       // 普通点 16px (= 25m 基准下限), 已开头像
const closer = run('近景 2km', 200000);     // 24px
const closest = run('近景 1km', 100000);    // 48px, 触顶

let ok = true;
const check = (cond, msg) => { console.log(`  ${cond ? '✓' : '✗'} ${msg}`); if (!cond) ok = false; };
const all = [wide, mid, near, closer, closest];
check(!wide.on, `全图视野退回画点 (同屏 ${wide.arc} 个点 > 上限)`);
check(near.on, `放大到 5km 即开头像 (${near.ipx}px)`);
check(near.drawImage > 100, `近景有实际头像 blit (${near.drawImage} 次)`);
check(near.drawImage <= 2500, `单帧头像数量受 LOD 上限约束 (${near.drawImage} ≤ 2500)`);
check(near.drawImage >= closer.drawImage && closer.drawImage >= closest.drawImage,
      `视野越小可见头像越少 (${near.drawImage} → ${closer.drawImage} → ${closest.drawImage})`);
check(closest.sprites > 0, `精灵缓存已建立 (${closest.sprites} 个)`);
check(all.every(r => r.ipx >= 16 && r.ipx <= 48), '普通点头像尺寸恒在 16~48 px 内');
check(all.every(r => r.bpx >= 16 && r.bpx <= 96), 'Boss 头像尺寸恒在 16~96 px 内');
check(dunDraw === dunRooms, `地下城绘制标记数 = 洞口数 (${dunDraw} = ${dunRooms})`);
check(dunPts > dunDraw, `地下城重叠点已合并 (${dunPts} 点 → ${dunDraw} 标记)`);
check(!ev("PTS.some(p=>p.t==='D'||(p.t==='C'&&p.u))"), '旧的 D / 洞窟内部 C 图层已不存在 (统一为 DG)');
check(new Set(all.map(r => r.ipx)).size >= 3, '普通点头像存在多个尺寸档 (分段缩放生效)');
// 描边配色: Boss 红框 (#ff4d4f), 普通点仅夜间 蓝框 (#4d9fff)
const c5 = near.colors || {};
check((c5['#ff4d4f'] || 0) > 0, `Boss 头像描红框 (${c5['#ff4d4f'] || 0} 次)`);
check((c5['#4d9fff'] || 0) > 0, `仅夜间头像描蓝框 (${c5['#4d9fff'] || 0} 次)`);
check((c5['rgba(255,255,255,.72)'] || 0) > 0, `白天头像描白框 (${c5['rgba(255,255,255,.72)'] || 0} 次)`);
// 底图叠放: 世界树以左上角对齐叠到主图, 完全落在主图范围内, 切换 UI 已移除
const off = ev('MOFF[1]');
check(Math.abs(off[0] + 339748.5) < 1 && Math.abs(off[1] - 93797) < 1,
      `世界树叠放偏移 dx=${off[0]} dy=${off[1]} (左上角对齐 = 纯平移)`);
check(ev(`(function(){const o=MOFF[1],b=MAPS[1].bounds,B=MAPS[0].bounds;
        return b.minX+o[0]>=B.minX-1 && b.maxX+o[0]<=B.maxX+1 && b.minY+o[1]>=B.minY-1 && b.maxY+o[1]<=B.maxY+1;})()`),
      '世界树叠放矩形完全落在主图范围内');
check(ev("typeof buildMapTabs === 'undefined' && typeof switchMap === 'undefined' && typeof curMap === 'undefined'"),
      '已移除底图切换 (地图标签 / switchMap / curMap)');
check(ev("PTS.filter(p=>p.m===1&&!p.dd).length") > 0, '世界树点位仍在数据里 (参与搜索与绘制)');
check(ev("PXY(PTS.find(p=>p.m===1)).every(Number.isFinite)"), '世界树点位可投影到同一视图');
// 底图叠放 (抓 drawImage 的 5 参数调用 = 底图贴图): 两张都画, 世界树矩形在主图内且比例正确
const bg = near.bgRects || [];
check(bg.length >= 2, `两张底图都被绘制 (${bg.length} 次贴图)`);
if (bg.length >= 2) {
  const [ax, ay, aw, ah] = bg[0], [bx, by, bw, bh] = bg[1];
  check(bx >= ax - 1 && by >= ay - 1 && bx + bw <= ax + aw + 1 && by + bh <= ay + ah + 1,
        '世界树贴图矩形落在主图矩形内 (叠在空白区)');
  check(Math.abs(bw / aw - 0.236) < 0.01,
        `世界树贴图宽度比 ${(bw / aw).toFixed(3)} ≈ 0.236 (341797/1448800)`);
}

// ---- 触控手势: 在桩上派发真实 touch 事件, 检查捏合缩放/单指平移/轻点 ----
console.log('✓ 触控手势测试');
const cvEl = elements['cv'];
const hasTouch = cvEl && cvEl._lis && cvEl._lis.touchstart && cvEl._lis.touchmove && cvEl._lis.touchend;
check(!!hasTouch, 'canvas 已注册 touchstart / touchmove / touchend');
if (hasTouch) {
  // changed: touchend 时抬起的手指 (touches 为空, 必须显式给出)
  const fire = (type, touches, changed) => cvEl._lis[type].forEach(f => f({
    touches, changedTouches: changed || touches, preventDefault() {},
  }));
  const T = (x, y) => ({ clientX: x, clientY: y });
  const state = () => ev('({s:view.s, cx:view.cx, cy:view.cy})');

  // 1) 双指捏合放大: 两指间距 100 -> 200, 中点保持不动
  ev('view.s = 1920/1448800; view.cx = (MAPS[0].bounds.minX+MAPS[0].bounds.maxX)/2; view.cy = 0;');
  const before = state();
  const midX = 600, midY = 400;
  const anchorBefore = ev(`(function(){const w=s2w(${midX},${midY});return {x:w[0],y:w[1]};})()`);
  fire('touchstart', [T(midX - 50, midY), T(midX + 50, midY)]);
  fire('touchmove', [T(midX - 100, midY), T(midX + 100, midY)]);
  const after = state();
  const anchorAfter = ev(`(function(){const w=s2w(${midX},${midY});return {x:w[0],y:w[1]};})()`);
  check(Math.abs(after.s / before.s - 2) < 0.01, `双指间距翻倍 -> 缩放 ×${(after.s / before.s).toFixed(2)}`);
  check(Math.abs(anchorAfter.x - anchorBefore.x) < 1 && Math.abs(anchorAfter.y - anchorBefore.y) < 1,
        '缩放锚点(双指中点)下的世界坐标保持不变');
  fire('touchend', [], []);
  check(!ev('touch'), 'touchend 后手势状态已清空');

  // 2) 单指拖动平移: 屏幕向右 100px -> 世界 Y(东) 反向
  const p0 = state();
  fire('touchstart', [T(300, 300)]);
  fire('touchmove', [T(400, 300)]);
  const p1 = state();
  check(Math.abs((p0.cy - p1.cy) - 100 / p1.s) < 1, `单指横拖 100px -> 平移 ${((p0.cy - p1.cy) * p1.s).toFixed(0)}px (与世界坐标一致)`);
  check(Math.abs(p1.cx - p0.cx) < 1, '纯横向拖动不影响南北方向');
  fire('touchend', [], []);

  // 3) 双指整体拖动 (间距不变) 只平移不缩放
  const z0 = state();
  fire('touchstart', [T(500, 400), T(600, 400)]);
  fire('touchmove', [T(520, 400), T(620, 400)]);
  const z1 = state();
  check(Math.abs(z1.s - z0.s) < 1e-12, '双指等距平移不改变缩放');
  check(Math.abs((z0.cy - z1.cy) - 20 / z1.s) < 1, '双指平移跟随中点移动');
  fire('touchend', [], []);

  // 4) 轻点 -> 打开点位面板 (先把视口对准一个真实 Boss 点位, 再点它的屏幕坐标)
  const hitInfo = ev(`(function(){
      const p = PTS.find(q => q.t==='F' || q.t==='NB');
      view.cx = pX(p); view.cy = pY(p); view.s = 1920/1448800*6;
      const s = PXY(p); return {x:s[0], y:s[1], t:p.t, n:p.n};
  })()`);
  elements['detail'].style.display = 'none';
  fire('touchstart', [T(hitInfo.x, hitInfo.y)]);
  fire('touchend', [], [T(hitInfo.x, hitInfo.y)]);
  const shown = elements['detail'] && elements['detail'].style.display === 'block';
  check(shown, `轻点 Boss 点位 -> 详情面板打开 (${hitInfo.t} / ${hitInfo.n})`);

  // 5) 轻点空白处 -> 关闭面板
  elements['detail'].style.display = 'none';
  ev('view.cx = MAPS[0].bounds.maxX; view.cy = MAPS[0].bounds.minY;');   // 移到地图角落(无点位)
  fire('touchstart', [T(960, 540)]);
  fire('touchend', [], [T(960, 540)]);
  check(elements['detail'].style.display === 'none', '轻点空白处不打开面板');
}
console.log(ok ? '\nSMOKE TEST: PASS' : '\nSMOKE TEST: FAIL');
process.exit(ok ? 0 : 1);
