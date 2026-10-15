# -*- coding: utf-8 -*-
"""验证合并权重是否为求和, 并抽查若干刷怪器的占比合理性。"""
import json, re, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
T, P = d['tables'], d['pals']

def show(name):
    lst = T.get(name)
    if not lst:
        print(f'  (无 {name})'); return
    print(f'\n{name}  ({len(lst)} 条)')
    for e in lst:
        v = P.get(e['b']) if e.get('b') else None
        cn = v['n'] if v else e['id']
        rows = f" ×{e['rows']}" if e.get('rows', 1) > 1 else ''
        print(f"   {cn:9s} {e['id']:26s} w={e['w']:6.1f} ({e['pct']:5.1f}%{e.get('pb','')}){rows}"
              f"  lv{e['lv'][0]}-{e['lv'][1]} x{e['num'][0]}-{e['num'][1]}")

print('=== 修复验证: 同一帕鲁多行时权重应为各行之和 ===')
show('blue_B')          # Monkey_Fire: 25 + 10 = 35
show('blue_H')          # DarkCrow: 150 + 50 = 200
show('worldtree_9_01_A')  # ElecPanda: 80 + 50 = 130
show('skyisland_8_09w_D_forest')  # ElecLizard: 5 + 5 = 10

print('\n=== 无合并的常规刷怪器 (占比应加总约 100%) ===')
for name in ('skyisland_8_07_G_mountain', '5_1_island_tropical'):
    show(name)
    s = sum(e['pct'] for e in T.get(name, []) if e.get('pb', '') == '白天')
    s2 = sum(e['pct'] for e in T.get(name, []) if e.get('pb', '') == '夜间')
    if s or s2:
        print(f'   白天池占比合计 {s:.1f}%   夜间池合计 {s2:.1f}%')
    else:
        print(f'   占比合计 {sum(e["pct"] for e in T[name]):.1f}%')
