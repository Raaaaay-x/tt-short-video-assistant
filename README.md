# tt_agent — 短视频内容研究员

> 输入对标视频逐字稿 → 五层拆解 + 脚本二创 + 批量竞品分析 + 周复盘

**定位：内容情报与生产工具。**

---

## 架构

```
tt_agent/
├── tt_agent.py                  # CLI 入口: 逐字稿 → 拆解 + 二创
├── index.html                   # Web 版: 自包含单页, GitHub Pages 部署
├── CLAUDE.md                    # 项目总纲 + 开发约定
│
├── analyst/
│   ├── deconstructor.py         # 五层拆解 (钩子/结构/情绪/口播/爆款假设)
│   └── comment_miner.py         # 评论区情绪提炼 → 选题池回流
│
├── strategist/
│   ├── script_writer.py         # 脚本二创 (人设约束注入)
│   ├── topic_planner.py         # 周内容计划 (4-3-2-1 配比)
│   ├── platform_adapter.py      # 抖音/小红书/视频号三版适配
│   └── guardrail.py             # 合规检查 (隐私/广告法/人设)
│
├── store/
│   ├── corpus.py                # 对标库 + A/B 实验 + 多维检索
│   └── content_log.py           # 发布日志 + 表现回填 + 数据洞察
│
├── templates/
│   ├── hooks.py                 # 钩子模板 (A/B/C/D)
│   └── structures.py            # 结构模板 (对比型/科普型)
│
├── .claude/skills/
│   └── short-video-analysis.md  # Skill 封装
│
├── web/                         # Web 静态数据
│   ├── corpus_data.js
│   └── topic_pool_data.js
│
└── outputs/                     # 产物目录
    ├── corpus.jsonl             # 对标库
    ├── experiments.jsonl        # A/B 实验
    ├── topic_pool.jsonl         # 选题池
    ├── content_log.jsonl        # 发布日志
    └── weekly_plans/            # 周计划
```

### 数据流

```
对标视频逐字稿
    ↓
deconstructor (五层拆解)  ──→  corpus.jsonl  ──→  search() / A/B test
    ↓
script_writer (脚本二创)
    ↓
guardrail (合规检查)
    ↓
platform_adapter (三平台分发)
    ↓
content_log (发布追踪)  ──→  weekly_review() / insights()

评论区粘贴
    ↓
comment_miner (情绪提炼)  ──→  topic_pool.jsonl  ──→  topic_planner (周计划)
```

---

## Web 版使用方法

**访问**: https://raaaaay-x.github.io/tt-short-video-assistant/

### 三步上手

1. **设置 API Key**: 左侧边栏 → 输入 DeepSeek 或阶跃星辰 Key → 保存（仅存浏览器本地）
2. **粘贴逐字稿**: 点击"洗鞋效果展示"等示例标签自动填入，或手动粘贴
3. **一键全流程**: 等待 20-40 秒 → 拆解报告 / 二创脚本 / 合规检查 三栏切换 → 下载 Markdown

### 逐字稿格式

```txt
[0:00-0:03] 【画面】脏鞋特写，慢推镜头
【口播】你看这双鞋进来的样子，鞋底都磨平了。
[0:03-0:08] 【画面】清洗过程，手部特写
【口播】我们先用这个软化皮面，你看这个脏东西慢慢就出来了。
```

也可直接粘贴纯文本口播（无时间戳）。

### 批量模式

勾选"批量模式" → 用 `---` 分隔多个逐字稿 → 批量分析 → 自动生成汇总对比表

### 侧边栏功能

| 卡片 | 功能 |
|------|------|
| 📋 工作流 | 当前分析进度 (5 步指示器) |
| 🔎 对标库检索 | 搜索已拆解视频 (关键词 + 钩子/平台筛选) |
| 💡 选题池 | 从评论区挖掘的待拍选题 |
| 🔑 API 设置 | 模型选择 + Key 管理 |
| 🔍 拆解五维度 | 分析输出维度说明 |

---

## CLI 使用方法

```bash
# 单条分析
python tt_agent.py --input sample_transcript.txt

# 交互模式
python tt_agent.py
```

### Python API

```python
# 对标库搜索
from store.corpus import search
results = search(query="翻毛皮", hook_type="A1", min_score=3)

# 数据洞察
from store.content_log import insights, format_insights
print(format_insights(insights()))

# A/B 实验
from store.corpus import start_experiment, log_experiment_result
exp_id = start_experiment(
    title="钩子测试: 对比 vs 反常识",
    account_a="主号", hook_a="A1", structure_a="contrast",
    account_b="小号", hook_b="B1", structure_b="knowledge",
)
log_experiment_result(exp_id, branch="A", views=3200, completion_rate=0.52)

# 周计划
from strategist.topic_planner import load_candidates, assign_weekly_plan
plan = assign_weekly_plan(load_candidates())
```

---

## 版本

| 版本 | 内容 |
|------|------|
| v0.1 | 跨境 DTC TikTok 脚本生成 (→ legacy/) |
| v0.2 | 最小闭环: 逐字稿 → 拆解 → 二创 → Guardrail |
| v2.0 | 评论挖掘 + 选题规划 + 平台分发 + 内容日志 + A/B 实验 |
| v2.1 | 对标库多维检索 |
| v2.2 | 数据洞察引擎 |
| v2.3 | 选题池可视化 + 移动端适配 |
| v2.4 | 批量竞品分析 |
