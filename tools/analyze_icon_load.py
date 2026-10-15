# -*- coding: utf-8 -*-
"""可行性分析: 不同缩放档位下, 视口内可见的普通刷怪点数 (决定渲染压力)。

视口按 1920x1080 计算; "视野宽度" = 屏幕上横向覆盖的世界距离。
"""
import json, re, os, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PTS, TABLES = d['points'], d['tables']

W, H = 1920, 1080
common = [p for p in PTS if p['t'] == 'C' and not p['u']]
common_all = [p for p in PTS if p['t'] == 'C']          # 含洞窟内部
print(f'普通刷怪点: {len(common)} (地上) / {len(common_all)} (含洞窟内部) / 全部标记 {len(PTS)}')

# 最密集点作为视口中心 (压力最大的情况)
CELL = 200000.0
import collections
bk = collections.Counter((int(p['x'] // CELL), int(p['y'] // CELL)) for p in common)
(gx, gy), n = bk.most_common(1)[0]
cx, cy = (gx + .5) * CELL, (gy + .5) * CELL
print(f'最密集 2km 网格: {n} 个普通点, 中心 ({cx:.0f},{cy:.0f})\n')

print(f'{"视野宽度":>9} {"缩放(px/cm)":>12} {"视口内普通点":>12} {"视口内全部标记":>14} {"100m对应像素":>12}')
for km in (15, 10, 8, 5, 4, 3, 2, 1.5, 1.0, 0.6):
    span = km * 100000.0                     # 视野宽度(厘米)
    s = W / span                             # px per cm
    hw, hh = span / 2, span * H / W / 2
    nc = sum(1 for p in common if abs(p['x'] - cx) <= hh and abs(p['y'] - cy) <= hw)
    na = sum(1 for p in PTS if p['m'] == 0 and abs(p['x'] - cx) <= hh and abs(p['y'] - cy) <= hw)
    print(f'{km:8.1f}km {s:12.2e} {nc:12d} {na:14d} {100*100*s:11.1f}px')

# 各刷怪器的帕鲁条目数 -> 决定"按权重分配头像"的候选数
ent = [len(t) for t in TABLES.values()]
import statistics
print(f'\n刷怪表条目数: 平均 {statistics.mean(ent):.1f}, 中位 {statistics.median(ent):.0f}, '
      f'最大 {max(ent)}, 共 {len(TABLES)} 张表')
# 普通点覆盖的刷怪器数
names = {p['n'] for p in common}
print(f'普通点涉及刷怪器 {len(names)} 个; 这些表里的帕鲁条目合计 '
      f'{sum(len(TABLES.get(n) or []) for n in names)} 条')
# 每个刷怪器的点位数分布 -> 分配比例时的粒度
cnt = collections.Counter(p['n'] for p in common)
v = sorted(cnt.values())
print(f'每个刷怪器的点位数: 最小 {v[0]}, 中位 {v[len(v)//2]}, 最大 {v[-1]}')

# 图标资源规模
use = set()
for n in names:
    for e in (TABLES.get(n) or []):
        if e.get('b'):
            use.add(e['b'])
print(f'普通点会用到的不同帕鲁图标: {len(use)} 种 (总内嵌 {len(d["pals"])} 种)')
sizes = [len((d['pals'].get(b) or {}).get('i') or '') for b in use]
print(f'这些图标的 base64 体积合计 {sum(sizes)/1e6:.2f} MB (已内嵌, 无需新增)')
