# -*- coding: utf-8 -*-
"""16px = 25m 时, 两张底图的完整尺寸应为多少像素 (以及与现有 4096/8192 底图的对比)。

换算: 比例 = 16px / 25m; 底图像素 = 世界跨度 × 比例
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = json.load(open(os.path.join(ROOT, 'tools', 'maps_config.json'), encoding='utf-8'))['maps']

PX_PER_M = 16 / 25.0            # 16px 对应 25m
print(f'比例: 1m = {PX_PER_M:.4f}px  (1px = {1/PX_PER_M:.4f}m)\n')
print(f'{"底图":14s} {"世界跨度(km)":>14} {"完整尺寸(px)":>14} {"现有 8192 底图":>16} {"所需/现有":>10}')
rows = []
for m in cfg:
    b = m['bounds']
    sx = b['maxX'] - b['minX']          # 世界X跨度 (南北)
    sy = b['maxY'] - b['minY']          # 世界Y跨度 (东西)
    w = sy / 100.0 * PX_PER_M           # 像素宽 = 东西跨度
    h = sx / 100.0 * PX_PER_M           # 像素高 = 南北跨度
    need = max(w, h)
    rows.append((m['label'], sx / 100000, sy / 100000, w, h))
    print(f'{m["label"]:14s} {sx/100000:6.2f}×{sy/100000:<6.2f} {w:7.0f}×{h:<6.0f} '
          f'{8192:>16} {need/8192:9.2f}×')

print('\n=== 每张底图的"每个地图像素代表多少米" ===')
for m in cfg:
    b = m['bounds']
    sx = (b['maxX'] - b['minX']) / 100.0
    print(f'   {m["label"]:14s} 8192px: {sx/8192:.3f} m/px   '
          f'4096px: {sx/4096:.3f} m/px   '
          f'(16px=25m 时一个屏幕像素 = {1/PX_PER_M:.3f} m)')

print('\n=== 反推: 若底图正好按 16px=25m 的精度制作, 该用多大? ===')
print('   帕洛斯群岛 9272px -> 常用档位 10240 (1.10×所需) 或 16384 (1.77×)')
print('   世界树     2188px -> 常用档位 2048 已足够 (0.94×), 4096 有 1.87× 余量')

print('\n=== 其它基准下的需求 (供对照) ===')
for base_m, px in ((25, 16), (25, 24), (25, 48), (50, 16), (100, 16)):
    s = px / base_m
    print(f'   {px}px = {base_m}m (1m={s:.4f}px): ' +
          '  '.join(f'{m["label"]} {max((m["bounds"]["maxX"]-m["bounds"]["minX"]),(m["bounds"]["maxY"]-m["bounds"]["minY"]))/100*s:.0f}px'
                    for m in cfg))

# 现用底图尺寸
print('\n=== 本地底图文件 ===')
d = os.path.join(ROOT, 'maps')
for fn in sorted(os.listdir(d)):
    if fn.endswith('.webp'):
        print(f'   {fn}  {os.path.getsize(os.path.join(d, fn))/1e6:.2f} MB')
