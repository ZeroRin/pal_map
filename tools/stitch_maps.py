# -*- coding: utf-8 -*-
"""拼接底图瓦片 -> maps/ 下的整图, 并统计刷怪点在各底图间的归属。
用法: python tools/stitch_maps.py             (拼接两张图并写 maps_config.json)
      python tools/stitch_maps.py --config-only  (只重写配置, 不拼接)
瓦片来源: tools/fetch_tiles.mjs 从 cdn.paldb.cc 下载到 src/tiles/"""
import os, re, json
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TILES = os.path.join(ROOT, 'src', 'tiles')
MAPS_DIR = os.path.join(ROOT, 'maps')

MAPS = {
    'palpagos': {                       # 帕洛斯群岛 (paldb image/map8)
        'dir': os.path.join(TILES, 'map8'),
        'bounds': (-1099400.0, 349400.0, -724400.0, 724400.0),
        'out': os.path.join(MAPS_DIR, 'map_palpagos_8192.webp'),
        'out4k': os.path.join(MAPS_DIR, 'map_palpagos_4096.webp'),
    },
    'worldtree': {                      # 世界树 (paldb image/treemap8)
        'dir': os.path.join(TILES, 'treemap8'),
        'bounds': (347351.5, 689148.5, -818197.0, -476400.0),
        'out': os.path.join(MAPS_DIR, 'map_worldtree_8192.webp'),
        'out4k': os.path.join(MAPS_DIR, 'map_worldtree_4096.webp'),
    },
}
ZOOM, N, TILE = 4, 16, 512
SIZE = N * TILE


def stitch(d, size, out, quality=88):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    step = size // N
    miss = 0
    for x in range(N):
        for y in range(N):
            p = os.path.join(d, f'z{ZOOM}x{x}y{y}.webp')
            if not os.path.exists(p):
                miss += 1; continue
            t = Image.open(p).convert('RGBA')
            if t.size != (step, step):        # 目标格边长 (step) 而非瓦片原始尺寸
                t = t.resize((step, step), Image.LANCZOS)
            img.paste(t, (x * step, y * step))
    img.convert('RGB').save(out, 'WEBP', quality=quality, method=6)
    print(f'  {os.path.basename(out)}: {size}x{size} (每格 {step}px), '
          f'{os.path.getsize(out)/1e6:.2f} MB' + (f', 缺 {miss} 块' if miss else ''))


for key, m in MAPS.items():
    if '--config-only' in os.sys.argv:
        break
    if os.path.isdir(m['dir']):
        print(f'拼接 {key}...')
        stitch(m['dir'], SIZE, m['out'])
        stitch(m['dir'], 4096, m['out4k'], quality=85)
    else:
        print(f'跳过 {key}: 未找到瓦片目录 {m["dir"]} (可用 tools/fetch_tiles.mjs 下载)')

# 输出地图配置 (供 build_spawner_map.py 使用)
cfg = {
    'maps': [
        {'key': k, 'label': ('帕洛斯群岛' if k == 'palpagos' else '世界树'),
         'bounds': {'minX': v['bounds'][0], 'maxX': v['bounds'][1],
                    'minY': v['bounds'][2], 'maxY': v['bounds'][3]},
         'img8k': os.path.basename(v['out']), 'img4k': os.path.basename(v['out4k'])}
        for k, v in MAPS.items()
    ]
}
cfg_path = os.path.join(ROOT, 'tools', 'maps_config.json')
json.dump(cfg, open(cfg_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n已写入 {cfg_path}')

# 统计点位归属
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
data = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))


def inside(b, x, y):
    minx, maxx, miny, maxy = b
    return minx <= x <= maxx and miny <= y <= maxy


print('\n点位归属:')
for key in ('palpagos', 'worldtree'):
    b = MAPS[key]['bounds']
    ins = [p for p in data['points'] if inside(b, p['x'], p['y'])]
    print(f'  {key:10s} 世界范围 X[{b[0]:.0f},{b[1]:.0f}] Y[{b[2]:.0f},{b[3]:.0f}] -> {len(ins)} 点')
    reg = {}
    for p in ins:
        reg[p['r']] = reg.get(p['r'], 0) + 1
    for r, n in sorted(reg.items(), key=lambda kv: -kv[1])[:6]:
        print(f'      {r[:44]:44s} {n}')

# 两张图都覆盖不到的 (若有)
b1, b2 = MAPS['palpagos']['bounds'], MAPS['worldtree']['bounds']
out = [p for p in data['points'] if not inside(b1, p['x'], p['y']) and not inside(b2, p['x'], p['y'])]
print(f'\n两张图都覆盖不到的点: {len(out)}')
for p in out[:8]:
    print(f"   {p['n'][:34]:34s} X={p['x']:.0f} Y={p['y']:.0f} region={p['r'][:28]}")
