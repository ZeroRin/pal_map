# -*- coding: utf-8 -*-
"""普通刷怪范围内: 含 NPC 的行有多少? 这些行有没有头像可用?"""
import json, re, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PTS, ROWS, PALS = d['points'], d['rows'], d['pals']

N = collections.Counter()
for p in PTS:
    if p['t'] == 'C' and not p['u']:
        N[p['n']] += 1


def cn(e):
    v = PALS.get(e.get('b') or '') or {}
    return v.get('n') or e['id']


def is_npc(e):
    return (e.get('id') or '').startswith('NPC:')

print('=== 普通点(地上) 范围内含 NPC 的行 ===')
npc_rows = 0
npc_only_rows = 0
mixed_rows = 0
sp = set()
for n in N:
    for r in ROWS.get(n) or []:
        npcs = [e for e in r['pals'] if is_npc(e)]
        if not npcs:
            continue
        npc_rows += 1
        sp.add(n)
        if len(npcs) == len(r['pals']):
            npc_only_rows += 1
        else:
            mixed_rows += 1
        desc = ' + '.join(f"{cn(e)}×{e['num'][0]}{'~'+str(e['num'][1]) if e['num'][0]!=e['num'][1] else ''}"
                          f"{'(NPC)' if is_npc(e) else ''}" for e in r['pals'])
        print(f'   [{n[:30]:30s}] 点 {N[n]:4d}  w={r["w"]:<6g} {desc}')
print(f'\n含 NPC 的行 {npc_rows} 行 (纯 NPC 行 {npc_only_rows}, 混合行 {mixed_rows}), 涉及 {len(sp)} 个刷怪器')

# NPC 是否有头像
print('\n=== NPC 头像素材检查 ===')
npc_ids = set()
for n in N:
    for r in ROWS.get(n) or []:
        for e in r['pals']:
            if is_npc(e):
                npc_ids.add(e['id'])
have = 0
for pid in sorted(npc_ids):
    v = PALS.get(pid) or {}
    if v.get('i'):
        have += 1
print(f'  涉及 {len(npc_ids)} 种 NPC id, 其中有头像的 {have} 个')
print(f'  (普通人类 NPC 无头像素材, 详情面板用灰底 "NPC" 占位; 仅 33 个赏金首有图标, 且是独立图层)')
print('  样例:', ', '.join(sorted(npc_ids)[:8]))

# 不可定行里, 纯帕鲁 vs 含 NPC
print('\n=== "不可定"行分类 (普通点地上) ===')
pal_und = []
npc_und = []
for n in N:
    for r in ROWS.get(n) or []:
        if len(r['pals']) == 1:
            continue
        ones = sum(1 for e in r['pals'] if e['num'][0] == 1 and e['num'][1] == 1)
        uniq = sum(1 for e in r['pals']
                   if not any(e['id'] in [x['id'] for x in r2['pals']] for r2 in ROWS[n] if r2 is not r))
        if ones == 1 or uniq == 1:
            continue
        desc = ' + '.join(cn(e) for e in r['pals'])
        if any(is_npc(e) for e in r['pals']):
            npc_und.append((n, N[n], len(r['pals']), desc))
        else:
            pal_und.append((n, N[n], len(r['pals']), desc))
print(f'  纯帕鲁的不可定行 {len(pal_und)} 行:')
for n, pts, k, desc in pal_und:
    print(f'     [{n[:28]:28s}] 点 {pts:4d} 需 {k} 格   {desc}')
print(f'  含 NPC 的不可定行 {len(npc_und)} 行:')
for n, pts, k, desc in npc_und:
    print(f'     [{n[:28]:28s}] 点 {pts:4d} 需 {k} 格   {desc}')
