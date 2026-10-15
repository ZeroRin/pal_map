# -*- coding: utf-8 -*-
"""从 pal_spawner_map.html 提取内嵌数据, 渲染静态预览图 (逐张底图, 含钓点)。

产出:
  preview_<map>.png        每张底图的全图预览
  preview_<map>_zoom.png   中心区域局部放大 (验证相邻刷怪器不同色 / 钓点分布)
"""
import json, re, os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
data = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PTS = data['points']
maps = data['maps']


def hex2rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


PAL = [hex2rgb(h) for h in data['palette']]
COL = {'F': (248, 81, 73), 'D': (188, 140, 255), 'I': (210, 153, 34),
       'FC': (34, 211, 238), 'FR': (244, 114, 182)}
# 底图文件名在 tools/maps_config.json (DATA 里只存了 bounds 与内嵌图)
cfg = {m['key']: m for m in json.load(
    open(os.path.join(ROOT, 'tools', 'maps_config.json'), encoding='utf-8'))['maps']}


def map_file(key):
    return os.path.join(ROOT, 'maps', cfg[key]['img4k'])


for mi, m in enumerate(maps):
    b = m['bounds']
    out_size = 1600
    s = out_size / (b['maxY'] - b['minY'])
    img = Image.open(map_file(m['key'])).convert('RGB').resize(
        (out_size, out_size), Image.LANCZOS)
    d = ImageDraw.Draw(img)

    def w2p(x, y):
        return ((y - b['minY']) * s, out_size - (x - b['minX']) * s)

    sub = [p for p in PTS if p['m'] == mi]
    for p in sub:
        x, y = w2p(p['x'], p['y'])
        if not (0 <= x < out_size and 0 <= y < out_size):
            continue
        if p['t'] == 'C':
            c = p.get('c', -1)
            d.point((x, y), fill=PAL[c] if c >= 0 else (139, 148, 158))
        else:
            r = 2
            d.ellipse((x - r, y - r, x + r, y + r), outline=COL.get(p['t'], (200, 200, 200)))
    img.save(os.path.join(ROOT, f'preview_{m["key"]}.png'))
    print(f'saved preview_{m["key"]}.png  ({len(sub)} 点位)')

    # 中心区域放大
    cx = (b['minX'] + b['maxX']) / 2; cy = (b['minY'] + b['maxY']) / 2
    half = (b['maxX'] - b['minX']) * 0.06
    size = 1200
    ss = size / (2 * half)
    im2 = Image.open(map_file(m['key'])).convert('RGB')
    px_per_unit = im2.width / (b['maxY'] - b['minY'])
    box = (int((cy - half - b['minY']) * px_per_unit), int((b['maxX'] - (cx + half)) * px_per_unit),
           int((cy + half - b['minY']) * px_per_unit), int((b['maxX'] - (cx - half)) * px_per_unit))
    crop = im2.crop(box).resize((size, size), Image.LANCZOS)
    dd = ImageDraw.Draw(crop)

    def w2c(x, y):
        return ((y - (cy - half)) * ss, size - ((x - (cx - half)) * ss))

    n = 0
    for p in PTS:
        if p['m'] != mi:
            continue
        if not (cx - half <= p['x'] <= cx + half and cy - half <= p['y'] <= cy + half):
            continue
        x, y = w2c(p['x'], p['y'])
        n += 1
        if p['t'] == 'C':
            c = p.get('c', -1)
            r = 2
            dd.ellipse((x - r, y - r, x + r, y + r), fill=PAL[c] if c >= 0 else (139, 148, 158))
        else:
            r = 4
            dd.ellipse((x - r, y - r, x + r, y + r), fill=COL.get(p['t'], (200, 200, 200)), outline=(0, 0, 0))
    crop.save(os.path.join(ROOT, f'preview_{m["key"]}_zoom.png'))
    print(f'saved preview_{m["key"]}_zoom.png  ({n} 点位)')
