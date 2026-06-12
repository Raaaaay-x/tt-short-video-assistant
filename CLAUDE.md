# CLAUDE.md

> 本文件是 tt_agent 项目的总纲，Claude Code 每次开工请先读这里。
> 目的：让任何模型（Sonnet 写基准 / Opus 做封装 / Fable 啃硬骨头）一上来就懂项目全貌，不必反复对齐。

---

## 项目是什么

`tt_agent` 是一个**短视频内容情报 + 生产工具**，服务于「芮玛鞋城」的本地短视频 IP 运营。

输入一个对标视频链接（或逐字稿），输出：拆解报告 + 可直接拍摄的二创脚本。

**一句话定位：这不是电商工具，是内容情报与生产工具。**
不要引入任何电商逻辑（定价、ROI、挂车、跨境 DTC）——那些已在重构中被明确砍掉。

---

## 业务背景（理解约束的前提）

- 主体：芮玛鞋城，房山本地经营十余年的多品牌鞋城，郊区、一站式家庭购物定位。
- 护城河：**本地信任 + 老板娘真人 IP**，不是货品价格。
- 出镜人：老板娘本人，员工兼职拍摄，非专业团队。
- 账号阶段：从 0 起步，主攻品牌/口碑，前期不带货。
- 内容配比铁律：**信任故事 40% / 好物分享 30% / 活动福利 20% / 本地互动 10%**（简称 4-3-2-1）。

---

## 核心架构

```
tt_agent/
├── tt_agent.py              # 入口：链接/逐字稿 → 报告 + 脚本
├── analyst/
│   ├── deconstructor.py    # 视频理解 + 结构拆解
│   └── comment_miner.py    # 评论区情绪提炼（产出要回流到 topic_planner）
├── strategist/
│   ├── topic_planner.py    # 选题规划
│   ├── script_writer.py    # 脚本二创
│   ├── platform_adapter.py # 平台风格适配
│   └── guardrail.py        # 合规与风险过滤（输出前强制过一遍）
├── store/                   # 数据层：让工具能积累
│   ├── corpus.py           # 对标库：拆解结果结构化沉淀
│   └── content_log.py      # 已产出脚本 + 发布后表现回填
├── templates/
│   ├── hooks.py            # 钩子模板（价格锚定、身份认同、反常识…）
│   ├── structures.py       # 结构模板（对比型、教程序列、观点推演…）
│   └── platforms.py        # 平台规则（抖音/小红书/视频号）
├── .claude/skills/
│   └── short-video-analysis.md   # 拆解维度+模板+约束封装为 skill
└── outputs/
```

### 数据流要点
1. `deconstructor` 拆解 → 沉淀进 `store/corpus`
2. `comment_miner` 的情绪/高频问题 → **回流到** `topic_planner` 当选题来源
3. 平台规则与人设约束是**全局贯穿约束**，不是某一步——拆解和二创都要受其约束
4. `guardrail` 是脚本输出前的**强制关卡**，不是可选建议

---

## 不可逾越的红线（写进每条脚本的校验）

这些是真能导致罚款或出事的部分，`guardrail.py` 必须覆盖：

### 1. 隐私安全
- 子女真实姓名**模糊化**（只说「用儿子名字的谐音」，不报全名）
- 不输出作息规律、独自看店时间、家庭精确住址
- 店址只到商圈/街道级

### 2. 广告法合规
- 禁用绝对化用语：「最」「第一」「底价」「最低价」等
- 「工厂底价」→ 改「省去中间环节，让利街坊」
- 「良心店」等主观表达可保留

### 3. 内容人设一致性
- 必须符合 4-3-2-1 配比，信任故事不能缺位
- 二创脚本必须注入**人设约束**：本地口音、真人实景、老板娘视角
- 警惕「正确但不像他们」的脚本——大城市专业团队的对标内容直接套用会水土不服

---

## 拆解维度（deconstructor 至少输出这些层）

不要只停在「结构」，否则二创会很空：

- **钩子类型**（前 3 秒怎么抓人）
- **叙事结构**（对比 / 教程 / 观点推演…）
- **情绪曲线**（哪里起、哪里转、哪里落）
- **口播节奏**（单句长度、停顿位）
- **爆点假设**（为什么这条能火——给可证伪的假设，不要笼统夸赞）

拆解结果按以下 schema 输出（后续沉淀进 store/corpus 的格式）：

```python
{
  "source_url": str,          # 对标视频链接（或 "manual_transcript"）
  "platform": str,            # 抖音 / 小红书 / 视频号
  "deconstructed_at": str,    # ISO 日期
  "hook_type": str,           # A1/A2/B1...对应钩子模板
  "structure_type": str,      # 结构1/2/3/4
  "emotion_curve": list,      # [{"pct": "0-25", "emotion": "好奇"}, ...]
  "viral_hypothesis": str,    # 爆款假设（可证伪）
  "migrate_score": int,       # 对我们账号的适配度 1-5
  "tags": list[str],          # 自由标签
}
```

## 人设约束的具体落地规则

不要只说「本地口音、真人实景」——模型会偏。落地规则：

- 开场第一句话必须是「我们家」「我们店里」「房山这边」三选一
- 每 10 句话里至少出现一次「你看」/「你看这个」（引导视线，手机小屏看视频的习惯）
- 口播单句不超过 15 字，超过时必须拆成两句
- 🚫 拒绝书面语：比如「具有显著提升效果」→ 改「你看处理完确实不一样」
- 🚫 拒绝过度网感：「家人们」「宝子们」「绝绝子」「冲」
- ✅ 情绪词用北京口语风格：「真不错」「可以看看」「挺值的」「还行」
- 拍摄场景只在店内（操作台、货架、前台），拒绝绿幕/棚拍/布置过度的画面描述
- 提到鞋名时带上本地消费者的叫法，不要用过于专业的术语

## 对标参考（给模型的 taste 锚点）

- 行业：本地洗鞋/球鞋护理 + 鞋类零售
- 找对标的方法：抖音搜索「洗鞋」「球鞋修复」「鞋店」，筛选完播率高、评论区活跃的视频
- 好的拆解长什么样：见 `outputs/` 下积累的拆解报告，优先参考评分高（migrate_score≥4）的

## store/corpus 存储 schema

单条对标记录的完整结构（可增量追加到 JSONL）：

```python
# corpus.py 存储格式: outputs/corpus.jsonl（一行一条 JSON）
{
  "id": str,                   # 自动生成
  "source_url": str,
  "platform": str,
  "title": str,                # 视频标题
  "deconstructed_at": str,
  "hook_type": str,
  "structure_type": str,
  "emotion_curve": list,
  "speaking_style": {          # 口播特征（更新）
    "avg_sentence_len": int,
    "pause_positions": list,
    "tone_shifts": list,
  },
  "viral_hypothesis": str,
  "migrate_score": int,
  "migrate_notes": str,        # 迁移建议文本
  "tags": list[str],
}
```

---

## v0.2 已交付（通过初步验收 ✅）

最小闭环全部跑通：逐字稿进、拆解+二创出。

## v2.0 进行中

- [x] A/B 实验追踪 (`store/corpus.py`)
- [x] 评论区情绪提炼 (`analyst/comment_miner.py`)
- [x] 选题规划器 (`strategist/topic_planner.py`)
- [x] 平台分发适配 (`strategist/platform_adapter.py`)
- [x] 内容日志+周复盘 (`store/content_log.py`)
- [x] 对标库多维检索
- [x] 数据洞察引擎
- [x] 选题池可视化
- [x] 移动端适配
- [x] 批量竞品分析
- [x] UI 装修 (v2.5)

## Phase 2 — 云服务 + 数据仪表盘

### 目标
将 JSONL 本地存储升级为腾讯云数据库, 支持多设备访问 + 可视化数据看板。

### 技术栈
- **数据库**: 腾讯云 MySQL / TDSQL (关系型) 或 MongoDB (文档型, 适合 JSONL 结构迁移)
- **对象存储**: 腾讯云 COS (存储视频素材、脚本截图、逐字稿原文)
- **后端**: Python Flask/FastAPI (API 层, 连接数据库和前端)
- **前端**: 在现有 index.html 基础上扩展数据仪表盘页
- **部署**: 腾讯云轻量应用服务器 (Lighthouse) 或 CloudBase 云开发

### 数据库表设计 (MySQL 方案)
```
corpus (对标库)
  id, source_url, platform, title, hook_type, structure_type,
  emotion_curve(JSON), speaking_style(JSON), viral_hypothesis,
  migrate_score, tags(JSON), deconstructed_at

experiments (A/B实验)
  id, decon_id(FK), title, topic, hypothesis,
  branch_a(JSON), branch_b(JSON), result, winner, created_at

topic_pool (选题池)
  id, title, source, source_comment, content_type,
  priority, status, created_at

content_log (发布日志)
  id, title, platform, content_type, hook_type, structure_type,
  published_at, views, likes, comments, shares, saves,
  completion_rate, engagement_rate, store_inquiries, rating, learned

materials (素材库)
  id, filename, cos_url, type(视频/图片/逐字稿/脚本),
  tags(JSON), uploaded_at
```

### 数据仪表盘页面
- 核心指标卡: 累计拆解/脚本数, A/B实验数, 本周发布数
- 钩子表现趋势折线图 (周粒度)
- 内容类型转化对比柱状图
- 到店咨询漏斗 (播放→互动→咨询→到店)
- 选题池热力图 (按优先级和类型)

### 分步计划
1. 腾讯云 MySQL 实例创建 + 表建表脚本
2. JSONL 数据迁移脚本 (outputs/*.jsonl → MySQL)
3. FastAPI 后端搭建 (CRUD API + 数据统计 API)
4. 前端仪表盘页 (独立 HTML 或扩展现有页面)
5. 素材上传功能 (腾讯云 COS + 前端上传组件)
6. 部署上线 (Lighthouse + Nginx + HTTPS)

## 第一版交付清单（v0.2）

最小闭环，先跑通「逐字稿进、脚本出」：

- [ ] `tt_agent.py`: 入口，接收逐字稿文本 → 调用拆解 → 调用脚本生成 → 输出到 outputs/
- [ ] `analyst/deconstructor.py`: 五层拆解，输入逐字稿，输出结构化 dict（按上方 schema）
- [ ] `strategist/script_writer.py`: 输入拆解结果 + 人设约束 → 输出分镜脚本
- [ ] `strategist/guardrail.py`: 三道检查（隐私 / 广告法 / 人设一致性），脚本输出前强制过
- [ ] `templates/hooks.py`: 4 种钩子模板（A/B/C/D 各至少 1 个具体示例）
- [ ] `templates/structures.py`: 2 种结构模板（对比冲击型 + 知识科普型）
- [ ] `.claude/skills/short-video-analysis.md`: Skill 封装（拆解维度+模板+约束）
- [ ] 跑通验证: `python tt_agent.py --input sample_transcript.txt`
- [ ] `store/corpus.py`: 对标库基础写入（JSONL 追加）

### v0.3 (第二轮)
- [ ] `analyst/comment_miner.py`: 评论区情绪提炼 + 回流 `topic_planner`
- [ ] `strategist/platform_adapter.py`: 抖音/小红书/视频号三版本输出
- [ ] `strategist/topic_planner.py`: 基于对标库的选题规划
- [ ] `store/content_log.py`: 脚本发布后表现回填

## 当前开发阶段

- **现在：** v0.2 通过初步验收 ✅，进入 v2.0
- **v2.0 优先：** web 页面集成 A/B 实验、comment_miner、platform_adapter、内容日志
- **后续：** 矩阵号自动化、周复盘报告、到店转化归因

### 给开发模型的工作方式
- 每填完一个模块就 `python tt_agent.py` 跑一次，早发现接口对不上的问题
- 脚本二创后、输出前留一个 **human-in-the-loop 卡点**，由人确认或微调再定稿，前期不追求全自动
- 约束与模板写成数据（skill markdown/config），不写死在代码里——方便非技术人员看懂和提改动

---

## 输入格式约定

人工逐字稿用 txt 或直接贴进对话，格式按行：

```
[0:00-0:03] 【画面】脏鞋特写，慢推镜头
【口播】你看这双鞋进来的样子...
[0:03-0:08] 【画面】清洗过程，手部特写
【口播】我们先用这个...
```

- `【画面】` 描述镜头、动作、字幕/特效
- `【口播】` 记录完整口播文字
- 时间戳精度到秒即可，第一版不强求

## 输入现实约束

- 抖音链接无官方 API 取字幕。**第一版走「人工贴逐字稿」**，把 agent 价值聚焦在「拆解 + 二创」，不要卡在抓取上。
- 后续如需自动转录再单独评估第三方方案。

---

## 代码约定

- Python 3，模块职责单一，接口清晰（每个模块输入/输出用 dataclass 或 dict schema 约定好）
- **约束与模板写成数据，不写死在代码里**——放 skill markdown 或 config，方便非技术人员（老板娘/员工）看懂和提改动
- 注释用中文，与业务沟通一致
- 不引入重型依赖；优先标准库 + 必要的轻量包
- 输出文件统一进 `outputs/`

---

## 模型路由

不同任务分给不同模型，不要一把梭：

| 任务 | 推荐模型 | 原因 |
|------|---------|------|
| 五层拆解 (deconstructor) | Opus | 需要深度推理和爆款假设 |
| 脚本二创 (script_writer) | Opus / Sonnet | 依赖人设约束，Opus 更稳 |
| Guardrail 检查 | Sonnet / Haiku | 规则明确，轻量即可 |
| 批量处理 | Haiku | 拆解过的模板复用 |
| Skill 文件维护 | Opus | 需要运营判断和抽象 |

## 成功指标（怎么判断这个工具在变好）

- 二创脚本的**人工修改率**：理想 < 20%（每 10 句改不到 2 句）
- 对标库积累速度：每周至少 3 条新拆解入库
- 发布后**完播率变化**：用对标库里的钩子模板，完播率是否在提升
- Guardrail 拦截率：拦截了但人工 override 的比例应 < 10%

## 一句话心法（贴在最前面提醒自己）

**做信任号不做带货号；真实大于精致；约束即资产——把人设和红线写成可复用的配置，而不是埋在代码里。**
