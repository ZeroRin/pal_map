# -*- coding: utf-8 -*-
"""离屏模拟网页的 Boss 头像渲染 (含 100m 分段缩放), 用两个缩放档位验证效果。

产出 preview_boss_wide.png (全图视野) 与 preview_boss_close.png (近景),
头像尺寸使用与网页相同的算法: raw = 100m * 缩放, 截断到 [16,96] 并按 8px 量化。
"""
import json, re, os, io, base64, collections
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
PTS, PALS, TABLES, BOUNTY, MAPS = d['points'], d['pals'], d['tables'], d['bounty'], d['maps']

ICON_M, ICON_MIN, ICON_MAX, ICON_STEP = 100, 16, 96, 8


def icon_px(scale):
    raw = ICON_M * 100 * scale            # 100m(厘米) -> 像素
    q = round(max(ICON_MIN, min(ICON_MAX, raw)) / ICON_STEP) * ICON_STEP
    return int(max(ICON_MIN, q))


def boss_icon(p):
    if p['t'] == 'NB':
        return (BOUNTY.get(p.get('nb') or '') or {}).get('icon')
    if p['t'] in ('F', 'I'):
        lst = TABLES.get(p['n']) or []
        e = next((x for x in lst if x.get('bg')), None) or (lst[0] if lst else None)
        return (PALS.get((e or {}).get('b') or '') or {}).get('i')
    return None


bosses = [p for p in PTS if p['t'] in ('F', 'I', 'NB') and p['m'] == 0]
CELL = 200000.0
bucket = collections.Counter((int(p['x'] // CELL), int(p['y'] // CELL)) for p in bosses)
(gx, gy), n = bucket.most_common(1)[0]
cx, cy = (gx + 0.5) * CELL, (gy + 0.5) * CELL

b = MAPS[0]['bounds']
img = Image.open(os.path.join(ROOT, 'maps', 'map_palpagos_8192.webp')).convert('RGB')
P = img.width / (b['maxY'] - b['minY'])
SIZE = 1200
_cache = {}


def load_icon(src):
    if src in _cache:
        return _cache[src]
    try:
        im = Image.open(io.BytesIO(base64.b64decode(src.split(',')[1]))).convert('RGBA')
    except Exception:
        im = None
    _cache[src] = im
    return im


def render(half_m, out):
    HALF = half_m * 100.0                 # 米 -> 厘米
    box = (int((cy - HALF - b['minY']) * P), int((b['maxX'] - (cx + HALF)) * P),
           int((cy + HALF - b['minY']) * P), int((b['maxX'] - (cx - HALF)) * P))
    crop = img.crop(box).resize((SIZE, SIZE), Image.LANCZOS)
    scale = SIZE / (2 * HALF)
    ipx = icon_px(scale)
    dr = ImageDraw.Draw(crop)
    drawn = 0
    for p in PTS:
        if p['m'] != 0 or p['t'] not in ('F', 'I', 'NB'):
            continue
        x = (p['y'] - (cy - HALF)) * scale
        y = SIZE - ((p['x'] - (cx - HALF)) * scale)
        if not (-ipx <= x <= SIZE + ipx and -ipx <= y <= SIZE + ipx):
            continue
        src = boss_icon(p)
        im = load_icon(src) if src else None
        r = ipx / 2
        if im:
            m = Image.new('L', (ipx, ipx), 0)
            ImageDraw.Draw(m).ellipse((0, 0, ipx - 1, ipx - 1), fill=255)
            dr.ellipse((x - r - 2, y - r - 2, x + r + 2, y + r + 2),
                       fill=(13, 17, 23), outline=(255, 255, 255))
            crop.paste(im.resize((ipx, ipx)), (int(x - r), int(y - r)), m)
        else:
            dr.ellipse((x - r, y - r, x + r, y + r), fill=(255, 159, 28))
        drawn += 1
    crop.save(os.path.join(ROOT, out))
    print(f'{out}: 视野 {half_m*2/1000:.1f}km, 头像 {ipx}px (≈{ipx/scale/100:.0f}m), 渲染 {drawn} 个')


render(6000, 'preview_boss_wide.png')     # 12km 视野 (接近全图)
render(600, 'preview_boss_close.png')     # 1.2km 近景
