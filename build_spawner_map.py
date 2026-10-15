# -*- coding: utf-8 -*-
"""
幻兽帕鲁 刷怪区域可视化构建脚本

输入 (均在本项目文件夹内, 可整包分享):
  src/data/*.json                    解包得到的刷怪数据表 (DT_PalSpawnerPlacement / DT_PalWildSpawner
                                     / DT_PalMonsterParameter 作为图鉴号回退)
  src/palswiki/                      paldb 帕鲁列表存档页 (中文名 + 图标); tools/parse_pals_wiki.py 解析
  tools/pals_wiki.json               上者的解析结果 (内部ID -> 中文名/图鉴号/图标)
  tools/maps_config.json             双底图配置 (世界坐标范围 + 图片文件名); tools/stitch_maps.py 生成
  maps/map_*_4096.webp               底图 (内嵌进 HTML, 保证单文件自包含)
  maps/map_*_8192.webp               可选高清底图 (与 HTML 同目录时运行时自动加载)

输出:
  pal_spawner_map.html               自包含可视化页面, 双击即可打开

坐标系 (UE 惯例, 已用数据验证):
  世界坐标 +X = 北, +Y = 东, +Z = 高度, 单位厘米
  屏幕布局: 东(+Y)向右, 北(+X)向上, 与游戏内地图一致
"""
import json, os, base64, collections, re, random, zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
SPAWNER_DIR = os.path.join(ROOT, "src", "data")
MONSTER_JSON = os.path.join(ROOT, "src", "data", "DT_PalMonsterParameter.json")
WIKI_JSON = os.path.join(ROOT, "tools", "pals_wiki.json")
MAPS_JSON = os.path.join(ROOT, "tools", "maps_config.json")
ICON_DIR = os.path.join(ROOT, "src", "palswiki", "Pals - Palworld Database Wiki_files")
FISH_DIR = os.path.join(ROOT, "src", "data", "Fishing")
FISH_SPOTS_JSON = os.path.join(ROOT, "src", "paldb", "paldb_fishing_spots_all.json")
# 人类通缉犯(賞金首)资料: 中文名 / 参数 / 地图图标
L10N_DIR = os.path.join(ROOT, "src", "data", "l10n", "zh-Hans")
CHAR_DIR = os.path.join(ROOT, "src", "data", "Character")
UI_DIR = os.path.join(ROOT, "src", "data", "UI")
DUNGEON_DIR = os.path.join(ROOT, "src", "data", "Dungeon")
NPC_ICON_DIR = os.path.join(ROOT, "src", "npc_icons")
MAPS_DIR = os.path.join(ROOT, "maps")
MAPS_URL = "maps"                      # HTML 中引用高清底图的相对前缀
OUT_HTML = os.path.join(ROOT, "pal_spawner_map.html")

TYPE_MAP = {  # -> (短码, 中文名, 颜色); 字典顺序 = 页面图层的显示顺序
    "EPalSpawnedCharacterType::Common":            ("C", "普通刷怪",   "#3fb950"),
    "EPalSpawnedCharacterType::FieldBoss":         ("F", "野外Boss",   "#f85149"),
    "EPalSpawnedCharacterType::ImprisonmentBoss":  ("I", "监禁Boss",   "#d29922"),
    # 地下城: 洞窟Boss 与洞窟内部小怪点坐标完全重合, 统一归一个图层, 由合并后的地下城面板展示
    "EPalSpawnedCharacterType::RandomDungeonBoss": ("DG", "地下城",    "#bc8cff"),
    # 钓点 (坐标来自 paldb 地图数据; 类型与产出关联解包 DataTable)
    "EPalFishingSpotType::Common":                 ("FC", "普通钓点",  "#22d3ee"),
    "EPalFishingSpotType::Rare":                   ("FR", "稀有钓点",  "#f472b6"),
    # 人类通缉犯(賞金首): 点位来自 DT_PalSpawnerPlacement 的 Mono/SquadNPCSpawnerBossBase,
    # 名称/参数/图标来自 DT_HumanNameText(zh-Hans) + DT_PalHumanParameter + DT_PalBossNPCIcon
    "EPalSpawnerBossNPC::Bounty":                  ("NB", "人类通缉犯", "#ff9f1c"),
    # 刷怪表在当前版本数据中不存在的残留 sheet (默认不显示)
    "EPalSpawnerNoData::Deprecated":               ("ND", "无数据(疑似弃用)", "#6e7681"),
}
OFF_BY_DEFAULT = {"ND"}          # 默认不勾选的图层
NPC_BOSS_RE = re.compile(r"NPCSpawnerBossBase_(.+?)_C$")


def load_dungeon_meta():
    """洞窟元数据:
      spawner -> RankType (Boss / Normal / FishPal / NPCHuman)  来自 DT_DungeonEnemySpawnDataTable
      spawner -> (区域 id, 区域中文名)                          来自 DT_DungeonSpawnAreaDataTable + DT_DungeonNameText
    区域名文本里存在占位符 ("zh-hans text" / "-"), 视为无名称。"""
    f_enemy = os.path.join(DUNGEON_DIR, "DT_DungeonEnemySpawnDataTable.json")
    f_area = os.path.join(DUNGEON_DIR, "DT_DungeonSpawnAreaDataTable.json")
    f_text = os.path.join(L10N_DIR, "DT_DungeonNameText.json")
    if not os.path.exists(f_enemy):
        return {}, {}
    enemy = load_rows(f_enemy)
    area = load_rows(f_area) if os.path.exists(f_area) else {}
    text = load_rows(f_text) if os.path.exists(f_text) else {}

    def name_of(area_id):
        tid = (area.get(area_id) or {}).get("DungeonNameTextId", "")
        v = ((text.get(tid) or {}).get("TextData") or {}).get("LocalizedString", "") or ""
        # 占位符: "-" / "zh-hans text" / 以 NAME_ 开头
        if not v or v.strip() == "-" or v.startswith("NAME_") or v.lower().endswith(" text"):
            return ""
        return v

    # 表中的刷怪器名带 BP_PalSpawner_Sheets_ 前缀, 需归一化成我们使用的 SpawnerName
    PREFIX = "BP_PalSpawner_Sheets_"
    rank, area_of = {}, {}
    for _, v in enemy.items():
        asset = (v.get("SpawnerBlueprintSoftClass") or {}).get("AssetPathName", "").split("/")[-1].split(".")[0]
        if not asset:
            continue
        sp = asset[len(PREFIX):] if asset.startswith(PREFIX) else asset
        sid = v.get("SpawnAreaId", "")
        rank[sp] = v.get("RankType", "").split("::")[-1] or "Normal"
        nm = name_of(sid)
        if sp not in area_of or (not area_of[sp][1] and nm):
            area_of[sp] = (sid, nm)
    return rank, area_of


def load_boss_spawner_loc():
    """DT_BossSpawnerLoactionData (游戏 UI 用的"首领刷新点"表): SpawnerID / CharacterID / Location / Level。
    这是**权威的赏金首登记表**——布点表的 SpawnerClass 资产名可能与它不一致
    (实例: 资产名 BP_..._BOSS_Believer_Fat_GatlingGun_C, 但同坐标的登记是 BOSS_Believer_Fat_GiantClub)。
    返回 {(round(X//100), round(Y//100)): {"id": SpawnerID, "level": Level}}。"""
    p = os.path.join(UI_DIR, "DT_BossSpawnerLoactionData.json")
    if not os.path.exists(p):
        return {}
    idx = {}
    for _, r in load_rows(p).items():
        L = r.get("Location") or {}
        if "X" not in L:
            continue
        idx[(int(L["X"] // 100), int(L["Y"] // 100))] = {
            "id": r.get("SpawnerID", ""), "level": r.get("Level", 0),
            "x": L["X"], "y": L["Y"],
        }
    return idx


def nearest_loc(idx, x, y, tol=200.0):
    """在位置索引里找最近条目 (tol: 厘米容差, 默认 2m)"""
    best = None
    kx, ky = int(x // 100), int(y // 100)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            e = idx.get((kx + dx, ky + dy))
            if not e:
                continue
            d = ((e["x"] - x) ** 2 + (e["y"] - y) ** 2) ** 0.5
            if d <= tol and (best is None or d < best[0]):
                best = (d, e)
    return best[1] if best else None


def load_bounty(npc_ids):
    """人类通缉犯(賞金首)资料: npcId -> {name, icon(dataURI), bp, elem, hp}
    链路: 点位 SpawnerClass(BP_Mono/SquadNPCSpawnerBossBase_<NPC>) -> NPC id
          -> DT_HumanNameText_Common(zh-Hans) NAME_BOSS_* 名称
          -> DT_PalHumanParameter / DT_PalBossNPCIcon 参数与图标"""
    f_zh = os.path.join(L10N_DIR, "DT_HumanNameText_Common.json")
    f_hp = os.path.join(CHAR_DIR, "DT_PalHumanParameter.json")
    f_ic = os.path.join(CHAR_DIR, "DT_PalBossNPCIcon.json")
    if not all(os.path.exists(p) for p in (f_zh, f_hp, f_ic)):
        print("  (缺少赏金首资料表, 跳过)")
        return {}
    zh = {k.lower(): v for k, v in load_rows(f_zh).items()}
    hp = {k.lower(): v for k, v in load_rows(f_hp).items()}
    ic = {k.lower(): v for k, v in load_rows(f_ic).items()}

    def _cands(key):
        """候选键: 原名 / 补 BOSS_ 前缀 / 去 BOSS_ 前缀 (游戏里两种命名都存在, 且大小写不一致)"""
        out = [key]
        if key[:5].lower() == "boss_":
            out.append(key[5:])
        else:
            out.append("BOSS_" + key)
        return [c.lower() for c in out]

    def pick(tbl, key, require_boss=False):
        """候选键依次尝试; require_boss: 只接受 IsBoss=true 的行
        (避免把"普通版 NPC"(如 Believer_Fat_GatlingGun, IsBoss=false) 误当成赏金首)"""
        fallback = None
        for c in _cands(key):
            v = tbl.get(c)
            if not v:
                continue
            if require_boss and not v.get("IsBoss"):
                fallback = fallback or v
                continue
            return v
        return fallback

    out = {}
    for nid in npc_ids:
        e = pick(hp, nid, require_boss=True) or {}
        i = pick(ic, nid) or {}
        # 名称键有两种形态: NAME_BOSS_X 与 NAME_X; 无 BOSS_ 前缀时必须优先取通缉犯名
        # (否则 Viking 会取到通用 NPC 的 "天坠之民" 而非 "通缉犯 奈尔")
        n = {}
        for k in (["NAME_" + nid, "NAME_" + nid[5:]] if nid[:5].lower() == "boss_"
                  else ["NAME_BOSS_" + nid, "NAME_" + nid]):
            v = zh.get(k.lower())
            if v:
                n = v
                break
        ap = (i.get("Icon") or {}).get("AssetPathName", "")
        icon = None
        if ap:
            fp = os.path.join(NPC_ICON_DIR, os.path.basename(ap.split(".")[0]) + ".webp")
            if os.path.exists(fp):
                with open(fp, "rb") as fh:
                    icon = "data:image/webp;base64," + base64.b64encode(fh.read()).decode()
        out[nid] = {
            "name": (n.get("TextData") or {}).get("LocalizedString", "") or "",
            "icon": icon,
            "bp": e.get("BPClass", ""),
            "bpclass": e.get("BPClass", ""),
            "isBoss": bool(e.get("IsBoss")),
        }
    return out


def load_fishing(wiki, wiki_lower, zk_of, pal_meta):
    """构建 钓点类型 -> 可钓到的帕鲁 表。链路:
      钓点类型 (DT_PalFishingSpotLotteryNameDataTable)
      -> 加权产出 (DT_PalFishingSpotLotteryDataTable: FishShadowId / 等级 / 难度 / 掉落组)
      -> 鱼影表 (DT_PalFishShadowDataTable: PalId)"""
    fname = os.path.join(FISH_DIR, "DT_PalFishingSpotLotteryNameDataTable.json")
    flot = os.path.join(FISH_DIR, "DT_PalFishingSpotLotteryDataTable.json")
    fshadow = os.path.join(FISH_DIR, "DT_PalFishShadowDataTable.json")
    if not all(os.path.exists(p) for p in (fname, flot, fshadow)):
        print("  (未找到钓鱼数据表, 跳过钓点产出)")
        return {}
    names = load_rows(fname)
    lottery = load_rows(flot)
    shadow = load_rows(fshadow)
    by_lot = collections.defaultdict(list)
    for _, r in lottery.items():
        by_lot[r.get("LotteryName")].append(r)

    out = {}
    for tname, rs in by_lot.items():
        total = sum((r.get("Weight") or 0) for r in rs)
        entries = []
        for r in rs:
            sh = r.get("FishShadowId") or ""
            pid = (shadow.get(sh) or {}).get("PalId") or ""
            base, badge = pal_meta(pid, wiki, wiki_lower) if pid else (None, "")
            if badge == "未知":
                badge = ""
            w = r.get("Weight") or 0
            entries.append({
                "id": pid, "b": base, "bg": badge,
                "lv": [r.get("MinLevel", 0), r.get("MaxLevel", 0)],
                "w": w,
                "pct": round(w / total * 100, 1) if total else 0.0,
                "dif": strip_enum(r.get("FishingSpotDifficulty", "")),
                "drop": r.get("GainItemLotteryName", ""),
                "shadow": sh,
                "z": zk_of(base, pid) if base else 0,
            })
        entries.sort(key=lambda e: (-e["w"], e["z"] or 999, e["id"]))
        out[tname] = {
            "respawn": (names.get(tname) or {}).get("RespawnTime", 0),
            "rows": entries,
        }
    return out

def load_rows(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data[0]["Rows"]  # dict: rowName -> row

def strip_enum(v):
    return v.split("::")[-1] if isinstance(v, str) and "::" in v else v


def load_wiki():
    """paldb 帕鲁表: 内部ID -> {cn, zukan, icon, elem}; 另建小写索引应对大小写差异
    (游戏表里出现 Boss_Anubis / Icewitch, wiki 里是 Anubis / IceWitch)。"""
    if not os.path.exists(WIKI_JSON):
        return {}, {}
    wiki = json.load(open(WIKI_JSON, encoding="utf-8"))
    lower = {k.lower(): k for k in wiki}
    return wiki, lower


def pal_meta(pid, wiki, lower):
    """原始帕鲁ID -> (基础wikiID 或 None, 变体标签)
    处理: BOSS_/Boss 前缀、Quest_xxx_ 前缀、_后缀变体、大小写差异。"""
    if pid.startswith("NPC:"):
        return None, "NPC"
    s, badge = pid, ""
    if s[:5].lower() == "boss_":
        s, badge = s[5:], "首领"
    elif s[:4].lower() == "boss":
        s, badge = s[4:], "首领"
    if s[:6].lower() == "quest_":
        s = s.rsplit("_", 1)[-1]
        badge = (badge + " 任务").strip()
    if s.lower() in lower:
        return lower[s.lower()], badge
    if "_" in s:                        # 如 PlantSlime_Flower
        head, suf = s.split("_", 1)
        if head.lower() in lower:
            return lower[head.lower()], (badge + " " + suf).strip()
    return None, (badge or "未知")

def allocate_icon_units(units, n_slots):
    """把"单位"分配到 n_slots 个格子: 先每个单位保底 1 格, 剩余按权重用最大余数法补足。
    units: [(icon_key, weight), ...] (weight 已含夜间折算)
    单位数 > 格子数时按权重降序取前 n_slots 个 (调用方通常已先腾位)。
    返回"单位元组"列表, 长度恰为 n_slots (保留 is_night, 供仅夜间头像描蓝框)。"""
    k = len(units)
    if k == 0 or n_slots <= 0:
        return []
    if k >= n_slots:
        order = sorted(range(k), key=lambda i: (-units[i][1], units[i][0]))
        return [units[i] for i in order[:n_slots]]
    rem = n_slots - k
    tot = sum(u[1] for u in units) or 1.0
    exact = [rem * u[1] / tot for u in units]
    add = [int(x) for x in exact]
    left = rem - sum(add)
    for i in sorted(range(k), key=lambda i: -(exact[i] - add[i]))[:left]:
        add[i] += 1
    out = []
    for u, a in zip(units, add):
        out.extend([u] * (1 + a))
    return out


def build_icon_units(rows, is_pal, mimic_key="MimicDog", night_div=5.0):
    """把抽签行转成"头像单位": 每个单位 = 最终要占 1 格的一个头像。
      - 行内任何一只不是帕鲁(即 NPC) -> 整行 1 个单位, 用灰底 NPC 占位符
      - 单只帕鲁行 -> 取该帕鲁
      - 多只行且代表可定 (恰有 1 只数量固定为 1 的"头领", 或恰有 1 只本刷怪器其它行未出现) -> 取代表
      - 多只行且代表不可定 -> 权重均分, 行内每只各成 1 个单位
    权重: 仅夜间行按 night_div 折算 (夜晚约占全天 1/5)。
    返回 [(icon_key, weight, is_night)]"""
    def key_of(e):
        return (e.get("b") or e["id"])

    out = []
    for r in rows:
        night = r.get("time") == "Night"
        w = r["w"] / night_div if night else r["w"]
        if any(not is_pal(e) for e in r["pals"]):
            out.append(("NPC", w, night))
            continue
        if len(r["pals"]) == 1:
            out.append((key_of(r["pals"][0]), w, night))
            continue
        fixed1 = [e for e in r["pals"] if e["num"][0] == 1 and e["num"][1] == 1]
        if len(fixed1) == 1:
            out.append((key_of(fixed1[0]), w, night))
            continue
        uniq = [e for e in r["pals"]
                if not any(e["id"] in [x["id"] for x in r2["pals"]] for r2 in rows if r2 is not r)]
        if len(uniq) == 1:
            out.append((key_of(uniq[0]), w, night))
            continue
        for e in r["pals"]:                     # 不可定 -> 均分权重, 每只各占 1 格
            out.append((key_of(e), w / len(r["pals"]), night))
    return out


def trim_icon_units(units, n_slots, mimic_key="MimicDog"):
    """点位不足时腾位: ①移旺财 ②移仅夜间行。
    只要"单位数 > 格子数"就腾; 腾完即使少于格子数也没关系 (多出的格子按权重补给其它单位)。"""
    if len(units) <= n_slots:
        return units
    keep = [u for u in units if u[0] != mimic_key]
    if len(keep) < len(units):
        units = keep
    if len(units) > n_slots:
        keep = [u for u in units if not u[2]]
        if len(keep) < len(units):
            units = keep
    return units


def main():
    placement = load_rows(os.path.join(SPAWNER_DIR, "DT_PalSpawnerPlacement.json"))
    wild = load_rows(os.path.join(SPAWNER_DIR, "DT_PalWildSpawner.json"))

    # 帕鲁 -> 图鉴编号
    zukan = {}
    if os.path.exists(MONSTER_JSON):
        with open(MONSTER_JSON, encoding="utf-8") as f:
            mons = json.load(f)
        for pid, m in mons.items():
            zi = m.get("ZukanIndex", -1)
            if isinstance(zi, int) and zi > 0:
                zukan[pid] = zi

    wiki, wiki_lower = load_wiki()

    # wild: 按 SpawnerName 字段聚合 (一个 SpawnerName 有多行带权重的备选)
    wild_by_name = collections.defaultdict(list)
    row_weight_sum = collections.Counter()   # 兼容保留
    pool_all = collections.Counter()         # 每个刷怪器的权重总和 (整行计一次)
    pool_day = collections.Counter()         # 其中"无夜晚限制"部分的权重和
    for row_name, r in wild.items():
        w = r.get("Weight", 0.0)
        if w <= 0:
            continue  # 禁用占位行
        time = strip_enum(r.get("OnlyTime", ""))
        weather = strip_enum(r.get("OnlyWeather", ""))
        name = r["SpawnerName"]
        pool_all[name] += w                     # 全池: 夜晚可参与抽取的所有行
        if time != "Night":
            pool_day[name] += w                 # 白天池: 无夜晚限制的行
        for i in (1, 2, 3):
            pal = r.get(f"Pal_{i}", "None")
            npc = r.get(f"NPC_{i}", "None")
            if pal in ("None", "RowName", "", None) and npc in ("None", "", None):
                continue
            raw = pal if pal not in ("None", "RowName", "", None) else f"NPC:{npc}"
            base, badge = pal_meta(raw, wiki, wiki_lower)
            entry = {
                "id": raw,
                "b": base,          # wiki 基础 ID (用于查中文名/图标)
                "bg": badge,        # 变体标签 (首领/任务/后缀/NPC)
                "lv": [r.get(f"LvMin_{i}", 0), r.get(f"LvMax_{i}", 0)],
                "num": [r.get(f"NumMin_{i}", 0), r.get(f"NumMax_{i}", 0)],
                "w": w,
                "rn": row_name,     # 来源行 (合并时用于去重/求和, 输出前删除)
            }
            if time not in ("Undefined", ""):    entry["time"] = time
            if weather not in ("Undefined", ""): entry["weather"] = weather
            if r.get("bHasWorldTreeAura"):       entry["aura"] = 1  # 世界树光环: 觉醒帕鲁
            wild_by_name[name].append(entry)

    def zk_of(base, raw):
        """图鉴号: 优先用 wiki, 回退到 DT_PalMonsterParameter"""
        if base and base in wiki and wiki[base].get("zukan"):
            return wiki[base]["zukan"]
        return zukan.get(raw, 0)

    def merge_entries(entries, day_w, all_w):
        """同一帕鲁(同条件)的多条记录合并为一条。
        权重语义: 刷怪器按权重在"行"之间抽签, 同一帕鲁若出现在多行, 其被抽中的机会正比于
        这些行的权重【之和】(不是最大值); 同一行内重复出现只计一次。
        等级/数量取并集; rows 记录合并了几个行; 按权重降序 (同权重按图鉴号) 排序。
        占比分母按"同时段池": 夜晚限定行只在夜间参与抽取, 若把它们的权重算进白天分母,
        会系统性压低白天帕鲁的占比。故 白天可用者以白天池为分母, 夜晚限定者以全池为分母。"""
        out = {}
        for e in entries:
            key = (e["b"] or e["id"], e["bg"], e.get("time", ""), e.get("weather", ""), e.get("aura", 0))
            m = out.get(key)
            if m is None:
                out[key] = dict(e, lv=list(e["lv"]), num=list(e["num"]),
                                rows=1, rns={e["rn"]})
            else:
                if e["rn"] not in m["rns"]:        # 同一行内重复槽位不重复计权重
                    m["rns"].add(e["rn"])
                    m["w"] += e["w"]
                    m["rows"] += 1
                m["lv"][0] = min(m["lv"][0], e["lv"][0]); m["lv"][1] = max(m["lv"][1], e["lv"][1])
                m["num"][0] = min(m["num"][0], e["num"][0]); m["num"][1] = max(m["num"][1], e["num"][1])
        lst = list(out.values())
        mixed = all_w > day_w                   # 该刷怪器同时存在白天/夜晚行时才需要标注入池
        for e in lst:
            e.pop("rns", None); e.pop("rn", None)
            night = e.get("time") == "Night"
            base = all_w if night else day_w
            e["pct"] = round(e["w"] / base * 100, 1) if base else 0.0
            e["pb"] = ("夜间" if night else "白天") if mixed else ""
            e["z"] = zk_of(e["b"], e["id"])
        lst.sort(key=lambda e: (-e["w"], e["z"] or 999, e["id"]))
        return lst

    # ---- 帕鲁表按刷怪器名去重: 8253 个点位其实只有 ~372 种表, 避免每个点内嵌一份 ----
    tables = {}
    for name, entries in wild_by_name.items():
        tables[name] = merge_entries(entries, pool_day.get(name, 0), pool_all.get(name, 0))

    # ---- 抽签行表: 一个"行"就是一次抽签的结果(可能含多只, 如 1 首领 + n 同族小怪) ----
    # 前端以"行"为基本单位展示普通刷怪点: 每行列出该行包含的全部帕鲁与数量, 而不是按帕鲁汇总。
    def make_rows(entries, day_w, all_w):
        byrow = collections.defaultdict(list)
        for e in entries:
            byrow[e.get("rn", "")].append(e)
        out = []
        for rn, es in byrow.items():
            seen = set(); keep = []
            for e in es:                     # 同一行内重复槽位只保留一份 (极少见)
                if e["id"] in seen:
                    continue
                seen.add(e["id"]); keep.append(e)
            w = es[0]["w"]
            base = all_w if es[0].get("time") == "Night" else day_w
            out.append({
                "rn": rn, "w": w,
                "pct": round(w / base * 100, 1) if base else 0.0,
                "time": es[0].get("time", ""), "weather": es[0].get("weather", ""),
                "aura": es[0].get("aura", 0),
                "pals": [{"id": e["id"], "b": e["b"], "bg": e["bg"], "lv": e["lv"], "num": e["num"]}
                         for e in keep],
            })
        out.sort(key=lambda c: (-c["w"], c["rn"]))
        return out

    rows = {}
    for name, entries in wild_by_name.items():
        rs = make_rows(entries, pool_day.get(name, 0), pool_all.get(name, 0))
        if rs:
            rows[name] = rs
    n_multi = sum(1 for v in rows.values() for r in v if len(r["pals"]) > 1)
    print(f"  抽签行: {len(rows)} 个刷怪器, 共 {sum(len(v) for v in rows.values())} 行 "
          f"(其中多只成组 {n_multi} 行)")

    # ---- 地图归属: 帕洛斯群岛 / 世界树是两张独立底图 (同一世界坐标系的不同窗口) ----
    if os.path.exists(MAPS_JSON):
        map_cfg = json.load(open(MAPS_JSON, encoding="utf-8"))["maps"]
    else:   # 兜底: paldb 的 image/map8 覆盖范围
        map_cfg = [{"key": "palpagos", "label": "帕洛斯群岛",
                    "bounds": {"minX": -1099400.0, "maxX": 349400.0,
                               "minY": -724400.0, "maxY": 724400.0}}]

    def map_index(x, y):
        for i, m in enumerate(map_cfg):
            b = m["bounds"]
            if b["minX"] <= x <= b["maxX"] and b["minY"] <= y <= b["maxY"]:
                return i
        return 0    # 不在任何底图窗口内 -> 归入主图

    # ---- 底图叠放: 副图(世界树)以"左上角对齐"叠到主图(帕洛斯)上 ----
    # 两图导出比例一致 => 左上角对齐等价于世界坐标的一个纯平移:
    #   dx = 主图 maxX - 副图 maxX   (屏幕上向右为 +Y, 向上为 +X, 故西北角对齐即 maxX/minY 对齐)
    #   dy = 主图 minY - 副图 minY
    base = map_cfg[0]["bounds"]
    for i, m in enumerate(map_cfg):
        if i == 0:
            m["off"] = [0.0, 0.0]
            continue
        dx = base["maxX"] - m["bounds"]["maxX"]
        dy = base["minY"] - m["bounds"]["minY"]
        m["off"] = [dx, dy]
        b = m["bounds"]
        rx0, rx1 = b["minX"] + dx, b["maxX"] + dx
        ry0, ry1 = b["minY"] + dy, b["maxY"] + dy
        inside = (rx0 >= base["minX"] - 1 and rx1 <= base["maxX"] + 1 and
                  ry0 >= base["minY"] - 1 and ry1 <= base["maxY"] + 1)
        print(f"  底图叠放: {m['label']} 平移 dx={dx:.0f} dy={dy:.0f} cm "
              f"-> 占据主图 X[{rx0:.0f},{rx1:.0f}] Y[{ry0:.0f},{ry1:.0f}] "
              f"({'在主图范围内' if inside else '超出主图范围!'})")

    n_merged = 0
    points = []
    unmatched = 0
    for _, p in placement.items():
        name = p.get("SpawnerName", "None")
        loc = p["Location"]
        t = TYPE_MAP.get(p.get("SpawnerType", ""), ("?", p.get("SpawnerType", "?"), "#888"))
        layers = p.get("LayerNames") or []
        region = layers[0].replace("EnemySpawner_", "") if layers else name
        # 无刷怪表的点: 人类通缉犯(Mono/SquadNPCSpawnerBossBase) 或 残留 sheet
        nb = ""
        cls = (p.get("SpawnerClass") or {}).get("AssetPathName", "").split("/")[-1].split(".")[-1]
        if name not in tables:
            unmatched += 1
            m = NPC_BOSS_RE.search(cls)
            if m:
                nb = m.group(1)
                t = TYPE_MAP["EPalSpawnerBossNPC::Bounty"]
            else:
                t = TYPE_MAP["EPalSpawnerNoData::Deprecated"]
        pt = {
            "n": name,
            "r": region,
            "x": round(loc["X"], 1), "y": round(loc["Y"], 1), "z": round(loc["Z"] / 100, 1),
            "t": t[0],
            "m": map_index(loc["X"], loc["Y"]),
            "u": 1 if "Dungeon" in p.get("PlacementType", "") else 0,
            "rad": p.get("StaticRadius", 0),
            "cool": p.get("RespawnCoolTime", 0),
            "nb": nb,                     # 赏金首 NPC id (非赏金首为空)
        }
        if t[0] == "ND":
            pt["cls"] = cls                # 无数据点保留类名便于排查
        # 洞窟内部小怪点(PlacementType 含 Dungeon) 与洞窟Boss 同属"地下城"图层;
        # db: 是否洞窟Boss点 (用于地下城面板区分 Boss 池/小怪池; 两者 u 都是 1, 不能用 u 区分)
        pt["db"] = 1 if p.get("PlacementType", "").endswith("DungeonBoss") else 0
        if "Dungeon" in p.get("PlacementType", ""):
            pt["t"] = TYPE_MAP["EPalSpawnedCharacterType::RandomDungeonBoss"][0]
        points.append(pt)
    n_merged = sum(len(v) for v in wild_by_name.values()) - sum(len(v) for v in tables.values())

    # ---- 人类通缉犯(賞金首)资料: 名称/参数/图标 ----
    # 布点表的 SpawnerClass 资产名偶尔与"赏金首登记"不一致 (如资产名 ..._Believer_Fat_GatlingGun,
    # 而游戏 UI 的 DT_BossSpawnerLoactionData 在同坐标登记为 ..._Believer_Fat_GiantClub),
    # 故先按类名解析, 解析不到名称/图标时用同坐标的登记 id 纠正, 并以该表的 Level 作为等级。
    bounty = load_bounty(sorted({p["nb"] for p in points if p.get("nb")}))
    loc_idx = load_boss_spawner_loc()
    fixed = {}
    n_lv = 0
    for p in points:
        nb = p.get("nb")
        if not nb:
            continue
        e = nearest_loc(loc_idx, p["x"], p["y"])
        if e and e.get("id"):
            p["lv"] = e["level"]
            n_lv += 1
        b = bounty.get(nb) or {}
        if b.get("name") and b.get("icon"):
            continue
        if e and e["id"] and e["id"] != nb:       # 类名不可用 -> 以 UI 表登记为准
            fixed[nb] = e["id"]
            p["nb_orig"] = nb                      # 保留原始类名, 面板里注明
            p["nb"] = e["id"]
    if fixed:
        bounty.update(load_bounty(sorted(set(fixed.values()))))
        print(f"  赏金首类名纠正: {len(fixed)} 例 " +
              ", ".join(f"{k} -> {v}" for k, v in fixed.items()))
    n_nb = sum(1 for p in points if p["t"] == "NB")
    n_nd = sum(1 for p in points if p["t"] == "ND")
    named = sum(1 for p in points if p.get("nb") and bounty.get(p["nb"], {}).get("name"))
    iconed = sum(1 for p in points if p.get("nb") and bounty.get(p["nb"], {}).get("icon"))
    print(f"  人类通缉犯: {n_nb} 个点位, {len(bounty)} 种 NPC, 其中 {named} 个点有中文名, "
          f"{iconed} 个点有图标, {n_lv} 个点带等级; 无数据(残留 sheet)点位 {n_nd} 个")

    # ---- 钓点: 坐标来自 paldb (src/paldb/paldb_fishing_spots_all.json), 类型关联解包表 ----
    fish_types = load_fishing(wiki, wiki_lower, zk_of, pal_meta)
    n_fish = 0
    fish_unmatched = 0
    if fish_types and os.path.exists(FISH_SPOTS_JSON):
        fish_spots = json.load(open(FISH_SPOTS_JSON, encoding="utf-8"))
        for s in fish_spots:
            x, y = s["pos"]["X"], s["pos"]["Y"]
            href = s["href"]
            if href not in fish_types:
                fish_unmatched += 1
                continue
            points.append({
                "n": href,                       # 复用 n 字段存钓点类型 ID
                "r": "钓点",
                "x": round(x, 1), "y": round(y, 1), "z": round(s["pos"].get("Z", 0) / 100, 1),
                "t": "FR" if s["type"] == "Rare Fishing Spot" else "FC",
                "m": map_index(x, y),
                "u": 0, "rad": 0, "cool": 0,
            })
            n_fish += 1
        print(f"  钓点: {n_fish} 个 (未匹配类型 {fish_unmatched}), 类型表 {len(fish_types)} 种")

    # ---- 普通刷怪点的头像分配 ----
    # 原则: ①以"抽签行"为基本单位; ②先算出该刷怪器各头像的【数量】, 再用【固定种子】把头像
    # 随机分配到具体点位 —— 换种子只会改变位置, 不改变数量, 避免某只头像数量异常偏多。
    # ③名称不足时腾位: 先移旺财, 再移仅夜间行。
    ICON_SEED = 20251009                      # 固定种子 (改动会重排位置, 数量不变)
    NO_ICON_SPAWNERS = {"worldtree_9_55_WorldTreeAura"}   # 世界树觉醒池: 随机事件, 整片不画头像
    def _is_pal(e):
        return bool(e.get("b"))               # 归一化后能查到帕鲁条目 (不看 NPC_ 前缀)

    common_idx = collections.defaultdict(list)          # 刷怪器 -> 该刷怪器的普通点下标
    for i, p in enumerate(points):
        if p["t"] == "C" and not p["u"]:
            common_idx[p["n"]].append(i)

    icon_names, icon_pos = [], {}
    def icon_id(key):
        if key not in icon_pos:
            icon_pos[key] = len(icon_names)
            icon_names.append(key)
        return icon_pos[key]

    n_icon_pts = 0
    stats = {"spawners": 0, "units": 0, "trim_mimic": 0, "trim_night": 0, "truncated": 0,
             "no_icon": 0, "npc": 0, "split": 0, "night": 0}
    for name, idxs in common_idx.items():
        rs = rows.get(name) or []
        if not rs:
            continue
        stats["spawners"] += 1
        # 稳定顺序: 按 (底图, X, Y, Z) 排序, 与表内顺序无关
        idxs = sorted(idxs, key=lambda i: (points[i]["m"], points[i]["x"], points[i]["y"], points[i]["z"]))
        N = len(idxs)
        if name in NO_ICON_SPAWNERS:
            stats["no_icon"] += 1
            for i in idxs:
                points[i]["ii"] = -1
            continue
        flags = [r.get("time") == "Night" for r in rs]
        units0 = build_icon_units(rs, _is_pal)
        units = trim_icon_units(units0, N)
        if len(units) < len(units0):
            if any(u[0] == "MimicDog" for u in units0) and not any(u[0] == "MimicDog" for u in units):
                stats["trim_mimic"] += 1
            else:
                stats["trim_night"] += 1
        if len(units) > N:
            stats["truncated"] += 1
        stats["units"] += len(units)
        quota = allocate_icon_units(units, N)
        stats["npc"] += sum(1 for q in quota if q[0] == "NPC")
        stats["night"] += sum(1 for q in quota if q[2])
        rng = random.Random(ICON_SEED ^ zlib.crc32(name.encode("utf-8")))
        rng.shuffle(quota)                     # 只打乱位置, 数量已固定
        for i, u in zip(idxs, quota):
            points[i]["ii"] = icon_id(u[0])
            if u[2]:
                points[i]["ni"] = 1            # 该头像来自"仅夜间"行 -> 页面描蓝框
            n_icon_pts += 1
    print(f"  普通点头像: {n_icon_pts} 个点位已分配 ({len(icon_names)} 种头像) · "
          f"刷怪器 {stats['spawners']} 个 · 单位 {stats['units']} · NPC 占位 {stats['npc']} · "
          f"仅夜间(蓝框) {stats['night']} · "
          f"腾位(旺财 {stats['trim_mimic']} / 夜间 {stats['trim_night']}) · "
          f"截断 {stats['truncated']} · 整片跳过 {stats['no_icon']}")

    # ---- 洞窟位置索引: 同一洞口处 boss 表与小怪表在地图上坐标完全重合, 需按位置合并展示 ----
    # 每个洞口只保留一个"代表点"用于绘制 (db=1 的 Boss 点优先), 其余标 dd=1 由前端跳过绘制,
    # 但它们仍留在数据里供搜索/面板使用。
    dun_rank, dun_area = load_dungeon_meta()
    dungeons = {}
    for i, p in enumerate(points):
        if p["t"] != "DG":
            continue
        k = f'{p["m"]}:{int(p["x"] // 100)}:{int(p["y"] // 100)}'      # 1m 粒度 (与 JS Math.floor 一致)
        d = dungeons.setdefault(k, {"x": p["x"], "y": p["y"], "z": p["z"], "r": p["r"],
                                    "bosses": [], "minions": [], "idx": [],
                                    "pools": {"Boss": [], "Normal": [], "FishPal": [], "NPCHuman": []},
                                    "aname": ""})
        d["idx"].append(i)
        lst = d["bosses"] if p.get("db") else d["minions"]
        if p["n"] not in lst:
            lst.append(p["n"])
        rk = dun_rank.get(p["n"], "Boss" if p.get("db") else "Normal")
        pool = d["pools"].setdefault(rk, [])
        if p["n"] not in pool:
            pool.append(p["n"])
        an = dun_area.get(p["n"], ("", "", 0))[1]
        if an and not d["aname"]:
            d["aname"] = an
    n_dun_dup = 0
    for d in dungeons.values():
        rep = next((i for i in d["idx"] if points[i].get("db")), d["idx"][0])
        points[rep]["dr"] = 1                     # 代表点
        for i in d["idx"]:
            if i != rep:
                points[i]["dd"] = 1               # 重叠点: 不绘制
                n_dun_dup += 1
        d.pop("idx")
    print(f"  地下城点位: {sum(1 for p in points if p['t'] == 'DG')} 个点 -> 合并为 "
          f"{len(dungeons)} 个洞口标记 (并入 {n_dun_dup} 个重叠点)")
    named = sum(1 for v in dungeons.values() if v["aname"])
    print(f"  洞窟洞口: {len(dungeons)} 个位置 ({named} 个有中文名), "
          f"Boss表 {len({n for v in dungeons.values() for n in v['bosses']})} 种 / "
          f"小怪表 {len({n for v in dungeons.values() for n in v['minions']})} 种, "
          f"每处 {min(len(v['bosses'])+len(v['minions']) for v in dungeons.values())}"
          f"~{max(len(v['bosses'])+len(v['minions']) for v in dungeons.values())} 个刷怪器")

    # ---- 普通点按刷怪器图着色 (相邻不同刷怪器 => 不同色) ----
    # 节点 = (SpawnerName, 该刷怪器点集的空间连通片)。刷怪器对应一张实际刷怪表,
    # 是"实际刷什么"的基本单元 (同一 LayerName 下可能含多个刷怪器, 如 Area_SkyIsland)。
    # 算法: DSATUR (按邻居已用色数优先) + 冲突局部精修, 12 色可达零相邻冲突。
    # 不参与着色的点 (c=-1 灰): 洞窟内部点 (多副本叠放, 坐标无意义)。
    PALETTE = [
        "#4fc3f7", "#ffb74d", "#81c784", "#f06292", "#ba68c8", "#fff176",
        "#4db6ac", "#ff8a65", "#90a4ae", "#aed581", "#e57373", "#9575cd",
    ]
    NEUTRAL = "#8b949e"
    ADJ_T = 50000.0  # 邻接/连通阈值: 500m (厘米单位)
    common_idx = [i for i, p in enumerate(points) if p["t"] == "C" and not p["u"]]
    for i, p in enumerate(points):
        if p["t"] == "C" and p["u"]:
            p["c"] = -1

    def find(parent, a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a

    # 1) 每个刷怪器内部空间聚类 (同一刷怪器散布多处时拆成独立节点)
    by_spawner = collections.defaultdict(list)
    for i in common_idx:
        by_spawner[points[i]["n"]].append(i)
    key_of = {}   # point idx -> (spawner, cluster)
    keys = set()
    for g, idxs in by_spawner.items():
        parent = {i: i for i in idxs}
        grid = {}
        for i in idxs:
            p = points[i]
            gk = (int(p["x"] // ADJ_T), int(p["y"] // ADJ_T))
            grid.setdefault(gk, []).append(i)
        for i in idxs:
            p = points[i]
            gx, gy = int(p["x"] // ADJ_T), int(p["y"] // ADJ_T)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for j in grid.get((gx + dx, gy + dy), []):
                        if j <= i: continue
                        q = points[j]
                        if (p["x"] - q["x"]) ** 2 + (p["y"] - q["y"]) ** 2 < ADJ_T ** 2:
                            ra, rb = find(parent, i), find(parent, j)
                            if ra != rb: parent[ra] = rb
        for i in idxs:
            k = (g, find(parent, i))
            key_of[i] = k; keys.add(k)

    # 2) 全局空间哈希找跨刷怪器近邻点对 -> 邻接边
    grid = {}
    for i in common_idx:
        p = points[i]
        gk = (int(p["x"] // ADJ_T), int(p["y"] // ADJ_T))
        grid.setdefault(gk, []).append(i)
    adj = {k: set() for k in keys}
    for i in common_idx:
        p = points[i]
        gx, gy = int(p["x"] // ADJ_T), int(p["y"] // ADJ_T)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((gx + dx, gy + dy), []):
                    if j <= i: continue
                    q = points[j]
                    if p["n"] == q["n"]: continue
                    if (p["x"] - q["x"]) ** 2 + (p["y"] - q["y"]) ** 2 < ADJ_T ** 2:
                        a, b = key_of[i], key_of[j]
                        if a != b:
                            adj[a].add(b); adj[b].add(a)

    # 3) DSATUR 着色
    color = {}
    sat = {k: set() for k in keys}
    un = set(keys)
    while un:
        k = max(un, key=lambda k: (len(sat[k]), len(adj[k])))
        used = sat[k]
        c = next((c for c in range(len(PALETTE)) if c not in used), None)
        if c is None:
            cnt = collections.Counter(color[n] for n in adj[k] if n in color)
            c = min(range(len(PALETTE)), key=lambda c: cnt.get(c, 0))
        color[k] = c
        un.discard(k)
        for n in adj[k]:
            if n in un:
                sat[n].add(c)
    # 4) 局部精修: 冲突节点换到邻居未用的颜色
    for _ in range(200):
        conf = [k for k in keys if any(color[n] == color[k] for n in adj[k])]
        if not conf: break
        improved = False
        for k in sorted(conf, key=lambda k: -len(adj[k])):
            nb = {color[n] for n in adj[k]}
            free = [c for c in set(color.values()) if c not in nb]
            if free:
                color[k] = free[0]; improved = True
        if not improved: break

    conflicts = sum(1 for a in keys for b in adj[a] if color[a] == color[b]) // 2
    n_edges = sum(len(v) for v in adj.values()) // 2
    max_deg = max((len(v) for v in adj.values()), default=0)
    used_colors = len(set(color.values()))
    for i in common_idx:
        points[i]["c"] = color[key_of[i]]
    print(f"spawnerPatches={len(keys)} (from {len(by_spawner)} spawners) adjEdges={n_edges} "
          f"maxDegree={max_deg} colorsUsed={used_colors}/{len(PALETTE)} adjacentConflicts={conflicts}")

    # ---- 帕鲁名/图标表: 只内嵌实际用到的帕鲁 (刷怪表 + 钓点产出) ----
    used_bases = {e["b"] for lst in tables.values() for e in lst if e.get("b")}
    used_bases |= {e["b"] for v in fish_types.values() for e in v["rows"] if e.get("b")}
    pal_tbl = {}
    n_icon = 0
    for b in sorted(used_bases):
        v = wiki.get(b) or {}
        item = {"n": v.get("cn") or b, "z": zk_of(b, b), "e": (v.get("elem") or [""])[0]}
        icon = v.get("icon")
        if icon:
            path = os.path.join(ICON_DIR, icon)
            if os.path.exists(path):
                with open(path, "rb") as fh:
                    item["i"] = "data:image/webp;base64," + base64.b64encode(fh.read()).decode()
                n_icon += 1
        pal_tbl[b] = item

    xs = [p["x"] for p in points]; ys = [p["y"] for p in points]
    # 底图: 内嵌 4096 版本保证单文件自包含; 同名 8192 文件若与 HTML 同目录则运行时自动替换为高清
    maps_out = []
    for m in map_cfg:
        item = {"key": m["key"], "label": m["label"], "bounds": m["bounds"],
                "off": m.get("off", [0.0, 0.0]),      # 叠放平移量 (世界坐标 cm, 主图为 0)
                # 高清底图用相对路径引用: 与 HTML 同目录时自动加载, 缺失则退回内嵌 4096

                "embed": None, "size": 4096}
        f4 = os.path.join(MAPS_DIR, m.get("img4k", ""))
        if m.get("img4k") and os.path.exists(f4):
            with open(f4, "rb") as fh:
                item["embed"] = "data:image/webp;base64," + base64.b64encode(fh.read()).decode()
            print(f'  底图 {m["label"]}: 内嵌 maps/{m.get("img4k")} ({os.path.getsize(f4)/1e6:.2f} MB)')
        else:
            print(f'  底图 {m["label"]}: 未找到 maps/{m.get("img4k")}, 将仅显示网格')
        maps_out.append(item)

    data = {
        "maps": maps_out,
        "types": {k: {"code": v[0], "label": v[1], "color": v[2],
                      "off": 1 if v[0] in OFF_BY_DEFAULT else 0} for k, v in TYPE_MAP.items()},
        "palette": PALETTE,
        "pals": pal_tbl,
        "tables": tables,
        "fishing": fish_types,
        "bounty": bounty,
        "rows": rows,
        "icons": icon_names,
        "dungeons": dungeons,
        "points": points,
    }
    counts = collections.Counter(p["t"] for p in points)
    per_map = collections.Counter(p["m"] for p in points)
    print(f"points={len(points)}  byType={dict(counts)}  unmatchedSpawnerName={unmatched}")
    print("  按底图:" + "  ".join(f'{map_cfg[k]["label"]}={v}' for k, v in sorted(per_map.items())))
    print(f"pals={len(pal_tbl)} (icons={n_icon})  spawnerTables={len(tables)}  合并重复条目 {n_merged} 条")
    print(f"bounds X[{min(xs):.0f},{max(xs):.0f}] Y[{min(ys):.0f},{max(ys):.0f}]  (cm)")

    html = HTML_TEMPLATE.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"written: {OUT_HTML} ({os.path.getsize(OUT_HTML)/1e6:.1f} MB)")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>幻兽帕鲁 · 刷怪区域分布图</title>
<style>
  html,body{margin:0;height:100%;background:#0d1117;color:#c9d1d9;font:13px/1.5 "Segoe UI",sans-serif;overflow:hidden;overscroll-behavior:none}
  /* touch-action:none 让浏览器不再把画布上的双指操作当成"页面缩放", 改由下面的触控逻辑处理 */
  #cv{display:block;cursor:grab;touch-action:none;-webkit-tap-highlight-color:transparent}
  #cv.drag{cursor:grabbing}
  .panel{position:absolute;background:rgba(22,27,34,.92);border:1px solid #30363d;border-radius:8px;padding:10px 12px;backdrop-filter:blur(4px)}
  #ctrl{top:10px;left:10px;max-width:290px;max-height:calc(100vh - 20px);overflow:auto}
  #ctrlHead{display:flex;align-items:center;gap:8px;margin:0 0 6px}
  #ctgl{flex:0 0 auto;width:32px;height:32px;border-radius:50%;border:1px solid #30363d;background:#0d1117;
        color:#c9d1d9;font:16px/1 system-ui,sans-serif;cursor:pointer;padding:0}
  #ctgl:hover{border-color:#58a6ff;color:#58a6ff}
  #ctrl h1{font-size:14px;margin:0}
  /* 收起状态: 整个面板缩成左上角一个小圆点 (只留把手按钮) */
  #ctrl.collapsed{max-width:none;padding:6px;border-radius:50%;overflow:visible}
  #ctrl.collapsed #ctrlHead{margin:0}
  #ctrl.collapsed h1,#ctrl.collapsed #ctrlBody{display:none}
  #ctrl label{display:flex;align-items:center;gap:6px;margin:3px 0;cursor:pointer;user-select:none}
  .sw{width:10px;height:10px;border-radius:50%;display:inline-block}
  #search{width:100%;box-sizing:border-box;background:#0d1117;border:1px solid #30363d;border-radius:5px;color:#c9d1d9;padding:5px 8px;margin-top:6px}
  #stats{color:#8b949e;font-size:12px;margin-top:6px;white-space:pre-line}
  #detail{top:10px;right:10px;width:340px;max-height:80vh;overflow:auto;display:none}
  #detail h2{font-size:14px;margin:0 0 4px}
  #detail .sub{color:#8b949e;font-size:12px;margin-bottom:8px}
  #detail table{width:100%;border-collapse:collapse;font-size:12px}
  #detail td,#detail th{border-bottom:1px solid #21262d;padding:3px 4px;text-align:left}
  #tip{position:absolute;pointer-events:none;background:rgba(22,27,34,.95);border:1px solid #30363d;border-radius:5px;padding:4px 8px;font-size:12px;display:none;z-index:9}
  #closeX{position:absolute;top:6px;right:10px;cursor:pointer;color:#8b949e}
  .hit{color:#f0883e}
  /* 手机/窄屏: 控制面板收窄、把手加大便于手指点按, 详情面板改为贴底全宽 */
  @media (max-width: 700px){
    #ctrl{max-width:calc(100vw - 40px);font-size:12px}
    #ctrl h1{font-size:13px}
    #ctgl{width:40px;height:40px;font-size:19px}
    #detail{left:8px;right:8px;width:auto;top:auto;bottom:8px;max-height:52vh}
    #stats{font-size:11px}
  }
</style>
</head>
<body>
<canvas id="cv"></canvas>
<div id="tip"></div>
<div class="panel" id="ctrl">
  <div id="ctrlHead">
    <button id="ctgl" title="展开 / 收起控制面板" aria-label="展开或收起控制面板">☰</button>
    <h1>幻兽帕鲁 · 刷怪区域分布</h1>
  </div>
  <div id="ctrlBody">
    <div id="layers"></div>
    <label><input type="checkbox" id="ckRegion" checked> 普通点按刷怪器着色 (相邻不同色; 灰=洞窟内部)</label>
    <label><input type="checkbox" id="ckPalIcon" checked> 普通点显示帕鲁头像 (放大到位后自动启用)</label>
    <label><input type="checkbox" id="ckRadius"> 显示辅助圆 (填充, 便于放大后辨认点位)</label>
    <label style="display:block">辅助圆半径 <output id="radVal">25</output> m
      <input type="range" id="radRange" min="1" max="150" step="1" value="25" style="width:100%">
    </label>
    <label><input type="checkbox" id="ckGrid"> 显示公里网格</label>
    <input id="search" placeholder="搜索帕鲁: 中文名 / 英文ID / 图鉴号 / 属性">
    <div id="hits" style="color:#8b949e;font-size:11px;margin-top:4px"></div>
    <div id="stats"></div>
  </div>
</div>
<div class="panel" id="detail"><span id="closeX">✕</span><h2></h2><div class="sub"></div><div class="body"></div></div>
<script>
const DATA = /*__DATA__*/;
const cv = document.getElementById('cv'), ctx = cv.getContext('2d');
const tip = document.getElementById('tip'), detail = document.getElementById('detail');
const PTS = DATA.points, MAPS = DATA.maps, PALS = DATA.pals, TABLES = DATA.tables;
const FISH = DATA.fishing, BOUNTY = DATA.bounty, ROWS = DATA.rows, DUNGEONS = DATA.dungeons;
const EMPTY = [];
const palsOf = p => TABLES[p.n] || EMPTY;   // 帕鲁表按刷怪器名共享
const isFish = p => p.t === 'FC' || p.t === 'FR';
const isBounty = p => p.t === 'NB';
const fishOf = p => FISH[p.n] || null;      // 钓点类型 -> 可钓到的帕鲁
const bountyOf = p => (p.nb && BOUNTY[p.nb]) || null;   // 赏金首 NPC id -> 名称/图标/参数
const isDun = p => p.t === 'DG';   // 地下城点 (洞口处 boss 与小怪坐标重合, 已合并为单一图层)
const dkeyOf = p => p.m + ':' + Math.floor(p.x / 100) + ':' + Math.floor(p.y / 100);
const dungeonOf = p => (isDun(p) ? (DUNGEONS[dkeyOf(p)] || null) : null);

// ---- Boss 头像: 野外Boss/监禁Boss 用其帕鲁图标, 人类通缉犯用 NPC 图标 ----
const ICON_CACHE = new Map();
let iconRedrawPending = false;
function imgFor(src){
  if(!src) return null;
  let im=ICON_CACHE.get(src);
  if(im===undefined){
    im=new Image();
    im.onload=()=>{                        // 解码完成后重绘一次 (合并同一帧内的多次加载)
      if(iconRedrawPending) return;
      iconRedrawPending=true;
      requestAnimationFrame(()=>{ iconRedrawPending=false; draw(); });
    };
    im.src=src;
    ICON_CACHE.set(src, im);
  }
  return (im.complete && im.naturalWidth) ? im : null;
}
function bossIconSrc(p){
  if(isBounty(p)){ const b=bountyOf(p); return (b&&b.icon)||null; }
  if(p.t==='F' || p.t==='I'){
    const list=palsOf(p);
    const e=list.find(x=>x.bg)||list[0];    // 优先"首领"那条 (BOSS_ 前缀)
    const v=e&&e.b?PALS[e.b]:null;
    return (v&&v.i)||null;
  }
  return null;
}
const isIconBoss = p => p.t==='F' || p.t==='I' || p.t==='NB';

// ---- 普通点头像 (构建时已按"先算数量、再定位置(固定种子)"分配好, 见 build_spawner_map.py) ----
const ICON_KEY = DATA.icons;                 // 全局头像字典: 帕鲁基名 或 "NPC"
const PAL_ICON = {};                         // 帕鲁基名 -> 头像 data URI
for(const k in PALS){ if(PALS[k].i) PAL_ICON[k]=PALS[k].i; }
let palIconMode = true;                      // 复选框状态
let palIconsOn = false;                      // 本帧是否真的画头像 (由 LOD 决定)
const PAL_LOD_PX = 16;                       // 普通点头像小于此像素 -> 退回画点 (16 = 尺寸下限, 即只要在尺寸区间内就显示)
const PAL_LOD_MAX = 2500;                    // 同屏候选超过此数 -> 退回画点
// 描边配色: Boss(含人类通缉犯)=红框; 普通点中"仅夜间出现"的头像=蓝框; 其余白框。均先描一圈深色以压住任何底图
const RING_BOSS = '#ff4d4f', RING_NIGHT = '#4d9fff', RING_DAY = 'rgba(255,255,255,.72)', RING_HL = '#f0883e';
let spritePx = 0;                            // 精灵缓存对应的头像像素档
let spriteBudget = 0;                        // 每帧最多新建几个精灵 (避免换档瞬间长卡顿)
const SPRITES = new Map();                   // key -> 预渲染好的圆形头像画布
function spriteOf(key, px, night){
  const ck = key + (night ? '|n' : '');
  const c = SPRITES.get(ck);
  if(c) return c;
  if(spriteBudget <= 0) return null;         // 本帧预算用完 -> 先画点, 下一帧继续
  spriteBudget--;
  const S = Math.max(8, Math.round(px*dpr)), pad = Math.ceil(3*dpr);
  const cv2 = document.createElement('canvas');
  cv2.width = cv2.height = S + pad*2;
  const g = cv2.getContext('2d'), cx = cv2.width/2, cy = cv2.height/2, r = S/2;
  const ring = key === 'NPC' ? RING_DAY : (night ? RING_NIGHT : RING_DAY);
  if(key === 'NPC'){                         // 普通人类 NPC: 灰底占位符 (无图标素材)
    g.beginPath(); g.arc(cx,cy,r,0,7); g.fillStyle='#30363d'; g.fill();
    ringStroke(g, cx, cy, r, ring);
    g.fillStyle='#c9d1d9'; g.font=`bold ${Math.max(8, S*0.32)}px sans-serif`;
    g.textAlign='center'; g.textBaseline='middle'; g.fillText('NPC', cx, cy);
  } else {
    const im = PAL_ICON[key] ? imgFor(PAL_ICON[key]) : null;
    if(!im) return null;                     // 图未解码完 -> 本帧先画点, 解码后会自动重绘
    g.beginPath(); g.arc(cx,cy,r+1.4*dpr,0,7); g.fillStyle='rgba(13,17,23,.9)'; g.fill();
    ringStroke(g, cx, cy, r+1.4*dpr, ring);
    g.save(); g.beginPath(); g.arc(cx,cy,r,0,7); g.clip();
    g.drawImage(im, cx-r, cy-r, S, S); g.restore();
  }
  SPRITES.set(ck, cv2);
  return cv2;
}
function ringStroke(g, cx, cy, r, color){    // 深色底圈 + 彩色描边 (保证在任何底图上都清晰)
  g.beginPath(); g.arc(cx,cy,r,0,7);
  g.strokeStyle='rgba(0,0,0,.62)'; g.lineWidth=Math.max(2,3.2*dpr); g.stroke();
  g.beginPath(); g.arc(cx,cy,r,0,7);
  g.strokeStyle=color; g.lineWidth=Math.max(1,1.8*dpr); g.stroke();
}
// Boss 头像尺寸: 目标为"直径≈50m 的地图范围", 分段量化 (避免连续缩放时抖动) 并按像素上下限截断。
// 全图视野下 50m 只有几像素, 故下限 16px 保证可辨认; 放大后最大 96px。
const ICON_STEP = 8;                         // 尺寸量化步长 (两套尺寸共用)
const BOSS_M = 50,  BOSS_MIN = 16, BOSS_MAX = 96;    // Boss 头像: 50m / 16~96px
const PAL_M = 25,  PAL_MIN = 16,  PAL_MAX = 48;      // 普通点头像: 25m / 16~48px
function iconPxOf(m, lo, hi){
  const raw = m * 100 * view.s;              // 米(厘米) -> 像素
  const q = Math.round(Math.max(lo, Math.min(hi, raw)) / ICON_STEP) * ICON_STEP;
  return Math.max(lo, q);
}
const iconPxBoss = () => iconPxOf(BOSS_M, BOSS_MIN, BOSS_MAX);
const iconPxPal  = () => iconPxOf(PAL_M,  PAL_MIN,  PAL_MAX);
const TCOL = {}; for (const k in DATA.types) TCOL[DATA.types[k].code] = DATA.types[k].color;
const TLBL = {}; for (const k in DATA.types) TLBL[DATA.types[k].code] = DATA.types[k].label;
const PALETTE = DATA.palette; // 普通点区域着色调色板 (相邻区域保证不同色)
const ADJ_T_M = 500;         // 构建时的邻接/连通阈值 (米), 供参考
let regionColor = true;
let radM = 25;               // 辅助圆半径 (米), 纯显示用, 与表内 StaticRadius 无关
let lastIconPx = 0;          // 上次渲染的 Boss 头像像素尺寸 (用于检测分段变化)
let lastIconPxPal = 0;       // 上次渲染的普通点头像像素尺寸
let lastPalIcons = false;    // 上次渲染的"普通点头像是否生效" (用于检测 LOD 切换)
let ready = false;           // 初始化完成标志 (避免早期 onload 触发的 draw 访问未初始化状态)
const B = MAPS[0].bounds;    // 视图范围 = 主图的世界坐标范围 (副图叠在其内)
// 副图(世界树)以左上角对齐叠到主图上 —— 两图导出比例一致, 故等价于世界坐标的一个纯平移
const MOFF = MAPS.map(m => m.off || [0, 0]);
const pX = p => p.x + MOFF[p.m][0];
const pY = p => p.y + MOFF[p.m][1];
const PXY = p => w2s(pX(p), pY(p));
let showGrid = false;
const inCur = () => true;    // 叠放后所有点位同处一张图, 不再按底图过滤
const mapCountTxt = MAPS.map((m, i) => {
  const sub = PTS.filter(p => p.m === i);
  const sp = sub.filter(p => !isFish(p) && !p.dd).length, fi = sub.filter(p => isFish(p)).length;
  return `${sp} 刷怪 + ${fi} 钓点`;
});
function pointColor(p){
  if(p.t=='C' && regionColor) return (p.c!=null && p.c>=0) ? PALETTE[p.c] : '#8b949e'; // 灰=洞窟内部/零散点
  return TCOL[p.t];
}
// 帕鲁条目 -> 显示信息 (中文名优先, 回退内部ID)
function palInfo(e){
  const v = e.b ? PALS[e.b] : null;
  return {
    name: v ? v.n : e.id.replace(/^NPC:/,''),
    id: e.id,
    z: v ? v.z : (e.z||0),
    icon: v ? v.i : null,
    elem: v ? v.e : '',
  };
}

// ---- 视图状态: 世界坐标(厘米)。朝向按游戏内地图校准: 屏幕东=世界+Y, 屏幕北=世界+X ----
// (等价于旧布局逆时针旋转90°后再左右翻转)
let view = {cx:(B.minX+B.maxX)/2, cy:(B.minY+B.maxY)/2, s:1}; // cx:世界X中心(北), cy:世界Y中心(东)
let dpr = 1;
// ---- 底图: 主图 + 叠放的副图 (世界树叠在左上角空白区) ----
// 只用内嵌的 4096 版: 随 HTML 一起到达, 无额外请求、也不受网络状况影响
// (8192 高清版已弃用: 每个访客要多下 8.3MB, 而实际观感提升很有限)
const mapImgs = MAPS.map(m => {
  const im = new Image();
  if (m.embed) im.src = m.embed;
  return im;
});

function resize(){
  dpr = devicePixelRatio||1;
  cv.width = innerWidth*dpr; cv.height = innerHeight*dpr;
  cv.style.width = innerWidth+'px'; cv.style.height = innerHeight+'px';
}
function fit(){
  const m = 0.96;
  view.s = Math.min(innerWidth/(B.maxY-B.minY), innerHeight/(B.maxX-B.minX))*m;
  view.cx=(B.minX+B.maxX)/2; view.cy=(B.minY+B.maxY)/2;
}
function w2s(x,y){ // world(世界X=北, 世界Y=东) -> screen(px, CSS单位)
  return [(y-view.cy)*view.s + innerWidth/2, -(x-view.cx)*view.s + innerHeight/2];
}
function s2w(sx,sy){ // screen -> world [x,y]
  return [-(sy-innerHeight/2)/view.s+view.cx, (sx-innerWidth/2)/view.s+view.cy];
}

// ---- 过滤状态 ----
const show = {}; for (const k in DATA.types) show[DATA.types[k].code] = !DATA.types[k].off;   // off=1 的图层默认不显示
let showRadius=false, highlight=null; // highlight: Set(pointIndex)
const palHits = buildPalIndex();
function buildPalIndex(){
  // 键: 中文名 / 内部ID / 基础ID / 图鉴号 / 属性 —— 任一命中即高亮该点
  const idx = new Map();
  const put = (key,i)=>{ if(!key) return; key=String(key).toLowerCase();
    if(!idx.has(key)) idx.set(key,[]); idx.get(key).push(i); };
  PTS.forEach((p,i)=>{
    const list = isFish(p) ? ((fishOf(p)||{}).rows||EMPTY) : palsOf(p);
    for(const e of list){
      const v = e.b ? PALS[e.b] : null;
      put(e.id, i);
      if(v){ put(v.n, i); put(e.b, i); put(v.z, i); put(v.e, i); }
    }
  });
  return idx;
}

// ---- 交互 ----
let drag=null;
// 触屏设备没有真正的悬停, 关掉 hover 提示 (否则点击后可能留下残影)
const noHover = (typeof matchMedia==='function') && matchMedia('(hover: none)').matches;
cv.addEventListener('mousedown',e=>{drag={x:e.clientX,y:e.clientY};cv.classList.add('drag');});
addEventListener('mouseup',()=>{drag=null;cv.classList.remove('drag');});
addEventListener('mousemove',e=>{
  if(drag){
    view.cy -= (e.clientX-drag.x)/view.s;   // 屏幕横向 = 世界Y(东西)
    view.cx += (e.clientY-drag.y)/view.s;   // 屏幕纵向 = 世界X(南北)
    drag={x:e.clientX,y:e.clientY}; draw();
  } else if(!noHover) hover(e);
});
// 以屏幕点 (sx,sy) 为锚点缩放 k 倍: 锚点下的世界坐标保持不动
function zoomAt(sx, sy, k){
  const [wx,wy]=s2w(sx,sy);
  view.s=Math.min(Math.max(view.s*k,1e-5),2);
  // 反解: 让 (wx,wy) 仍落在 (sx,sy) —— w2s 为线性映射, 直接解出 cx/cy
  view.cy = wy - (sx - innerWidth/2)/view.s;
  view.cx = wx + (sy - innerHeight/2)/view.s;
}
cv.addEventListener('wheel',e=>{
  e.preventDefault();
  zoomAt(e.clientX, e.clientY, e.deltaY<0?1.2:1/1.2);
  draw();
},{passive:false});
cv.addEventListener('dblclick',()=>{fit();draw();});
cv.addEventListener('click',e=>{
  if(Date.now()-lastTouchTs<600) return;    // 触屏轻点已在 touchend 处理, 忽略补发的 click
  const hit=pick(e.clientX,e.clientY);
  if(hit>=0) showDetail(hit); else detail.style.display='none';
});
// ---- 触控: 单指拖动平移 / 双指捏合缩放 / 轻点查看点位 / 双击复位 ----
// (canvas 上已设 touch-action:none, 浏览器不会再把双指当成页面缩放)
let touch=null, lastTap=0, lastTapX=0, lastTapY=0, lastTouchTs=0;
function touchDist(a,b){ return Math.hypot(a.clientX-b.clientX, a.clientY-b.clientY); }
cv.addEventListener('touchstart',e=>{
  if(e.touches.length===1){
    const t=e.touches[0];
    touch={mode:'pan', x:t.clientX, y:t.clientY, moved:0, t0:Date.now()};
  }else if(e.touches.length>=2){
    const a=e.touches[0], b=e.touches[1];
    touch={mode:'pinch', d:touchDist(a,b), mx:(a.clientX+b.clientX)/2, my:(a.clientY+b.clientY)/2};
  }
  e.preventDefault();
},{passive:false});
cv.addEventListener('touchmove',e=>{
  if(touch && touch.mode==='pan' && e.touches.length===1){
    const t=e.touches[0];
    const dx=t.clientX-touch.x, dy=t.clientY-touch.y;
    touch.moved += Math.hypot(dx,dy);
    touch.x=t.clientX; touch.y=t.clientY;
    view.cy -= dx/view.s;                  // 屏幕横向 = 世界Y(东西)
    view.cx += dy/view.s;                  // 屏幕纵向 = 世界X(南北)
    draw();
  }else if(touch && touch.mode==='pinch' && e.touches.length>=2){
    const a=e.touches[0], b=e.touches[1];
    const d=touchDist(a,b), mx=(a.clientX+b.clientX)/2, my=(a.clientY+b.clientY)/2;
    if(touch.d>0) zoomAt(mx, my, d/touch.d);          // 以双指中点为锚点缩放
    view.cy -= (mx-touch.mx)/view.s;                  // 双指整体移动 = 平移
    view.cx += (my-touch.my)/view.s;
    touch.d=d; touch.mx=mx; touch.my=my;
    draw();
  }else if(e.touches.length===0){
    touch=null;
  }
  e.preventDefault();
},{passive:false});
cv.addEventListener('touchend',e=>{
  if(e.touches.length>0){                  // 还有手指按着 -> 按剩余手指数重置手势
    if(e.touches.length===1){
      const t=e.touches[0];
      touch={mode:'pan', x:t.clientX, y:t.clientY, moved:99, t0:Date.now()};
    }
  }else if(touch && touch.mode==='pan'){
    const t=e.changedTouches[0];
    const now=Date.now();
    lastTouchTs=now;                                   // 让补发的 click 被忽略
    if(touch.moved<12 && now-touch.t0<400){           // 轻点: 查看点位 / 双击: 复位
      if(now-lastTap<300 && Math.hypot(t.clientX-lastTapX, t.clientY-lastTapY)<24){
        fit(); detail.style.display='none'; lastTap=0;  // 双击复位 (并收起首次轻点打开的面板)
      }else{
        lastTap=now; lastTapX=t.clientX; lastTapY=t.clientY;
        const hit=pick(t.clientX, t.clientY, 18);       // 手指点击放宽判定半径
        if(hit>=0) showDetail(hit); else detail.style.display='none';
      }
    }
    touch=null;
  }else{
    touch=null;
  }
  e.preventDefault();
},{passive:false});
cv.addEventListener('touchcancel',()=>{touch=null;});
document.getElementById('closeX').onclick=()=>detail.style.display='none';
// ---- 控制面板折叠: 手机默认收起成左上角一个小圆点 (☰), 点一下展开 ----
const ctrlEl=document.getElementById('ctrl'), ctglEl=document.getElementById('ctgl');
function setCtrlCollapsed(v){
  ctrlEl.classList.toggle('collapsed', v);
  ctglEl.textContent = v ? '☰' : '✕';
  ctglEl.title = v ? '展开控制面板' : '收起控制面板';
}
// 窄屏/触屏默认收起 (面板会占满手机屏幕), 桌面默认展开
const ctrlDefaultCollapsed = (typeof matchMedia==='function') &&
  (matchMedia('(max-width: 700px)').matches || matchMedia('(hover: none)').matches);
setCtrlCollapsed(ctrlDefaultCollapsed);
ctglEl.onclick=()=>setCtrlCollapsed(!ctrlEl.classList.contains('collapsed'));
addEventListener('resize',()=>{resize();draw();});

function pick(mx,my,tolMin){
  // 按"到点距离 / 该点的判定半径"取最优: 头像点判定半径=图标半径, 普通点=10px
  // tolMin: 最小判定半径 (触屏用手指时放宽)
  let best=-1, bestScore=1.0;
  for(let i=0;i<PTS.length;i++){
    const p=PTS[i];
    if(!inCur(p)) continue;
    if(!show[p.t] || p.dd) continue;      // 地下城重叠点不参与拾取 (代表点会命中同一面板)
    const [sx,sy]=PXY(p);
    const d=Math.hypot(sx-mx,sy-my);
    const bIcon = isIconBoss(p) && bossIconSrc(p);
    const pIcon = palIconsOn && p.t==='C' && !p.u && p.ii!=null && p.ii>=0;
    const tol = Math.max(tolMin||0, bIcon ? iconPxBoss()/2 : (pIcon ? iconPxPal()/2 : 10));
    const score=d/tol;
    if(score<bestScore){ bestScore=score; best=i; }
  }
  return best;
}
function hover(e){
  const hit=pick(e.clientX,e.clientY);
  if(hit>=0){
    const p=PTS[hit];
    tip.style.display='block';
    tip.style.left=(e.clientX+12)+'px'; tip.style.top=(e.clientY+12)+'px';
    let palTxt;
    if(isBounty(p)){
      const b=bountyOf(p);
      tip.innerHTML=`<b>${esc((b&&b.name)||p.nb||'人类通缉犯')}</b><br>人类通缉犯${p.lv?' · Lv '+p.lv:''}${b&&b.bp?' · '+esc(b.bp):''}<br>`+
        `<span style="color:#6e7681">NPC ID: ${esc(p.nb||'-')}</span>`;
    } else if(dungeonOf(p)){
      const d=dungeonOf(p);
      tip.innerHTML=`<b>洞窟</b>（该洞口 ${d.bosses.length + d.minions.length} 个刷怪器）<br>`+
        `Boss 池 ${d.bosses.length} 种 · 小怪池 ${d.minions.length} 种<br>`+
        `<span style="color:#6e7681">点击查看可能的 Boss / 小怪</span>`;
    } else if(isFish(p)){
      const f=fishOf(p);
      const names=f?[...new Set(f.rows.map(x=>palInfo(x).name))]:[];
      palTxt=names.length?('可钓: '+names.slice(0,4).join('、')+(names.length>4?` 等${names.length}种`:'')):'(无产出表)';
      tip.innerHTML=`<b>${esc(p.n)}</b><br>${TLBL[p.t]}${f?` · 重生 ${f.respawn}s`:''}<br>${esc(palTxt)}`;
    } else {
      palTxt='(无刷怪表)';
      const list=palsOf(p);
      if(list.length){
        const names=[...new Set(list.map(x=>palInfo(x).name))];
        palTxt=names.slice(0,4).join('、')+(names.length>4?` 等${names.length}种`:'');
      }
      tip.innerHTML=`<b>${p.n}</b><br>${TLBL[p.t]} · ${p.r}<br>${esc(palTxt)}`;
    }
  } else tip.style.display='none';
}

// ---- 详情面板 ----
function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
function palCell(e, extra){
  const v=palInfo(e);
  const img=v.icon?`<img src="${v.icon}" width="26" height="26" style="vertical-align:middle;border-radius:50%;background:#21262d">`
                  :`<span style="display:inline-block;width:26px;height:26px;line-height:26px;text-align:center;
                     border-radius:50%;background:#21262d;color:#8b949e;font-size:11px;vertical-align:middle">${e.b?'?':'NPC'}</span>`;
  const badge=e.bg?`<span style="background:#30363d;color:#8b949e;border-radius:3px;padding:0 4px;font-size:10px;margin-left:4px">${esc(e.bg)}</span>`:'';
  return `<div style="display:flex;align-items:center;gap:6px">${img}
    <div style="min-width:0">
      <div>${v.z?'<span style="color:#8b949e">#'+v.z+'</span> ':''}<b>${esc(v.name)}</b>${badge}</div>
      <div style="color:#6e7681;font-size:10px;overflow:hidden;text-overflow:ellipsis">${esc(v.id)}${v.elem?' · '+esc(v.elem):''}${extra?' · '+esc(extra):''}</div>
    </div></div>`;
}
// ---- 抽签行表渲染 (公共): 一行 = 一次抽签的结果, 抽中后该行内容整组出现 ----
// names: 刷怪器名数组 (多个时按权重合并展示, 用于洞窟同一池的多个模板)
function rowTable(names, maxRows){
  const rows=[], seen=new Set();
  for(const nm of names){
    for(const c of (ROWS[nm]||EMPTY)){
      const sig=c.pals.map(x=>x.id+'x'+x.num[0]+'-'+x.num[1]).join('|')+'@'+c.w;
      if(seen.has(sig)) continue; seen.add(sig);   // 不同洞窟模板的同一行去重
      rows.push(c);
    }
  }
  if(!rows.length) return '';
  rows.sort((a,b)=>b.w-a.w);
  const lim=maxRows||80;
  let h='<table><tr><th>抽签行 (整组出现)</th><th>总只数</th><th>等级</th><th>权重</th></tr>';
  for(const c of rows.slice(0,lim)){
    let cells='', total=0; const lvs=[];
    for(const e of c.pals){
      const v=e.b?PALS[e.b]:null;
      const img=v&&v.i?`<img src="${v.i}" width="24" height="24" style="vertical-align:middle;border-radius:50%;background:#21262d">`:'';
      const cn=(v&&v.n)||e.id, n0=e.num[0], n1=e.num[1];
      cells+=`<div style="display:flex;align-items:center;gap:5px;margin:2px 0">${img}
        <span${e.bg?' style="color:#f0883e"':''}>${esc(cn)}${e.bg?'·'+esc(e.bg):''}</span>
        <span style="color:#6e7681">×${n0}${n0!=n1?'~'+n1:''}</span></div>`;
      total+=n1||n0; lvs.push(e.lv[0]+(e.lv[0]!=e.lv[1]?'~'+e.lv[1]:''));
    }
    const cond=[c.time,c.weather,c.aura?'✦世界树光环':''].filter(Boolean).join(' / ');
    h+=`<tr><td>${cells}</td><td>${total} 只</td><td>${lvs.join('<br>')}</td>`+
       `<td>${c.w}<span style="color:#6e7681"> (${c.pct}%)</span>`+
       `${cond?'<br><span style="color:#6e7681">'+esc(cond)+'</span>':''}</td></tr>`;
  }
  h+='</table>';
  if(rows.length>lim) h+=`<div style="color:#8b949e;font-size:11px">…共 ${rows.length} 行，已显示前 ${lim}</div>`;
  return h;
}

function showDetail(i){
  const p=PTS[i];
  detail.style.display='block';
  if(isBounty(p)) return showBountyDetail(p);
  if(dungeonOf(p)) return showDungeonDetail(p);
  if(isFish(p)) return showFishDetail(p);
  detail.querySelector('h2').textContent=p.r;  detail.querySelector('.sub').innerHTML=
    `${TLBL[p.t]} · 刷怪器 <code>${esc(p.n)}</code>${p.u?' · <span style="color:#bc8cff">地下</span>':''}<br>`+
    `坐标 X=${p.x.toFixed(0)} Y=${p.y.toFixed(0)} 高度 Z=${p.z}m · 表内 StaticRadius ${(p.rad/100).toFixed(0)}m (全表默认常量, 疑似弃用)`+
    (p.cool>0?` · 重生冷却 ${p.cool}s`:'');
  const list=palsOf(p);
  if(!list.length){
    detail.querySelector('.body').innerHTML=
      `<i>该刷怪器的刷怪表在当前版本数据中不存在</i><br><br>
       <span style="color:#8b949e;font-size:11px">刷怪器类 <code>${esc((p.cls||''))}</code>；
       这些 <code>BP_PalSpawner_Sheets_*</code> 只在 DT_PalSpawnerPlacement 中出现，
       DT_PalWildSpawner 等表中均无对应行——判断为 1.0 移除/未启用的残留 sheet。</span>`;
    return;
  }
  // 以"抽签行"为基本单位展示: 每行 = 一次抽签的结果, 抽中后该行内容整组一起出现
  const rows=ROWS[p.n]||EMPTY;
  const kinds=new Set();
  for(const r of rows) for(const e of r.pals) kinds.add(e.b||e.id);
  const multi=rows.filter(r=>r.pals.length>1).length;
  let h=`<div style="color:#8b949e;font-size:11px;margin-bottom:4px">
          <b>${rows.length}</b> 个抽签行 (涉及 ${kinds.size} 种帕鲁${multi?`, 其中 ${multi} 行会一次刷出多只`:''})，按权重降序<br>
          刷怪器按权重在行间抽签；抽中某行后，该行列出的帕鲁会<b>整组一起出现</b><br>
          占比分母: 白天可用的行用<b>白天池</b>, 夜晚限定的行用<b>全池</b></div>`;
  h+=rowTable([p.n], 200);
  detail.querySelector('.body').innerHTML=h;
}

// 人类通缉犯详情: 名称/图标/参数 + 坐标。点位来自 DT_PalSpawnerPlacement 的 Mono/SquadNPCSpawnerBossBase,
// 名称取自 DT_HumanNameText(zh-Hans), 参数取自 DT_PalHumanParameter, 图标取自 DT_PalBossNPCIcon
function showBountyDetail(p){
  const b=bountyOf(p)||{};
  detail.querySelector('h2').textContent=b.name||'人类通缉犯（无名称记录）';
  detail.querySelector('.sub').innerHTML=
    `<span style="color:${TCOL[p.t]}">▲</span> 人类通缉犯 (賞金首) · 世界坐标 X=${p.x.toFixed(0)} Y=${p.y.toFixed(0)} Z=${p.z}m`+
    (p.lv?` · <b>Lv ${p.lv}</b>`:'')+`<br>`+
    `NPC ID <code>${esc(p.nb||'-')}</code>${b.bp?' · BP <code>'+esc(b.bp)+'</code>':''}`;
  const img=b.icon?`<img src="${b.icon}" width="72" height="72" style="border-radius:8px;background:#21262d">`
                  :`<span style="display:inline-block;width:72px;height:72px;line-height:72px;text-align:center;
                     border-radius:8px;background:#21262d;color:#8b949e">无图标</span>`;
  let h=`<div style="display:flex;gap:10px;align-items:center;margin-bottom:8px">${img}
    <div>
      <div><b>${esc(b.name||'（游戏数据中无此 NPC 的名称条目）')}</b></div>
      <div style="color:#6e7681;font-size:11px">通缉犯点位：击败后可获得悬赏证明，与悬赏商人兑换</div>
      <div style="color:#6e7681;font-size:11px">刷怪器类: BP_${'Mono/Squad'}NPCSpawnerBossBase_${esc(p.nb_orig||p.nb||'')}</div>
    </div></div>`;
  if(p.nb_orig && p.nb_orig!==p.nb){
    // 布点资产名与赏金首登记不一致: 以 DT_BossSpawnerLoactionData 的同坐标登记为准
    h+=`<div style="color:#8b949e;font-size:11px">该点位的布点资产名为 <code>${esc(p.nb_orig)}</code>，
        但游戏 UI 表 <code>DT_BossSpawnerLoactionData</code> 在同一坐标登记的通缉犯是
        <code>${esc(p.nb)}</code>（Lv ${p.lv||'-'}），故名称/图标/等级按后者解析。</div>`;
  }
  if(!b.name){
    h+=`<div style="color:#8b949e;font-size:11px">该点位引用的 NPC id 在 DT_HumanNameText_Common /
        DT_PalHumanParameter / DT_PalBossNPCIcon 中均无对应条目，故无名称与图标。</div>`;
  }
  detail.querySelector('.body').innerHTML=h;
}

// 洞窟详情: 洞口处 Boss 点与小怪点坐标完全重合, 故按位置合并展示两个池
// Boss 池以"组合"呈现 (一行 = 一次抽签: 1 boss + n 同族小怪), 小怪池按帕鲁合并
function showDungeonDetail(p){
  const d=dungeonOf(p);
  // 官方分类 (DT_DungeonEnemySpawnDataTable 的 RankType) 归并为面板分区:
  // Boss/MidBoss 指向同一批刷怪器 (既作中Boss又作最终Boss); Normal02.. 是额外小怪池; Monster = *_monsteronly
  const SEC=[
    {name:'洞窟 Boss', ranks:['Boss','MidBoss'], note:'每行一种组合，抽中后整组一起出现；含中层首领', combo:true},
    {name:'洞窟小怪', ranks:['Normal','Normal02','Normal03','Normal04'], note:''},
    {name:'洞窟怪物池 (monsteronly)', ranks:['Monster'], note:''},
    {name:'洞窟内的人类 NPC', ranks:['NPCHuman'], note:''},
    {name:'洞窟内的钓点帕鲁', ranks:['FishPal'], note:'该洞窟内有钓点（洞窟内钓点位置未标注在地图上）'},
  ];
  const pools=d.pools||{};
  const used=new Set();
  const secs=SEC.map(s=>({...s, list:[...(s.ranks.flatMap(r=>pools[r]||[]))]}));
  // 表里出现但未列入 SEC 的分类, 原样展示, 避免漏显示
  for(const rk of Object.keys(pools)){
    if(SEC.some(s=>s.ranks.includes(rk))) continue;
    secs.push({name:rk, ranks:[rk], note:'', list:[...(pools[rk]||[])]});
  }
  for(const s of secs){ s.list=[...new Set(s.list)]; }

  detail.querySelector('h2').textContent='洞窟 · '+(d.aname||d.r||'');
  detail.querySelector('.sub').innerHTML=
    `洞口坐标 X=${d.x.toFixed(0)} Y=${d.y.toFixed(0)} Z=${d.z}m<br>`+
    `该处共 <b>${d.bosses.length + d.minions.length}</b> 个刷怪器`+
    `<span style="color:#6e7681">（Boss 点与小怪点在地图上坐标完全重合，已按位置合并；
     分类取自 DT_DungeonEnemySpawnDataTable 的 RankType）</span>`;

  let h='', any=false;
  for(const s of secs){
    if(!s.list.length) continue;
    any=true;
    h+=`<div style="margin:10px 0 4px;font-weight:bold;border-top:1px solid #21262d;padding-top:8px">◆ ${s.name} `+
       `<span style="color:#6e7681;font-weight:normal">(${s.list.length} 个刷怪器${s.note?' · '+s.note:''})</span></div>`;
    if(s.combo){
      // Boss 池: 以抽签行为单位列出 (含单只行)
      h+=rowTable(s.list, 80);
    } else {
      const mm=new Map();
      for(const nm of s.list){
        for(const e of (TABLES[nm]||EMPTY)){
          const k=e.b||e.id, m=mm.get(k);
          if(!m) mm.set(k,{e, lv:[...e.lv], num:[...e.num], tpl:1});
          else{
            m.lv[0]=Math.min(m.lv[0],e.lv[0]); m.lv[1]=Math.max(m.lv[1],e.lv[1]);
            m.num[0]=Math.min(m.num[0],e.num[0]); m.num[1]=Math.max(m.num[1],e.num[1]);
            m.tpl++;
          }
        }
      }
      if(!mm.size){ h+='<i style="color:#8b949e">（无数据）</i>'; continue; }
      h+='<table><tr><th>帕鲁</th><th>等级</th><th>数量</th><th>洞窟模板</th></tr>';
      for(const {e,lv,num,tpl} of mm.values()){
        h+=`<tr><td>${palCell(e)}</td><td>${lv[0]}${lv[0]!=lv[1]?'~'+lv[1]:''}</td>`+
           `<td>${num[0]}${num[0]!=num[1]?'~'+num[1]:''}</td><td>${tpl} 个</td></tr>`;
      }
      h+='</table>';
    }
  }
  detail.querySelector('.body').innerHTML = any ? h : '<i>无数据</i>';
}

function showFishDetail(p){
  const f=fishOf(p);
  detail.querySelector('h2').textContent=p.n;
  detail.querySelector('.sub').innerHTML=
    `<span style="color:${TCOL[p.t]}">●</span> ${TLBL[p.t]} · 世界坐标 X=${p.x.toFixed(0)} Y=${p.y.toFixed(0)} Z=${p.z}m<br>`+
    (f?`重生时间 ${f.respawn}s · 可钓到 <b>${f.rows.length}</b> 种帕鲁`:'<i>未找到该类型的产出表</i>');
  if(!f){detail.querySelector('.body').innerHTML='';return;}
  let h=`<div style="color:#8b949e;font-size:11px;margin-bottom:4px">
          按权重降序; 占比 = 该条权重 / 本类型权重总和。鱼影(Boss) 为同种帕鲁的强化个体。<br>
          数据链: 钓点类型 → 抽签表 → 鱼影表 → 帕鲁</div>`;
  h+='<table><tr><th>帕鲁 (鱼影)</th><th>等级</th><th>权重</th><th>难度</th><th>掉落组</th></tr>';
  for(const e of f.rows){
    const lv=e.lv[0]+(e.lv[0]!=e.lv[1]?'~'+e.lv[1]:'');
    const wp=`${e.w}<span style="color:#6e7681"> (${e.pct}%)</span>`;
    // 同一帕鲁可能有多种鱼影 (普通/首领/稀有 或不同尺寸), 故显示鱼影 ID 以区分
    const shadow=(e.shadow||'').replace('FishShadow_','');
    h+=`<tr><td>${palCell(e, shadow)}</td><td>${lv}</td><td>${wp}</td><td>${esc(e.dif||'-')}</td>`+
       `<td style="color:#6e7681;font-size:11px">${esc(e.drop||'-')}</td></tr>`;
  }
  detail.querySelector('.body').innerHTML=h+'</table>';
}

// ---- 搜索高亮 (支持 中文名 / 内部ID / 图鉴号 / 属性) ----
document.getElementById('search').addEventListener('input',e=>{
  const q=e.target.value.trim().toLowerCase();
  highlight=null;
  const hitsBox=document.getElementById('hits');
  if(q){
    const set=new Set(), names=new Map();
    PTS.forEach((p,i)=>{
      const list = isFish(p) ? ((fishOf(p)||{}).rows||EMPTY) : palsOf(p);
      for(const en of list){
        const v=en.b?PALS[en.b]:null;
        const key=[en.id, v&&v.n, en.b, v&&v.z, v&&v.e].filter(x=>x!=null&&x!=='').join('|').toLowerCase();
        if(key.includes(q)){ set.add(i); names.set(en.b||en.id, (v&&v.n)||en.id.replace(/^NPC:/,'')); }
      }
    });
    highlight=set;
    const arr=[...names.values()];
    const here=[...set].filter(i=>inCur(PTS[i])).length;
    hitsBox.innerHTML = arr.length
      ? `匹配 <b>${arr.length}</b> 种帕鲁 · ${set.size} 个点位 (本图 ${here})<br>` +
        arr.slice(0,14).map(esc).join('、') + (arr.length>14?` 等`:``)
      : '<span style="color:#f85149">无匹配</span>';
  } else hitsBox.innerHTML='';
  draw(); updateStats();
});

// ---- 图层控件 ----
(function(){
  const box=document.getElementById('layers');
  for(const k in DATA.types){
    const t=DATA.types[k];
    const lb=document.createElement('label');
    lb.innerHTML=`<input type="checkbox" ${t.off?'':'checked'} data-c="${t.code}"><span class="sw" style="background:${t.color}"></span>${t.label}`;
    lb.querySelector('input').onchange=ev=>{show[ev.target.dataset.c]=ev.target.checked;draw();updateStats();};
    box.appendChild(lb);
  }
  document.getElementById('ckRegion').onchange=e=>{regionColor=e.target.checked;draw();};
  document.getElementById('ckPalIcon').onchange=e=>{palIconMode=e.target.checked;SPRITES.clear();draw();};
  document.getElementById('ckRadius').onchange=e=>{showRadius=e.target.checked;draw();};
  document.getElementById('radRange').oninput=e=>{
    radM=+e.target.value; document.getElementById('radVal').textContent=radM; draw();
  };
  document.getElementById('ckGrid').onchange=e=>{showGrid=e.target.checked;draw();};
})();

function updateStats(){
  const c={}; for(const k in DATA.types) c[DATA.types[k].code]=0;
  let n=0, tot=0;
  PTS.forEach((p,i)=>{ if(!inCur(p))return;
    tot++;
    if(!show[p.t]||p.dd)return;
    if(highlight&&!highlight.has(i))return; c[p.t]++; n++; });
  const parts=[];
  for(const k in DATA.types){
    const t=DATA.types[k];
    if(t.code==='FC'||t.code==='FR') continue;
    parts.push(`${t.label} ${c[t.code]}`);
  }
  document.getElementById('stats').innerHTML=
    `显示 ${n} / ${tot} 个标记`+
    (MAPS.length>1?`（${MAPS.map((m,i)=>`${m.label} ${mapCountTxt[i]}`).join(' · ')}）`:'')+`\n`+
    parts.join(' · ')+
    `\n普通钓点 ${c.FC} · 稀有钓点 ${c.FR}`+
    (show['ND']?`\n无数据(残留 sheet) ${c.ND}`:`\n<span style="color:#6e7681">无数据图层已隐藏 (${c.ND} 个)</span>`)+
    `\n<span style="color:#6e7681">Boss 头像 ${BOSS_M}m→${iconPxBoss()}px (${BOSS_MIN}~${BOSS_MAX})</span>`+
    `\n<span style="color:#6e7681">普通点头像 ${PAL_M}m→${iconPxPal()}px (${PAL_MIN}~${PAL_MAX}): `+
    `${palIconMode?(palIconsOn?'显示中':`已开启, 放大到位后显示 (需 ≥${PAL_LOD_PX}px 且同屏 ≤${PAL_LOD_MAX} 个)`):'已关闭'}</span>`;
}

// ---- 渲染 ----
function drawBg(){
  // 按顺序绘制所有底图: 主图(帕洛斯) 打底, 副图(世界树) 按左上角对齐叠在其空白区
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  for(let i=0;i<MAPS.length;i++){
    const im = mapImgs[i];
    if(!im || !im.complete || !im.naturalWidth) continue;
    const b = MAPS[i].bounds, o = MOFF[i];
    // 底图左上角 = 世界北界(maxX)+西界(minY); 屏幕上 x 向右为东, y 向下为南
    const [x0,y0] = w2s(b.maxX + o[0], b.minY + o[1]);
    const [x1,y1] = w2s(b.minX + o[0], b.maxY + o[1]);
    ctx.drawImage(im, x0*dpr, y0*dpr, (x1-x0)*dpr, (y1-y0)*dpr);
  }
}
function drawGrid(){
  ctx.strokeStyle='#ffffff22'; ctx.fillStyle='#58a6ff';
  ctx.lineWidth=1; ctx.font='11px sans-serif'; ctx.textAlign='left';
  const step=100000; // 1km
  const [wminx,wminy]=s2w(0,innerHeight), [wmaxx,wmaxy]=s2w(innerWidth,0);
  for(let y=Math.floor(wminy/step)*step;y<=wmaxy;y+=step){ // 竖线 = 世界Y(东西向)等距
    const [sx]=w2s(0,y);
    ctx.beginPath();ctx.moveTo(sx*dpr,0);ctx.lineTo(sx*dpr,innerHeight*dpr);ctx.stroke();
    if(view.s>3e-5) ctx.fillText('E'+(y/100000).toFixed(0)+'km', sx*dpr+3, innerHeight*dpr-6);
  }
  for(let x=Math.floor(wminx/step)*step;x<=wmaxx;x+=step){ // 横线 = 世界X(南北向)等距
    const [,sy]=w2s(x,0);
    ctx.beginPath();ctx.moveTo(0,sy*dpr);ctx.lineTo(innerWidth*dpr,sy*dpr);ctx.stroke();
    if(view.s>3e-5) ctx.fillText('N'+(x/100000).toFixed(0)+'km', 4, sy*dpr-4);
  }
  ctx.textAlign='left';
}
function drawCompass(){
  ctx.save();ctx.translate(innerWidth*dpr-40*dpr,60*dpr);
  ctx.fillStyle='#8b949e';ctx.font='bold 14px sans-serif';ctx.textAlign='center';
  ctx.beginPath();ctx.moveTo(0,-14*dpr);ctx.lineTo(6*dpr,8*dpr);ctx.lineTo(-6*dpr,8*dpr);ctx.closePath();ctx.fill();
  ctx.fillText('N',0,-20*dpr);ctx.restore();
  ctx.textAlign='left';
}

function draw(){
  if(!ready) return;                         // 初始化未完成时(如图片早期 onload)不绘制
  ctx.setTransform(1,0,0,1,0,0);
  ctx.fillStyle='#0a1a24';ctx.fillRect(0,0,cv.width,cv.height);
  if(iconPxBoss()!==lastIconPx || iconPxPal()!==lastIconPxPal){        // 尺寸分段变化时刷新统计行
    lastIconPx=iconPxBoss(); lastIconPxPal=iconPxPal(); updateStats();
  }
  drawBg();
  if(showGrid) drawGrid();
  drawCompass();
  const dim = highlight?0.12:1;
  // 辅助圆 (世界单位, 半透明填充; 先画, 点盖在上面)
  if(showRadius){
    // 纯显示辅助: 半径由用户自定义, 与表内 StaticRadius 无关 (那是全表默认常量, 疑似弃用)。
    // 按颜色分组 -> 每组所有圆放进同一条路径只 fill 一次, 重叠处不会因反复叠加而变不透明。
    const R = radM*100;
    const groups = new Map();
    for(let i=0;i<PTS.length;i++){
      const p=PTS[i];
      if(!inCur(p))continue;
      if(!show[p.t]||p.dd)continue;
      if(highlight && !highlight.has(i))continue;
      const [sx,sy]=PXY(p), r=R*view.s*dpr;
      if(r<1.5)continue;                      // 放大到可辨认才画
      const col=pointColor(p);
      let arr=groups.get(col);
      if(!arr) groups.set(col, arr=[]);
      arr.push([sx*dpr,sy*dpr,r]);
    }
    ctx.globalAlpha = 0.5;                    // 50% 透明填充
    for(const [col,arr] of groups){
      ctx.beginPath();
      for(const [x,y,r] of arr){ ctx.moveTo(x+r,y); ctx.arc(x,y,r,0,7); }
      ctx.fillStyle = col;
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }
  // 普通点头像的 LOD: 头像太小或同屏候选太多时退回画点 (避免几千个图标逐帧 blit)
  spriteBudget = 48;                         // 每帧最多新建 48 个精灵
  {
    let cand = 0;
    if(palIconMode){
      for(let i=0;i<PTS.length;i++){
        const p=PTS[i];
        if(p.t!=='C'||p.u||p.dd||p.ii==null||p.ii<0||!show[p.t]) continue;
        if(!inCur(p)) continue;
        const [sx,sy]=PXY(p);
        if(sx<-40||sy<-40||sx>innerWidth+40||sy>innerHeight+40) continue;
        if(++cand > PAL_LOD_MAX) break;
      }
    }
    const want = palIconMode && iconPxPal()>=PAL_LOD_PX && cand<=PAL_LOD_MAX;
    if(want && (!palIconsOn || spritePx!==iconPxPal())){ SPRITES.clear(); spritePx=iconPxPal(); }
    palIconsOn = want;
    if(palIconsOn!==lastPalIcons){ lastPalIcons=palIconsOn; updateStats(); }   // LOD 切换时刷新统计行
  }
  // 点 (四遍: 洞窟小怪 → 普通点 → 普通点头像 → Boss 头像, 保证头像压在最上层)
  for(let pass=0; pass<4; pass++){
  for(let i=0;i<PTS.length;i++){
    const p=PTS[i];
    if(!inCur(p))continue;
    const bsrc = isIconBoss(p) ? bossIconSrc(p) : null;
    const palIcon = palIconsOn && p.t==='C' && !p.u && p.ii!=null && p.ii>=0;
    const wantPass = p.t==='DG' ? 0 : (bsrc ? 3 : (palIcon ? 2 : 1));
    if(pass!==wantPass) continue;
    if(!show[p.t]||p.dd)continue;
    const [sx,sy]=PXY(p);
    const ipx = bsrc ? iconPxBoss() : iconPxPal();      // 两套尺寸各自独立
    if(sx<-ipx||sy<-ipx||sx>innerWidth+ipx||sy>innerHeight+ipx)continue;   // 头像余量随尺寸变化
    const hl=highlight&&highlight.has(i);
    if(palIcon){                               // 普通点头像 (预渲染精灵, 直接 blit)
      const sp=spriteOf(ICON_KEY[p.ii], ipx, p.ni);
      if(sp){
        ctx.globalAlpha = hl?1:dim;
        ctx.drawImage(sp, sx*dpr-sp.width/2, sy*dpr-sp.height/2);
        if(hl){
          ctx.beginPath(); ctx.arc(sx*dpr, sy*dpr, sp.width/2-1*dpr, 0, 7);
          ctx.strokeStyle='#f0883e'; ctx.lineWidth=3*dpr; ctx.stroke();
        }
        ctx.globalAlpha=1;
        continue;
      }                                        // 图标未就绪 -> 本帧退回画点
    }
    ctx.globalAlpha=hl?1:dim;
    ctx.fillStyle=hl?'#f0883e':pointColor(p);
    const fish=isFish(p);
    const rad=(fish?3.2:(p.t=='C'?2.2:4.5))*dpr;
    const bimg = isIconBoss(p) ? imgFor(bossIconSrc(p)) : null;
    if(bimg){                                  // Boss 头像 (红框; 圆形裁剪 + 底衬)
      const sz=ipx*dpr, r=sz/2, x=sx*dpr, y=sy*dpr;
      ctx.beginPath(); ctx.arc(x,y,r+1.4*dpr,0,7);
      ctx.fillStyle='rgba(13,17,23,.9)'; ctx.fill();
      ringStroke(ctx, x, y, r+1.4*dpr, hl?RING_HL:RING_BOSS);
      if(hl){ ctx.beginPath(); ctx.arc(x,y,r+0.6*dpr,0,7); ctx.strokeStyle=RING_HL; ctx.lineWidth=2*dpr; ctx.stroke(); }
      ctx.save();
      ctx.beginPath(); ctx.arc(x,y,r,0,7); ctx.clip();
      ctx.drawImage(bimg, x-r, y-r, sz, sz);
      ctx.restore();
      ctx.globalAlpha=1;
      continue;
    }
    if(isBounty(p)){                           // 人类通缉犯 (无图标时回退三角)
      const r=rad*1.5;
      ctx.beginPath();
      ctx.moveTo(sx*dpr, sy*dpr-r); ctx.lineTo(sx*dpr+r*0.9, sy*dpr+r*0.75);
      ctx.lineTo(sx*dpr-r*0.9, sy*dpr+r*0.75); ctx.closePath();
      ctx.fill();
      ctx.strokeStyle='rgba(0,0,0,.7)'; ctx.lineWidth=1*dpr; ctx.stroke();
    } else if(p.t=='ND'){                      // 无数据: 空心小方
      const r=rad*0.9;
      ctx.strokeStyle=hl?'#f0883e':'#8b949e'; ctx.lineWidth=1.2*dpr;
      ctx.strokeRect(sx*dpr-r, sy*dpr-r, r*2, r*2);
    } else if(fish){                           // 钓点: 菱形
      ctx.save();
      ctx.translate(sx*dpr,sy*dpr); ctx.rotate(Math.PI/4);
      ctx.fillRect(-rad,-rad,rad*2,rad*2);
      ctx.strokeStyle='rgba(0,0,0,.65)'; ctx.lineWidth=1*dpr;
      ctx.strokeRect(-rad,-rad,rad*2,rad*2);
      ctx.restore();
    } else if(p.t=='DG'){                      // 地下城: 紫色圆点 + 深色描边 (每个洞口只有一个代表标记)
      ctx.beginPath(); ctx.arc(sx*dpr,sy*dpr,rad*1.15,0,7); ctx.fill();
      ctx.strokeStyle=hl?'#f0883e':'rgba(0,0,0,.75)'; ctx.lineWidth=1.4*dpr; ctx.stroke();
    }else{
      ctx.beginPath();ctx.arc(sx*dpr,sy*dpr,rad,0,7);ctx.fill();
    }
  }
  }
  ctx.globalAlpha=1;
}

// 初始化时从 DOM 复选框回读状态, 避免"界面已勾选但 JS 变量为 false"这类不一致
(function syncFromUI(){
  showRadius  = document.getElementById('ckRadius').checked;
  regionColor = document.getElementById('ckRegion').checked;
  palIconMode = document.getElementById('ckPalIcon').checked;
  showGrid    = document.getElementById('ckGrid').checked;
  document.querySelectorAll('#layers input[data-c]').forEach(el=>{ show[el.dataset.c]=el.checked; });
})();

ready = true;                // 初始化完成, 之后允许绘制
resize(); fit(); updateStats(); draw();

addEventListener('load', draw);   // 内嵌底图解码完成后重绘一次
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
