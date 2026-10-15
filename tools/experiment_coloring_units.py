# -*- coding: utf-8 -*-
"""实验: 比较着色单元 (LayerName vs SpawnerName) 与着色算法的代价。
排除洞窟内部点 (坐标叠放无意义)。"""
import json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.path.join(ROOT, 'src', 'data')

with open(os.path.join(SP, 'DT_PalSpawnerPlacement.json'), encoding='utf-8') as f:
    placement = json.load(f)[0]['Rows']

pts = []
for _, p in placement.items():
    if p.get('SpawnerType') != 'EPalSpawnedCharacterType::Common':
        continue
    if 'Dungeon' in p.get('PlacementType', ''):
        continue  # 洞窟内部: 多副本叠放, 不参与地表着色
    loc = p['Location']
    layers = p.get('LayerNames') or []
    pts.append({
        'n': p.get('SpawnerName', 'None'),
        'r': (layers[0].replace('EnemySpawner_', '') if layers else p.get('SpawnerName', 'None')),
        'x': loc['X'], 'y': loc['Y'],
    })
print(f'参与着色的普通点: {len(pts)}')


def build_graph(pts, unit, T=50000.0, min_pts=1):
    field = {'region': 'r', 'spawner': 'n'}[unit]

    def find(par, a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    groups = collections.defaultdict(list)
    for i, p in enumerate(pts):
        groups[p[field]].append(i)
    key_of, keys = {}, set()
    for g, idxs in groups.items():
        par = {i: i for i in idxs}
        grid = collections.defaultdict(list)
        for i in idxs:
            p = pts[i]
            grid[(int(p['x'] // T), int(p['y'] // T))].append(i)
        for i in idxs:
            p = pts[i]
            gx, gy = int(p['x'] // T), int(p['y'] // T)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for j in grid.get((gx + dx, gy + dy), []):
                        if j <= i:
                            continue
                        q = pts[j]
                        if (p['x'] - q['x']) ** 2 + (p['y'] - q['y']) ** 2 < T * T:
                            ra, rb = find(par, i), find(par, j)
                            if ra != rb:
                                par[ra] = rb
        for i in idxs:
            k = (g, find(par, i))
            key_of[i] = k
            keys.add(k)
    if min_pts > 1:
        ksize = collections.Counter(key_of.values())
        for i, k in list(key_of.items()):
            if ksize[k] < min_pts:
                del key_of[i]
        keys = {k for k in keys if ksize[k] >= min_pts}
    grid = collections.defaultdict(list)
    for i, p in enumerate(pts):
        grid[(int(p['x'] // T), int(p['y'] // T))].append(i)
    adj = {k: set() for k in keys}
    for i, p in enumerate(pts):
        gx, gy = int(p['x'] // T), int(p['y'] // T)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((gx + dx, gy + dy), []):
                    if j <= i:
                        continue
                    q = pts[j]
                    if p[field] == q[field]:
                        continue
                    if (p['x'] - q['x']) ** 2 + (p['y'] - q['y']) ** 2 < T * T:
                        a, b = key_of.get(i), key_of.get(j)
                        if a is None or b is None or a == b:
                            continue
                        adj[a].add(b)
                        adj[b].add(a)
    return keys, adj


def greedy_wp(keys, adj, PAL):
    color = {}
    for k in sorted(keys, key=lambda k: -len(adj[k])):
        used = {color[n] for n in adj[k] if n in color}
        c = next((c for c in range(PAL) if c not in used), None)
        if c is None:
            cnt = collections.Counter(color[n] for n in adj[k] if n in color)
            c = min(range(PAL), key=lambda c: cnt.get(c, 0))
        color[k] = c
    return color


def dsatur(keys, adj, PAL):
    color, sat = {}, {k: set() for k in keys}
    un = set(keys)
    while un:
        k = max(un, key=lambda k: (len(sat[k]), len(adj[k])))
        used = sat[k]
        c = next((c for c in range(PAL) if c not in used), None)
        if c is None:
            cnt = collections.Counter(color[n] for n in adj[k] if n in color)
            c = min(range(PAL), key=lambda c: cnt.get(c, 0))
        color[k] = c
        un.discard(k)
        for n in adj[k]:
            if n in un:
                sat[n].add(c)
    return color


def refine(keys, adj, color, rounds=200):
    """局部搜索: 反复给冲突节点换到无冲突颜色"""
    for _ in range(rounds):
        conf = [k for k in keys if any(color[n] == color[k] for n in adj[k])]
        if not conf:
            break
        improved = False
        for k in sorted(conf, key=lambda k: -len(adj[k])):
            nb = {color[n] for n in adj[k]}
            free = [c for c in set(color.values()) if c not in nb]
            if free:
                color[k] = free[0]
                improved = True
        if not improved:
            break
    return color


def stats(keys, adj, color):
    conf = sum(1 for a in keys for b in adj[a] if color[a] == color[b]) // 2
    return conf, len(set(color.values()))


for unit, min_pts in (('region', 3), ('spawner', 1), ('spawner', 3)):
    keys, adj = build_graph(pts, unit, min_pts=min_pts)
    edges = sum(len(v) for v in adj.values()) // 2
    max_deg = max((len(v) for v in adj.values()), default=0)
    print(f"\n=== unit={unit} minPts={min_pts}: nodes={len(keys)} edges={edges} maxDeg={max_deg}")
    for PAL in (12, 14, 16, 18, 20):
        c1 = greedy_wp(keys, adj, PAL)
        e1, u1 = stats(keys, adj, c1)
        c2 = dsatur(keys, adj, PAL)
        e2, u2 = stats(keys, adj, c2)
        c3 = refine(keys, adj, dict(c2))
        e3, u3 = stats(keys, adj, c3)
        print(f"   palette={PAL:2d} | WP: used={u1:2d} conf={e1:3d} "
              f"| DSATUR: used={u2:2d} conf={e2:3d} | DSATUR+精修: used={u3:2d} conf={e3:3d}")
