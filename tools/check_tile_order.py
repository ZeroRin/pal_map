# -*- coding: utf-8 -*-
"""判断瓦片排列方式: 对比相邻瓦片接缝处的像素连续性, 差异越小说明排列越正确。
(不依赖 numpy, 用 PIL 的 getdata 做小样本抽样)"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N, TILE = 16, 512


def load(d):
    tiles = {}
    for x in range(N):
        for y in range(N):
            p = os.path.join(d, f'z4x{x}y{y}.webp')
            tiles[(x, y)] = Image.open(p).convert('RGB').load()
    return tiles


def col_diff(a, b, xs_a, xs_b):
    """两列/两行的平均绝对差, 抽样间隔 4 像素"""
    tot = 0.0; n = 0
    for i in range(0, TILE, 4):
        pa = a[xs_a, i]; pb = b[xs_b, i]
        tot += abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]) + abs(pa[2] - pb[2]); n += 1
    return tot / (n * 3)


def row_diff(a, b, ys_a, ys_b):
    tot = 0.0; n = 0
    for i in range(0, TILE, 4):
        pa = a[i, ys_a]; pb = b[i, ys_b]
        tot += abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]) + abs(pa[2] - pb[2]); n += 1
    return tot / (n * 3)


def seam_score(tiles, swap):
    vd, hd = [], []
    for x in range(N - 1):
        for y in range(N):
            a = tiles[(x, y)] if not swap else tiles[(y, x)]
            b = tiles[(x + 1, y)] if not swap else tiles[(y, x + 1)]
            vd.append(col_diff(a, b, TILE - 1, 0))
    for x in range(N):
        for y in range(N - 1):
            a = tiles[(x, y)] if not swap else tiles[(y, x)]
            b = tiles[(x, y + 1)] if not swap else tiles[(y + 1, x)]
            hd.append(row_diff(a, b, TILE - 1, 0))
    return sum(vd) / len(vd), sum(hd) / len(hd)


for label, d in (('palpagos (map8)', os.path.join(ROOT, 'src', 'tiles', 'map8')),
                 ('worldtree (treemap8)', os.path.join(ROOT, 'src', 'tiles', 'treemap8'))):
    if not os.path.isdir(d):
        continue
    tiles = load(d)
    nv, nh = seam_score(tiles, False)
    tv, th = seam_score(tiles, True)
    print(f'{label}:')
    print(f'   正常 (x右/y下): 纵缝 {nv:6.2f}  横缝 {nh:6.2f}  合计 {nv+nh:6.2f}')
    print(f'   对调 (y右/x下): 纵缝 {tv:6.2f}  横缝 {th:6.2f}  合计 {tv+th:6.2f}')
    print(f'   => 更可能是: {"正常" if nv + nh <= tv + th else "对调"}')

d = os.path.join(ROOT, 'src', 'tiles', 'treemap8')
sizes = sorted(os.path.getsize(os.path.join(d, f)) for f in os.listdir(d))
print(f'\ntreemap8 文件大小: 最小 {sizes[0]}B  中位 {sizes[len(sizes)//2]}B  最大 {sizes[-1]}B')
print(f'疑似空白瓦片 (<2KB): {sum(1 for s in sizes if s < 2000)} 个')
