# -*- coding: utf-8 -*-
"""校验成品 HTML 中的钓点数据: 图层/类型/关联链/底图归属。"""
import json, re, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))

print('DATA 键:', list(d.keys()))
print('图层:', {v['code']: v['label'] for v in d['types'].values()})

pts = d['points']
fish = [p for p in pts if p['t'] in ('FC', 'FR')]
sp = [p for p in pts if p['t'] not in ('FC', 'FR')]
print(f'\n点位: 刷怪 {len(sp)} + 钓点 {len(fish)} = {len(pts)}')
for i, m in enumerate(d['maps']):
    sub = [p for p in pts if p['m'] == i]
    fi = [p for p in sub if p['t'] in ('FC', 'FR')]
    print(f'   {m["label"]:6s}: 刷怪 {len(sub)-len(fi):4d} + 钓点 {len(fi):3d}')

print(f'\n钓点类型表: {len(d["fishing"])} 种')
unresolved = sorted({p['n'] for p in fish if p['n'] not in d['fishing']})
print('  实例中未匹配类型:', unresolved or '无')

# 抽查一个世界树钓点 + 一个帕洛斯钓点
for want in ('FishingSpot_WorldTree_Rare', 'FishingSpot_A_Ocean_Common'):
    inst = [p for p in fish if p['n'] == want]
    f = d['fishing'].get(want)
    if not inst or not f:
        print(f'\n(缺 {want})'); continue
    p = inst[0]
    print(f'\n=== {want} ===')
    print(f'   实例 {len(inst)} 个, 例: X={p["x"]:.0f} Y={p["y"]:.0f} Z={p["z"]}m 底图={d["maps"][p["m"]]["label"]} 稀有={p["t"]=="FR"}')
    print(f'   重生 {f["respawn"]}s, 可钓 {len(f["rows"])} 种:')
    for e in f['rows'][:6]:
        v = d['pals'].get(e['b']) if e.get('b') else None
        cn = (v or {}).get('n', e['id'])
        icon = '有图标' if (v or {}).get('i') else '无图标'
        print(f'      {cn:10s} {e["id"]:28s} {e.get("bg","") or "-":4s} Lv{e["lv"][0]}-{e["lv"][1]} '
              f'w={e["w"]}({e["pct"]}%) 难度={e["dif"]:8s} [{icon}]')

# 中文名/图标覆盖
tot = miss = 0
for t in d['fishing'].values():
    for e in t['rows']:
        tot += 1
        v = d['pals'].get(e['b']) if e.get('b') else None
        if not v or not v.get('i'):
            miss += 1
print(f'\n钓点产出条目 {tot} 条, 有中文名+图标 {tot-miss} ({100*(tot-miss)/tot:.1f}%)')
