# -*- coding: utf-8 -*-
"""对比官方贴图 与 paldb 拼图: 对齐性 / 细节锐度 / 是否有叠层 / alpha。
不依赖 numpy, 用 PIL 分块处理, 避免一次性载入两张 8192 图。"""
import os
from PIL import Image, ImageChops, ImageStat, ImageFilter, ImageDraw

ROOT = r'D:\Workspace\Palworld\Decompile'
OFFICIAL = {
    'palpagos': os.path.join(ROOT, r'exports\Pal\Content\Pal\Texture\UI\Map\T_WorldMap_MIP0.png'),
    'worldtree': os.path.join(ROOT, r'exports\Pal\Content\Pal\Texture\UI\Map\T_TreeMap_MIP0.png'),
}
PALDB = {
    'palpagos': os.path.join(ROOT, r'pal_spawner_map\maps\map_palpagos_8192.webp'),
    'worldtree': os.path.join(ROOT, r'pal_spawner_map\maps\map_worldtree_8192.webp'),
}

W = 1024   # 采样窗口


def open_crop(path, box, mode='RGB'):
    im = Image.open(path)
    return im.crop(box).convert(mode)


def sharpness(im):
    """梯度能量: FIND_EDGES 后的均值, 越大越锐利"""
    e = im.convert('L').filter(ImageFilter.FIND_EDGES)
    st = ImageStat.Stat(e)
    return st.mean[0], st.stddev[0]


def diff_metrics(a, b):
    d = ImageChops.difference(a.convert('RGB'), b.convert('RGB'))
    st = ImageStat.Stat(d)
    return sum(st.mean) / 3, max(st.extrema[i][1] for i in range(3))


for key in ('palpagos', 'worldtree'):
    print(f'\n===== {key} =====')
    oa = Image.open(OFFICIAL[key])
    pa = Image.open(PALDB[key])
    print(f'  官方 {oa.size} {oa.mode}    paldb {pa.size} {pa.mode}')
    if oa.mode == 'RGBA':
        alpha = oa.getchannel('A')
        ast = ImageStat.Stat(alpha)
        print(f'  官方 alpha: 均值 {ast.mean[0]:.1f}/255  最小 {ast.extrema[0][0]}  最大 {ast.extrema[0][1]}'
              f'   (0=该处透明)')

    # 采样窗口: 中心 + 三个偏移
    centers = [(4096, 4096), (2048, 2048), (6144, 4096), (4096, 2048)]
    for ci, (cx, cy) in enumerate(centers):
        box = (max(0, cx - W // 2), max(0, cy - W // 2),
               min(8192, cx + W // 2), min(8192, cy + W // 2))
        o = open_crop(OFFICIAL[key], box)
        p = open_crop(PALDB[key], box)
        md, mx = diff_metrics(o, p)
        so = sharpness(o); sp = sharpness(p)
        print(f'  窗口{ci} {box[:2]}: 平均差 {md:6.2f} 最大差 {mx:3d} | '
              f'梯度 官方 {so[0]:6.2f}/σ{so[1]:6.2f}  paldb {sp[0]:6.2f}/σ{sp[1]:6.2f}')
        if ci == 0:
            side = Image.new('RGB', (W * 2 + 8, W), (0, 0, 0))
            side.paste(o, (0, 0)); side.paste(p, (W + 8, 0))
            d = ImageDraw.Draw(side)
            d.text((8, 8), 'OFFICIAL', fill=(255, 80, 80))
            d.text((W + 16, 8), 'PALDB', fill=(80, 200, 255))
            side.resize((W, W // 2), Image.LANCZOS).save(
                os.path.join(ROOT, f'compare_{key}_center.png'))
            print(f'     -> compare_{key}_center.png (左官方/右paldb)')

    # 对齐性: 无偏移 vs 人为偏移 64px 的差异对比
    box = (3584, 3584, 4608, 4608)
    o = open_crop(OFFICIAL[key], box)
    p0 = open_crop(PALDB[key], box)
    box_s = (3584 + 64, 3584, 4608 + 64, 4608)
    ps = open_crop(PALDB[key], box_s)
    d0, _ = diff_metrics(o, p0)
    d1, _ = diff_metrics(o, ps)
    print(f'  对齐性: 零偏移平均差 {d0:6.2f}   偏移64px后 {d1:6.2f}   '
          f'=> {"已对齐 (零偏移明显更小)" if d0 < d1 * 0.8 else "可能未对齐/内容不同"}')
