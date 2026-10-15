# -*- coding: utf-8 -*-
"""精确分解: 规则1 失败的行 → 规则2 能否救 → 真正"两条都不行"的到底是哪些行。

统一定义:
  ones = 该行内"数量固定为 1"的帕鲁个数
  uniq = 该行内"在本刷怪器其它行都没出现过"的帕鲁个数
  规则1 成立 = (ones == 1)
  规则2 成立 = (uniq == 1)
"""
import json, re, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
ROWS, PALS = d['rows'], d['pals']


def cn(e):
    v = PALS.get(e.get('b') or '') or {}
    return v.get('n') or e['id']


def desc(r):
    return ' + '.join(f"{cn(e)}×{e['num'][0]}{'~'+str(e['num'][1]) if e['num'][0]!=e['num'][1] else ''}"
                      for e in r['pals'])


rows_info = []
for n, rs in ROWS.items():
    for r in rs:
        if len(r['pals']) < 2:
            continue
        ones = sum(1 for e in r['pals'] if e['num'][0] == 1 and e['num'][1] == 1)
        uniq = 0
        for e in r['pals']:
            if not any(e['id'] in [x['id'] for x in r2['pals']] for r2 in rs if r2 is not r):
                uniq += 1
        rows_info.append({'n': n, 'r': r, 'ones': ones, 'uniq': uniq,
                          'r1': ones == 1, 'r2': uniq == 1})

print(f'多只行 {len(rows_info)}')
print(f'  规则1 成立 {sum(1 for x in rows_info if x["r1"])}')
print(f'  规则1 失败 {sum(1 for x in rows_info if not x["r1"])}')

fail1 = [x for x in rows_info if not x['r1']]
print(f'\n=== 规则1 失败的 {len(fail1)} 行 ===')
print(f'{"刷怪器":30s} {"固定1":>5} {"独有":>4} {"规则2":>5}  内容')
for x in fail1:
    print(f'{x["n"][:30]:30s} {x["ones"]:5d} {x["uniq"]:4d} {"✓救" if x["r2"] else "✗":>5}  {desc(x["r"])}')

both_fail = [x for x in rows_info if not x['r1'] and not x['r2']]
print(f'\n=== 两条都不行: {len(both_fail)} 行 ===')
aa = collections.Counter()
for x in both_fail:
    aa[(x['ones'], x['uniq'])] += 1
print(f'   按 (固定1数, 独有数) 分解: {dict(sorted(aa.items()))}')
for x in both_fail:
    print(f'   [{x["n"][:28]:28s}] 固定1={x["ones"]} 独有={x["uniq"]}  {desc(x["r"])}')

# 交叉核对: "0 只独有" 的行落在哪
zero = [x for x in rows_info if x['uniq'] == 0]
print(f'\n=== 交叉核对: 独有=0 的行共 {len(zero)} 行 ===')
for x in zero:
    tag = '规则1可救(不在这15里)' if x['r1'] else '→ 落在"两条都不行"里'
    print(f'   [{x["n"][:26]:26s}] 固定1={x["ones"]}  {tag}  {desc(x["r"])}')

# "独有>=2" 的行共有多少, 其中规则1 失败的多少
many = [x for x in rows_info if x['uniq'] >= 2]
print(f'\n=== 独有≥2 的行 {len(many)} 行: 其中规则1 失败的 {sum(1 for x in many if not x["r1"])} 行 ===')
