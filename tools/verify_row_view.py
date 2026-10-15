# -*- coding: utf-8 -*-
"""校验"以抽签行为基本单位"的展示: 数据侧统计 + 成品代码检查。"""
import json, re, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PTS, ROWS = d['points'], d['rows']

print('=== 成品代码检查 ===')
for key, desc in (('function rowTable(', '公共抽签行渲染函数'),
                  ('抽签行 (整组出现)', '行表表头'),
                  ('const rows=ROWS[p.n]||EMPTY;', '普通点面板以行为主视图'),
                  ('rowTable([p.n], 200)', '普通点调用'),
                  ('rowTable(s.list, 80)', '洞窟 Boss 池调用')):
    print(f'   {"✓" if key in html else "✗"}  {desc}: {key}')
print(f'   {"✓" if "comboTable" not in html else "✗"}  旧的 comboTable 已移除')
print(f'   {"✓" if "◆ 成组出现的行" not in html else "✗"}  旧的独立组合分区已移除')

# 分类统计: 行数 / 多只行数 / 点位
def cat(p):
    if p['t'] == 'C':
        return '普通点(地上)' if not p['u'] else '普通点(洞窟内部)'
    return {'DG': '地下城', 'F': '野外Boss', 'I': '监禁Boss', 'NB': '人类通缉犯'}.get(p['t'], p['t'])


agg = collections.defaultdict(lambda: {'sp': set(), 'pts': 0, 'rows': 0, 'multi': 0})
for p in PTS:
    rs = ROWS.get(p['n'])
    if not rs:
        continue
    c = cat(p)
    a = agg[c]
    if p['n'] not in a['sp']:
        a['sp'].add(p['n'])
        a['rows'] += len(rs)
        a['multi'] += sum(1 for r in rs if len(r['pals']) > 1)
    a['pts'] += 1

print('\n=== 各类型点位的行数据 ===')
print(f'{"类别":18s} {"刷怪器":>6} {"抽签行":>7} {"多只行":>6} {"点位":>6}')
for c, a in sorted(agg.items(), key=lambda kv: -kv[1]['pts']):
    print(f'{c:18s} {len(a["sp"]):6d} {a["rows"]:7d} {a["multi"]:6d} {a["pts"]:6d}')

total_rows = sum(len(v) for v in ROWS.values())
total_multi = sum(1 for v in ROWS.values() for r in v if len(r['pals']) > 1)
print(f'\n全表: {len(ROWS)} 个刷怪器 / {total_rows} 行 / 其中多只行 {total_multi}')

# 抽查: 普通点的行视图内容
for s in ('blue_B', 'yellow_D'):
    print(f'\n=== {s} 的抽签行 (前 5) ===')
    for r in (ROWS.get(s) or [])[:5]:
        pals = ' + '.join(f"{e.get('b') or e['id']}{'·'+e['bg'] if e.get('bg') else ''}"
                          f"×{e['num'][0]}{'~'+str(e['num'][1]) if e['num'][0]!=e['num'][1] else ''}"
                          f"(Lv{e['lv'][0]}{'~'+str(e['lv'][1]) if e['lv'][0]!=e['lv'][1] else ''})"
                          for e in r['pals'])
        cond = r.get('time') or '-'
        print(f'   w={r["w"]:<6} ({r["pct"]:5}%) {cond:9s} {pals}')
