# -*- coding: utf-8 -*-
"""检查"唯一固定1的帕鲁不在槽位1"的那 8 行, 判断槽位1与头领哪个更像代表。"""
import json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'data')
wild = json.load(open(os.path.join(SRC, 'DT_PalWildSpawner.json'), encoding='utf-8'))[0]['Rows']
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
import re
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PALS = d['pals']


def cn(pid):
    if pid.startswith('NPC:'):
        return pid
    v = PALS.get(pid[5:] if pid[:5].lower() == 'boss_' else pid) or {}
    return v.get('n') or pid


def slots(r):
    out = []
    for i in (1, 2, 3):
        p = r.get(f'Pal_{i}')
        if p not in ('None', 'RowName', '', None):
            out.append((i, p, r.get(f'NumMin_{i}'), r.get(f'NumMax_{i}'), r.get(f'LvMin_{i}')))
    for i in (1, 2, 3):
        n = r.get(f'NPC_{i}')
        if n not in ('None', '', None):
            out.append((i, 'NPC:' + n, r.get(f'NumMin_{i}'), r.get(f'NumMax_{i}'), r.get(f'LvMin_{i}')))
    return out


print('=== 唯一"固定1"的帕鲁不在槽位1 的行 (8 行) ===')
for n, r in ((n, r) for n, r in wild.items() if r.get('Weight', 0) > 0):
    ss = slots(r)
    if len(ss) < 2:
        continue
    ones = [s for s in ss if s[2] == 1 and s[3] == 1]
    if len(ones) != 1 or ones[0][0] == 1:
        continue
    desc = ' | '.join(f'槽{i}:{cn(p)}×{a}~{b}(Lv{lv})' for i, p, a, b, lv in ss)
    lead = f'头领={cn(ones[0][1])}(槽{ones[0][0]})'
    print(f'   [{r["SpawnerName"][:26]:26s}] w={r["Weight"]:<5g} {lead}')
    print(f'      {desc}')
