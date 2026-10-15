# -*- coding: utf-8 -*-
"""头像抽选可行性分析:
1) 每个刷怪器的点位数 N vs 其帕鲁条目数 -> 权重分配后有多少条目会"分不到点"
2) 夜间限定帕鲁按 1/5 权重折算后的影响
分配规则: 调整权重 w' = w (白天可用) 或 w/5 (仅夜间), 份额 p=w'/Σw', 期望点数 = N*p
"""
import json, re, os, collections, statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PTS, TABLES, PALS = d['points'], d['tables'], d['pals']

common = [p for p in PTS if p['t'] == 'C' and not p['u']]
N_by_spawner = collections.Counter(p['n'] for p in common)
print(f'普通点 {len(common)} 个, 涉及刷怪器 {len(N_by_spawner)} 个')

ity = sorted(N_by_spawner.values())
print(f'每个刷怪器的点位数 N: 最小 {ity[0]}, p25 {ity[len(ity)//4]}, 中位 {ity[len(ity)//2]}, '
      f'p90 {ity[int(len(ity)*0.9)]}, 最大 {ity[-1]}')
hist = collections.Counter()
for n in ity:
    hist['1' if n == 1 else '2-4' if n < 5 else '5-9' if n < 10 else '10-19' if n < 20 else '20-49' if n < 50 else '50+'] += 1
print('  N 分布:', dict(hist))


def alloc(n, entries, night_div):
    """返回 (可见条目数, 分不到点的条目列表, 期望点数表)"""
    ws = []
    for e in entries:
        w = e['w']
        if night_div and e.get('time') == 'Night':
            w = w / night_div
        ws.append(w)
    tot = sum(ws)
    if tot <= 0:
        return 0, entries, []
    exp = [n * w / tot for w in ws]
    vis = sum(1 for x in exp if x >= 1.0)
    miss = [e for e, x in zip(entries, exp) if x < 1.0]
    return vis, miss, exp


for night_div, label in ((1, '不折算 (对照)'), (5, '夜间权重 ×1/5 (你的规则)')):
    tot_entries = tot_vis = tot_miss = 0
    night_entries = night_vis = 0
    spawners_all_visible = 0
    spawners_missing = []
    for n, ents in ((N_by_spawner[s], TABLES.get(s) or []) for s in N_by_spawner):
        if not ents:
            continue
        vis, miss, exp = alloc(n, ents, night_div)
        tot_entries += len(ents)
        tot_vis += vis
        tot_miss += len(miss)
        for e in ents:
            if e.get('time') == 'Night':
                night_entries += 1
        for e, x in zip(ents, exp):
            if e.get('time') == 'Night' and x >= 1.0:
                night_vis += 1
        if not miss:
            spawners_all_visible += 1
        elif miss:
            spawners_missing.append((len(miss), n, len(ents), s if False else None))
    print(f'\n=== {label} ===')
    print(f'  (刷怪器, 帕鲁条目) 组合 {tot_entries} 个: 期望点数≥1 的 {tot_vis} ({100*tot_vis/tot_entries:.1f}%), '
          f'<1 会被舍掉的 {tot_miss} ({100*tot_miss/tot_entries:.1f}%)')
    print(f'  完全能画全的刷怪器: {spawners_all_visible} / {len(N_by_spawner)}')
    print(f'  夜间限定条目 {night_entries} 个, 其中能画上 {night_vis} ({100*night_vis/max(night_entries,1):.1f}%)')

# 结构性不足: 条目数 > 点位数
over = [(N_by_spawner[s], len(TABLES.get(s) or []), s) for s in N_by_spawner
        if TABLES.get(s) and len(TABLES[s]) > N_by_spawner[s]]
over.sort(reverse=True)
print(f'\n=== 结构性不足 (条目数 > 点位数): {len(over)} 个刷怪器 ===')
for n, k, s in over[:10]:
    print(f'   {s[:38]:38s} 点 {n:4d}, 帕鲁条目 {k:3d}, 缺 {k-n} 个位置')

# 最坏情况: 条目最多的几个刷怪器在 1/5 规则下的可见比例
print('\n=== 条目最多的 8 个刷怪器 (夜间×1/5) ===')
for s, ents in sorted(TABLES.items(), key=lambda kv: -len(kv[1]))[:8]:
    n = N_by_spawner.get(s, 0)
    if not n:
        continue
    vis, miss, exp = alloc(n, ents, 5)
    night = [e for e in ents if e.get('time') == 'Night']
    print(f'   {s[:34]:34s} 点 {n:4d}, 条目 {len(ents):3d} (夜间 {len(night):2d}) -> 可画 {vis:3d}, '
          f'舍掉 {len(miss):3d}')

# 期望点数 <1 的阈值: 需要多少点才能画上全部条目
print('\n=== 要让全部条目都分到 ≥1 个点, 需要多少点 (夜间×1/5) ===')
need = []
for s, ents in TABLES.items():
    n = N_by_spawner.get(s)
    if not n or not ents:
        continue
    # 最小 N 使所有期望 ≥1  => N >= 1/min(share)
    ws = [(e['w'] / (5 if e.get('time') == 'Night' else 1)) for e in ents]
    tot = sum(ws)
    if tot <= 0:
        continue
    mn = min(ws) / tot
    need.append((1 / mn if mn > 0 else 9e9, n, len(ents), s))
need.sort(reverse=True)
print(f'   需要点数中位 {statistics.median([x[0] for x in need]):.0f}, 最大 {need[0][0]:.0f}')
for need_n, n, k, s in need[:6]:
    print(f'   {s[:34]:34s} 现有 {n:4d} 点, 条目 {k:3d}, 需 {need_n:6.0f} 点')
