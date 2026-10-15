# -*- coding: utf-8 -*-
"""确认野外Boss/监禁Boss 点位的头像图标解析覆盖率 (与 JS 端同一套逻辑)。"""
import json, re, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PTS, PALS, TABLES, BOUNTY = d['points'], d['pals'], d['tables'], d['bounty']

def icon_src(p):
    if p['t'] == 'NB':
        b = BOUNTY.get(p.get('nb') or '')
        return (b or {}).get('icon')
    if p['t'] in ('F', 'I'):
        lst = TABLES.get(p['n']) or []
        e = next((x for x in lst if x.get('bg')), None) or (lst[0] if lst else None)
        if not e:
            return None
        v = PALS.get(e.get('b') or '') or {}
        return v.get('i')
    return None

for t in ('F', 'I', 'NB'):
    pts = [p for p in PTS if p['t'] == t]
    ok = [p for p in pts if icon_src(p)]
    print(f'{t}: {len(pts)} 个点位, 有图标 {len(ok)}')
    miss = [p for p in pts if not icon_src(p)]
    for p in miss[:5]:
        print(f'    缺图标: {p["n"]}  (nb={p.get("nb","")})')

# F/I 用到的头像是否都在内嵌图标里
srcs = collections.Counter()
for p in PTS:
    if p['t'] in ('F', 'I', 'NB'):
        s = icon_src(p)
        srcs[(p['t'], s[:40] if s else None)] += 1
print(f'\n涉及不同图标源 {len(srcs)} 种 (前 8):')
for (t, s), n in srcs.most_common(8):
    print(f'   {t} x{n:<3} {s}')
