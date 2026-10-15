# -*- coding: utf-8 -*-
"""打印成品 HTML 里的图层显示顺序 (应与 TYPE_MAP 顺序一致)。"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
h = open(os.path.join(ROOT, 'pal_spawner_map.html'), encoding='utf-8').read()
d = json.loads(re.search(r'const DATA = (\{.*?\});\s*\nconst cv', h, re.S).group(1))
print('控制面板图层顺序:')
for i, v in enumerate(d['types'].values(), 1):
    print(f'   {i}. {v["code"]:3s} {v["label"]:16s} {v["color"]}  off={v.get("off", 0)}')
