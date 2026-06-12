"""
对标库 — 拆解结果结构化沉淀 + 矩阵号 A/B 实验追踪

v2.0:
  - 拆解记录的完整 schema (含口播风格)
  - A/B 实验: 同一选题两个账号不同钩子/结构, 48h 数据回收
  - 统计分析: 按平台/钩子/结构/实验结论查询
"""

import json
import uuid
from pathlib import Path
from datetime import datetime, date
from dataclasses import dataclass, field, asdict
from typing import Optional

CORPUS_PATH = Path(__file__).parent.parent / "outputs" / "corpus.jsonl"
EXPERIMENT_PATH = Path(__file__).parent.parent / "outputs" / "experiments.jsonl"


# ══════════════════════════════════════════════════════════════
# 拆解记录
# ══════════════════════════════════════════════════════════════

@dataclass
class SpeakingStyle:
    avg_sentence_len: int = 0
    pause_positions: list = field(default_factory=list)
    tone_shifts: list = field(default_factory=list)


@dataclass
class DeconRecord:
    id: str = ""
    source_url: str = ""
    platform: str = "抖音"
    title: str = ""
    deconstructed_at: str = ""
    hook_type: str = ""           # A1/B1/C1/D1
    structure_type: str = ""      # contrast/knowledge
    emotion_curve: list = field(default_factory=list)
    speaking_style: dict = field(default_factory=dict)
    viral_hypothesis: str = ""
    migrate_score: int = 0        # 1-5
    migrate_notes: str = ""
    tags: list = field(default_factory=list)
    # v2.0 新增
    has_experiment: bool = False  # 是否已开 A/B 测试
    experiment_id: str = ""


def save_deconstruction(record: dict) -> str:
    """追加一条拆解记录到对标库, 返回记录 ID。"""
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    record.setdefault("id", uuid.uuid4().hex[:8])
    record.setdefault("deconstructed_at", datetime.now().isoformat())
    record.setdefault("tags", [])
    record.setdefault("has_experiment", False)
    record.setdefault("experiment_id", "")
    record.setdefault("emotion_curve", [])
    record.setdefault("speaking_style", {})
    record.setdefault("migrate_notes", "")

    with open(CORPUS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record["id"]


def load_corpus() -> list[dict]:
    """读取全部对标记录。"""
    if not CORPUS_PATH.exists():
        return []
    records = []
    with open(CORPUS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def search_by_tag(tag: str) -> list[dict]:
    """按标签搜索对标记录。"""
    return [r for r in load_corpus() if tag in r.get("tags", [])]


def search(
    query: str = "",
    hook_type: str = "",
    structure_type: str = "",
    platform: str = "",
    min_score: int = 0,
    has_experiment: bool | None = None,
    sort_by: str = "date",   # date / score / relevance
    limit: int = 20,
) -> list[dict]:
    """
    对标库多维检索。

    示例:
      search(query="洗鞋", hook_type="A1", min_score=3)
      search(query="", platform="小红书", has_experiment=True)
      search(query="翻毛皮", sort_by="score")
    """
    records = load_corpus()
    results = []

    query_lower = query.lower() if query else ""

    for r in records:
        # 文本匹配 (title + hypothesis + tags + migrate_notes)
        if query_lower:
            search_text = " ".join([
                r.get("title", ""),
                r.get("viral_hypothesis", ""),
                r.get("migrate_notes", ""),
                " ".join(r.get("tags", [])),
            ]).lower()

            # 支持多关键词 (空格分隔), OR 逻辑
            keywords = query_lower.split()
            if not any(kw in search_text for kw in keywords):
                continue

        # 精确过滤
        if hook_type and r.get("hook_type") != hook_type:
            continue
        if structure_type and r.get("structure_type") != structure_type:
            continue
        if platform and r.get("platform") != platform:
            continue
        if min_score and r.get("migrate_score", 0) < min_score:
            continue
        if has_experiment is not None and r.get("has_experiment") != has_experiment:
            continue

        # 计算相关性 (简单: 关键词命中数)
        if query_lower:
            r["_relevance"] = sum(
                1 for kw in keywords
                if kw in (r.get("title","") + r.get("viral_hypothesis","") + r.get("migrate_notes","")).lower()
            )
        else:
            r["_relevance"] = 0

        results.append(r)

    # 排序
    if sort_by == "score":
        results.sort(key=lambda r: r.get("migrate_score", 0), reverse=True)
    elif sort_by == "relevance":
        results.sort(key=lambda r: r.get("_relevance", 0), reverse=True)
    else:  # date
        results.sort(key=lambda r: r.get("deconstructed_at", ""), reverse=True)

    return results[:limit]


def list_hook_types() -> list[str]:
    """列出对标库中所有钩子类型及使用次数。"""
    counts = {}
    for r in load_corpus():
        h = r.get("hook_type", "")
        if h:
            counts[h] = counts.get(h, 0) + 1
    return sorted(counts, key=counts.get, reverse=True)  # type: ignore


def list_structure_types() -> list[str]:
    """列出对标库中所有结构类型及使用次数。"""
    counts = {}
    for r in load_corpus():
        s = r.get("structure_type", "")
        if s:
            counts[s] = counts.get(s, 0) + 1
    return sorted(counts, key=counts.get, reverse=True)  # type: ignore


# ══════════════════════════════════════════════════════════════
# A/B 实验追踪
# ══════════════════════════════════════════════════════════════

@dataclass
class ExperimentBranch:
    """实验分支: 一个账号的一组参数"""
    account: str           # "主号" / "流量号" / "矩阵号-3"
    hook_type: str         # 用的钩子
    structure_type: str    # 用的结构
    published_at: str = "" # ISO 日期
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0         # 收藏 (小红书核心指标)
    engagement_rate: float = 0.0  # 互动率
    completion_rate: float = 0.0  # 完播率
    store_inquiries: int = 0      # 到店咨询量 (线下业务核心)


@dataclass
class Experiment:
    id: str = ""
    title: str = ""                 # 实验名称
    topic: str = ""                 # 选题
    hypothesis: str = ""            # 被测试的爆款假设
    decon_id: str = ""             # 关联的对标记录
    branch_a: dict = field(default_factory=dict)  # ExperimentBranch
    branch_b: dict = field(default_factory=dict)  # ExperimentBranch
    result: str = ""               # 结论
    winner: str = ""               # "A" / "B" / "tie"
    learned_at: str = ""           # 得出结论的日期
    created_at: str = ""


def start_experiment(
    title: str,
    topic: str,
    hypothesis: str,
    decon_id: str,
    account_a: str,
    hook_a: str,
    structure_a: str,
    account_b: str,
    hook_b: str,
    structure_b: str,
) -> str:
    """
    发起一次 A/B 测试。

    示例:
    start_experiment(
        title="洗鞋展示: 身份认同 vs 反常识",
        topic="翻毛皮清洗效果展示",
        hypothesis="身份认同钩子在本地服务业的完播率 > 反常识钩子",
        decon_id="344e8b36",
        account_a="芮玛鞋城主号", hook_a="C1", structure_a="contrast",
        account_b="洗鞋技术号",  hook_b="B1", structure_b="knowledge",
    )
    """
    exp_id = uuid.uuid4().hex[:8]
    now = datetime.now().isoformat()

    exp = Experiment(
        id=exp_id,
        title=title,
        topic=topic,
        hypothesis=hypothesis,
        decon_id=decon_id,
        branch_a=asdict(ExperimentBranch(
            account=account_a, hook_type=hook_a, structure_type=structure_a,
            published_at=date.today().isoformat(),
        )),
        branch_b=asdict(ExperimentBranch(
            account=account_b, hook_type=hook_b, structure_type=structure_b,
            published_at=date.today().isoformat(),
        )),
        created_at=now,
    )

    EXPERIMENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EXPERIMENT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(exp), ensure_ascii=False) + "\n")

    # 更新对标记录的关联
    _update_decon_experiment(decon_id, exp_id)

    return exp_id


def log_experiment_result(
    exp_id: str,
    branch: str,  # "A" or "B"
    views: int = 0,
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    saves: int = 0,
    engagement_rate: float = 0.0,
    completion_rate: float = 0.0,
    store_inquiries: int = 0,
    result: str = "",
    winner: str = "",
) -> bool:
    """
    48h 后回填实验数据 + 结论。
    """
    experiments = load_experiments()
    updated = False

    for i, exp in enumerate(experiments):
        if exp.get("id") != exp_id:
            continue

        branch_key = f"branch_{branch.lower()}"
        if branch_key in exp:
            exp[branch_key].update({
                "views": views, "likes": likes, "comments": comments,
                "shares": shares, "saves": saves,
                "engagement_rate": engagement_rate,
                "completion_rate": completion_rate,
                "store_inquiries": store_inquiries,
            })

        if result:
            exp["result"] = result
        if winner:
            exp["winner"] = winner
        exp["learned_at"] = datetime.now().isoformat()

        experiments[i] = exp
        updated = True
        break

    if updated:
        _write_experiments(experiments)

    return updated


def load_experiments() -> list[dict]:
    """读取全部实验记录。"""
    if not EXPERIMENT_PATH.exists():
        return []
    records = []
    with open(EXPERIMENT_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def get_experiment(exp_id: str) -> dict | None:
    for e in load_experiments():
        if e.get("id") == exp_id:
            return e
    return None


def list_experiments(status: str = "all") -> list[dict]:
    """
    列出实验。
    status: "all" / "pending" (未回填) / "concluded" (已出结论)
    """
    all_exp = load_experiments()
    if status == "pending":
        return [e for e in all_exp if not e.get("result")]
    if status == "concluded":
        return [e for e in all_exp if e.get("result")]
    return all_exp


def experiment_stats() -> dict:
    """实验统计: 哪种钩子/结构胜率最高。"""
    concluded = list_experiments("concluded")
    if not concluded:
        return {"total_experiments": 0}

    hook_wins = {}     # hook_type → win count
    structure_wins = {}
    hypotheses_tested = []
    wins_by_account = {}

    for e in concluded:
        hypotheses_tested.append(e.get("hypothesis", ""))
        winner = e.get("winner", "")
        if winner:
            winning_branch = e.get(f"branch_{winner.lower()}", {})
            h = winning_branch.get("hook_type", "")
            s = winning_branch.get("structure_type", "")
            a = winning_branch.get("account", "")
            hook_wins[h] = hook_wins.get(h, 0) + 1
            structure_wins[s] = structure_wins.get(s, 0) + 1
            wins_by_account[a] = wins_by_account.get(a, 0) + 1

    return {
        "total_experiments": len(concluded),
        "hook_win_rate": hook_wins,
        "structure_win_rate": structure_wins,
        "wins_by_account": wins_by_account,
        "latest_hypothesis": hypotheses_tested[-1] if hypotheses_tested else "",
        "best_hook": max(hook_wins, key=hook_wins.get) if hook_wins else "N/A",
        "best_structure": max(structure_wins, key=structure_wins.get) if structure_wins else "N/A",
    }


# ══════════════════════════════════════════════════════════════
# 综合统计
# ══════════════════════════════════════════════════════════════

def stats() -> dict:
    """对标库 + 实验库综合统计。"""
    records = load_corpus()
    exp_stats = experiment_stats()

    platforms = {}
    hook_types = {}
    avg_migrate = 0
    for r in records:
        p = r.get("platform", "unknown")
        platforms[p] = platforms.get(p, 0) + 1
        h = r.get("hook_type", "unknown")
        hook_types[h] = hook_types.get(h, 0) + 1
        avg_migrate += r.get("migrate_score", 0)

    corpus_stat = {
        "total": len(records),
        "with_experiment": sum(1 for r in records if r.get("has_experiment")),
        "by_platform": platforms,
        "by_hook_type": hook_types,
        "avg_migrate_score": round(avg_migrate / len(records), 1) if records else 0,
    }

    return {**corpus_stat, **exp_stats}


# ══════════════════════════════════════════════════════════════
# 内部方法
# ══════════════════════════════════════════════════════════════

def _update_decon_experiment(decon_id: str, exp_id: str):
    records = load_corpus()
    updated = False
    for i, r in enumerate(records):
        if r.get("id") == decon_id:
            r["has_experiment"] = True
            r["experiment_id"] = exp_id
            records[i] = r
            updated = True
            break

    if updated:
        # 重写 corpus (JSONL 不支持原位更新, 先读后写)
        with open(CORPUS_PATH, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _write_experiments(experiments: list[dict]):
    with open(EXPERIMENT_PATH, "w", encoding="utf-8") as f:
        for e in experiments:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


# ══════════════════════════════════════════════════════════════
# 自测
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 1. 存一条拆解
    decon = {
        "source_url": "manual_transcript",
        "platform": "抖音",
        "title": "翻毛皮清洗对比",
        "hook_type": "A1",
        "structure_type": "contrast",
        "emotion_curve": [
            {"pct": "0-25", "emotion": "好奇"},
            {"pct": "25-75", "emotion": "投入"},
            {"pct": "75-100", "emotion": "满足"},
        ],
        "viral_hypothesis": "洗鞋视频的对比钩子完播率最高, 因为结果展示本身就是最直接的信任证明",
        "migrate_score": 5,
        "migrate_notes": "直接适配芮玛鞋城, 不挑拍摄水平, 手机即可",
        "tags": ["洗鞋", "对比", "翻毛皮"],
    }
    decon_id = save_deconstruction(decon)
    print(f"拆解记录: {decon_id}")

    # 2. 发起 A/B 实验
    exp_id = start_experiment(
        title="洗鞋展示: 对比钩子 vs 反常识钩子",
        topic="翻毛皮清洗效果展示",
        hypothesis="对比钩子(A1)在本地洗鞋的完播率 > 反常识钩子(B1), 因为结果展示本身就是信任证明",
        decon_id=decon_id,
        account_a="芮玛鞋城主号", hook_a="A1", structure_a="contrast",
        account_b="洗鞋技术号", hook_b="B1", structure_b="knowledge",
    )
    print(f"实验发起: {exp_id}")

    # 3. 48h 后回填数据
    log_experiment_result(
        exp_id=exp_id, branch="A",
        views=4200, likes=185, comments=32, shares=15, saves=28,
        engagement_rate=0.062, completion_rate=0.58, store_inquiries=8,
    )
    log_experiment_result(
        exp_id=exp_id, branch="B",
        views=2800, likes=210, comments=47, shares=22, saves=35,
        engagement_rate=0.112, completion_rate=0.41, store_inquiries=3,
        result="B1 互动率更高但 A1 到店咨询多。结论: 主号用对比钩子(转化), 流量号用反常识钩子(互动)",
        winner="tie",
    )

    # 4. 查看统计
    print("\n=== 综合统计 ===")
    import pprint
    pprint.pprint(stats())

    print("\n=== 实验列表 ===")
    for e in list_experiments():
        print(f"  {e['id']}: {e['title']} → winner={e.get('winner','pending')}")
