# -*- coding: utf-8 -*-
"""1) 打通 鱼影ID -> 帕鲁 的映射; 2) 把 paldb 钓点画到地图上验证 (钓点应落在水面)。"""
import json, os, re
from PIL import Image, ImageDraw

ROOT = r'D:\Workspace\Palworld\Decompile'
FISH = os.path.join(ROOT, 'exports', 'Pal', 'Content', 'Pal', 'DataTable', 'Fishing')


def rows(fn):
    return json.load(open(os.path.join(FISH, fn), encoding='utf-8'))[0]['Rows']


shadow_raw = open(os.path.join(FISH, 'DT_PalFishShadowDataTable.json'), encoding='utf-8').read()
i = shadow_raw.find('FishShadow_TentacleTurtle_Common')
print('=== DT_PalFishShadowDataTable 中该字符串的上下文 ===')
print(shadow_raw[max(0, i - 400): i + 400])

shadow = rows('DT_PalFishShadowDataTable.json')
print(f'\n鱼影表 {len(shadow)} 行, 行名样例: {list(shadow)[:6]}')
# 检查是否存在以 FishShadow_ 开头的键 或 字段
ks = [k for k in shadow if k.startswith('FishShadow_')]
print(f'以 FishShadow_ 开头的行: {len(ks)} -> {ks[:5]}')
for k in list(shadow)[:3]:
    v = shadow[k]
    print(f'   {k}: keys={list(v)}')

# ---- 2) 落水面校验 ----
spots = json.load(open(os.path.join(ROOT, 'downloads', 'paldb_fishing_spots.json'), encoding='utf-8'))
cfg = json.load(open(os.path.join(ROOT, 'pal_spawner_map', 'tools', 'maps_config.json'), encoding='utf-8'))['maps']
pa = [m for m in cfg if m['key'] == 'palpagos'][0]
b = pa['bounds']
img = Image.open(os.path.join(ROOT, 'pal_spawner_map', 'maps', pa['img4k'])).convert('RGB')
W, H = img.size
px = img.load()


def is_water(r, g, b_):
    return b_ > g >= r or (r + g + b_) < 240


water = land = outside = 0
for s in spots:
    x, y = s['pos']['X'], s['pos']['Y']
    ix = (y - b['minY']) / (b['maxY'] - b['minY']) * W
    iy = (b['maxX'] - x) / (b['maxX'] - b['minX']) * H
    if not (0 <= ix < W and 0 <= iy < H):
        outside += 1; continue
    r, g, bb = px[int(ix), int(iy)]
    if is_water(r, g, bb):
        water += 1
    else:
        land += 1
tot = water + land
print(f'\n=== 钓点落点校验 (帕洛斯底图) ===')
print(f'在水面: {water} ({water/tot*100:.1f}%)   在陆地: {land} ({land/tot*100:.1f}%)   超出底图: {outside}')

# 画出来看看
prev = img.resize((2048, 2048), Image.LANCZOS)
d = ImageDraw.Draw(prev)
for s in spots:
    x, y = s['pos']['X'], s['pos']['Y']
    ix = (y - b['minY']) / (b['maxY'] - b['minY']) * 2048
    iy = (b['maxX'] - x) / (b['maxX'] - b['minX']) * 2048
    if not (0 <= ix < 2048 and 0 <= iy < 2048):
        continue
    rare = 'Rare' in s['href']
    r = 4
    d.ellipse((ix - r, iy - r, ix + r, iy + r), fill=(255, 80, 80) if rare else (255, 220, 60), outline=(0, 0, 0))
prev.save(os.path.join(ROOT, 'downloads', 'fishing_spots_check.png'))
print('saved downloads/fishing_spots_check.png (黄=普通钓点, 红=稀有钓点)')
