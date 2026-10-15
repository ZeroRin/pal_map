# 幻兽帕鲁 · 刷怪区域分布图

把解包得到的刷怪数据表（`DT_PalSpawnerPlacement` / `DT_PalWildSpawner`）与钓点数据可视化到真实地图上：
每个刷怪点的位置、类型、刷怪表（帕鲁中文名 / 图标 / 等级 / 数量 / 权重占比 / 昼夜条件），
以及钓点位置与其可钓到的帕鲁，都能在网页里查看与检索。

- 在线查看：<https://zerorin.github.io/pal_spawner_map/>
- 单文件分享：只需要 `pal_spawner_map.html`（6.8 MB，内嵌全部数据与 4096 底图）
- 重新构建：`python build_spawner_map.py`（需要 `src/` 里的解包数据表与 `maps/` 底图）

> 数据与素材版权归 Pocketpair 所有，本仓库只做**数据可视化**，不分发游戏本体资源。

## 仓库结构

```
pal_spawner_map.html        成品页面 (自包含, 双击即用)
index.html                  GitHub Pages 入口 (跳转到上面的页面)
build_spawner_map.py        构建脚本: 读 src/ + maps/ -> 生成 HTML
maps/                       底图 (4096 会被内嵌进 HTML; 8192 仅供出图脚本使用)
src/                        解包数据表、图标素材、paldb 存档、底图瓦片
tools/                      抓取/解析/校验/导出脚本 (见文末清单)
docs/                       分析记录 (如点位不足清单)
export/                     静态 PNG 导出结果 (git 忽略, 可用 tools/export_png.py 重建)
```

## 怎么用

**双击 `pal_spawner_map.html` 即可**（无需服务器、无需联网）。
页面已内嵌两张 4096 底图与 288 只帕鲁图标，单文件就能跑（约 7 MB）；
底图用的是**内嵌的 4096 版**（随 HTML 一起到达，无额外请求）。
`maps/*_8192.webp` 高清版**页面已不再加载**（每个访客要多下 8.3 MB，实际观感提升有限），
那两张文件只作为 `tools/export_png.py` 出静态图时的源图保留在仓库里。

操作：

| 操作 | 说明 |
|---|---|
| 鼠标拖拽 / 滚轮 | 平移 / 缩放（双击复位到整图） |
| **触屏单指拖动** | 平移地图 |
| **触屏双指捏合** | 缩放地图（以双指中点为锚点；双指整体移动＝平移） |
| **触屏轻点 / 双击** | 轻点查看点位详情 / 双击复位到整图（判定半径放宽到 18 px，便于手指点击） |
| **控制面板折叠** | 左上角把手 `☰` / `✕` 切换控制面板；**手机与触屏设备默认收起成左上角一个小圆点**，桌面默认展开 |
| 底图叠放 | 世界树**直接叠在主图左上角的空白区**（不再切换底图）；全部点位共用一套视图坐标 |
| 图层勾选框 | 普通刷怪 / 野外Boss / 监禁Boss / **地下城** / 普通钓点 / 稀有钓点 / **人类通缉犯** / 无数据(默认关闭) —— 顺序即面板里的显示顺序 |
| Boss 头像 | 野外Boss、监禁Boss 显示其帕鲁头像（取该刷怪器表中带"首领"标签的条目），人类通缉犯显示 NPC 头像；共 123 个点位，图标内嵌在 HTML 中 |
| 普通点按刷怪器着色 | 每个刷怪器一个颜色，**相邻刷怪器保证不同色**（图着色算法，12 色零冲突）；灰色 = 洞窟内部点 |
| 显示辅助圆 | 纯显示辅助：自定义半径（1–150 m）的 50% 透明填充圆，放大后可辨认点位 |
| 搜索框 | 支持 **中文名 / 英文内部ID / 图鉴号 / 属性**；命中的点位高亮，其余淡出（钓点产出同样参与搜索） |
| 点击点位 | 刷怪点**以抽签行为单位**列出（每行＝一次抽签，抽中后该行整组一起出现）；钓点显示可钓到的帕鲁；人类通缉犯显示名称/图标/BP 类；洞窟点位打开按位置合并的洞窟面板 |

点位样式：普通刷怪=圆点（洞窟内部为方块）、钓点=菱形（青/粉）、无数据=灰色空心方；
**野外Boss / 监禁Boss / 人类通缉犯 显示圆形头像**（尺寸按“直径≈100 m 的地图范围”分段缩放，16–96 px 量化到 8 px 步长，
点击判定半径随图标尺寸；参数在渲染段 `ICON_M / ICON_MIN / ICON_MAX / ICON_STEP`）。

## 目录结构

```
pal_spawner_map/
├─ pal_spawner_map.html          成品（双击打开）
├─ maps/                         底图
│  ├─ map_palpagos_8192.webp     帕洛斯群岛 8192²（仅供出图脚本，页面不加载）
│  ├─ map_worldtree_8192.webp    世界树   8192²（仅供出图脚本，页面不加载）
│  └─ map_*_4096.webp            4096² 版（构建时内嵌进 HTML）
├─ build_spawner_map.py          构建脚本：数据 + 底图 -> HTML
├─ tools/                        辅助脚本（解析 / 下载 / 拼接 / 校验）
└─ src/                          原始材料
   ├─ data/                      解包得到的 DataTable JSON
   │  ├─ Character/              人类 NPC 参数 / Boss NPC 图标表
   │  ├─ Fishing/                钓鱼相关表（类型/抽签/鱼影/鱼塘）
   │  └─ l10n/zh-Hans/           简体中文文本（赏金首名、帕鲁名）
   ├─ npc_icons/                 赏金首地图图标（32 张，来自 paldb CDN）
   ├─ palswiki/                  paldb 帕鲁列表存档页 + 图标
   ├─ tiles/                     底图瓦片（map8 / treemap8，各 256 块）
   └─ paldb/                     paldb 页面与数据存档（含钓点坐标）
```

## 重新构建

依赖：Python 3 + Pillow（`pip install pillow`）；下载瓦片需要 Node 18+。

```bash
# 0) 仅当帕鲁表有更新时才需要：重新解析中文名/图标
python tools/parse_pals_wiki.py

# 1) 底图瓦片（已随包提供；缺失时从 cdn.paldb.cc 重新下载）
node tools/fetch_tiles.mjs 4 src/tiles/map8     https://cdn.paldb.cc/image/map8/z{z}x{x}y{y}.webp
node tools/fetch_tiles.mjs 4 src/tiles/treemap8 https://cdn.paldb.cc/image/treemap8/z{z}x{x}y{y}.webp

# 2) 拼接底图 -> maps/ 并刷新 tools/maps_config.json
python tools/stitch_maps.py

# 3) 生成网页（自动组装刷怪表与钓点产出）
python build_spawner_map.py        # 输出 pal_spawner_map.html
```

只想改数据、不动底图时，直接跑第 3 步即可（用现有 `maps/`、`tools/pals_wiki.json` 与 `src/paldb/`）。

钓点相关（仅当要更新钓点坐标时才需要）：

```bash
# 从 paldb 存档数据重新提取钓点坐标 (两张地图的数据文件各跑一次)
node tools/fishing_extract_spots.mjs src/paldb/paldb_map_data.js    src/paldb/paldb_fishing_spots.json
node tools/fishing_extract_spots.mjs src/paldb/paldb_treemap_data.js src/paldb/paldb_fishing_spots_tree.json
python tools/fishing_merge_spots.py        # 合并 -> paldb_fishing_spots_all.json (按底图归属)
python tools/fishing_chain_check.py        # 校验 类型→抽签表→鱼影→帕鲁 链路
```

赏金首图标（仅当要重抓时）：

```bash
node tools/fetch_boss_icons.mjs .          # 按 DT_PalBossNPCIcon 的路径抓取到 src/npc_icons/
```

赏金首名称需要 **zh-Hans** 文本表：在 FModel 里把导出语言设为简体中文，导出
`Pal/Content/L10N/zh-Hans/Pal/DataTable/Text/DT_HumanNameText_Common`，放到 `src/data/l10n/zh-Hans/`。

## 关键技术点

### 坐标系（已用数据验证）

- 世界坐标 +X = **北**，+Y = **东**，+Z = 高度，单位 **厘米**（UE 惯例；旁证：`DT_PalMonsterParameter` 的速度值为 cm/s 量级）
- 页面布局：东向右、北向上，与游戏内地图一致
- 帕洛斯群岛底图覆盖世界 X[-1099400, 349400] Y[-724400, 724400]；世界树是其**西北方向的高分辨率子窗口**，
  覆盖 X[347351, 689148] Y[-818197, -476400]。两张图各自带 bounds，点位按坐标落入哪个窗口自动归属
  （7828 / 425 点，无遗漏）

坐标标定参数取自 paldb 页面的 `map_data_cn.js` / `treemap_data_cn.js`（`landScapeRealPositionMin/Max`、
`minMapTextureBlockSize`）与 `map.js` 的 `transformRposToTpos`：

```
像素x = (世界Y - minY) / (maxY - minY) × 8192
像素y = (maxX - 世界X) / (maxX - minX) × 8192
```

### 数据关联

- `DT_PalSpawnerPlacement`（8253 行）给位置/类型/半径；`DT_PalWildSpawner`（1691 行）给刷怪表，
  两者用 `SpawnerName` 关联（372 种刷怪器中 364 种可匹配）
- 一个刷怪器的多行按权重在行间抽签；**同一只帕鲁出现在多行时，其权重为各行之和**
- 权重占比分母分池：白天可用者用「白天池」（无夜晚限制的行），夜晚限定者用「全池」——否则夜晚行会压低白天数值

### 钓点数据的来源与关联

钓点坐标**不在任何 DataTable 里**——钓点是关卡中摆放的 MapObject 蓝图
（`Blueprint/MapObject/Object/FIshing/FishingSpot/.../BP_FishingSpot_*`），
DataTable 只描述「每种类型能钓到什么」。因此坐标取自 paldb 地图数据（`src/paldb/`），
其余全部来自解包表，通过 ID 串起来：

```
钓点实例 (坐标 + 类型 ID, 共 577 个)
  └─ href = FishingSpot_A_Ocean_Common
       └─ DT_PalFishingSpotLotteryNameDataTable   类型 -> 重生时间 (900s 普通 / 3600s 稀有)
       └─ DT_PalFishingSpotLotteryDataTable        类型 -> 加权产出 (1252 行)
            └─ FishShadowId ─→ DT_PalFishShadowDataTable.PalId   真正能钓到的帕鲁
```

- 577 个实例（帕洛斯 500 / 世界树 77）= 94 种类型，与类型表 **100% 匹配**
- 校验：98.6% 的钓点落在水面像素上（`tools/fishing_verify_positions.py`）
- 同一帕鲁可能存在多种鱼影（普通 / 首领 / 稀有），列表中以鱼影 ID 区分

### 人类通缉犯（賞金首）

`DT_PalSpawnerPlacement` 里有一批点位的 `SpawnerName` 为 `None`（界面原显示"无刷怪表"），
实为**人类通缉犯（日文"賞金首"）的固定刷新点**——刷怪器类是 `BP_MonoNPCSpawnerBossBase_*`（单体）
与 `BP_SquadNPCSpawnerBossBase_*`（小队），共 **33 个**，与游戏自己的地图图标表 **33 行完全吻合**。
数据链路全部来自解包表：

```
点位 SpawnerClass = BP_(Mono|Squad)NPCSpawnerBossBase_<NPC id>
  ├─ Text/DT_HumanNameText_Common (zh-Hans)  NAME_BOSS_*  -> "通缉犯 霍克" 等
  ├─ Character/DT_PalHumanParameter          BOSS_* 行 (IsBoss=true) -> BPClass / 属性 / 参数
  ├─ Character/DT_PalBossNPCIcon             33 行 -> 地图图标 T_BOSS_NPC_*.webp
  └─ UI/DT_BossSpawnerLoactionData           159 行 (SpawnerID/CharacterID/Location/Level)
                                             -> 按坐标权威定位 + 等级
```

**33 个点全部有中文名、图标与等级。** 名称查找需**大小写无关 + `BOSS_` 前缀双向尝试**：
游戏里存在 `BOSS_Police_old`(小写)、`Male_Trader01`（名称键为 `NAME_BOSS_Male_Trader01`）这类不一致，
且无前缀时必须优先取通缉犯名（否则 `Viking` 会取到通用 NPC 的"天坠之民"而非"通缉犯 奈尔"）。

#### 一个布点资产名与登记不符的案例（已解决）

`BOSS_Believer_Fat_GatlingGun` 这个点位曾解析不出名称/图标。追查结论：

1. 布点表的资产名确实是 `BP_MonoNPCSpawnerBossBase_BOSS_Believer_Fat_GatlingGun_C`
   → 我们的 id 提取没错，是**游戏侧资产名与赏金首登记不一致**；
2. 该 id 在三张表里都不存在（名字表只有 `NAME_BOSS_Believer_Fat_GiantClub`、图标表只有
   `BOSS_Believer_Fat_GiantClub`；参数表**只有不带 `BOSS_` 前缀的 `Believer_Fat_GatlingGun`**，
   而那是**普通版 NPC**：`IsBoss=false`、`BPClass=NPC_Believer_Fat`）；
3. 我们此前的候选键回退（去掉 `BOSS_` 再查）**静默匹配到了那个普通版行**，于是产出一个
   半成品条目（有 BPClass、无名称、无图标）——这是我们的 bug，不只是"缺数据"；
4. 权威来源是 `DT_BossSpawnerLoactionData`：同坐标（距离 **0.0 m**）登记的是
   `BOSS_Believer_Fat_GiantClub`、`Level=30`。

**修复**：① 参数表解析要求 `IsBoss=true`（避免匹配普通版）；② 按类名解析不到名称/图标时，
用同坐标（±2 m）的登记 id 纠正，并以该表的 Level 作为等级。现在该点位显示为
**「通缉犯 布里克」Lv 30**（与 paldb 的 `Hostile_Defender_Brick` 一致），面板中会注明
"布点资产名 → 登记 id" 的差异。

33 个点位与该表逐条交叉核对：**27 个完全一致**、5 个仅差 `BOSS_` 前缀（已由前缀回退处理）、
**1 个**即上述真实改名。

- 图标取自 paldb CDN（`cdn.paldb.cc/image/Pal/Texture/PalIcon/NPC/T_BOSS_NPC_*.webp`），
  由 `tools/fetch_boss_icons.mjs` 按图标表路径批量抓取

### 地下城：单一图层 + 按位置合并的 Boss / 小怪池 + 组合显示

洞窟的 **Boss 点与普通小怪点在地图上坐标完全重合**（170 个洞口位置，689 个点位，100% 重合），
因此**统一为单一图层「地下城」**（类型码 `DG`，紫色圆点）：既不再按"洞窟Boss / 普通刷怪"分层，
也**移除了原来的"显示地下/洞窟点"辅助勾选框**——所有地下城点位的显隐只由「地下城」这一个勾选框决定。

同一洞口有 2~6 个重合点，构建时**只保留一个代表标记**（Boss 点优先，其余标 `dd=1` 由前端跳过绘制）：
**689 个点位 → 170 个标记**。这些点位仍留在数据里供搜索与面板使用（搜索命中任一池都会高亮该洞口）。

点击任一地下城标记，面板会一次列出该洞口的全部池，
并按游戏自己的分类（`DT_DungeonEnemySpawnDataTable.RankType`）分区：

| RankType | 面板分区 | 说明 |
|---|---|---|
| `Boss` / `MidBoss` | 洞窟 Boss | 两者指向同一批刷怪器（既作中层首领又作最终 Boss），合并展示 |
| `Normal` / `Normal02`~`04` | 洞窟小怪 | Normal02~04 是 Yakushima 洞窟的额外小怪池 |
| `Monster` | 洞窟怪物池 | 即 `*_monsteronly` 刷怪器 |
| `NPCHuman` | 洞窟内的人类 NPC | 例：`50_17_dungeon_grass` |
| `FishPal` | 洞窟内的钓点帕鲁 | 例：`50_16_dungeon_grass`；洞窟内钓点位置未在图上标注 |

洞窟中文名来自 `DT_DungeonSpawnAreaDataTable` → `DT_DungeonNameText`(zh-Hans)，共 10 种：
丘陵洞窟(33)、天坠洞窟(30)、溪流洞窟(30)、溪谷洞窟(15)、樱花洞窟(15)、灵峰洞窟(15)、
火山洞窟(15)、沙丘洞窟(15)、天阳乡空域(1)、？？？(1)。**170 个洞口全部有名称**。

**抽签行（详情面板的基本单位）**：`DT_PalWildSpawner` 一行最多 3 个槽位（`Pal_1..3` + `NPC_1..3`），
**一行就是一次抽签的结果，抽中后该行列出的帕鲁整组一起出现**。因此详情面板以"行"为基本单位展示，
而不是把同一只帕鲁跨行汇总——汇总会把"一次出几只"的关系抹掉。

- 构建产出 `rows`：**1663 行 / 420 个刷怪器**（另有 5 个空行被跳过），其中 **193 行是多只成组**
  （`BOSS_X + X` 首领+同族小怪最常见，另有"双 Boss"与"多人 NPC 小队"）
- 面板表格四列：**抽签行**（图标+名+×数量，多只分行列出） / **总只数**（该行合计） / **等级** / **权重+占比**（附昼夜/天气/光环条件）
- 占比分母仍按同时段池：白天可用的行用**白天池**、夜晚限定的行用**全池**，故同一面板里不同行的百分比不在同一分母下
- 各类型覆盖面：普通点(地上) 237 刷怪器/1230 行/44 行多只；洞窟 Boss 10/160/**104**；野外Boss 71/71/17；监禁Boss 18/18/4
- 洞窟面板的 Boss 池也复用同一套行渲染；小怪/NPC/钓点池仍按帕鲁合并（同一池有多个洞窟模板，占比分母不同）

两个统计口径上的坑（早期都踩过）：判重必须用**原始 ID**（`BOSS_X + X` 按基础名会被误当成同一只），
统计行时必须**把 `NPC_1..3` 槽位算进去**（只数 `Pal` 槽会漏掉 NPC 组）。

### 普通点头像（普通刷怪点画成帕鲁头像）

#### 分配规则（构建时算好，见 `build_spawner_map.py`）

普通刷怪点在**放大到位后**显示为帕鲁头像；缩小到一定程度自动退回彩色圆点（性能兜底），
勾选框「普通点显示帕鲁头像」控制总开关，统计行会显示当前状态。

**分配规则（构建时算好，见 `build_spawner_map.py` 的 `build_icon_units` / `trim_icon_units` /
`allocate_icon_units`）**：

1. **以抽签行为基本单位**：一行 = 一次抽签，抽中后该行内容整组出现；
2. 每行映射为若干"头像单位"：
   - 行内含 NPC → **1 个灰底 `NPC` 占位符**（普通人类 NPC 无图标素材）；
   - 单只帕鲁行 → 该帕鲁；
   - 多只行且代表可定（恰有 1 只"数量固定为 1"的头领，或恰有 1 只"本刷怪器其它行未出现"）→ 取代表；
   - 多只行且代表不可定（普通刷怪范围内共 7 行"纯帕鲁 1+1"）→ **权重均分，行内每只各占 1 格**；
3. **先定数量、再定位置**：`allocate_icon_units` 按"每单位保底 1 格 + 剩余按权重用最大余数法补足"
   算出该刷怪器的**头像数量表**（仅夜间行权重 ×1/5），**然后**用**固定种子**
   （`ICON_SEED = 20251009 ^ crc32(刷怪器名)`）把头像随机打到具体点位上。
   换种子只会重排位置，**各头像的数量不变**，避免随机导致某只头像异常偏多；
4. **点位不足时腾位**：① 移旺财(MimicDog) ② 移仅夜间行（当前 3 个刷怪器用①、1 个用②，无截断）；
5. **整片跳过**：`worldtree_9_55_WorldTreeAura`（随机事件池）不画头像。

当前结果：**7382 / 7403** 个普通点分到头像（253 种，含 82 个 NPC 占位），
每个刷怪器的头像数量之和 = 该刷怪器点位数（`tools/verify_icon_alloc.py` 校验：
覆盖 0 异常 · 数量守恒 · 换种子数量不变）。

**渲染**：头像**预渲染成圆形精灵**（`spriteOf`：底衬 + 描边 + 圆形裁剪）再 `drawImage`，
不用逐帧 `clip`；精灵按当前尺寸档缓存，换档清空，且**每帧最多新建 48 个**避免换档瞬间卡顿。
实测各缩放档 blit 次数见 `tools/smoke_test_js.mjs`（在 Node 里用桩 DOM/Canvas 直接跑成品页面的脚本，
含渲染分档、描边配色、底图叠放几何、**触控手势模拟**与控制面板折叠的断言；
`node tools/smoke_test_js.mjs --mobile` 用 390×844 的手机参数再跑一遍，验证手机默认收起面板）。

**描边配色**：Boss（野外/监禁/人类通缉犯）**红框** `#ff4d4f`；普通点中来自"仅夜间"行的头像
**蓝框** `#4d9fff`（当前 1085 个，占 14.7%）；其余白框。所有描边都先描一圈深色再描彩色，
保证在海洋/雪地/火山等任何底图上都清晰；搜索高亮时统一改为橙框。精灵缓存键包含"是否夜间"，
所以同一只帕鲁的白天/夜间图标各自缓存。

**尺寸规则（两套，均按"直径≈N 米地图范围"分段缩放，8px 量化）**：

| | 基准 | 上下限 | 100% 对齐的视野区间 | 更远 / 更近 |
|---|---|---|---|---|
| Boss（野外/监禁/通缉犯） | **50 m** | **16 ~ 96 px** | 1.0 ~ 6.0 km | 固定 16px（全图时代表 125m）/ 固定 96px（0.5km 时代表 25m） |
| 普通点 | **25 m** | **16 ~ 48 px** | 1.0 ~ 3.0 km | 固定 16px（全图时代表 125m）/ 固定 48px（0.5km 时代表 12m） |

常量在渲染段开头：`BOSS_M/BOSS_MIN/BOSS_MAX`、`PAL_M/PAL_MIN/PAL_MAX`、`ICON_STEP`。
两套尺寸由 `iconPxBoss()` / `iconPxPal()` 分别计算（`tools/report_icon_scaling.py` 可复现全部数值）。

**LOD（仅普通点）**：`palIconMode && iconPxPal() ≥ PAL_LOD_PX(16) && 同屏候选 ≤ PAL_LOD_MAX(2500)`。
阈值 16 = 普通点尺寸下限，因此**只要在尺寸区间内就显示**，实际开关只由同屏数量决定：
最密集区域 **≤5.46 km** 开头像（该视野 2498 个普通点，逼近 2500 上限），稀疏区域（如世界树 418 点）
则一开始就显示。

> 注：上一轮已处理 Boss（野外Boss / 监禁Boss / 洞窟Boss）的图标与组合，本节只针对**普通刷怪点**。
> 代表头像的最终判据由使用者确定，本书记录数据事实，不作为推荐。

普通刷怪点范围内的多只行共 **44 行**，其中**无法唯一确定代表帕鲁的只有 10 行**：

| 类别 | 行数 | 说明 |
|---|---|---|
| 纯帕鲁的"1+1" | **7** | 行内两只数量都是 1、且两只在本刷怪器的其它行里同样出现（或都只在此行出现）→ 判据失效：`yellow_D`/`yellow_H` 艾小兔+姬小兔、`worldtree_9_10_L` 百合女王+黑月女王、`orange_C` 叶胖达+莉芳、`worldtree_9_02_B` 丹烽+泰锋、`snow_orange_E` 森猛犸+雪猛犸、`worldtree_9_13_M` 荷鲁斯+伊西斯 |
| 含 NPC 的组 | **3** | `yamijima_pink_NPC`（Viking+Viking_Elite）、`desert_orange_Oasis_Hunters`（3 人）、`yellow_A_Belivers`（2 人） |

**处理方式（已定）**：纯帕鲁的"1+1"行**把权重均分给行内每只，每只各占 1 格**；
**NPC 行一律用灰底 NPC 占位符**（1 行 = 1 格）。

**格子是否够（逐刷怪器核算，全线只剩 1 个不足）**：

| 刷怪器 | 点位 | 原始需求 | 去旺财后 | 去夜间后 | 结果 |
|---|---|---|---|---|---|
| `worldtree_9_55_WorldTreeAura` | 21 | 72 | 71 | 71 | 仍缺 50（已决定整片不画头像） |
| `snow_orange_D` | 10 | 11 | 10 | 10 | 够 |
| `desert_orange_G` | 8 | 12 | 11 | 8 | 够 |
| `snow_orange_E` | 7 | 9 | 8 | 6 | 够（最紧的一个，余 1 格） |
| `blue_C` | 3 | 4 | 4 | 2 | 够 |

其余 232 个刷怪器本来就够。**结论：除已排除的 `worldtree_9_55` 外，普通刷怪的格子全部够，零缺口。**

**关键限制：普通人类 NPC 没有头像素材**，故一律用灰底占位符。`NPC:Viking`、`NPC:Believer_CrossBow`、
`NPC:Hunter_Rifle`、`NPC:Male_Ninja01` 等 9 种 NPC id 在整个数据集中**有 0 个头像**
（只有 33 个赏金首有图标，且那是独立图层）。普通刷怪范围内含 NPC 的行共 **8 行**、
涉及 8 个刷怪器，且**全部是纯 NPC 行**：

| 刷怪器 | 点位 | 行 |
|---|---|---|
| `yamijima_purple_NPC` | 22 | NPC:Viking×2~3 + NPC:Viking_Elite×1 |
| `yamijima_pink_NPC` | 21 | NPC:Viking×1 + NPC:Viking_Elite×1 |
| `orange_B` | 19 | NPC:Believer_CrossBow×2~4 |
| `sakura_red_A_NPC` | 8 | NPC:Male_Ninja01×2~3 + Male_NinjaElite01×1 |
| `sakura_Waterfront_purple_A_NPC` | 4 | NPC:Male_Ninja01×2~3 + Male_NinjaElite01×1 |
| `volcano_orange_C_Firecult` | 4 | NPC:FireCult_FlameThrower×2~4 |
| `desert_orange_Oasis_Hunters` | 3 | NPC 三人组（持枪/步枪/手雷猎人） |
| `yellow_A_Belivers` | 1 | NPC:Believer_CrossBow×3~4 + NPC:Believer_Bat×1~2 |

⚠️ **判定 NPC 不能只看 `NPC_` 前缀**：游戏数据里部分人类 NPC 不带前缀（如 `Male_NinjaElite01`、
`Viking`、`VikingElite`），必须用"归一化后能否在帕鲁图鉴表里查到"来判定。
按前缀判定会把这 2 行误记为"帕鲁与 NPC 混排"——实际上**全数据集"帕鲁+NPC 同行"的行数为 0**。

### 静态 PNG 导出（离线出图）

```bash
python tools/export_png.py                          # 默认: 16px=25m, 图标走网页公式 (普通点16px / Boss32px)
python tools/export_png.py --icon-px 24 --marker-px 24   # 普通点放大到 24px(=37.5m), 非头像标记也 24px
python tools/export_png.py --icon-scale 1.5         # 用倍数代替绝对值
python tools/export_png.py --maps palpagos          # 只导某一张
python tools/export_png.py --with-nd                # 额外画出"无数据"图层 (网页默认隐藏)
python tools/export_png.py --combine                 # 导出后再拼一张合并图 (世界树贴到主图左上角空白区)
python tools/export_png.py --icon-px 24 --combine-only   # 不重渲染, 直接用已有 PNG 拼接
```

输出（`export/`，文件名自动带参数后缀，不会互相覆盖）：

| 文件 | 尺寸 | 体积 | 图标尺寸 |
|---|---|---|---|
| `palpagos_0p64px_per_m.png` | 9272 × 9272 | 36.9 MB | 普通点 16px(=25m) · Boss 32px(=50m) · 标记小 |
| `palpagos_0p64px_per_m_pal24px_marker24px.png` | 9272 × 9272 | 35.9 MB | **普通点 24px(=37.5m)** · Boss 32px · **标记 24px** |
| `combined_0p64px_per_m.png` | 9272 × 9272 | 39.0 MB | 默认尺寸 + 世界树拼贴 |
| `combined_0p64px_per_m_pal24px_marker24px.png` | 9272 × 9272 | 39.8 MB | 24px 尺寸 + 世界树拼贴 |
| `worldtree_0p64px_per_m.png` | 2188 × 2188 | 4.0 MB | 世界树单独一张 |

**合并图（`--combine`）**：主图左上角有 **2683 px 的纯空白正方形**（世界树图 2188² 可完整放下），
把世界树图**按左上角对齐贴到 (0,0)** 即可：该区域原本完全空白（内容包围盒为空，不遮挡任何底图内容），
且两者黑度一致（主图空白亮度 20~21，世界树图边缘 19~21 → **接缝不可见**）。
拼接前脚本会重新校验该区域仍为空白，不满足则拒绝拼接。
另：世界树在世界坐标里本来就在主图**北侧偏西**（X 起点 347351.5 ≈ 主图北界 349400），
所以放在左上角与地理位置也是吻合的。

- **底图固定按 0.64 px/m 缩放**（16px=25m）：帕洛斯 8192²→9272²（放大 1.13×）；世界树 8192²→2188²（缩小 0.27×）
- **点位与头像沿用网页同一套规则**：抽签行分配结果（`ii`/`ni`）、描边配色（Boss 红框 / 仅夜间蓝框 / 白框）、
  圆形裁剪 + 深色外圈、地下城每洞口只画一个代表点
- `--icon-px / --boss-px / --marker-px` 直接给像素直径（覆盖网页公式）；`--marker-px` 同时作用于
  地下城圆点、钓点菱形与无数据方框
- 静态图不适用 LOD（网页的"缩小退回画点"只是性能兜底），所以全部点位都会绘制
- 实际画出（帕洛斯）：地下城 170 · 普通点头像 6985 · 野外Boss 65 · 监禁Boss 18 · 通缉犯 33 · 钓点 500；
  世界树：普通点 397 · 野外Boss 7 · 钓点 77（`worldtree_9_55_WorldTreeAura` 按规则不画头像）

### 底图叠放（世界树叠在主图左上角）

两张底图**不再切换**：主图（帕洛斯群岛）打底，世界树按**左上角对齐**叠在其左上角空白区。

- 主图左上角有 **2683 px 的纯空白正方形**（世界树图 2188² 放得下），且两者黑度一致（20~21 vs 19~21），
  叠上去**无接缝、不遮挡**任何底图内容（校验见 `tools/measure_blank_area.py`）
- 两图导出比例一致，所以"左上角对齐"等价于世界坐标的一次**纯平移**，构建时算出并写进 `DATA.maps[].off`：

  | 底图 | 平移 | 叠放后占据（主图世界坐标） |
  |---|---|---|
  | 帕洛斯群岛（主图） | `[0, 0]` | X[-1099400, 349400] Y[-724400, 724400] |
  | 世界树（副图） | `dx=-339748.5  dy=+93797` | X[7603, 349400] Y[-724400, -382603] |

  公式：`dx = 主图.maxX - 副图.maxX`、`dy = 主图.minY - 副图.minY`（西北角对齐）。
- 前端用 `PXY(p) = w2s(p.x + MOFF[p.m][0], p.y + MOFF[p.m][1])` 统一投影，
  所以两张图的点位、拾取、搜索、LOD 全在同一套视图坐标里；**面板里显示的仍是点位的真实世界坐标**
- 世界树在世界坐标里本就位于主图北侧偏西（X 起点 347351.5 ≈ 主图北界 349400），
  所以放在左上角与地理位置也是吻合的；若要做**世界坐标精确拼接**（两图按真实经纬相邻，
  而非对角对齐），需要把画布向北扩展约 2174 px，目前未采用
- 静态 PNG 导出（`--combine`）用的是同一套对齐方式，两者结果一致

### 无数据点位（38 个，默认隐藏）

另有 7 种 `BP_PalSpawner_Sheets_*`（`3_1_volcano_1` 17 个、`desert_orange_Oasis_Suzakus` 13 个等）
共 38 个点，其刷怪器名**只在 `DT_PalSpawnerPlacement` 中出现**，`DT_PalWildSpawner` 等全部 476 张表
均无对应行——判断为 1.0 移除/未启用的残留 sheet。页面把它们收进「无数据」图层并**默认不勾选**。

### 已知限制

- 表内 `StaticRadius` 全表仅 15000/20000 两个值（150 m / 200 m），是默认常量；而点位最近邻间距中位数仅约 49 m，
  按此半径画圆 100% 互相重叠。结合游戏内实测（刷新偏移几乎不超过 1 m），判断该字段**疑似弃用**，
  故页面把它降级为「辅助圆」并允许自定义半径
- 洞窟内部点（`PlacementType` 含 `Dungeon`）的 X/Y 是多副本叠放坐标，在地表标注意义不大，
  页面用灰色方块显示，并排除在区域着色之外；点击洞窟标记会打开按位置合并的洞窟面板（见上）
- 世界树在世界坐标上是主图**北侧偏西**的另一块区域（3.42 km 见方），页面把它按"左上角对齐"
  叠在主图空白区显示（见「底图叠放」）；两图的相对位置是**对角对齐**而非世界坐标精确拼接
  （精确拼接需要把画布向北扩展，见「底图叠放」一节的说明）
- 洞窟内的钓点类型（`FishingSpot_Dungeon_*`）在 paldb 数据中没有实例，故未出现在图上
- 赏金首点位中有 1 个（`BOSS_Believer_Fat_GatlingGun`）在游戏数据里没有名称/图标条目，属游戏侧遗留改名
- 「无数据」图层的 38 个点判定为 1.0 移除/未启用的残留 sheet，默认不显示

## 数据来源

- 刷怪数据 / 人类通缉犯点位：游戏本体解包（`Pal/Content/Pal/DataTable/Spawner`）
- 钓点类型/产出、人类 NPC 参数与图标：游戏本体解包（`Pal/Content/Pal/DataTable/{Fishing,Character}`）
- 人类通缉犯中文名、帕鲁中文名：游戏本体解包（`Pal/Content/L10N/zh-Hans/Pal/DataTable/Text`）
- 帕鲁中文名/图标/图鉴号（备用来源）：<https://paldb.cc/cn/Pals>（存档页见 `src/palswiki/`）
- 底图瓦片、钓点坐标、赏金首图标：<https://paldb.cc/cn/Palpagos_Islands>、<https://paldb.cc/cn/The_World_Tree>
  （`cdn.paldb.cc/image/map8/`、`cdn.paldb.cc/image/treemap8/`、`cdn.paldb.cc/image/Pal/Texture/PalIcon/NPC/`）

本项目为粉丝向数据整理，与 Pocketpair 无关；图片与名称版权归原权利方所有，仅供个人研究使用。
