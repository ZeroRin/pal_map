# -*- coding: utf-8 -*-
"""普通刷怪点: "不可定行 => 均分权重, 每只各占一格" 的格子需求核算 (修正版)。

可定 = 行内恰有 1 只"数量固定为1"(头领) 或 恰有 1 只"本刷怪器其它行未出现"
不可定 = 其它 -> 该行 k 只都要画, 占 k 格
腾位: ①先移除旺财行 ②若仍不足则移除仅夜间行 (以"是否降低需求"为准)
"""
import json, re, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PTS, ROWS, PALS = d['points'], d['rows'], d['pals']
MIMIC = 'MimicDog'


def cn(e):
    v = PALS.get(e.get('b') or '') or {}
    return v.get('n') or e['id']


def dsc(r):
    return ' + '.join(f"{cn(e)}×{e['num'][0]}{'~'+str(e['num'][1]) if e['num'][0]!=e['num'][1] else ''}"
                      for e in r['pals'])


N = collections.Counter()
for p in PTS:
    if p['t'] == 'C' and not p['u']:
        N[p['n']] += 1


def is_pal(e):
    """真正的帕鲁: 归一化后能在帕鲁表里查到 (不能只看 NPC_ 前缀)"""
    return bool(e.get('b')) and e['b'] in PALS


def is_determined(n, r):
    if len(r['pals']) == 1:
        return True
    ones = sum(1 for e in r['pals'] if e['num'][0] == 1 and e['num'][1] == 1)
    uniq = sum(1 for e in r['pals']
               if not any(e['id'] in [x['id'] for x in r2['pals']] for r2 in ROWS[n] if r2 is not r))
    return ones == 1 or uniq == 1


def need_of(n, rs):
    """格子需求: 含 NPC 的行统一记 1 格 (灰底占位符); 纯帕鲁行按代表/均分规则"""
    total = 0
    for r in rs:
        if any(not is_pal(e) for e in r['pals']):
            total += 1                      # NPC 行 -> 1 个灰底占位符
        elif len(r['pals']) == 1 or is_determined(n, r):
            total += 1
        else:
            total += len(r['pals'])         # 不可定 -> 均分, 每只各 1 格
    return total


print(f'普通点(地上): {sum(N.values())} 点位 / {len(N)} 刷怪器\n')
print(f'{"刷怪器":32s} {"点":>4} {"原始需":>6} {"去旺财":>6} {"去夜间":>6}  结果')
short = []
for n, pts in sorted(N.items(), key=lambda kv: -kv[1]):
    rs = ROWS.get(n) or []
    need0 = need_of(n, rs)
    rs1 = [r for r in rs if not all((e.get('b') or e['id']) == MIMIC for e in r['pals'])]
    need1 = need_of(n, rs1)
    rs2 = rs1
    if need1 > pts:                                   # 仍不足才腾夜间
        cand = [r for r in rs1 if r.get('time') != 'Night']
        if need_of(n, cand) < need1:
            rs2 = cand
    need2 = need_of(n, rs2)
    if need0 > pts:
        short.append((need2 - pts, n, pts, need0, need1, need2, rs2))
print(f'原始就"不足"的刷怪器: {len(short)} 个 (下表按最终缺口排序)')
print(f'{"刷怪器":32s} {"点":>4} {"原始需":>6} {"去旺财":>6} {"去夜间":>6}  结果')
for miss, n, pts, n0, n1, n2, rs2 in sorted(short, reverse=True):
    res = '✓ 解决' if n2 <= pts else f'✗ 仍缺 {n2-pts}'
    print(f'{n[:32]:32s} {pts:4d} {n0:6d} {n1:6d} {n2:6d}  {res}')

print('\n=== 仍不足的刷怪器明细 ===')
for miss, n, pts, n0, n1, n2, rs2 in sorted(short, reverse=True):
    if n2 <= pts:
        continue
    print(f'\n[{n}] 点 {pts}, 最终需 {n2} 格:')
    for r in sorted(rs2, key=lambda r: -r['w']):
        mark = '' if is_determined(n, r) else f"  ← 不可定, 占 {len(r['pals'])} 格"
        print(f'   w={r["w"]:<6g} {r.get("time") or "-":8s} {dsc(r)}{mark}')

# 全体汇总
tot_pts = sum(N.values())
tot_need0 = sum(need_of(n, ROWS.get(n) or []) for n in N)
tot_need2 = 0
for n, pts in N.items():
    rs = ROWS.get(n) or []
    rs1 = [r for r in rs if not all((e.get('b') or e['id']) == MIMIC for e in r['pals'])]
    if need_of(n, rs1) > pts:
        cand = [r for r in rs1 if r.get('time') != 'Night']
        if need_of(n, cand) < need_of(n, rs1):
            rs1 = cand
    tot_need2 += need_of(n, rs1)
print(f'\n=== 汇总 ===')
print(f'  点位总数 {tot_pts}, 原始格子需求 {tot_need0}, 腾位后 {tot_need2}')
print(f'  全局看 {"够" if tot_need2 <= tot_pts else "缺 %d 格" % (tot_need2-tot_pts)}'
      f' (但逐刷怪器看仍有 {sum(1 for m,n,p,a,b,c,rs in short if c>p)} 个不足, 因为格子不能跨刷怪器调拨)')
