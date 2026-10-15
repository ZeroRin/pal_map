# -*- coding: utf-8 -*-
"""用"行"而非"帕鲁"重新判定点位是否真的不足。

R = 有效行数(每次抽签的一种结果, 一行可能是一组多只)
K = 合并后的帕鲁种类数
N = 点位数
若 R <= N 但 K > N, 说明多出的种类来自"同一行的组合", 一个点位即可代表整组 -> 不算不足。
"""
import json, re, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'data')
wild = json.load(open(os.path.join(SRC, 'DT_PalWildSpawner.json'), encoding='utf-8'))[0]['Rows']
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PALS, MAPS = d['pals'], d['maps']
common = [p for p in d['points'] if p['t'] == 'C' and not p['u']]
N = collections.Counter(p['n'] for p in common)
pts_by = collections.defaultdict(list)
for p in common:
    pts_by[p['n']].append(p)

# 每个刷怪器的行信息
rows_by = collections.defaultdict(list)
for rn, r in wild.items():
    if r.get('Weight', 0) > 0:
        rows_by[r['SpawnerName']].append((rn, r))


def pals_of_row(r):
    return [r.get(f'Pal_{i}') for i in (1, 2, 3)
            if r.get(f'Pal_{i}') not in ('None', 'RowName', '', None)]


print(f'{"刷怪器":40s} {"点N":>4} {"行R":>4} {"种类K":>5}  判定')
print('-' * 78)
really_bad = []
for s in sorted(N):
    rows = rows_by.get(s) or []
    if not rows:
        continue
    R = len(rows)
    K = len({r.get(f'Pal_{i}') for rn, r in rows for i in (1, 2, 3)
             if r.get(f'Pal_{i}') not in ('None', 'RowName', '', None)})
    n = N[s]
    if K <= n:
        continue
    if R > n:
        verdict = f'✗ 真不足 (行 R={R} > 点 N={n})'
        really_bad.append((s, n, R, K))
    else:
        verdict = f'○ 组合导致 (行 R={R} ≤ 点 N={n})'
    print(f'{s[:40]:40s} {n:4d} {R:4d} {K:5d}  {verdict}')

print(f'\n真正点位不足 (行数 > 点位数): {len(really_bad)} 个')
for s, n, R, K in sorted(really_bad, key=lambda x: -(x[2] - x[1])):
    print(f'   {s:40s} 点 {n:3d}, 行 {R:3d}, 种类 {K:3d}  (缺 {R-n} 种抽签结果)')

# LazyDragon 家族的行结构
print('\n=== LazyDragon 家族的行结构 ===')
def cn(pid):
    v = PALS.get(pid if pid[:5].lower() != 'boss_' else pid[5:]) or {}
    return v.get('n') or pid
for s in sorted(rows_by):
    if 'azydragon' in s.lower() and N.get(s):
        rows = rows_by[s]
        print(f'   {s:44s} 点 {N[s]}  行数 {len(rows)}')
        for rn, r in rows:
            ps = pals_of_row(r)
            det = ', '.join(f'{cn(p)}x{r.get(f"NumMin_{i}")}-{r.get(f"NumMax_{i}")}'
                            for i, p in ((i, r.get(f'Pal_{i}')) for i in (1, 2, 3))
                            if p not in ('None', 'RowName', '', None))
            print(f'      w={r["Weight"]:<4g} {rn:22s} {det}')
