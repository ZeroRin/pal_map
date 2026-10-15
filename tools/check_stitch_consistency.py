# -*- coding: utf-8 -*-
"""校验 4096 拼图与 8192 缩图一致 (修复前二者会完全错位)。"""
import os
from PIL import Image, ImageChops

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for name in ('palpagos', 'worldtree'):
    big = Image.open(os.path.join(ROOT, 'maps', f'map_{name}_8192.webp')).convert('RGB')
    small = Image.open(os.path.join(ROOT, 'maps', f'map_{name}_4096.webp')).convert('RGB')
    ref = big.resize((4096, 4096), Image.LANCZOS)
    diff = ImageChops.difference(ref, small)
    stat = diff.convert('L')
    hist = stat.histogram()
    total = sum(hist)
    mean = sum(i * h for i, h in enumerate(hist)) / total
    over16 = sum(h for i, h in enumerate(hist) if i > 16) / total * 100
    print(f'{name:10s} 4096 vs 8192缩图: 平均差 {mean:5.2f}/255, 差值>16 的像素占比 {over16:5.2f}%'
          f'  {"一致 ✓" if mean < 6 else "不一致 ✗"}')
