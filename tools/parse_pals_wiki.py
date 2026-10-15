# -*- coding: utf-8 -*-
"""从 palswiki 存档页解析帕鲁表: 内部ID -> 中文名/图鉴号/图标, 并核对刷怪数据的覆盖率。
用法: python tools/parse_pals_wiki.py   -> 写出 tools/pals_wiki.json 供 build_spawner_map.py 使用"""
import json, re, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, 'src', 'palswiki', 'Pals - Palworld Database Wiki.html')
OUT = os.path.join(ROOT, 'tools', 'pals_wiki.json')

raw = open(HTML, encoding='utf-8').read()
cards = raw.split('<div class="col" data-filters=')
print(f'卡片数: {len(cards)-1}')

pals = {}
for c in cards[1:]:
    m_id = re.search(r'data-pal-id="([^"]+)"', c)
    if not m_id:
        continue
    pid = m_id.group(1)
    m_icon = re.search(r'src="[^"]*?/(T_[^"/]+_icon[^"/]*\.webp)"', c)
    m_name = re.search(r'class="itemname"[^>]*>([^<]+)<', c)
    m_zk = re.search(r'#(\d+)', c)
    m_elem = re.findall(r'data-bs-title="([^"]*属性)"', c)
    if not m_name:
        continue
    pals[pid] = {
        'cn': m_name.group(1).strip(),
        'zukan': int(m_zk.group(1)) if m_zk else 0,
        'icon': m_icon.group(1) if m_icon else '',
        'elem': m_elem[:2],
    }
print(f'解析到帕鲁: {len(pals)}')
print('样例:', list(pals.items())[:3])

# 刷怪数据里出现的所有帕鲁 ID
SP = os.path.join(ROOT, 'src', 'data')
wild = json.load(open(os.path.join(SP, 'DT_PalWildSpawner.json'), encoding='utf-8'))[0]['Rows']
used = collections.Counter()
for r in wild.values():
    if r.get('Weight', 0) <= 0:
        continue
    for i in (1, 2, 3):
        p = r.get(f'Pal_{i}', 'None')
        if p and p not in ('None', 'RowName'):
            used[p] += 1
print(f'\n刷怪表用到的帕鲁 ID: {len(used)} 种')

hit, miss = [], []
for p in used:
    base = p[5:] if p.startswith('BOSS_') else p
    (hit if base in pals else miss).append(p)
print(f'  直接/去BOSS_前缀 命中: {len(hit)}')
print(f'  未命中: {len(miss)}')

# 未命中再尝试去后缀
still = []
for p in miss:
    base = p[5:] if p.startswith('BOSS_') else p
    cand = None
    for suf in ('_Dark', '_2', '_Oilrig', '_Tower', '_Raid', '_Ice', '_Fire', '_Electric',
                '_Water', '_Grass', '_Ground', '_Normal', '_Pink', '_Purple', '_Snow'):
        if base.endswith(suf) and base[:-len(suf)] in pals:
            cand = base[:-len(suf)]
            break
    # 变体命名如 SheepBall_Dark / xxx_BOSS / _Max
    if cand is None and '_' in base:
        head = base.split('_')[0]
        if head in pals:
            cand = head
    if cand:
        still.append((p, cand))
    else:
        still.append((p, None))
print('\n未命中明细 (前 40):')
for p, cand in still[:40]:
    print(f'   {p:45s} -> {"可映射到 " + cand if cand else "无法映射"}')
print(f'   共 {len(still)} 个, 其中可二次映射 {sum(1 for _, c in still if c)}')

if not os.path.exists(OUT) or True:
    json.dump(pals, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n已写入 {OUT}')
