# -*- coding: utf-8 -*-
"""测试官方 8192 PNG 的压缩方案 (体积 vs 质量), 为替换底图做准备。"""
import os
from PIL import Image, ImageChops, ImageStat

ROOT = r'D:\Workspace\Palworld\Decompile'
SRC = {
    'palpagos': os.path.join(ROOT, r'exports\Pal\Content\Pal\Texture\UI\Map\T_WorldMap_MIP0.png'),
    'worldtree': os.path.join(ROOT, r'exports\Pal\Content\Pal\Texture\UI\Map\T_TreeMap_MIP0.png'),
}
OUTDIR = os.path.join(ROOT, 'downloads', 'map_compress_test')
os.makedirs(OUTDIR, exist_ok=True)


def mean_diff(a, b):
    d = ImageChops.difference(a.convert('RGB'), b.convert('RGB'))
    st = ImageStat.Stat(d)
    return sum(st.mean) / 3


for key, path in SRC.items():
    print(f'\n===== {key}: 原始 PNG {os.path.getsize(path)/1e6:.1f} MB =====')
    im = Image.open(path).convert('RGB')
    # 8192 原尺寸的几种编码
    for name, kwargs, ext in (
        ('webp q95', dict(format='WEBP', quality=95, method=6), 'webp'),
        ('webp q90', dict(format='WEBP', quality=90, method=6), 'webp'),
        ('webp lossless', dict(format='WEBP', lossless=True, method=6), 'webp'),
    ):
        p = os.path.join(OUTDIR, f'{key}_8192_{name.replace(" ", "")}.{ext}')
        im.save(p, **kwargs)
        chk = Image.open(p)
        print(f'  {name:14s} {os.path.getsize(p)/1e6:7.2f} MB   与原图平均差 {mean_diff(im, chk):5.2f}')
    # 4096 内嵌候选
    small = im.resize((4096, 4096), Image.LANCZOS)
    for name, kwargs in (('webp q85', dict(format='WEBP', quality=85, method=6)),
                         ('webp q92', dict(format='WEBP', quality=92, method=6))):
        p = os.path.join(OUTDIR, f'{key}_4096_{name.replace(" ", "")}.webp')
        small.save(p, **kwargs)
        chk = Image.open(p)
        print(f'  4096 {name:9s} {os.path.getsize(p)/1e6:7.2f} MB   与自身缩图差 {mean_diff(small, chk):5.2f}')
