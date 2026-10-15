# -*- coding: utf-8 -*-
"""验证钓点坐标(paldb) 与 解包 DataTable 的关联可行性。"""
import json, os, collections

ROOT = r'D:\Workspace\Palworld\Decompile'
FISH = os.path.join(ROOT, 'exports', 'Pal', 'Content', 'Pal', 'DataTable', 'Fishing')


def rows(fn):
    return json.load(open(os.path.join(FISH, fn), encoding='utf-8'))[0]['Rows']


spots = json.load(open(os.path.join(ROOT, 'downloads', 'paldb_fishing_spots.json'), encoding='utf-8'))
names = rows('DT_PalFishingSpotLotteryNameDataTable.json')       # 类型 -> RespawnTime
lottery = rows('DT_PalFishingSpotLotteryDataTable.json')          # 逐条权重
shadow = rows('DT_PalFishShadowDataTable.json')                   # 鱼影?

print(f'钓点实例 {len(spots)} 个; 类型表 {len(names)} 行; 抽签表 {len(lottery)} 行; 鱼影表 {len(shadow)} 行')

hrefs = collections.Counter(s['href'] for s in spots)
hit = [h for h in hrefs if h in names]
miss = [h for h in hrefs if h not in names]
print(f'\n实例类型与类型表关联: 命中 {len(hit)} 种 / 未命中 {len(miss)} 种')
if miss:
    print('   未命中:', miss)
print(f'   覆盖实例数: {sum(hrefs[h] for h in hit)} / {len(spots)}')

# 抽签表按类型分组
by_lot = collections.defaultdict(list)
for k, v in lottery.items():
    by_lot[v.get('LotteryName')].append(v)
print(f'\n抽签表覆盖的钓点类型: {len(by_lot)}')
example = by_lot.get('FishingSpot_A_Ocean_Common', [])
print(f'以 FishingSpot_A_Ocean_Common 为例, {len(example)} 条可能产出:')
for e in example[:6]:
    print(f"   权重{e.get('Weight'):>6} 鱼影={e.get('FishShadowId'):14s} 掉落={e.get('GainItemLotteryName'):22s} "
          f"Lv{e.get('MinLevel')}-{e.get('MaxLevel')} 难度={e.get('FishingSpotDifficulty','').split('::')[-1]}")

print('\n鱼影表样例行:')
k0 = list(shadow)[0]
print(f'  {k0}: {json.dumps(shadow[k0], ensure_ascii=False)[:300]}')
print('  行名前 10:', list(shadow)[:10])

# 类型表里有多少类型在实际实例中出现
unused = [n for n in names if n not in hrefs]
print(f'\n类型表中未被任何实例引用的类型: {len(unused)} 个 (多为测试/未启用): {unused[:12]}')
