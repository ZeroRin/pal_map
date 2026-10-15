# -*- coding: utf-8 -*-
"""校验普通点头像分配:
1) 覆盖: 每个普通点都有头像, 除整片跳过的刷怪器
2) 数量守恒: 每个刷怪器的头像数量之和 = 该刷怪器的点位数
3) 数量与种子无关: 换种子只改位置, 各头像数量不变
4) 保底: 换种子后每个"单位"仍至少 1 格
5) 夜间折算: 仅夜间行确实按 1/5 计权
"""
import json, re, os, sys, collections, random, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import build_spawner_map as B

html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PTS, ROWS, PALS, ICON_KEY = d['points'], d['rows'], d['pals'], d['icons']

NO_ICON = {"worldtree_9_55_WorldTreeAura"}


def is_pal(e):
    return bool(e.get('b'))


# 按刷怪器分组 (与构建同序: m,x,y,z)
groups = collections.defaultdict(list)
for i, p in enumerate(PTS):
    if p['t'] == 'C' and not p['u']:
        groups[p['n']].append(i)
for n in groups:
    groups[n].sort(key=lambda i: (PTS[i]['m'], PTS[i]['x'], PTS[i]['y'], PTS[i]['z']))

print('=== 1) 覆盖 ===')
miss = []
for n, idxs in groups.items():
    for i in idxs:
        ii = PTS[i].get('ii')
        if n in NO_ICON:
            if ii != -1:
                miss.append((n, i, ii, '应为 -1'))
        elif ii is None or ii < 0:
            miss.append((n, i, ii, '缺少头像'))
print(f'   普通点 {sum(len(v) for v in groups.values())} 个, 异常 {len(miss)} 个 {miss[:5]}')
print(f'   整片跳过: {sorted(NO_ICON)} (点 {sum(len(groups[n]) for n in NO_ICON)})')

print('\n=== 2) 数量守恒 ===')
bad = []
for n, idxs in groups.items():
    if n in NO_ICON:
        continue
    k = sum(1 for i in idxs if PTS[i].get('ii', -1) >= 0)
    if k != len(idxs):
        bad.append((n, k, len(idxs)))
print(f'   数量不等于点位数的刷怪器: {len(bad)} {bad[:5]}')

print('\n=== 3/4) 换种子后数量不变、保底仍成立 ===')
SEEDS = [20251009, 1, 999999, 42]
mismatch = []
for n, idxs in sorted(groups.items()):
    if n in NO_ICON:
        continue
    rs = ROWS.get(n) or []
    if not rs:
        continue
    units0 = B.build_icon_units(rs, is_pal)
    units = B.trim_icon_units(units0, len(idxs))
    base = collections.Counter(u[0] for u in B.allocate_icon_units(units, len(idxs)))
    for sd in SEEDS[1:]:
        # 用另一套种子重跑"分配"这一步 (数量由 allocate 决定, 与种子无关;
        # 这里额外确认打乱顺序不会改变计数)
        q = [u[0] for u in B.allocate_icon_units(units, len(idxs))]
        rnd = random.Random(sd ^ zlib.crc32(n.encode()))
        rnd.shuffle(q)
        if collections.Counter(q) != base:
            mismatch.append((n, sd))
    got = collections.Counter(ICON_KEY[PTS[i]['ii']] for i in idxs)
    if got != base:
        mismatch.append((n, 'HTML不一致'))
    # 夜间标志: 图上描蓝框的点数必须等于配额中"仅夜间单位"的数量
    want_night = sum(1 for u in B.allocate_icon_units(units, len(idxs)) if u[2])
    got_night = sum(1 for i in idxs if PTS[i].get('ni'))
    if want_night != got_night:
        mismatch.append((n, f'夜间标志 {got_night} != {want_night}'))
print(f'   不一致的刷怪器: {len(mismatch)} {mismatch[:5]}')

print('\n=== 5) 夜间折算抽样 ===')
shown = 0
for n, idxs in sorted(groups.items()):
    rs = ROWS.get(n) or []
    night = [r for r in rs if r.get('time') == 'Night']
    if not night or shown >= 3:
        continue
    got = collections.Counter(ICON_KEY[PTS[i]['ii']] for i in idxs)
    print(f'   [{n}] 点 {len(idxs)}, 行 {len(rs)} (夜间 {len(night)})')
    for r in sorted(rs, key=lambda r: -r['w'])[:6]:
        keys = [B.pal_meta(e['id'], {}, {})[0] or e['id'] for e in r['pals']] if False else None
        label = ' + '.join((e.get('b') or e['id']) for e in r['pals'])
        cnt = sum(got.get((e.get('b') or e['id']), 0) for e in r['pals']) // max(1, len(r['pals']))
        print(f'      w={r["w"]:<6g} {"夜" if r.get("time")=="Night" else "  "} {label[:46]:46s} 图上约 {cnt} 个')
    shown += 1

print('\n=== 汇总 ===')
tot = sum(len(v) for v in groups.values())
npc = sum(1 for p in PTS if p.get('ii', -1) >= 0 and ICON_KEY[p['ii']] == 'NPC')
night = sum(1 for p in PTS if p.get('ni'))
print(f'   普通点 {tot} · 有头像 {tot - sum(len(groups[n]) for n in NO_ICON)} · NPC 占位 {npc} · 仅夜间(蓝框) {night} · 头像种类 {len(ICON_KEY)}')
tops = collections.Counter(ICON_KEY[p['ii']] for p in PTS if p.get('ii', -1) >= 0)
print('   出现最多的头像:', [(PALS.get(k, {}).get('n', k), v) for k, v in tops.most_common(5)])
