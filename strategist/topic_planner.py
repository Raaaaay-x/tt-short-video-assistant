"""
选题规划器 — 基于对标库 + 评论选题池 + 内容配比 生成周更计划

输入:
  - topic_pool.jsonl (来自 comment_miner)
  - corpus.jsonl (来自 deconstructor)
  - 账号内容配比 (4-3-2-1)

输出:
  - 本周内容日历 (可执行的选题 x 日期 x 类型)
  - Markdown 周计划表

v2.0: 本地规划 + LLM 润色
"""

import json
from pathlib import Path
from datetime import date, timedelta, datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

POOL_PATH = Path(__file__).parent.parent / "outputs" / "topic_pool.jsonl"
CORPUS_PATH = Path(__file__).parent.parent / "outputs" / "corpus.jsonl"
PLAN_PATH = Path(__file__).parent.parent / "outputs" / "weekly_plans"

# 4-3-2-1 内容配比
CONTENT_MIX = {
    "效果展示": 0.40,   # 信任内容
    "知识科普": 0.30,   # 专业度
    "经营故事": 0.20,   # 真人感
    "活动促销": 0.10,   # 转化
}

# 周发布频率建议
WEEKLY_POSTS = 5  # 周一至周五, 每天一条


@dataclass
class TopicCard:
    title: str
    content_type: str          # 效果展示/知识科普/经营故事/活动促销
    source: str               # corpus / comment_miner / manual
    hook_type: str = ""       # A1/B1/C1/D1
    structure_type: str = ""  # contrast/knowledge
    priority: str = "medium"
    assigned_day: str = ""    # 周几
    notes: str = ""


@dataclass
class WeekPlan:
    week_start: str = ""      # ISO 周一日期
    topics: list = field(default_factory=list)
    mix_check: dict = field(default_factory=dict)  # 实际配比 vs 目标配比


def load_candidates() -> list[dict]:
    """从选题池 + 对标库加载可用的选题候选。"""
    candidates = []

    # 1. 从选题池加载 (来自 comment_miner)
    if POOL_PATH.exists():
        with open(POOL_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        r = json.loads(line)
                        if r.get("status") == "new":
                            candidates.append({
                                "title": r.get("title", ""),
                                "content_type": _map_type(r.get("content_type", "")),
                                "source": "comment_miner",
                                "priority": r.get("priority", "medium"),
                                "source_comment": r.get("source_comment", ""),
                            })
                    except json.JSONDecodeError:
                        continue

    # 2. 从对标库加载迁移建议 (来自 deconstructor)
    if CORPUS_PATH.exists():
        with open(CORPUS_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        r = json.loads(line)
                        if r.get("migrate_score", 0) >= 3 and r.get("migrate_notes"):
                            candidates.append({
                                "title": f"对标迁移: {r.get('title', '')[:30]}",
                                "content_type": "效果展示",
                                "source": "corpus",
                                "hook_type": r.get("hook_type", ""),
                                "structure_type": r.get("structure_type", ""),
                                "priority": "medium",
                                "corpus_id": r.get("id", ""),
                                "migrate_notes": r.get("migrate_notes", ""),
                            })
                    except json.JSONDecodeError:
                        continue

    return candidates


def assign_weekly_plan(
    candidates: list[dict],
    week_start: date | None = None,
    posts_per_week: int = WEEKLY_POSTS,
) -> WeekPlan:
    """
    按 4-3-2-1 配比, 从候选池中选材, 分配一周内容。

    规则:
    1. 优先选 comment_miner 的高优先级选题 (用户真实问题)
    2. 按内容配比填满一周
    3. 同类内容不连续排列
    4. 周五放活动/促销类 (转化日)
    """
    today = date.today()
    monday = week_start or (today - timedelta(days=today.weekday()))

    # 按优先级排序 (high → medium)
    sorted_candidates = sorted(candidates, key=lambda c: (
        0 if c["priority"] == "high" else 1,
        0 if c["source"] == "comment_miner" else 1,  # 评论选题优先
    ))

    # 按内容类型分组
    by_type = {}
    for c in sorted_candidates:
        ct = c["content_type"]
        by_type.setdefault(ct, []).append(c)

    # 计算每种类型需要的数量
    slots = posts_per_week
    needed = {t: max(1, round(slots * pct)) for t, pct in CONTENT_MIX.items()}
    # 调整使总数 = slots
    diff = slots - sum(needed.values())
    if diff > 0:
        needed["效果展示"] += diff  # 默认多放效果展示

    # 分配
    assigned = []
    used_titles = set()

    for ctype, n in needed.items():
        pool = by_type.get(ctype, [])
        count = 0
        for c in pool:
            if count >= n:
                break
            title = c["title"]
            if title not in used_titles:
                c["assigned_day"] = ""  # 后续填具体日期
                assigned.append(c)
                used_titles.add(title)
                count += 1

    # 排日期 (周一→周五), 避免同类相邻
    weekdays = [(monday + timedelta(days=i)).isoformat() for i in range(5)]
    daily = {d: [] for d in weekdays}

    # 周五固定: 活动/促销
    friday = weekdays[-1]
    promo_candidates = [c for c in assigned if c["content_type"] == "活动促销"]
    if promo_candidates:
        promo_candidates[0]["assigned_day"] = friday
        daily[friday].append(promo_candidates[0])

    # 其他按类型轮询分配
    remaining = [c for c in assigned if not c["assigned_day"]]
    day_idx = 0
    for c in remaining:
        # 找第一个不同类且未满的日期
        attempts = 0
        while attempts < 5:
            d = weekdays[day_idx % 5]
            existing_types = {t["content_type"] for t in daily[d]}
            if c["content_type"] not in existing_types and len(daily[d]) < 1:
                c["assigned_day"] = d
                daily[d].append(c)
                day_idx = (day_idx + 1) % 5
                break
            day_idx = (day_idx + 1) % 5
            attempts += 1
        if not c["assigned_day"]:
            # fallback: 放人数最少的日子
            min_day = min(weekdays, key=lambda d: len(daily[d]))
            c["assigned_day"] = min_day
            daily[min_day].append(c)

    # 构造结果
    topics = []
    for d in weekdays:
        for c in daily[d]:
            topics.append(TopicCard(
                title=c["title"],
                content_type=c["content_type"],
                source=c.get("source", ""),
                hook_type=c.get("hook_type", ""),
                structure_type=c.get("structure_type", ""),
                priority=c.get("priority", "medium"),
                assigned_day=c["assigned_day"],
                notes=c.get("source_comment", c.get("migrate_notes", "")),
            ))

    # 配比检查
    actual_mix = {}
    for t in topics:
        actual_mix[t.content_type] = actual_mix.get(t.content_type, 0) + 1

    return WeekPlan(
        week_start=monday.isoformat(),
        topics=[asdict(t) for t in topics],
        mix_check={"target": needed, "actual": actual_mix},
    )


def format_week_plan(plan: WeekPlan) -> str:
    """格式化周计划为 Markdown。"""
    lines = [
        f"# 本周内容计划 | {plan.week_start}",
        "",
        "## 📊 配比",
    ]
    target = plan.mix_check.get("target", {})
    actual = plan.mix_check.get("actual", {})
    for ct in ["效果展示", "知识科普", "经营故事", "活动促销"]:
        t = target.get(ct, 0)
        a = actual.get(ct, 0)
        ok = "✅" if a >= t else "⚠️"
        lines.append(f"- {ok} {ct}: {a}条 (目标 {t}条)")

    lines.extend(["", "## 📅 每日安排", ""])

    day_names = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五"}
    by_day = {}
    for t in plan.topics:
        by_day.setdefault(t["assigned_day"], []).append(t)

    import datetime as dt
    monday = dt.date.fromisoformat(plan.week_start)
    for i in range(5):
        d = (monday + timedelta(days=i)).isoformat()
        day_label = day_names[i]
        lines.append(f"### {day_label} ({d})")
        items = by_day.get(d, [])
        if not items:
            lines.append("- *(休息/补发)*")
        else:
            for item in items:
                hook = f" 钩子:{item['hook_type']}" if item.get('hook_type') else ""
                struct = f" 结构:{item['structure_type']}" if item.get('structure_type') else ""
                lines.append(
                    f"- [{item['content_type']}] **{item['title']}**{hook}{struct}"
                )
                if item.get("notes"):
                    lines.append(f"  > {item['notes'][:80]}")
        lines.append("")

    return "\n".join(lines)


def save_plan(plan: WeekPlan) -> str:
    """保存周计划到文件。"""
    PLAN_PATH.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d")
    filepath = PLAN_PATH / f"week_plan_{plan.week_start}_{ts}.md"
    md = format_week_plan(plan)
    filepath.write_text(md, encoding="utf-8")
    return str(filepath)


def _map_type(ctype: str) -> str:
    """映射评论中的内容类型到 4-3-2-1 分类。"""
    mapping = {
        "答疑": "知识科普", "教程": "知识科普", "科普": "知识科普",
        "验证": "效果展示",
        "揭秘": "知识科普",
    }
    return mapping.get(ctype, "知识科普")


# ════════════════════════════════════════════════════════
# 自测
# ════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 用 comment_miner 生成的选题池测试
    candidates = load_candidates()
    print(f"候选选题: {len(candidates)} 条")

    if not candidates:
        # 如果有选题池数据就加载, 否则手动造
        candidates = [
            {"title": "翻毛皮到底能不能洗？一次说清楚", "content_type": "知识科普", "source": "comment_miner", "priority": "high"},
            {"title": "白鞋发黄怎么救？三个方法对比", "content_type": "知识科普", "source": "comment_miner", "priority": "high"},
            {"title": "洗鞋价格为什么有贵有便宜", "content_type": "知识科普", "source": "comment_miner", "priority": "medium"},
            {"title": "真皮和假皮怎么一眼分辨", "content_type": "知识科普", "source": "comment_miner", "priority": "medium"},
            {"title": "对比展示: AJ深度清洗前后", "content_type": "效果展示", "source": "manual", "hook_type": "A1", "structure_type": "contrast"},
            {"title": "客户故事: 一双穿了10年的马丁靴", "content_type": "经营故事", "source": "manual", "hook_type": "C1"},
            {"title": "本周会员日: 洗二送一", "content_type": "活动促销", "source": "manual", "hook_type": "D1"},
            {"title": "如何判断鞋子该洗还是该扔", "content_type": "知识科普", "source": "manual"},
        ]

    plan = assign_weekly_plan(candidates)
    print(format_week_plan(plan))
    print(f"\n已保存: {save_plan(plan)}")
