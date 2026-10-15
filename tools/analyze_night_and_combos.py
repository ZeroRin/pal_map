# -*- coding: utf-8 -*-
"""1) 剔除仅夜间行后, 4 个不足刷怪器的格子是否够
2) 按"行"统计组合在各类刷怪器中的分布 (普通点/野外Boss/洞窟Boss), 校正之前的说法
"""
import json, re, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'data')
wild = json.load(open(os.path.join(SRC, 'DT_PalWildSpawner.json'), encoding='utf-8'))[0]['Rows']
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PTS, PALS = d['points'], d['pals']

rows_by = collections.defaultdict(list)
for rn, r in wild.items():
    if r.get('Weight', 0) > 0:
        rows_by[r['SpawnerName']].append((rn, r))


def slots(r):
    return [r.get(f'Pal_{i}') for i in (1, 2, 3) if r.get(f'Pal_{i}') not in ('None', 'RowName', '', None)]


def is_combo(r):
    return len(set(slots(r))) >= 2


def is_night(r):
    return r.get('OnlyTime', '').endswith('Night')


# 点位分类
pts_by = collections.defaultdict(list)
for p in PTS:
    if p['t'] == 'C' and not p['u']:
        pts_by[p['n']].append(p)

print('=== 1) 剔除仅夜间行后, 4 个不足刷怪器是否够 ===')
for s in ('worldtree_9_55_WorldTreeAura', 'desert_orange_G', 'snow_orange_D', 'blue_C'):
    rows = rows_by.get(s) or []
    n = len(pts_by.get(s, []))
    day = [r for _, r in rows if not is_night(r)]
    print(f'   {s:34s} 点 {n:3d} | 全部行 {len(rows):3d} -> 剔除夜间后 {len(day):3d} '
          f'{"✓ 够" if len(day) <= n else "✗ 仍差 %d" % (len(day)-n)}'
          f'   (夜间行 {len(rows)-len(day)})')

print('\n=== 2) 组合行的分布 (按点位类型) ===')
# 把每个刷怪器归类: 普通点 / 野外Boss / 监禁Boss / 洞窟Boss / 其他
kind = {}
for p in PTS:
    kind.setdefault(p['n'], set()).add(p['t'])
names = collections.defaultdict(list)
for s in kind:
    names[','.join(sorted(kind[s]))].append(s)

for label in sorted(names, key=lambda k: -len(names[k])):
    group = names[label]
    tot_rows = combos = 0
    with_combo = 0
    pts = 0
    for s in group:
        rs = rows_by.get(s) or []
        c = sum(1 for _, r in rs if is_combo(r))
        tot_rows += len(rs)
        combos += c
        if c:
            with_combo += 1
        pts += len(pts_by.get(s, []))
    print(f'   点位类型 {label:12s}: 刷怪器 {len(group):4d}, 行 {tot_rows:5d}, '
          f'含组合的刷怪器 {with_combo:3d}, 组合行 {combos:4d}')

# 普通点里的组合行明细
print('\n=== 普通刷怪点中含组合行的刷怪器 ===')
tot_pts = 0
for s in sorted(pts_by):
    rs = rows_by.get(s) or []
    cs = [(rn, r) for rn, r in rs if is_combo(r)]
    if not cs:
        continue
    tot_pts += len(pts_by[s])
    print(f'   {s[:38]:38s} 点 {len(pts_by[s]):3d}, 行 {len(rs):2d}, 组合行 {len(cs):2d}')
print(f'   合计覆盖点位 {tot_pts} / {sum(len(v) for v in pts_by.values())}')

# 野外Boss 的"是否固定单一组合"
print('\n=== 野外Boss 的行/组合情况 (核对我之前的说法) ===')
fb = [p['n'] for p in PTS if p['t'] == 'F']
seen = {}
for s in set(fb):
    rs = rows_by.get(s) or []
    sigs = {tuple(sorted(slots(r))) for _, r in rs}
    seen[s] = (len(rs), len(sigs))
multi = {s: v for s, v in seen.items() if v[1] > 1}
print(f'   野外Boss 刷怪器 {len(seen)} 个: 只有 1 种组合的 {len(seen)-len(multi)} 个, '
      f'有多种组合的 {len(multi)} 个')
for s, (nr, ns) in list(multi.items())[:5]:
    print(f'      {s}: {nr} 行 / {ns} 种不同组合')
