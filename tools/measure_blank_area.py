# -*- coding: utf-8 -*-
"""测量主图左上角空白区域与世界树图的内容范围 (纯 PIL, 无 numpy)。"""
import os
from PIL import Image, ImageChops

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EX = os.path.join(ROOT, 'export')
TH = 24                                    # 亮度阈值: 低于此视为"空白/黑"


def mask(im):
    """返回二值图: 有内容=白"""
    g = im.convert('L').point(lambda v: 255 if v > TH else 0)
    return g


def has_content(im):
    return mask(im).getbbox() is not None


pal = Image.open(os.path.join(EX, 'palpagos_0p64px_per_m_pal24px_marker24px.png')).convert('RGB')
wt = Image.open(os.path.join(EX, 'worldtree_0p64px_per_m_pal24px_marker24px.png')).convert('RGB')
H = pal.size[0]
S = wt.size[0]
print(f'主图 {pal.size}, 世界树图 {wt.size}')

print('\n内容包围盒 (x0,y0,x1,y1):')
print('   主图  ', mask(pal).getbbox())
print('   世界树', mask(wt).getbbox())

print('\n主图四角: 从角向内最大的"全空白"正方形边长 (二分):')
def corner_blank(corner):
    lo, hi = 0, H
    while lo < hi:
        mid = (lo + hi + 1) // 2
        box = {'TL': (0, 0, mid, mid), 'TR': (H - mid, 0, H, mid),
               'BL': (0, H - mid, mid, H), 'BR': (H - mid, H - mid, H, H)}[corner]
        if not has_content(pal.crop(box)):
            lo = mid
        else:
            hi = mid - 1
    return lo

for c, name in (('TL', '左上'), ('TR', '右上'), ('BL', '左下'), ('BR', '右下')):
    print(f'   {name}: {corner_blank(c)} px')

print(f'\n把世界树图({S}px)贴到主图左上角:')
patch = pal.crop((0, 0, S, S))
bb = mask(patch).getbbox()
print(f'   覆盖内容包围盒 {bb} -> ' + ('完全空白, 不会遮挡任何底图内容' if bb is None else '有内容, 会覆盖!'))
print(f'   覆盖区亮度范围 {patch.convert("L").getextrema()}')

print('\n世界树图四边亮度 (判断拼接缝):')
for name, box in (('上边', (0, 0, S, 2)), ('下边', (0, S - 2, S, S)),
                  ('左边', (0, 0, 2, S)), ('右边', (S - 2, 0, S, S))):
    print(f'   {name}: {wt.crop(box).convert("L").getextrema()}')

print('\n主图左上角区域含色数 (判断是否纯色):')
print('   colors =', len(patch.getcolors(maxcolors=1 << 20) or []))
