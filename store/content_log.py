"""
内容日志 — 已产出脚本追踪 + 发布表现回填 + 周复盘

v2.0: JSONL 存储, 支持手动回填数据, 周复盘报告生成
"""

import json
from pathlib import Path
from datetime import date, datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional

LOG_PATH = Path(__file__).parent.parent / "outputs" / "content_log.jsonl"


@dataclass
class ContentEntry:
    id: str = ""
    title: str = ""
    platform: str = "抖音"
    content_type: str = ""          # 效果展示/知识科普/经营故事/活动促销
    hook_type: str = ""
    structure_type: str = ""
    published_at: str = ""          # ISO 日期
    script_file: str = ""           # 关联的脚本文件

    # 发布后表现 (48h 后回填)
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    completion_rate: float = 0.0    # 完播率
    engagement_rate: float = 0.0    # 互动率
    followers_gained: int = 0       # 涨粉

    # 线下转化 (鞋店核心)
    store_inquiries: int = 0        # 到店咨询量
    store_visits: int = 0           # 实际到店

    # 复盘
    notes: str = ""                 # 人工备注
    rating: int = 0                 # 1-5 自评
    learned: str = ""               # 学到了什么


def log_published(
    title: str,
    content_type: str,
    platform: str = "抖音",
    hook_type: str = "",
    structure_type: str = "",
    script_file: str = "",
    published_at: str = "",
) -> str:
    """记录一条已发布的内容 (发布时调用, 数据待回填)。"""
    import uuid

    entry = ContentEntry(
        id=uuid.uuid4().hex[:8],
        title=title,
        platform=platform,
        content_type=content_type,
        hook_type=hook_type,
        structure_type=structure_type,
        published_at=published_at or date.today().isoformat(),
        script_file=script_file,
    )

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    return entry.id


def backfill_performance(
    entry_id: str,
    views: int = 0,
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    saves: int = 0,
    completion_rate: float = 0.0,
    engagement_rate: float = 0.0,
    followers_gained: int = 0,
    store_inquiries: int = 0,
    store_visits: int = 0,
    rating: int = 0,
    notes: str = "",
    learned: str = "",
) -> bool:
    """48h 后回填发布数据。"""
    entries = load_log()
    updated = False

    for i, e in enumerate(entries):
        if e.get("id") == entry_id:
            e.update({
                "views": views, "likes": likes, "comments": comments,
                "shares": shares, "saves": saves,
                "completion_rate": completion_rate,
                "engagement_rate": engagement_rate,
                "followers_gained": followers_gained,
                "store_inquiries": store_inquiries,
                "store_visits": store_visits,
                "rating": rating, "notes": notes, "learned": learned,
            })
            entries[i] = e
            updated = True
            break

    if updated:
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    return updated


def load_log(days: int = 30) -> list[dict]:
    """读取最近 N 天的内容日志。"""
    if not LOG_PATH.exists():
        return []
    cutoff = date.today() - timedelta(days=days)
    records = []
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    r = json.loads(line)
                    pub = r.get("published_at", "")
                    if pub >= cutoff.isoformat():
                        records.append(r)
                except json.JSONDecodeError:
                    continue
    return records


def weekly_review(week_start: date | None = None) -> dict:
    """
    周复盘: 分析本周发布的内容表现。

    返回 dict 含:
      - 本周发布数
      - 按类型/平台/钩子的表现排行
      - 最佳表现内容
      - 到店转化汇总
    """
    today = date.today()
    monday = week_start or (today - timedelta(days=today.weekday()))
    sunday = monday + timedelta(days=6)

    entries = load_log(days=14)  # 多拉几天确保覆盖
    week_entries = [e for e in entries if monday.isoformat() <= e.get("published_at", "") <= sunday.isoformat()]

    if not week_entries:
        return {"week": f"{monday} → {sunday}", "published": 0, "message": "本周暂无发布记录"}

    # 按钩子/结构聚合
    by_hook = {}
    by_type = {}
    total_views = 0
    total_store = 0
    best = None
    best_score = 0

    for e in week_entries:
        h = e.get("hook_type", "unknown")
        by_hook[h] = by_hook.get(h, {"count": 0, "avg_views": 0, "avg_engagement": 0})
        by_hook[h]["count"] += 1
        by_hook[h]["avg_views"] += e.get("views", 0)

        ct = e.get("content_type", "unknown")
        by_type[ct] = by_type.get(ct, {"count": 0, "avg_views": 0})
        by_type[ct]["count"] += 1
        by_type[ct]["avg_views"] += e.get("views", 0)

        total_views += e.get("views", 0)
        total_store += e.get("store_visits", 0) + e.get("store_inquiries", 0)

        score = e.get("views", 0) * 0.3 + e.get("engagement_rate", 0) * 500
        if score > best_score:
            best_score = score
            best = e

    # 计算平均值
    for h in by_hook:
        if by_hook[h]["count"] > 0:
            by_hook[h]["avg_views"] = round(by_hook[h]["avg_views"] / by_hook[h]["count"])
    for ct in by_type:
        if by_type[ct]["count"] > 0:
            by_type[ct]["avg_views"] = round(by_type[ct]["avg_views"] / by_type[ct]["count"])

    return {
        "week": f"{monday} → {sunday}",
        "published": len(week_entries),
        "total_views": total_views,
        "total_store_inquiries": total_store,
        "by_hook": by_hook,
        "by_type": by_type,
        "best": {
            "title": best.get("title", "") if best else "",
            "views": best.get("views", 0) if best else 0,
            "hook": best.get("hook_type", "") if best else "",
            "learned": best.get("learned", "") if best else "",
        } if best else None,
        "content_with_feedback": sum(1 for e in week_entries if e.get("learned")),
    }


def insights() -> dict:
    """
    数据洞察引擎 — 从已发布数据中提取可执行的结论。

    返回:
      - hook_ranking: 钩子表现排行 (按完播/互动/涨粉)
      - type_ranking: 内容类型表现排行
      - best_time: 推测最佳发布时间 (粗略)
      - trend: 近两周对比
      - recommendations: 3-5 条具体建议
    """
    entries = load_log(days=60)
    if len(entries) < 3:
        return {"message": "数据不足，至少需要 3 条有回填数据的记录", "ready": False}

    # 只取有回填数据的记录
    with_data = [e for e in entries if e.get("views", 0) > 0]
    if len(with_data) < 2:
        return {"message": "回填数据不足，请至少回填 2 条的发布表现", "ready": False}

    # ── 钩子排行 ──
    hook_stats = {}
    for e in with_data:
        h = e.get("hook_type", "unknown")
        if h not in hook_stats:
            hook_stats[h] = {"count": 0, "views": 0, "completion": 0, "engagement": 0, "store": 0}
        hs = hook_stats[h]
        hs["count"] += 1
        hs["views"] += e.get("views", 0)
        hs["completion"] += e.get("completion_rate", 0)
        hs["engagement"] += e.get("engagement_rate", 0)
        hs["store"] += e.get("store_inquiries", 0) + e.get("store_visits", 0)

    for h in hook_stats:
        n = hook_stats[h]["count"]
        hook_stats[h]["avg_views"] = round(hook_stats[h]["views"] / n)
        hook_stats[h]["avg_completion"] = round(hook_stats[h]["completion"] / n, 3)
        hook_stats[h]["avg_engagement"] = round(hook_stats[h]["engagement"] / n, 3)
        hook_stats[h]["total_store"] = hook_stats[h]["store"]

    hook_ranking = sorted(hook_stats.items(), key=lambda x: x[1]["avg_completion"], reverse=True)
    best_hook = hook_ranking[0][0] if hook_ranking else "N/A"

    # ── 内容类型排行 (按到店转化) ──
    type_stats = {}
    for e in with_data:
        ct = e.get("content_type", "unknown")
        if ct not in type_stats:
            type_stats[ct] = {"count": 0, "views": 0, "store": 0}
        type_stats[ct]["count"] += 1
        type_stats[ct]["views"] += e.get("views", 0)
        type_stats[ct]["store"] += e.get("store_inquiries", 0) + e.get("store_visits", 0)

    for ct in type_stats:
        n = type_stats[ct]["count"]
        type_stats[ct]["avg_views"] = round(type_stats[ct]["views"] / n)
        type_stats[ct]["total_store"] = type_stats[ct]["store"]

    type_ranking = sorted(type_stats.items(), key=lambda x: x[1]["total_store"], reverse=True)
    best_type = type_ranking[0][0] if type_ranking else "N/A"

    # ── 趋势 (最近2周 vs 前2周) ──
    recent = [e for e in with_data if e.get("published_at", "") >= (date.today() - timedelta(days=14)).isoformat()]
    older = [e for e in with_data if e.get("published_at", "") < (date.today() - timedelta(days=14)).isoformat()]

    trend = "stable"
    if recent and older:
        recent_avg = sum(e.get("views", 0) for e in recent) / len(recent)
        older_avg = sum(e.get("views", 0) for e in older) / len(older)
        if older_avg > 0:
            change = (recent_avg - older_avg) / older_avg
            if change > 0.2:
                trend = "improving ↑"
            elif change < -0.2:
                trend = "declining ↓"
            else:
                trend = f"stable ({change:+.0%})"

    # ── 推荐 ──
    recommendations = []
    if best_hook and best_hook != "N/A":
        recommendations.append(f"多用 {best_hook} 钩子 — 完播率最高")
    if best_type and best_type != "N/A":
        recommendations.append(f"核心内容: {best_type} — 到店转化最多")
    if len(recent) < 2:
        recommendations.append("发布频率偏低，建议恢复到一周 5 条")
    if trend == "declining ↓":
        recommendations.append("近两周播放下滑，检查是否换钩子/结构，或平台算法调整")

    return {
        "ready": True,
        "total_with_data": len(with_data),
        "hook_ranking": [{"hook": h, **s} for h, s in hook_ranking],
        "type_ranking": [{"type": ct, **s} for ct, s in type_ranking],
        "best_hook": best_hook,
        "best_type": best_type,
        "trend": trend,
        "recommendations": recommendations,
    }


def format_insights(ins: dict) -> str:
    """格式化洞察为可读文本。"""
    if not ins.get("ready"):
        return f"数据洞察不可用: {ins.get('message')}"

    lines = [
        "# 📊 数据洞察",
        f"基于 {ins['total_with_data']} 条已回填数据",
        "",
        "## 🎯 钩子表现排行",
    ]
    for h in ins.get("hook_ranking", []):
        lines.append(
            f"- **{h['hook']}**: {h['count']}条, "
            f"均播 {h['avg_views']:,}, "
            f"完播率 {h['avg_completion']:.1%}, "
            f"互动率 {h['avg_engagement']:.1%}, "
            f"到店 {h['total_store']}次"
        )

    lines.extend([
        "",
        "## 📂 内容类型排行 (按到店转化)",
    ])
    for t in ins.get("type_ranking", []):
        lines.append(f"- **{t['type']}**: {t['count']}条, 均播 {t['avg_views']:,}, 到店 {t['total_store']}次")

    lines.extend([
        "",
        f"## 📈 趋势: {ins.get('trend', 'unknown')}",
        "",
        "## 💡 行动建议",
    ])
    for r in ins.get("recommendations", []):
        lines.append(f"- {r}")

    return "\n".join(lines)


def format_weekly_review(review: dict) -> str:
    """格式化周复盘为 Markdown。"""
    if review.get("message"):
        return f"# 周复盘 | {review['week']}\n\n{review['message']}"

    lines = [
        f"# 周复盘 | {review['week']}",
        "",
        f"## 📊 概览",
        f"- 发布: {review['published']} 条",
        f"- 总播放: {review['total_views']:,}",
        f"- 到店咨询/访问: {review['total_store_inquiries']} 次",
        f"- 已复盘: {review['content_with_feedback']} 条",
        "",
        "## 🎯 按钩子表现",
    ]

    for hook, stats in sorted(review.get("by_hook", {}).items(), key=lambda x: -x[1]["avg_views"]):
        lines.append(f"- {hook}: {stats['count']}条, 平均播放 {stats['avg_views']:,}")

    lines.extend(["", "## 📂 按内容类型表现"])
    for ct, stats in sorted(review.get("by_type", {}).items(), key=lambda x: -x[1]["avg_views"]):
        lines.append(f"- {ct}: {stats['count']}条, 平均播放 {stats['avg_views']:,}")

    if review.get("best"):
        b = review["best"]
        lines.extend(["", "## 🏆 本周最佳", f"- **{b['title']}**", f"- 播放: {b['views']:,}", f"- 钩子: {b['hook']}"])
        if b["learned"]:
            lines.append(f"- 复盘: {b['learned']}")

    return "\n".join(lines)


# ════════════════════════════════════════════════════════
# 自测
# ════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 1. 记录一条发布
    eid = log_published(
        title="翻毛皮清洗效果展示",
        content_type="效果展示",
        platform="抖音",
        hook_type="A1",
        structure_type="contrast",
    )
    print(f"记录发布: {eid}")

    # 2. 回填数据
    backfill_performance(
        eid,
        views=3200, likes=145, comments=28, shares=12, saves=18,
        completion_rate=0.52, engagement_rate=0.065,
        store_inquiries=5, store_visits=2,
        rating=4, learned="对比钩子完播率高于预期, 但CTA转化还需要优化",
    )

    # 3. 周复盘
    review = weekly_review()
    print("\n" + format_weekly_review(review))
