# -*- coding: utf-8 -*-
"""补充: 1) 列出规则2 无法定夺的行; 2) 检查"槽位顺序"是否可作统一判据;
3) 分析 1+1 行里两只的关系 (同族变体?/不同种?)"""
import json, re, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'data')
wild = json.load(open(os.path.join(SRC, 'DT_PalWildSpawner.json'), encoding='utf-8'))[0]['Rows']
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
ROWS, PALS = d['rows'], d['pals']

# 原始行: 保留槽位序号
raw_by_name = collections.defaultdict(list)
for rn, r in wild.items():
    if r.get('Weight', 0) > 0:
        raw_by_name[r['SpawnerName']].append((rn, r))


def slots(r):
    out = []
    for i in (1, 2, 3):
        p = r.get(f'Pal_{i}')
        if p not in ('None', 'RowName', '', None):
            out.append((i, p, r.get(f'NumMin_{i}'), r.get(f'NumMax_{i}')))
    for i in (1, 2, 3):
        n = r.get(f'NPC_{i}')
        if n not in ('None', '', None):
            out.append((i, 'NPC:' + n, r.get(f'NumMin_{i}'), r.get(f'NumMax_{i}')))
    return out


def cn(pid):
    if pid.startswith('NPC:'):
        return pid
    v = PALS.get(pid[5:] if pid[:5].lower() == 'boss_' else pid) or {}
    return v.get('n') or pid


multi_raw = [(n, rn, r) for n, rs in raw_by_name.items() for rn, r in rs if len(slots(r)) > 1]
print(f'原始多只行 {len(multi_raw)} 行')

# 1) 唯一固定1的槽位分布
lead_slot = collections.Counter()
for n, rn, r in multi_raw:
    ss = slots(r)
    ones = [(i, p) for i, p, a, b in ss if a == 1 and b == 1]
    if len(ones) == 1:
        lead_slot[ones[0][0]] += 1
print(f'\n=== 唯一"固定1"帕鲁所在槽位 === {dict(sorted(lead_slot.items()))}')
first_ok = sum(v for k, v in lead_slot.items() if k == 1)
print(f'   其中位于槽位1的: {first_ok} / {sum(lead_slot.values())}')

# 2) 规则2 无法定夺的行 (两只都在别的行出现)
print('\n=== 规则2 无法定夺 (行内两只都在本刷怪器其它行出现过) ===')
cnt = 0
for n, rs in ROWS.items():
    for r in rs:
        if len(r['pals']) < 2:
            continue
        uniq = [e for e in r['pals']
                if not any(e['id'] in [x['id'] for x in r2['pals']] for r2 in rs if r2 is not r)]
        if uniq:
            continue
        cnt += 1
        desc = ' + '.join(f"{cn(e['id'])}×{e['num'][0]}~{e['num'][1]}" for e in r['pals'])
        print(f'   [{n[:32]:32s}] w={r["w"]:<6g} {desc}')
        # 该刷怪器共几行
        print(f'      该刷怪器共 {len(rs)} 行')
print(f'   合计 {cnt} 行')

# 3) 槽位1 是否总是"头领/代表" (1+n 行)
print('\n=== 各类行的槽位1 内容 ===')
stat = collections.Counter()
for n, rn, r in multi_raw:
    ss = slots(r)
    ones = [p for i, p, a, b in ss if a == 1 and b == 1]
    first = ss[0][1]
    if len(ones) == 1:
        stat['1+n: 槽位1=头领' if first == ones[0] else '1+n: 槽位1≠头领'] += 1
    elif len(ones) >= 2:
        stat['全固定1: 槽位1 是其中一只'] += 1
    else:
        stat['无固定1'] += 1
for k, v in stat.most_common():
    print(f'   {k:28s} {v}')

# 4) 1+1 行的两只关系
print('\n=== 全固定1 的行: 两只是否同族变体 ===')
def family(pid):
    base = pid[5:] if pid[:5].lower() == 'boss_' else pid
    return base.split('_')[0]
for n, rn, r in multi_raw:
    ss = slots(r)
    if len(ss) < 2 or not all(a == 1 and b == 1 for _, _, a, b in ss):
        continue
    fams = [family(p) for _, p, _, _ in ss]
    same = len(set(fams)) == 1
    desc = ' + '.join(f'{cn(p)}({p})' for _, p, _, _ in ss)
    print(f'   [{"同族" if same else "异族"}] [{n[:26]:26s}] {desc}')
