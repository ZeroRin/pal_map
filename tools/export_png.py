#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出静态 PNG 地图: 含点位与头像, 底图按 16px = 25m (0.64 px/m) 缩放。

与网页同一套视觉规则:
  地下城(紫点, 每洞口一个)  →  钓点(青/粉菱形)与无数据(灰框)  →  普通点帕鲁头像  →  Boss/通缉犯头像
  头像 = 深色底衬 + 深色外圈 + 彩色描边 (Boss 红框 / 仅夜间蓝框 / 其余白框), 圆形裁剪
  尺寸按网页同一公式: 普通点 25m 基准 16~48px, Boss 50m 基准 16~96px (含 8px 量化)

用法:
  python tools/export_png.py                     # 导出两张图 (默认)
  python tools/export_png.py --icon-scale 1.5    # 头像放大 1.5 倍 (仅影响观感, 不改变底图比例尺)
  python tools/export_png.py --maps palpagos     # 只导某一张
  python tools/export_png.py --with-nd           # 额外画出"无数据"图层 (网页默认隐藏)
"""
import json, re, os, io, base64, argparse, math
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'export')

RING_BOSS = (255, 77, 79)
RING_NIGHT = (77, 159, 255)
RING_DAY = (255, 255, 255)
BG_DARK = (13, 17, 23)
NPC_BG = (48, 54, 61)
NPC_FG = (201, 209, 217)

ICON_STEP = 8


def icon_px(base_m, lo, hi, ppm):
    raw = base_m * ppm
    q = round(max(lo, min(hi, raw)) / ICON_STEP) * ICON_STEP
    return int(max(lo, q))


def load_data():
    html = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
    d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', html, re.S).group(1))
    # 底图文件名在 tools/maps_config.json (DATA.maps 里只有 bounds 与内嵌图)
    cfg = json.load(open(os.path.join(ROOT, 'tools', 'maps_config.json'), encoding='utf-8'))['maps']
    by_key = {m['key']: m for m in cfg}
    for m in d['maps']:
        c = by_key.get(m['key'], {})
        m['img8k'] = c.get('img8k', '')
        m['img4k'] = c.get('img4k', '')
    return d


def load_icon(src, cache):
    if src in cache:
        return cache[src]
    im = None
    try:
        im = Image.open(io.BytesIO(base64.b64decode(src.split(',')[1]))).convert('RGBA')
    except Exception:
        im = None
    cache[src] = im
    return im


def ring(dr, cx, cy, r, color, dpr=1):
    """深色外圈 + 彩色描边 (与网页 ringStroke 一致)"""
    dr.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(0, 0, 0, 158), width=3)
    dr.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color + (255,), width=2)


def make_sprite(key, size, src, night, font):
    """预渲染一个圆形头像精灵 (RGBA), 返回 Image"""
    pad = 4
    S = size
    canvas = Image.new('RGBA', (S + pad * 2, S + pad * 2), (0, 0, 0, 0))
    dr = ImageDraw.Draw(canvas)
    cx = cy = S / 2 + pad
    r = S / 2
    if key == 'NPC':                                  # 普通人类 NPC: 灰底占位符
        dr.ellipse((cx - r, cy - r, cx + r, cy + r), fill=NPC_BG + (255,))
        ring(dr, cx, cy, r, RING_NIGHT if night else RING_DAY)
        if font is not None and S >= 18:
            t = 'NPC'
            bb = dr.textbbox((0, 0), t, font=font)
            dr.text((cx - (bb[2] - bb[0]) / 2 - bb[0], cy - (bb[3] - bb[1]) / 2 - bb[1]),
                    t, font=font, fill=NPC_FG + (255,))
        else:                                          # 太小: 画个简笔人形
            hr = max(1.5, S * 0.13)
            dr.ellipse((cx - hr, cy - r * 0.55, cx + hr, cy - r * 0.55 + hr * 2), fill=NPC_FG + (255,))
            dr.pieslice((cx - r * 0.5, cy + r * 0.05, cx + r * 0.5, cy + r * 0.85), 180, 360,
                        fill=NPC_FG + (255,))
    else:
        if src is None:
            return None
        im = src
        rr = r + 1.4
        dr.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=BG_DARK + (230,))
        ring(dr, cx, cy, rr, RING_NIGHT if night else RING_DAY)
        thumb = im.resize((S, S), Image.LANCZOS)
        mask = Image.new('L', (S, S), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, S - 1, S - 1), fill=255)
        canvas.paste(thumb, (int(cx - r), int(cy - r)), mask)
    return canvas


def export(map_item, data, args, icon_cache, font):
    b = map_item['bounds']
    m_idx = data['maps'].index(map_item) if map_item in data['maps'] else None
    ppm = args.px_per_m
    W = int(round((b['maxY'] - b['minY']) / 100.0 * ppm))
    H = int(round((b['maxX'] - b['minX']) / 100.0 * ppm))
    print(f"\n[{map_item['label']}] 世界跨度 {(b['maxY']-b['minY'])/100000:.2f}×{(b['maxX']-b['minX'])/100000:.2f} km"
          f" -> {W}×{H} px  ({ppm:g} px/m)")

    # 底图
    src_path = os.path.join(ROOT, 'maps', map_item.get('img8k') or map_item.get('img4k'))
    if not os.path.exists(src_path):
        src_path = os.path.join(ROOT, 'maps', map_item.get('img4k'))
    im = Image.open(src_path).convert('RGB')
    print(f"   底图 {os.path.basename(src_path)} {im.width}px -> {W}px "
          f"({'放大' if W > im.width else '缩小'} {W/im.width:.2f}×)")
    img = im.resize((W, H), Image.LANCZOS)
    im.close()

    def w2p(x, y):
        return ((y - b['minY']) / 100.0 * ppm, (b['maxX'] - x) / 100.0 * ppm)

    pal_size = (int(args.icon_px) if args.icon_px
                else max(6, int(round(icon_px(25, 16, 48, ppm) * args.icon_scale))))
    boss_size = (int(args.boss_px) if args.boss_px
                 else max(8, int(round(icon_px(50, 16, 96, ppm) * args.icon_scale))))
    mk = args.marker_px                              # 非头像标记直径 (None = 沿用默认小尺寸)
    r_dg = (mk / 2) if mk else 5
    r_fish = (mk / 2) if mk else 5.5
    r_nd = (mk / 2 * 0.8) if mk else 4
    print(f"   头像尺寸: 普通点 {pal_size}px, Boss {boss_size}px"
          + (" (参数覆盖)" if (args.icon_px or args.boss_px) else f" (网页公式 × {args.icon_scale:g})")
          + (f"; 非头像标记直径 {mk:g}px" if mk else ""))
    print(f"     换算: 普通点 {pal_size}px = {pal_size/ppm:.1f}m, Boss {boss_size}px = {boss_size/ppm:.1f}m"
          + (f", 非头像标记 {mk:g}px = {mk/ppm:.1f}m" if mk else ""))

    PTS, ICON_KEY, PALS, BOUNTY = data['points'], data['icons'], data['pals'], data['bounty']
    pts = [p for p in PTS if p['m'] == m_idx and not p.get('dd')]

    sprites = {}
    def sprite(key, size, night):
        ck = (key, size, night)
        sp = sprites.get(ck)
        if sp is None:
            src = None
            if key != 'NPC':
                v = PALS.get(key) or {}
                src = load_icon(v.get('i'), icon_cache) if v.get('i') else None
            sp = make_sprite(key, size, src, night, font) or False
            sprites[ck] = sp
        return sp or None

    # 描画顺序与网页一致: 地下城 → 钓点/无数据 → 普通点头像 → Boss 头像
    def draw_marker(p, key, size, ringcolor):
        px, py = w2p(p['x'], p['y'])
        if not (-size <= px <= W + size and -size <= py <= H + size):
            return 0
        sp = sprite(key, size, p.get('ni', 0) == 1) if key != 'BOSS' else None
        if sp is None:
            return 0
        if ringcolor == RING_BOSS:                     # Boss: 换红框
            sp = sp.copy()
            d2 = ImageDraw.Draw(sp)
            rr = size / 2 + 1.4 + 4
            cx = cy = sp.width / 2
            d2.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(0, 0, 0, 158), width=3)
            d2.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=RING_BOSS + (255,), width=2)
        img.paste(sp, (int(px - sp.width / 2), int(py - sp.height / 2)), sp)
        return 1

    dr = ImageDraw.Draw(img)
    n = {'DG': 0, 'F': 0, 'I': 0, 'NB': 0, 'C': 0, 'FC': 0, 'FR': 0, 'ND': 0}
    for p in pts:                                      # 1) 地下城 (每洞口一个代表点)
        if p['t'] != 'DG':
            continue
        px, py = w2p(p['x'], p['y'])
        r = r_dg
        dr.ellipse((px - r, py - r, px + r, py + r), fill=(188, 140, 255, 255), outline=(0, 0, 0, 200), width=max(2, int(r/5)))
        n['DG'] += 1
    for p in pts:                                      # 2) 钓点 + 无数据
        if p['t'] not in ('FC', 'FR', 'ND'):
            continue
        if p['t'] == 'ND' and not args.with_nd:
            continue
        px, py = w2p(p['x'], p['y'])
        if p['t'] == 'ND':
            r = r_nd
            dr.rectangle((px - r, py - r, px + r, py + r), outline=(139, 148, 158, 255), width=max(2, int(r/5)))
        else:
            r = r_fish
            col = (34, 211, 238, 255) if p['t'] == 'FC' else (244, 114, 182, 255)
            dr.polygon([(px, py - r), (px + r, py), (px, py + r), (px - r, py)],
                       fill=col, outline=(0, 0, 0, 200))
        n[p['t']] += 1
    for p in pts:                                      # 3) 普通点头像
        if p['t'] != 'C' or p.get('ii', -1) < 0:
            continue
        if draw_marker(p, ICON_KEY[p['ii']], pal_size, None):
            n['C'] += 1
    for p in pts:                                      # 4) Boss / 通缉犯头像 (红框)
        if p['t'] not in ('F', 'I', 'NB'):
            continue
        b2 = BOUNTY.get(p.get('nb') or '') or {}
        key = (b2.get('name') and p['nb']) or ''
        if p['t'] == 'NB':                             # 通缉犯用 NPC 图标
            icon = b2.get('icon')
            src = load_icon(icon, icon_cache) if icon else None
            sp = None
            if src is not None:
                sp = make_sprite(p['nb'], boss_size, src, False, font)
                d2 = ImageDraw.Draw(sp)
                rr = boss_size / 2 + 1.4 + 4
                cx = cy = sp.width / 2
                d2.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(0, 0, 0, 158), width=3)
                d2.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=RING_BOSS + (255,), width=2)
            if sp is not None:
                px, py = w2p(p['x'], p['y'])
                img.paste(sp, (int(px - sp.width / 2), int(py - sp.height / 2)), sp)
                n['NB'] += 1
            continue
        # 野外/监禁 Boss: 取该刷怪器表中带"首领"标签的条目
        lst = data['tables'].get(p['n']) or []
        e = next((x for x in lst if x.get('bg')), None) or (lst[0] if lst else None)
        base = (e or {}).get('b')
        if not base:
            continue
        px, py = w2p(p['x'], p['y'])
        sp = sprite(base, boss_size, False)
        if sp is None:
            continue
        sp = sp.copy()
        d2 = ImageDraw.Draw(sp)
        rr = boss_size / 2 + 1.4 + 4
        cx = cy = sp.width / 2
        d2.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(0, 0, 0, 158), width=3)
        d2.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=RING_BOSS + (255,), width=2)
        img.paste(sp, (int(px - sp.width / 2), int(py - sp.height / 2)), sp)
        n[p['t']] += 1

    os.makedirs(OUT_DIR, exist_ok=True)
    tag = f"{ppm:g}".replace('.', 'p')
    name = f"{map_item['key']}_{tag}px_per_m"
    if args.icon_scale != 1.0:
        name += f"_icon{args.icon_scale:g}x".replace('.', 'p')
    if args.icon_px:
        name += f"_pal{args.icon_px}px"
    if args.boss_px:
        name += f"_boss{args.boss_px}px"
    if args.marker_px:
        name += f"_marker{args.marker_px}px"
    if args.with_nd:
        name += '_withnd'
    out = os.path.join(OUT_DIR, name + '.png')
    img.save(out, 'PNG', optimize=True)
    print(f"   已画出: 地下城 {n['DG']} · 普通点头像 {n['C']} · 野外Boss {n['F']} · 监禁Boss {n['I']} · "
          f"通缉犯 {n['NB']} · 普通钓点 {n['FC']} · 稀有钓点 {n['FR']}"
          + (f" · 无数据 {n['ND']}" if args.with_nd else ""))
    print(f"   -> {out}  ({os.path.getsize(out)/1e6:.1f} MB, {W}×{H})")
    return out


def combine(data, args, pal_path, wt_path):
    """把世界树图贴到主图的左上角空白区 (两者黑度一致, 无缝且不遮挡底图内容)。
    先校验该区域确实为空白, 避免日后底图变化导致误遮挡。"""
    pal = Image.open(pal_path).convert('RGB')
    wt = Image.open(wt_path).convert('RGB')
    S = wt.size[0]
    if S > pal.size[0]:
        print('   [跳过拼接] 世界树图比主图还大')
        return None

    def blank(im):
        bb = im.convert('L').point(lambda v: 255 if v > 24 else 0).getbbox()
        return bb is None

    patch = pal.crop((0, 0, S, S))
    if not blank(patch):
        print('   [跳过拼接] 主图左上角不是空白, 拼接会遮挡底图内容')
        return None
    lo_p, hi_p = patch.convert('L').getextrema()
    # 接缝看的是"边框一圈"的亮度 (世界树图边缘 vs 主图空白), 而不是整幅图的范围
    b = 4
    edges = [wt.crop(x) for x in ((0, 0, S, b), (0, S - b, S, S), (0, 0, b, S), (S - b, 0, S, S))]
    w_lo = min(e.convert('L').getextrema()[0] for e in edges)
    w_hi = max(e.convert('L').getextrema()[1] for e in edges)
    pal.paste(wt, (0, 0))
    tag = os.path.basename(pal_path)[len(data['maps'][0]['key']) + 1:-4]
    out = os.path.join(OUT_DIR, f"combined_{tag}.png")
    pal.save(out, 'PNG', optimize=True)
    print(f"\n[拼接] 世界树图 {S}×{S} 贴到主图左上角 (0,0)")
    print(f"   覆盖区亮度 {lo_p}~{hi_p} · 世界树图边缘亮度 {w_lo}~{w_hi} -> "
          + ('接缝不可见' if abs(w_hi - hi_p) <= 8 else '可能有可见接缝'))
    print(f"   -> {out}  ({os.path.getsize(out)/1e6:.1f} MB, {pal.size[0]}×{pal.size[1]})")
    return out


def out_path_for(map_item, args):
    """与 export() 相同的命名规则 (供 --combine-only 复用已有文件)"""
    ppm = args.px_per_m
    tag = f"{ppm:g}".replace('.', 'p')
    name = f"{map_item['key']}_{tag}px_per_m"
    if args.icon_scale != 1.0:
        name += f"_icon{args.icon_scale:g}x".replace('.', 'p')
    if args.icon_px:
        name += f"_pal{args.icon_px}px"
    if args.boss_px:
        name += f"_boss{args.boss_px}px"
    if args.marker_px:
        name += f"_marker{args.marker_px}px"
    if args.with_nd:
        name += '_withnd'
    return os.path.join(OUT_DIR, name + '.png')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--px-per-m', type=float, default=16 / 25, help='比例尺, 默认 16px=25m -> 0.64 px/m')
    ap.add_argument('--icon-scale', type=float, default=1.0, help='头像尺寸倍数 (只影响观感)')
    ap.add_argument('--icon-px', type=int, default=0, help='普通点头像直径(px), 覆盖公式')
    ap.add_argument('--boss-px', type=int, default=0, help='Boss头像直径(px), 覆盖公式')
    ap.add_argument('--marker-px', type=int, default=0, help='非头像标记(地下城/钓点/无数据)直径(px)')
    ap.add_argument('--maps', default='all', help='all / palpagos / worldtree')
    ap.add_argument('--with-nd', action='store_true', help='一并画出"无数据"图层')
    ap.add_argument('--combine', action='store_true',
                    help='导出后再把世界树图贴到主图左上角空白区, 生成一张合并图')
    ap.add_argument('--combine-only', action='store_true',
                    help='不重新渲染, 直接用已有的两张 PNG 拼接')
    args = ap.parse_args()

    data = load_data()
    if args.combine_only:
        pal = next(m for m in data['maps'] if m['key'] == 'palpagos')
        wt = next(m for m in data['maps'] if m['key'] == 'worldtree')
        p, w = out_path_for(pal, args), out_path_for(wt, args)
        for f in (p, w):
            if not os.path.exists(f):
                print(f'缺少 {f}, 请先正常导出')
                return
        combine(data, args, p, w)
        return

    print(f"点位 {len(data['points'])} 个 · 头像字典 {len(data['icons'])} 种 · 底图 {len(data['maps'])} 张")
    try:
        font = ImageFont.truetype('arial.ttf', 9)
    except Exception:
        font = None
    icon_cache = {}
    made = {}
    for m in data['maps']:
        if args.maps not in ('all', m['key']):
            continue
        made[m['key']] = export(m, data, args, icon_cache, font)
    if args.combine and args.maps == 'all' and 'palpagos' in made and 'worldtree' in made:
        combine(data, args, made['palpagos'], made['worldtree'])


if __name__ == '__main__':
    main()
