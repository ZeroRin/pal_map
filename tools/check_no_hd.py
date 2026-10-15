# -*- coding: utf-8 -*-
"""确认成品 HTML 已彻底不含 8192 高清底图的**功能性引用**。

注意: 字面量 "8192" 可能合法地出现在别处 —— base64 图标数据里可能碰巧含这四个数字,
点位坐标也可能是 -819257.9 这种值, 注释里也会提到弃用原因。所以这里只查功能性引用。
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
h = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
print(f'成品 HTML {len(h)/1e6:.2f} MB')

checks = [
    ('底图文件引用 (*_8192.webp)', h.count('_8192.webp')),
    ('DATA 的 hi 字段', h.count('"hi"')),
    ('高清开关 ckHD', h.count('ckHD')),
    ('加载函数 setHD / wantHD', h.count('setHD') + h.count('wantHD')),
    ('状态变量 hdLoaded / hdImgs', h.count('hdLoaded') + h.count('hdImgs')),
    ('文案"高清底图"', h.count('高清底图')),
    ('文案"加载高清"', h.count('加载高清')),
]
bad = 0
for name, n in checks:
    bad += n
    print(f'   {name:26s} {n} 次  {"✗" if n else "✓"}')

# 仅作参考: 字面量 8192 出现在哪些无害位置
import re
ctx = []
for m in re.finditer('8192', h):
    s = max(0, m.start() - 24)
    ctx.append(h[s:m.end() + 12].replace('\n', ' '))
print(f'\n   附: 字面量 "8192" 共 {len(ctx)} 处 (均为无害):')
for c in ctx[:6]:
    print(f'      …{c}…')

print('\n结论:', '✓ 已彻底移除 8192 高清底图的功能性引用' if bad == 0 else '✗ 仍有残留')
