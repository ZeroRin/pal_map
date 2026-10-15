# -*- coding: utf-8 -*-
"""列出两张刷怪表的全部字段及其取值情况, 检查 UI 是否漏掉条件类字段。"""
import json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.path.join(ROOT, 'src', 'data')

for fn, label in (('DT_PalWildSpawner.json', 'DT_PalWildSpawner'),
                  ('DT_PalSpawnerPlacement.json', 'DT_PalSpawnerPlacement')):
    with open(os.path.join(SP, fn), encoding='utf-8') as f:
        rows = json.load(f)[0]['Rows']
    keys = collections.Counter()
    for r in rows.values():
        for k in r:
            keys[k] += 1
    print(f'\n===== {label}  ({len(rows)} 行) 字段清单 =====')
    for k, n in keys.most_common():
        vals = [r.get(k) for r in rows.values() if k in r]
        uniq = {json.dumps(v, ensure_ascii=False, sort_keys=True) for v in vals}
        if len(uniq) <= 4:
            sample = ' | '.join(sorted(uniq)[:4])
        else:
            sample = f'{len(uniq)} 种不同值'
        print(f'   {k:28s} 出现{n:5d}行   {sample[:100]}')

    # 条件类字段候选: 名字含 Time/Weather/Condition/Only/Flag 等
    print(f'   -- 条件类字段候选 --')
    for k in keys:
        if any(s in k.lower() for s in ('time', 'weather', 'condition', 'only', 'flag', 'rate', 'cool')):
            c = collections.Counter(json.dumps(r.get(k), ensure_ascii=False) for r in rows.values() if k in r)
            print(f'     {k}: ' + ', '.join(f'{v} x{n}' for v, n in c.most_common(6)))
