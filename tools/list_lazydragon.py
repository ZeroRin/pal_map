# -*- coding: utf-8 -*-
"""LazyDragon 家族与其余点位不足刷怪器的帕鲁构成。"""
import json, re, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PALS, TABLES = d['pals'], d['tables']
common = [p for p in d['points'] if p['t'] == 'C' and not p['u']]
by = collections.Counter(p['n'] for p in common)


def cn(e):
    v = PALS.get(e.get('b') or '') or {}
    return v.get('n') or e['id']


def desc(e):
    return (f'{cn(e)}(w={e["w"]:g}, Lv{e["lv"][0]}-{e["lv"][1]}, '
            f'x{e["num"][0]}-{e["num"][1]}{", 夜" if e.get("time") == "Night" else ""})')


print('=== LazyDragon 家族 (各 1 点 / 2 种) ===')
for s in sorted(TABLES):
    if 'azydragon' in s.lower():
        ents = TABLES[s]
        print(f'   {s:44s} -> ' + ' + '.join(desc(e) for e in ents))
        print(f'      点位 {by.get(s, 0)} 个')

print('\n=== 其余点位不足的刷怪器 ===')
for s in ('desert_orange_G', 'snow_orange_D', 'blue_C'):
    ents = TABLES.get(s) or []
    print(f'\n   {s}: 点 {by.get(s, 0)} / 种 {len(ents)}')
    for e in sorted(ents, key=lambda e: -e['w']):
        print(f'      {desc(e)}')
