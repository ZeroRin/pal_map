# -*- coding: utf-8 -*-
"""校验新规则: 点位不足时 ①先移除"旺财"(MimicDog) ②仍不够再移除仅夜间行。

同时统计旺财的分布, 验证"极低概率、几乎无处不在"的说法。
"""
import json, re, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PTS, ROWS, PALS = d['points'], d['rows'], d['pals']
MIMIC = 'MimicDog'          # 旺财

def is_mimic(e):
    return (e.get('b') or e['id']) == MIMIC


def cat(p):
    if p['t'] == 'C':
        return '普通点(地上)' if not p['u'] else '普通点(洞窟内部)'
    return {'DG': '地下城', 'F': '野外Boss', 'I': '监禁Boss'}.get(p['t'], p['t'])


info = {}
for p in PTS:
    if p['t'] in ('FC', 'FR', 'NB', 'ND'):
        continue
    e = info.setdefault(p['n'], {'n': 0, 'cat': set(), 'r': p['r'], 'm': p['m'], 'pts': []})
    e['n'] += 1
    e['cat'].add(cat(p))
    e['pts'].append(p)

# ---- 旺财分布 ----
tot_rows = 0
mimic_single = mimic_multi = 0
spawners_with_mimic = 0
weights = []
for n, rs in ROWS.items():
    tot_rows += len(rs)
    ms = [r for r in rs if any(is_mimic(e) for e in r['pals'])]
    if not ms:
        continue
    spawners_with_mimic += 1
    for r in ms:
        weights.append(r['w'])
        if len(r['pals']) == 1:
            mimic_single += 1
        else:
            mimic_multi += 1
print(f'=== 旺财(MimicDog) 分布 ===')
print(f'  出现在 {spawners_with_mimic} / {len(ROWS)} 个刷怪器, 共 {mimic_single + mimic_multi} 行'
      f'（单只行 {mimic_single}, 与其他帕鲁同行 {mimic_multi}）')
if weights:
    ws = sorted(weights)
    print(f'  权重范围 {ws[0]:g}~{ws[-1]:g}, 中位 {ws[len(ws)//2]:g}')
if mimic_multi:
    print('  与其他帕鲁同行的例子:')
    for n, rs in ROWS.items():
        for r in rs:
            if len(r['pals']) > 1 and any(is_mimic(e) for e in r['pals']):
                print(f'     {n}: ' + ' + '.join((e.get('b') or e['id']) for e in r['pals']))
                break
        else:
            continue
        break

# ---- 应用新规则 ----
print(f'\n=== 新规则效果 (普通点(地上)) ===')
rows_out = []
for n, e in info.items():
    rs = ROWS.get(n)
    if not rs or '普通点(地上)' not in e['cat']:
        continue
    N = e['n']
    R = len(rs)
    if R <= N:
        continue
    # ① 移除旺财行 (仅当该行只含旺财; 若与其他帕鲁同行则只从该行摘掉旺财)
    step1 = []
    dropped_mimic = 0
    for r in rs:
        if all(is_mimic(x) for x in r['pals']):
            dropped_mimic += 1
            continue
        step1.append(r)
    # ② 仍不够则移除仅夜间行
    R1 = len(step1)
    dropped_night = 0
    if R1 > N:
        keep = [r for r in step1 if r.get('time') != 'Night']
        dropped_night = R1 - len(keep)
        if len(keep) >= N:
            step1 = keep
        else:
            step1 = keep            # 记下仍然不够
    R2 = len(step1)
    rows_out.append((n, N, R, dropped_mimic, R1, dropped_night, R2, e['r'], e['m']))

print(f'{"刷怪器":38s} {"点":>4} {"行":>4} {"去旺财":>6} {"剩":>4} {"去夜间":>6} {"终":>4}  结果')
for n, N, R, dm, R1, dn, R2, reg, m in sorted(rows_out, key=lambda x: -(x[6] - x[1])):
    ok = '✓ 够' if R2 <= N else f'✗ 仍缺 {R2-N}'
    print(f'{n[:38]:38s} {N:4d} {R:4d} {dm:6d} {R1:4d} {dn:6d} {R2:4d}  {ok}')

print('\n仍不足的:', [n for n, N, R, dm, R1, dn, R2, reg, m in rows_out if R2 > N] or '无')

# 洞窟类同样算一遍(仅作参考)
print('\n=== 洞窟类 (走合并面板, 仅参考) ===')
for n, e in info.items():
    if '普通点(地上)' in e['cat']:
        continue
    rs = ROWS.get(n)
    if not rs or len(rs) <= e['n']:
        continue
    dm = sum(1 for r in rs if all(is_mimic(x) for x in r['pals']))
    R1 = len(rs) - dm
    keep = [r for r in rs if r.get('time') != 'Night']
    R2 = len(keep)
    print(f'   {n:38s} 点 {e["n"]:3d} 行 {len(rs):3d} -> 去旺财 {R1:3d} -> 去夜间 {R2:3d} '
          f'{"✓" if R2 <= e["n"] else "✗ 仍缺 %d" % (R2-e["n"])}')
