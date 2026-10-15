# -*- coding: utf-8 -*-
"""校验洞窟合并视图: 名称/分类池/组合/小怪, 并按分类统计。"""
import json, re, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
DUN, ROWS, TABLES, PALS = d['dungeons'], d['rows'], d['tables'], d['pals']

print(f'洞口 {len(DUN)} 个, 有名称 {sum(1 for v in DUN.values() if v["aname"])}, '
      f'组合表 {sum(len(v) for v in ROWS.values())} 种')

# 分类池统计
poolstat = collections.Counter()
for v in DUN.values():
    for rk, lst in (v.get('pools') or {}).items():
        if lst:
            poolstat[rk] += 1
print('含各类池的洞口数:', dict(poolstat))

# 名称分布
names = collections.Counter(v['aname'] for v in DUN.values() if v['aname'])
print(f'\n洞窟名 {len(names)} 种:')
for n, c in names.most_common(15):
    print(f'   {n:16s} {c} 个洞口')

# 抽查 3 个不同类型的洞口
print('\n=== 抽查 ===')
shown = 0
for k, v in DUN.items():
    pools = v.get('pools') or {}
    if not (pools.get('FishPal') or pools.get('NPCHuman')):
        continue
    print(f'\n[{v["aname"]}] {k}  ({v["x"]:.0f},{v["y"]:.0f})')
    for rk in ('Boss', 'Normal', 'NPCHuman', 'FishPal'):
        lst = pools.get(rk) or []
        if not lst:
            continue
        print(f'   {rk:9s} {lst}')
        if rk == 'Boss':
            n = 0
            for nm in lst:
                for c in (ROWS.get(nm) or []):
                    pals = ' + '.join(f"{e.get('b') or e['id']}{'·'+e['bg'] if e.get('bg') else ''}×{e['num'][0]}"
                                      for e in c['pals'])
                    print(f'        组合 w={c["w"]:<6} {pals}')
                    n += 1
                    if n >= 3: break
                if n >= 3: break
        else:
            pals = []
            for nm in lst:
                for e in (TABLES.get(nm) or []):
                    vv = PALS.get(e['b']) if e.get('b') else None
                    pals.append(((vv or {}).get('n') or e['id']))
            print(f'        -> {sorted(set(pals))}')
    shown += 1
    if shown >= 2:
        break

# 洞窟内钓点池 (FishPal) 涉及的帕鲁
fp = set()
for v in DUN.values():
    for nm in (v.get('pools') or {}).get('FishPal') or []:
        for e in (TABLES.get(nm) or []):
            fp.add((PALS.get(e['b']) or {}).get('n') or e['id'])
print(f'\n洞窟钓点池涉及的帕鲁: {sorted(fp)}')
