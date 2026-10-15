# -*- coding: utf-8 -*-
"""验证辅助圆填充渲染: 在离屏画布上复现 HTML 的 "按颜色分组, 每组只 fill 一次" 语义。
PIL 无路径填充语义, 故每组先画一张二值掩膜 (重叠处仍为 255), 再用该掩膜以 50% alpha 合成,
等价于 canvas 里同一条路径一次 fill => 重叠区不会叠加变实。
"""
import json, re, os, collections
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
data = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
pts = data['points']
PAL = [tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) for h in data['palette']]
TCOL = {'F': (248, 81, 73), 'D': (188, 140, 255), 'I': (210, 153, 34)}

# 找最密的 400m x 400m 网格, 作为观察窗口
CELL = 40000.0
bucket = collections.Counter()
for p in pts:
    if p['t'] != 'C' or p['u']:
        continue
    bucket[(int(p['x'] // CELL), int(p['y'] // CELL))] += 1
(gx, gy), n = bucket.most_common(1)[0]
cx, cy = (gx + 0.5) * CELL, (gy + 0.5) * CELL
print(f'最密网格: 世界 X(北)={cx:.0f} Y(东)={cy:.0f}, 该格 {n} 个普通点')

W = H = 1200
HALF = 20000.0                      # 窗口半宽 (cm) => 400m 见方
scale = W / (2 * HALF)

def w2p(x, y):
    return ((y - (cy - HALF)) * scale, H - (x - (cx - HALF)) * scale)

sub = [p for p in pts if abs(p['x'] - cx) <= HALF and abs(p['y'] - cy) <= HALF]

RAD_M = 25
R = RAD_M * 100 * scale             # 半径像素

def render(rad_px, path):
    img = Image.new('RGB', (W, H), (13, 17, 23))
    # 按颜色分组: 每组画一张掩膜 -> 一次性 50% 合成
    groups = collections.defaultdict(list)
    for p in sub:
        if not p['t']:
            continue
        col = PAL[p['c']] if (p['t'] == 'C' and p.get('c', -1) >= 0) else (
            TCOL.get(p['t'], (139, 148, 158)) if p['t'] != 'C' else (139, 148, 158))
        groups[col].append(p)
    for col, ps in groups.items():
        mask = Image.new('L', (W, H), 0)
        md = ImageDraw.Draw(mask)
        for p in ps:
            x, y = w2p(p['x'], p['y'])
            md.ellipse((x - rad_px, y - rad_px, x + rad_px, y + rad_px), fill=255)
        img = Image.composite(Image.new('RGB', (W, H), col), img,
                              mask.point(lambda v: 128 if v else 0))
    d = ImageDraw.Draw(img)
    for p in sub:                    # 点画在最上层
        x, y = w2p(p['x'], p['y'])
        r = 2.5
        if p['t'] == 'C':
            c = PAL[p['c']] if p.get('c', -1) >= 0 else (139, 148, 158)
            d.ellipse((x - r, y - r, x + r, y + r), fill=c)
        else:
            d.ellipse((x - r - 1, y - r - 1, x + r + 1, y + r + 1), outline=TCOL[p['t']], width=2)
    img.save(os.path.join(ROOT, path))
    print(f'saved {path}  ({len(sub)} 点, 半径 {rad_px:.0f}px)')

render(R, 'spawner_preview_circle25.png')
render(R * 4, 'spawner_preview_circle100.png')
