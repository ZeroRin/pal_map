# -*- coding: utf-8 -*-
"""输出两套头像缩放的实际数值:
  Boss  : 50m 基准, 16~96px
  普通点: 25m 基准,  16~48px
以及普通点头像 LOD 的实际开关边界。与 JS 用同一套算法。
"""
import json, re, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PTS = d['points']

STEP = 8
BOSS = ('Boss', 50, 16, 96)
PAL = ('普通点', 25, 16, 48)
PAL_LOD_PX, PAL_LOD_MAX = 16, 2500


def size(m, lo, hi, span_cm, W=1920):
    raw = m * 100 * (W / span_cm)
    q = round(max(lo, min(hi, raw)) / STEP) * STEP
    return int(max(lo, q)), raw


def table(spec, span_cm, W=1920):
    name, m, lo, hi = spec
    px, raw = size(m, lo, hi, span_cm, W)
    world = px / (W / span_cm) / 100
    note = '下限截断' if raw < lo else ('上限截断' if raw > hi else '量化')
    return px, raw, world, note


print('=== 尺寸表 (窗口 1920px, dpr=1) ===')
print(f'{"视野":>8} | {"Boss(50m)":>22} | {"普通点(25m)":>22}')
print(f'{"":>8} | {"理论px":>7} {"尺寸":>5} {"代表":>6} | {"理论px":>7} {"尺寸":>5} {"代表":>6}')
for km in (15, 12, 10, 8, 6, 5, 4, 3, 2.5, 2, 1.5, 1, 0.5):
    span = km * 100000
    b = table(BOSS, span)
    p = table(PAL, span)
    print(f'{km:7.1f}km | {b[1]:7.1f} {b[0]:4d}px {b[2]:5.0f}m | {p[1]:7.1f} {p[0]:4d}px {p[2]:5.0f}m')

for spec in (BOSS, PAL):
    name, m, lo, hi = spec
    W = 1920
    far = m * 100 * W / lo / 100000
    near = m * 100 * W / hi / 100000
    print(f'\n=== {name}: 基准 {m}m, 上下限 {lo}~{hi}px, 量化 {STEP}px ===')
    print(f'   100%对齐 {m}m 的区间: 视野 {near:.2f}km ~ {far:.2f}km'
          f'  (量化误差 ≤ ±{STEP/2}px)')
    e_far = lo / (W / (15 * 100000)) / 100      # 全图 15km 时该下限尺寸代表的范围
    e_near = hi / (W / (0.5 * 100000)) / 100    # 0.5km 时该上限尺寸代表的范围
    print(f'   更远(全图 15km) -> 固定 {lo}px, 实际代表 {e_far:.0f}m (大于 {m}m)')
    print(f'   更近(0.5km)    -> 固定 {hi}px, 实际代表 {e_near:.0f}m (小于 {m}m)')

# 普通点 LOD 边界
common = [p for p in PTS if p['t'] == 'C' and not p['u']]
CELL = 200000
(gx, gy), _ = collections.Counter((int(p['x'] // CELL), int(p['y'] // CELL)) for p in common).most_common(1)[0]
cx, cy = (gx + .5) * CELL, (gy + .5) * CELL


def visible(span_cm, src=common, cxx=None, cyy=None, W=1920, H=1080):
    cxx = cx if cxx is None else cxx
    cyy = cy if cyy is None else cyy
    hw, hh = span_cm / 2, span_cm * H / W / 2
    return sum(1 for p in src if abs(p['x'] - cxx) <= hh and abs(p['y'] - cyy) <= hw)


print(f'\n=== 普通点头像 LOD (阈值: 尺寸 ≥{PAL_LOD_PX}px 且同屏 ≤{PAL_LOD_MAX} 个) ===')
print(f'{"视野":>8} {"普通点px":>8} {"同屏普通点":>10}  结果')
for km in (15, 8, 5, 4, 3, 2.5, 2, 1.5, 1):
    span = km * 100000
    px, _, _, _ = table(PAL, span)
    n = visible(span)
    print(f'{km:7.1f}km {px:7d}px {n:10d}  {"头像" if px >= PAL_LOD_PX and n <= PAL_LOD_MAX else "画点"}')

thr = None
for i in range(2000, 49, -1):
    km = i / 100
    span = km * 100000
    px, _, _, _ = table(PAL, span)
    if px >= PAL_LOD_PX and visible(span) <= PAL_LOD_MAX:
        thr = km
        break
print(f'\n   最密集区域: 视野 ≤ {thr:.2f}km 时开头像 (该视野 {visible(thr*100000)} 个普通点)')
tree = [p for p in common if p['m'] == 1]
if tree:
    tx = sum(p['x'] for p in tree) / len(tree); ty = sum(p['y'] for p in tree) / len(tree)
    thr2 = None
    for i in range(2000, 49, -1):
        km = i / 100
        px, _, _, _ = table(PAL, km * 100000)
        if px >= PAL_LOD_PX and visible(km * 100000, tree, tx, ty) <= PAL_LOD_MAX:
            thr2 = km
            break
    print(f'   世界树(稀疏): 视野 ≤ {thr2:.2f}km 时开头像 (受 {PAL_LOD_PX}px 阈值限制, 与点数无关)')
print(f'\n   注: 普通点尺寸上限 {PAL[3]}px 对应视野 {PAL[1]*100*1920/PAL[3]/100000:.2f}km; '
      f'低于 {PAL_LOD_PX}px 的 {PAL[2]}~{PAL_LOD_PX}px 区间不会显示头像')
