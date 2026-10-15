# -*- coding: utf-8 -*-
"""检查 鱼影ID -> PalId -> 中文名 的链路完整度, 以及世界树钓点类型是否在表内。"""
import json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FISH = os.path.join(ROOT, 'src', 'data', 'Fishing')
wiki = json.load(open(os.path.join(ROOT, 'tools', 'pals_wiki.json'), encoding='utf-8'))
lower = {k.lower(): k for k in wiki}


def rows(p):
    return json.load(open(p, encoding='utf-8'))[0]['Rows']


shadow = rows(os.path.join(FISH, 'DT_PalFishShadowDataTable.json'))
lottery = rows(os.path.join(FISH, 'DT_PalFishingSpotLotteryDataTable.json'))
names = rows(os.path.join(FISH, 'DT_PalFishingSpotLotteryNameDataTable.json'))
spots = json.load(open(os.path.join(ROOT, 'src', 'paldb', 'paldb_fishing_spots_all.json'), encoding='utf-8'))

# 用例类型是否都在类型表
hrefs = set(s['href'] for s in spots)
print(f'实例类型 {len(hrefs)} 种, 在类型表中: {len([h for h in hrefs if h in names])} 种')
print('  未命中:', [h for h in hrefs if h not in names])

# 抽签表的 FishShadowId -> 帕鲁
shadow_ids = set(v.get('FishShadowId') for v in lottery.values())
print(f'\n抽签表引用鱼影ID {len(shadow_ids)} 种, 在鱼影表中: {len([s for s in shadow_ids if s in shadow])}')
miss = [s for s in shadow_ids if s not in shadow]
print('  未命中:', miss[:10])

pals = sorted({shadow[s]['PalId'] for s in shadow_ids if s in shadow})
print(f'\n涉及帕鲁 {len(pals)} 种, 中文名命中: {len([p for p in pals if p.lower() in lower])}')
print('  未命中:', [p for p in pals if p.lower() not in lower])

# 世界树钓点类型的产出
print('\n世界树钓点类型的产出条数:')
for t in sorted(h for h in hrefs if 'WorldTree' in h):
    n = sum(1 for v in lottery.values() if v.get('LotteryName') == t)
    print(f'   {t:34s} {n:3d} 条, 重生 {names[t]["RespawnTime"]}s')
