# -*- coding: utf-8 -*-
"""补充统计: 其他可能影响"实际刷怪"的字段 (世界树光环 / 随机化 / NPC / 冷却)。"""
import json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.path.join(ROOT, 'src', 'data')
with open(os.path.join(SP, 'DT_PalWildSpawner.json'), encoding='utf-8') as f:
    wild = json.load(f)[0]['Rows']
with open(os.path.join(SP, 'DT_PalSpawnerPlacement.json'), encoding='utf-8') as f:
    placement = json.load(f)[0]['Rows']

w0 = {k: r for k, r in wild.items() if r.get('Weight', 0) > 0}
print(f'Weight>0 行: {len(w0)}')

print('\nbHasWorldTreeAura = true 的行:',
      sum(1 for r in w0.values() if r.get('bHasWorldTreeAura')))
if any(r.get('bHasWorldTreeAura') for r in w0.values()):
    names = {r['SpawnerName'] for r in w0.values() if r.get('bHasWorldTreeAura')}
    print('   涉及刷怪器:', sorted(names)[:10], f'(共{len(names)})')

print('\nbIsAllowRandomizer = true 的行:', sum(1 for r in w0.values() if r.get('bIsAllowRandomizer')),
      ' / false:', sum(1 for r in w0.values() if not r.get('bIsAllowRandomizer')))

print('\nWeight<=0 (被跳过) 的行:')
for k, r in wild.items():
    if r.get('Weight', 0) <= 0:
        print(f'   {k:35s} name={r["SpawnerName"]:30s} pal1={r.get("Pal_1")}')

print('\nNPC 字段取值:')
c = collections.Counter()
for r in w0.values():
    for i in (1, 2, 3):
        v = r.get(f'NPC_{i}', 'None')
        if v not in ('None', ''):
            c[v] += 1
for v, n in c.most_common():
    print(f'   {v:35s} x{n}')

# placement 侧: 冷却 / NPC 半径
print('\nRespawnCoolTime=60 的点位:')
for _, r in placement.items():
    if r.get('RespawnCoolTime'):
        print(f'   {r["InstanceName"][:60]:60s} name={r["SpawnerName"]} type={r["SpawnerType"].split("::")[-1]}')
