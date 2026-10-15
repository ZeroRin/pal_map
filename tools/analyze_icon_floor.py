# -*- coding: utf-8 -*-
"""补充分析: 保底规则的可行性, 以及条目数 > 点位数 的极端刷怪器。"""
import json, re, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PTS, TABLES, PALS = d['points'], d['tables'], d['pals']
N = collections.Counter(p['n'] for p in PTS if p['t'] == 'C' and not p['u'])


def nm(b):
    return (PALS.get(b) or {}).get('n') or b


# 1) 结构性不足的刷怪器, 影响多少点位
bad = [(N[s], len(TABLES[s]), s) for s in N if TABLES.get(s) and len(TABLES[s]) > N[s]]
pts_affected = sum(n for n, k, s in bad)
print(f'条目数 > 点位数 的刷怪器: {len(bad)} 个, 涉及点位 {pts_affected} / {sum(N.values())} 个 '
      f'({100*pts_affected/sum(N.values()):.2f}%)')
print('   即使"每条目保底 1 个点"也无法满足的部分:')
for n, k, s in sorted(bad, reverse=True)[:6]:
    print(f'     {s[:36]:36s} 点 {n:3d} < 条目 {k:3d}  -> 最多画 {n} 种, 得舍弃 {k-n} 种')

# 2) worldtree_9_55_WorldTreeAura 的条目结构
s0 = 'worldtree_9_55_WorldTreeAura'
ents = TABLES.get(s0) or []
print(f'\n=== {s0}: {N.get(s0,0)} 点 / {len(ents)} 条目 ===')
ws = [e['w'] for e in ents]
print(f'   权重范围 {min(ws)}~{max(ws)}, 不同权重值 {len(set(ws))} 种')
for e in ents[:6]:
    print(f'     w={e["w"]:<8} {nm(e.get("b") or e["id"]):12s} {e.get("bg","")}')
tot = sum(ws)
print(f'   最大份额 {max(ws)/tot*100:.2f}% -> 21 点下期望点数 {21*max(ws)/tot:.2f}')

# 3) 模拟"保底 1 + 剩余按权重"规则 (夜间 ×1/5)
def floor_alloc(n, entries, night_div=5):
    ws = [(e['w'] / (night_div if e.get('time') == 'Night' else 1)) for e in entries]
    k = len(entries)
    if n >= k:
        base = [1] * k
        rest = n - k
        tot = sum(ws)
        add = [rest * w / tot for w in ws] if tot > 0 else [0] * k
        # 最大余数法补足
        cnt = [b + int(a) for b, a in zip(base, add)]
        left = n - sum(cnt)
        order = sorted(range(k), key=lambda i: -(add[i] - int(add[i])))
        for i in order[:left]:
            cnt[i] += 1
        return cnt, 0
    # 点不够: 按权重取前 n 个条目各 1 点
    order = sorted(range(k), key=lambda i: -ws[i])
    cnt = [0] * k
    for i in order[:n]:
        cnt[i] = 1
    return cnt, k - n

tot_entries = shown = dropped = 0
for s, ents in TABLES.items():
    n = N.get(s)
    if not n or not ents:
        continue
    cnt, drop = floor_alloc(n, ents)
    tot_entries += len(ents)
    shown += sum(1 for c in cnt if c > 0)
    dropped += drop
print(f'\n=== 规则: 保底 1 个点 + 剩余按权重 (夜间×1/5) ===')
print(f'   条目 {tot_entries}: 能画上 {shown} ({100*shown/tot_entries:.1f}%), 舍弃 {dropped} ({100*dropped/tot_entries:.1f}%)')
print(f'   舍弃全部集中在 {len(bad)} 个"点位不足"的刷怪器上 ({pts_affected} 个点位)')

# 4) 夜间条目在该规则下的点数占比
night_pts = tot_pts = 0
night_entries = 0
for s, ents in TABLES.items():
    n = N.get(s)
    if not n or not ents:
        continue
    cnt, _ = floor_alloc(n, ents)
    for e, c in zip(ents, cnt):
        tot_pts += c
        if e.get('time') == 'Night':
            night_pts += c
            night_entries += 1
print(f'\n=== 夜间条目占用点数 ===')
print(f'   夜间条目 {night_entries} 个, 分到 {night_pts} 个点位, 占全部 {tot_pts} 个的 '
      f'{100*night_pts/tot_pts:.1f}%')
