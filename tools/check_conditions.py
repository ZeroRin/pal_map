# -*- coding: utf-8 -*-
"""枚举 DT_PalWildSpawner 的 OnlyTime / OnlyWeather 全部取值, 以及它们在 UI 中实际出现的组合。"""
import json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.path.join(ROOT, 'src', 'data')
with open(os.path.join(SP, 'DT_PalWildSpawner.json'), encoding='utf-8') as f:
    wild = json.load(f)[0]['Rows']

rows = list(wild.items())
print(f'DT_PalWildSpawner 总行数: {len(rows)}')

w0 = [(k, r) for k, r in rows if r.get('Weight', 0) > 0]
print(f'其中 Weight>0 (构建脚本采纳): {len(w0)}    Weight<=0 (被跳过): {len(rows)-len(w0)}')

for label, subset in (('全部行', rows), ('仅 Weight>0', w0)):
    print(f'\n===== {label} =====')
    for fld in ('OnlyTime', 'OnlyWeather'):
        c = collections.Counter(r.get(fld) for _, r in subset)
        print(f'  {fld}:')
        for v, n in c.most_common():
            print(f'     {v:55s} x{n}')

print('\n===== 组合 (Weight>0) =====')
combo = collections.Counter((r.get('OnlyTime'), r.get('OnlyWeather')) for _, r in w0)
for (t, w), n in combo.most_common():
    print(f'   time={t:45s} weather={w:45s} x{n}')

# 被 UI 展示的条件字符串 (脚本里 strip_enum 后的形态)
print('\n===== UI 中 strip_enum 后实际显示的条件 (Weight>0, 且 Pal 槽位非空) =====')
shown = collections.Counter()
for k, r in w0:
    t = r.get('OnlyTime', '').split('::')[-1]
    w = r.get('OnlyWeather', '').split('::')[-1]
    for i in (1, 2, 3):
        pal = r.get(f'Pal_{i}', 'None')
        npc = r.get(f'NPC_{i}', 'None')
        if pal in ('None', 'RowName', '', None) and npc in ('None', '', None):
            continue
        cond = ' / '.join([x for x in (t if t != 'Undefined' else '', w if w != 'Undefined' else '') if x])
        shown[cond if cond else '(无条件)'] += 1
for v, n in shown.most_common():
    print(f'   {v:40s} x{n}')
