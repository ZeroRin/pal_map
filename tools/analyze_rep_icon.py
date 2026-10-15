# -*- coding: utf-8 -*-
"""分析多只组合行的"代表头像"选取规则覆盖度。

规则1 (1+n): 行内恰有一只数量固定为 1 (头领), 其余 >1  -> 取该头领
规则2 (1+1): 行内多只数量都为 1 -> 取"同刷怪器其它行都没有出现的"那只
本脚本检查: 是否覆盖全部情形; 有无 多+多; 有无规则2 无法定夺的 1+1。
"""
import json, re, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
ROWS, PALS = d['rows'], d['pals']


def cn(e):
    v = PALS.get(e.get('b') or '') or {}
    return v.get('n') or e['id']


def cnt_txt(e):
    n0, n1 = e['num']
    return f'{n0}' if n0 == n1 else f'{n0}~{n1}'


multi = [(n, r) for n, rs in ROWS.items() for r in rs if len(r['pals']) > 1]
print(f'多只行共 {len(multi)} 行 (来自 {len({n for n, _ in multi})} 个刷怪器)\n')

# 每行每只的数量类型
def cls(e):
    n0, n1 = e['num']
    if n0 == 1 and n1 == 1:
        return 'one'        # 固定 1
    if n0 == 1:
        return 'maybe1'     # 1~n
    return 'gt1'            # ≥2

pat = collections.Counter()
examples = collections.defaultdict(list)
for n, r in multi:
    kinds = [cls(e) for e in r['pals']]
    k = len(kinds)
    ones = kinds.count('one')
    gt1 = kinds.count('gt1')
    maybe = kinds.count('maybe1')
    key = f'k={k} ones={ones} maybe1={maybe} gt1={gt1}'
    pat[key] += 1
    if len(examples[key]) < 3:
        examples[key].append((n, r))

print('=== 数量模式分布 ===')
for k, c in sorted(pat.items(), key=lambda kv: -kv[1]):
    print(f'   {k:34s} {c:3d} 行')

# 规则1 判定
print('\n=== 规则1 (取数量为1的头领) ===')
r1_ok, r1_amb, r1_none = [], [], []
for n, r in multi:
    ones = [e for e in r['pals'] if cls(e) == 'one']
    if len(ones) == 1:
        r1_ok.append((n, r, ones[0]))
    elif len(ones) == 0:
        r1_none.append((n, r))
    else:
        r1_amb.append((n, r, ones))
print(f'   唯一头领 -> 可直接取: {len(r1_ok)} 行')
print(f'   没有固定为 1 的: {len(r1_none)} 行')
print(f'   有多个固定为 1 的: {len(r1_amb)} 行')

for label, lst in (('没有固定1的', r1_none), ('多个固定1的', r1_amb)):
    if not lst:
        continue
    print(f'\n   --- {label} 明细 (前 12) ---')
    for item in lst[:12]:
        n, r = item[0], item[1]
        desc = ' + '.join(f'{cn(e)}×{cnt_txt(e)}' for e in r['pals'])
        print(f'      [{n[:34]:34s}] w={r["w"]:<6g} {desc}')

# 规则2 判定: 该行的某只在该刷怪器的其它行里是否出现
print('\n=== 规则2 (取同刷怪器其它行没有出现的那只) ===')
r2_uniq1 = r2_uniq0 = r2_uniqN = 0
r2_fail = []
for n, r in multi:
    rs = ROWS[n]
    uniq = []
    for e in r['pals']:
        elsewhere = any(e['id'] in [x['id'] for x in r2['pals']] for r2 in rs if r2 is not r)
        if not elsewhere:
            uniq.append(e)
    if len(uniq) == 1:
        r2_uniq1 += 1
    elif len(uniq) == 0:
        r2_uniq0 += 1
        if len(r2_fail) < 12:
            r2_fail.append(('无独有帕鲁', n, r))
    else:
        r2_uniqN += 1
        if len(r2_fail) < 12:
            r2_fail.append((f'{len(uniq)} 只都独有', n, r))
print(f'   恰有 1 只独有 -> 可定夺: {r2_uniq1} 行')
print(f'   0 只独有      -> 无法定夺: {r2_uniq0} 行')
print(f'   多只都独有    -> 有歧义:   {r2_uniqN} 行')
if r2_fail:
    print('\n   困难案例:')
    for why, n, r in r2_fail[:10]:
        desc = ' + '.join(f'{cn(e)}×{cnt_txt(e)}' for e in r['pals'])
        print(f'      [{why}] [{n[:30]:30s}] {desc}')

# 组合覆盖: 规则1 唯一头领优先, 否则规则2
cover1 = cover2 = none = 0
unresolved = []
for n, r in multi:
    ones = [e for e in r['pals'] if cls(e) == 'one']
    if len(ones) == 1:
        cover1 += 1
        continue
    rs = ROWS[n]
    uniq = [e for e in r['pals']
            if not any(e['id'] in [x['id'] for x in r2['pals']] for r2 in rs if r2 is not r)]
    if len(uniq) == 1:
        cover2 += 1
    else:
        none += 1
        unresolved.append((n, r, len(ones), len(uniq)))
print(f'\n=== 覆盖度 (规则1 → 规则2) ===')
print(f'   规则1 解决: {cover1} ({100*cover1/len(multi):.1f}%)')
print(f'   规则2 解决: {cover2} ({100*cover2/len(multi):.1f}%)')
print(f'   两条都不行: {none} ({100*none/len(multi):.1f}%)')
for n, r, no, nu in unresolved[:10]:
    desc = ' + '.join(f'{cn(e)}×{cnt_txt(e)}' for e in r['pals'])
    print(f'      [{n[:30]:30s}] 固定1有{no}只, 独有{nu}只  {desc}')
