# -*- coding: utf-8 -*-
"""校验成品 HTML 中的赏金首图层与无数据图层。"""
import json, re, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))

print('图层 (off=1 表示默认不勾选):')
for k, v in d['types'].items():
    print(f"   {v['code']:3s} {v['label']:16s} {v['color']}  off={v.get('off',0)}")

pts = d['points']
nb = [p for p in pts if p['t'] == 'NB']
nd = [p for p in pts if p['t'] == 'ND']
print(f"\n赏金首点位 {len(nb)} 个 / 无数据点位 {len(nd)} 个")
print(f"bounty 资料表: {len(d['bounty'])} 条, 其中有名称 {sum(1 for v in d['bounty'].values() if v['name'])}, "
      f"有图标 {sum(1 for v in d['bounty'].values() if v['icon'])}")

print('\n赏金首点位明细 (前 12):')
for p in nb[:12]:
    b = d['bounty'].get(p['nb'], {})
    print(f"   {p['nb']:32s} {b.get('name','(无名称)'):12s} 图标={'✓' if b.get('icon') else '✗'} "
          f"底图={d['maps'][p['m']]['label']} X={p['x']:.0f} Y={p['y']:.0f} Z={p['z']}m")

print('\n赏金首完备性检查:')
miss_n = [p['nb'] for p in nb if not d['bounty'].get(p['nb'], {}).get('name')]
miss_i = [p['nb'] for p in nb if not d['bounty'].get(p['nb'], {}).get('icon')]
miss_l = [p['nb'] for p in nb if not p.get('lv')]
print(f"   缺名称 {len(miss_n)} {miss_n}")
print(f"   缺图标 {len(miss_i)} {miss_i}")
print(f"   缺等级 {len(miss_l)} {miss_l}")
fixed = [(p['nb_orig'], p['nb'], p.get('lv')) for p in nb if p.get('nb_orig')]
print(f"   类名被权威表纠正的点位 {len(fixed)}: {fixed}")
ok = not (miss_n or miss_i or miss_l)
print('   结论:', '✓ 33/33 完备 (名称/图标/等级)' if ok else '✗ 有缺失')

print('\n无名称的赏金首:')
for p in nb:
    b = d['bounty'].get(p['nb'], {})
    if not b.get('name'):
        print(f"   {p['nb']}  (点位 X={p['x']:.0f} Y={p['y']:.0f})")

print('\n无数据点位 (按类名汇总):')
import collections
c = collections.Counter((p.get('cls') or '?').split('_C')[0] for p in nd)
for k, n in c.most_common():
    print(f'   {n:3d}  {k}')
