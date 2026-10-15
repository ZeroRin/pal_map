# -*- coding: utf-8 -*-
"""检查 StaticRadius 取值与点位实际间距, 判断 150m 半径是否合理。"""
import json, os, collections, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.path.join(ROOT, 'src', 'data')
with open(os.path.join(SP, 'DT_PalSpawnerPlacement.json'), encoding='utf-8') as f:
    P = json.load(f)[0]['Rows']
rows = list(P.values())

print('StaticRadius 取值分布:')
for v, c in collections.Counter(r.get('StaticRadius') for r in rows).most_common(10):
    print(f'   {v}  x{c}')

print('\nRadiusType x StaticRadius:')
for (rt, sr), c in collections.Counter(
        (r.get('RadiusType'), r.get('StaticRadius')) for r in rows).most_common(10):
    print(f'   {rt}  radius={sr}  x{c}')

pts = [(r['Location']['X'], r['Location']['Y'], r.get('SpawnerName', '')) for r in rows
       if r.get('SpawnerType') == 'EPalSpawnedCharacterType::Common'
       and 'Dungeon' not in r.get('PlacementType', '')]
print(f'\n参与统计的普通点: {len(pts)}')

cell = 100000.0
grid = collections.defaultdict(list)
for i, (x, y, _) in enumerate(pts):
    grid[(int(x // cell), int(y // cell))].append(i)
nn = []
nn_same = []
for i, (x, y, n) in enumerate(pts):
    gx, gy = int(x // cell), int(y // cell)
    best = None
    best_same = None
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for j in grid.get((gx + dx, gy + dy), []):
                if j == i:
                    continue
                d = (x - pts[j][0]) ** 2 + (y - pts[j][1]) ** 2
                if best is None or d < best:
                    best = d
                if pts[j][2] == n and (best_same is None or d < best_same):
                    best_same = d
    if best is not None:
        nn.append(math.sqrt(best))
    if best_same is not None:
        nn_same.append(math.sqrt(best_same))
nn.sort(); nn_same.sort()
print('最近邻间距 (任意刷怪器):')
for q in (0.05, 0.25, 0.5, 0.75, 0.95):
    v = nn[int(len(nn) * q)]
    print(f'   p{int(q*100):02d} = {v:9.0f} cm = {v/100:7.1f} m')
print(f'同刷怪器内最近邻中位数: {nn_same[len(nn_same)//2]/100:.1f} m (n={len(nn_same)})')

# 半径 15000cm=150m 时, 与最近邻点的重叠比例
R = 15000.0
overlap = sum(1 for v in nn if v < 2 * R) / len(nn)
print(f'\n半径 150m: 与最近邻圆重叠的点占比 {overlap*100:.1f}%')
for r_m in (15, 30, 50, 75, 100, 150):
    r = r_m * 100
    ov = sum(1 for v in nn if v < 2 * r) / len(nn)
    print(f'   半径 {r_m:3d}m -> 重叠点占比 {ov*100:5.1f}%')
