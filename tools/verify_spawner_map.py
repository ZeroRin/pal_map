# -*- coding: utf-8 -*-
"""校验生成的 HTML: 提取 <script> 做语法检查(node --check), 并抽查帕鲁表数据。"""
import json, re, os, subprocess, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()

# 1) 语法检查
m = re.search(r'<script>(.*?)</script>', html, re.S)
js = m.group(1)
tmp = os.path.join(tempfile.gettempdir(), 'spawner_map_check.js')
open(tmp, 'w', encoding='utf-8').write(js)
r = subprocess.run(['node', '--check', tmp], capture_output=True, text=True)
print(f'node --check: {"PASS" if r.returncode == 0 else "FAIL"}')
if r.returncode:
    print(r.stderr[:2000])

# 2) 数据抽查
data = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
print(f'\nDATA 结构: {list(data.keys())}')
print(f'pals={len(data["pals"])} tables={len(data["tables"])} points={len(data["points"])}')

# 找一个有代表性的刷怪器表
sample = 'skyisland_8_07_G_mountain'
tbl = data['tables'].get(sample) or list(data['tables'].values())[0]
name = sample if sample in data['tables'] else list(data['tables'])[0]
print(f'\n刷怪表 "{name}" 共 {len(tbl)} 条:')
for e in tbl[:10]:
    v = data['pals'].get(e['b']) if e.get('b') else None
    cn = v['n'] if v else '(无)'
    img = '有图标' if (v and v.get('i')) else '无图标'
    cond = '/'.join(x for x in (e.get('time'), '光环' if e.get('aura') else None) if x) or '-'
    print(f"   #{str(e.get('z',0)):>3} {cn:8s} {e['id']:32s} {e.get('bg','') or '-':6s} "
          f"lv{e['lv'][0]}-{e['lv'][1]} x{e['num'][0]}-{e['num'][1]} w={e['w']}({e.get('pct')}%) {cond} [{img}]")

# 3) 覆盖率: 有多少条目能取到中文名
tot = miss = ic = 0
for lst in data['tables'].values():
    for e in lst:
        tot += 1
        v = data['pals'].get(e['b']) if e.get('b') else None
        if not v:
            miss += 1
        elif v.get('i'):
            ic += 1
print(f'\n全部刷怪条目 {tot}: 有中文名 {tot-miss} ({100*(tot-miss)/tot:.1f}%), 有图标 {ic} ({100*ic/tot:.1f}%)')
if miss:
    print('   无中文名的条目示例:')
    seen = set()
    for lst in data['tables'].values():
        for e in lst:
            if not (data['pals'].get(e['b']) if e.get('b') else None) and e['id'] not in seen:
                seen.add(e['id'])
    print('  ', list(seen)[:10])
