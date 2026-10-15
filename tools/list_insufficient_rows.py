# -*- coding: utf-8 -*-
"""按"抽签行"口径复核: 哪些刷怪器的点位数 < 抽签行数。
R      = 该刷怪器的抽签行数 (构建数据 rows)
R_day  = 其中非"仅夜间"行数
N      = 该刷怪器名下的点位数
"""
import json, re, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PTS, ROWS, MAPS = d['points'], d['rows'], d['maps']

# 点位按 (类型, 是否洞窟内部) 分类
def cat(p):
    if p['t'] == 'C':
        return '普通点(地上)' if not p['u'] else '普通点(洞窟内部)'
    return {'DG': '地下城', 'F': '野外Boss', 'I': '监禁Boss', 'NB': '人类通缉犯'}.get(p['t'], p['t'])

info = {}
for p in PTS:
    if p['t'] in ('FC', 'FR', 'NB', 'ND'):
        continue
    e = info.setdefault(p['n'], {'n': 0, 'cat': set(), 'pts': [], 'r': p['r'], 'm': p['m']})
    e['n'] += 1
    e['cat'].add(cat(p))
    e['pts'].append(p)

bad = []
for n, e in info.items():
    rs = ROWS.get(n)
    if not rs:
        continue
    R = len(rs)
    Rday = sum(1 for r in rs if r.get('time') != 'Night')
    if R > e['n']:
        bad.append((R - e['n'], R, Rday, e['n'], n, e))

print(f'点位 < 抽签行 的刷怪器: {len(bad)} 个\n')
print(f'{"刷怪器":40s} {"点":>4} {"行":>4} {"白天行":>6} {"缺":>4} {"剔除夜间后":>10}  类别')
print('-' * 96)
for miss, R, Rday, N, n, e in sorted(bad, reverse=True):
    v = '✓ 够' if Rday <= N else f'✗ 仍缺 {Rday-N}'
    print(f'{n[:40]:40s} {N:4d} {R:4d} {Rday:6d} {miss:4d} {v:>10}  {"/".join(sorted(e["cat"]))}')

pts_affected = sum(e['n'] for _, _, _, _, _, e in bad)
all_pts = sum(e['n'] for e in info.values())
print(f'\n涉及点位 {pts_affected} / {all_pts} ({100*pts_affected/all_pts:.2f}%)')
rem = [x for x in bad if x[2] > x[3]]
print(f'剔除仅夜间行后仍不足: {len(rem)} 个')
for miss, R, Rday, N, n, e in sorted(rem, reverse=True):
    ps = e['pts']
    xs = [p['x'] for p in ps]; ys = [p['y'] for p in ps]
    print(f'   {n:38s} 点 {N:3d} / 白天行 {Rday:3d} (缺 {Rday-N})  '
          f'X[{min(xs):.0f},{max(xs):.0f}] Y[{min(ys):.0f},{max(ys):.0f}] 区域 {e["r"]}')

# 各类型的不足情况
print('\n=== 按类别汇总 ===')
agg = collections.defaultdict(lambda: [0, 0, 0])   # 类别 -> [不足刷怪器数, 点位, 总刷怪器数]
for _, _, _, _, n, e in bad:
    c = '/'.join(sorted(e['cat']))
    agg[c][0] += 1
    agg[c][1] += e['n']
tot = collections.defaultdict(int)
for n, e in info.items():
    tot['/'.join(sorted(e['cat']))] += 1
for c, (nb, pts, _) in agg.items():
    print(f'   {c:18s} 不足 {nb} / {tot[c]} 个刷怪器, 涉及 {pts} 个点位')

# ---- 输出 Markdown 报告 ----
md = ['# 点位不足清单（以“抽签行”为口径）', '',
      '判据：**该刷怪器的抽签行数 R > 它名下的点位数 N**。一行 = 一次抽签的结果'
      '（抽中后整行内容一起出现），因此每个不同的行都需要一个位置才画得出来。', '',
      f'数据来源：构建产物 `ROWS`（{len(ROWS)} 个刷怪器 / {sum(len(v) for v in ROWS.values())} 行），'
      f'点位 {all_pts} 个。共 **{len(bad)} 个**刷怪器不足，涉及 {pts_affected} 个点位 '
      f'（{100*pts_affected/all_pts:.2f}%）。', '',
      '| 刷怪器 | 点位 | 行数 | 含夜间行? | 剔除仅夜间行后 | 类别 |', '|---|---|---|---|---|---|']
for miss, R, Rday, N, n, e in sorted(bad, reverse=True):
    night = R - Rday
    v = '仍不足 %d' % (Rday - N) if Rday > N else '够'
    md.append(f'| `{n}` | {N} | {R} | {"是(%d)" % night if night else "无"} | {v} | {"/".join(sorted(e["cat"]))} |')
md += ['', '## 逐条明细（仅真正影响图标分配的：普通点(地上)）', '']
for miss, R, Rday, N, n, e in sorted(bad, reverse=True):
    if '普通点(地上)' not in e['cat']:
        continue
    ps = sorted(e['pts'], key=lambda p: -p['x'])
    xs = [p['x'] for p in ps]; ys = [p['y'] for p in ps]
    md += [f'### {n}', '',
           f'- 底图 {MAPS[e["m"]]["label"]} · 区域 `{e["r"]}`',
           f'- **{N} 个点位 vs {R} 行**（其中仅夜间 {R-Rday} 行）；剔除仅夜间行后剩 {Rday} 行'
           + ('（仍缺 %d）' % (Rday - N) if Rday > N else '（够）'),
           f'- 坐标 X[{min(xs):.0f},{max(xs):.0f}] Y[{min(ys):.0f},{max(ys):.0f}]',
           '- 点位：' + '；'.join(f'({p["x"]:.0f},{p["y"]:.0f},{p["z"]:.1f}m)' for p in ps[:8]) + (' …' if N > 8 else ''),
           '', '| 权重 | 行内容 | 条件 |', '|---|---|---|']
    for r in sorted(ROWS[n], key=lambda r: -r['w']):
        content = ' + '.join(f"{x.get('b') or x['id']}×{x['num'][0]}~{x['num'][1]}" for x in r['pals'])
        md.append(f"| {r['w']:g} | {content} | {r.get('time') or '-'} |")
    md.append('')

md += ['', '## 处理规则与效果（点位不足时）', '',
       '按以下顺序腾位置，只影响**图标点位分配**，详情面板仍完整列出所有行：', '',
       '1. **先移除"旺财"(MimicDog) 行**——它只见于 112/420 个刷怪器、共 121 行，'
       '**全部是单只行**（不与其它帕鲁同行），权重中位仅 2，点位紧张时没必要占位；',
       '2. 仍不足 → **移除仅夜间行**；',
       '3. 仍不足 → 按权重从低到高丢弃（目前仅 `worldtree_9_55_WorldTreeAura`，已决定整片不画头像）。', '',
       '| 刷怪器 | 点位 | 行数 | 去旺财后 | 去夜间后 | 结果 |', '|---|---|---|---|---|---|']


def _mimic(e):
    return (e.get('b') or e['id']) == 'MimicDog'


for miss, R, Rday, N, n, e in sorted(bad, reverse=True):
    if '普通点(地上)' not in e['cat']:
        continue
    rs = ROWS[n]
    rs1 = [r for r in rs if not all(_mimic(x) for x in r['pals'])]
    R1 = len(rs1)
    # 第 2 步必须在"去掉旺财之后"的列表上做
    R2 = len([r for r in rs1 if r.get('time') != 'Night']) if R1 > N else R1
    md.append(f'| `{n}` | {N} | {R} | {R1} | {R2} | {"够" if R2 <= N else "仍缺 %d" % (R2 - N)} |')
md += ['', '洞窟相关的 9 个（洞窟Boss 4 个 + 洞窟内部点 5 个）点位也少于行数，但它们共用洞口坐标、'
       '走"按位置合并的洞窟面板"，池子以列表呈现、不做逐点分配，因此不受影响。', '']

out = os.path.join(ROOT, 'docs', '点位不足清单.md')
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'w', encoding='utf-8').write('\n'.join(md))
print(f'\n已写入 {out}')
