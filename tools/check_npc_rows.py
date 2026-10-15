# -*- coding: utf-8 -*-
"""核实: 普通刷怪范围内含 NPC 的行是否真的都是"纯 NPC"(无帕鲁)。

判定标准不能只看 id 前缀 (游戏数据里部分人类 NPC 没有 NPC_ 前缀, 如 Male_NinjaElite01),
要看该条目在帕鲁图鉴表里是否存在 / 是否有头像。
"""
import json, re, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PTS, ROWS, PALS = d['points'], d['rows'], d['pals']

N = collections.Counter()
for p in PTS:
    if p['t'] == 'C' and not p['u']:
        N[p['n']] += 1


def is_npc_id(e):
    return (e.get('id') or '').startswith('NPC:')


def is_pal(e):
    """真正的帕鲁: 归一化后能在帕鲁表里查到"""
    return bool(e.get('b')) and e['b'] in PALS


print('=== 普通刷怪范围内含"非帕鲁条目"的行 (逐条判定) ===')
rows = []
for n in N:
    for r in ROWS.get(n) or []:
        if all(is_pal(e) for e in r['pals']):
            continue
        rows.append((n, r))
for n, r in rows:
    print(f'\n[{n}] 点 {N[n]}  w={r["w"]:g}')
    for e in r['pals']:
        pal = is_pal(e)
        icon = bool((PALS.get(e.get('b') or '') or {}).get('i'))
        kind = '帕鲁' if pal else '非帕鲁(NPC)'
        print(f'   {e["id"]:28s} 归一化={str(e.get("b")):22s} {kind:12s} 头像={"有" if icon else "无"}')

print(f'\n合计 {len(rows)} 行含非帕鲁条目')
mixed = [(n, r) for n, r in rows if any(is_pal(e) for e in r['pals'])]
print(f'其中"帕鲁与 NPC 混排"的行: {len(mixed)}')
for n, r in mixed:
    print(f'   [{n}] ' + ' + '.join(f"{e['id']}({'帕鲁' if is_pal(e) else 'NPC'})" for e in r['pals']))

# 全数据集: 是否存在真实的混排行
print('\n=== 全数据集 (所有刷怪器) 的混排行 ===')
allmixed = []
for n, rs in ROWS.items():
    for r in rs:
        if len(r['pals']) < 2:
            continue
        pals = [e for e in r['pals'] if is_pal(e)]
        npcs = [e for e in r['pals'] if not is_pal(e)]
        if pals and npcs:
            allmixed.append((n, r, pals, npcs))
print(f'   帕鲁+NPC 同行的行: {len(allmixed)}')
for n, r, pals, npcs in allmixed[:10]:
    print(f'      [{n}] ' + ' + '.join(e['id'] for e in r['pals']))
