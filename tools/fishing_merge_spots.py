# -*- coding: utf-8 -*-
"""合并两张 paldb 数据集的钓点, 分析归属与类型分布。"""
import json, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'paldb')
cfg = json.load(open(os.path.join(ROOT, 'tools', 'maps_config.json'), encoding='utf-8'))['maps']
MAPS = {m['key']: m['bounds'] for m in cfg}
print('底图范围:', {k: (v['minX'], v['maxX'], v['minY'], v['maxY']) for k, v in MAPS.items()})

allspots = []
for fn, label in (('paldb_fishing_spots.json', '帕洛斯(map8)'), ('paldb_fishing_spots_tree.json', '世界树(treemap8)')):
    p = os.path.join(SRC, fn)
    if not os.path.exists(p):
        print(f'  (缺 {fn})'); continue
    data = json.load(open(p, encoding='utf-8'))
    print(f'{label}: {len(data)} 个钓点, 字段 {list(data[0]) if data else "-"}')
    for d in data:
        d['__src'] = fn
    allspots += data

print(f'\n合计 {len(allspots)} 个')


def which(x, y):
    for k, b in MAPS.items():
        if b['minX'] <= x <= b['maxX'] and b['minY'] <= y <= b['maxY']:
            return k
    return '?'


per_map = collections.Counter(which(s['pos']['X'], s['pos']['Y']) for s in allspots)
print('按底图归属:', dict(per_map))

by_type = collections.Counter(s['type'] for s in allspots)
print('按稀有度:', dict(by_type))

# 洞窟钓点 (位置是否可用)
dungeon = [s for s in allspots if 'Dungeon' in s['href']]
print(f"\n洞窟钓点: {len(dungeon)} 个")
if dungeon:
    xs = [s['pos']['X'] for s in dungeon]; ys = [s['pos']['Y'] for s in dungeon]
    zs = [s['pos'].get('Z') for s in dungeon]
    print(f'   X[{min(xs):.0f},{max(xs):.0f}] Y[{min(ys):.0f},{max(ys):.0f}] Z 取值 {sorted(set(zs))[:5]}')
    print(f'   示例: {[ (s["href"], s["pos"]) for s in dungeon[:3] ]}')

# Z 值分布 (看是否区分地表/水下)
zs = collections.Counter(s['pos'].get('Z') for s in allspots)
print(f'\nZ 值分布 (前 8): {zs.most_common(8)}')

# 每个底图的类型分布
print('\n各底图的类型数:')
for k in MAPS:
    sub = [s for s in allspots if which(s['pos']['X'], s['pos']['Y']) == k]
    print(f'   {k:10s} {len(sub):4d} 个, {len(set(s["href"] for s in sub))} 种类型')

json.dump(allspots, open(os.path.join(SRC, 'paldb_fishing_spots_all.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n已合并写入 src/paldb/paldb_fishing_spots_all.json')
