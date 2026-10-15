# -*- coding: utf-8 -*-
"""世界树底图 + 其刷怪点的贴图校验 (与 HTML 使用同一套变换)。"""
import os, re, json
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = json.load(open(os.path.join(ROOT, 'tools', 'maps_config.json'), encoding='utf-8'))['maps']
tree = [m for m in cfg if m['key'] == 'worldtree'][0]
b = tree['bounds']
img = Image.open(os.path.join(ROOT, 'maps', tree['img4k'])).convert('RGB')
W, H = img.size

html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
data = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
maps = data['maps']
ti = [i for i, m in enumerate(maps) if m['key'] == 'worldtree'][0]
pts = [p for p in data['points'] if p['m'] == ti]
print(f'世界树底图 {W}x{H}, 归属该图的点 {len(pts)}')

d = ImageDraw.Draw(img)
inside = 0
for p in pts:
    px = (p['y'] - b['minY']) / (b['maxY'] - b['minY']) * W
    py = (b['maxX'] - p['x']) / (b['maxX'] - b['minX']) * H
    if 0 <= px < W and 0 <= py < H:
        inside += 1
    col = {'C': (0, 255, 90), 'F': (255, 40, 40), 'D': (190, 140, 255), 'I': (255, 210, 40)}[p['t']]
    r = 3 if p['t'] == 'C' else 5
    d.ellipse((px - r, py - r, px + r, py + r), fill=col, outline=(0, 0, 0))
print(f'落在底图范围内: {inside} / {len(pts)}')
img.resize((1200, 1200), Image.LANCZOS).save(os.path.join(ROOT, 'map_check_worldtree.png'))
print('saved map_check_worldtree.png')
