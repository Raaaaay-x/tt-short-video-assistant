"""
评论区情绪提炼 — 从评论中挖选题金矿

输入: 原始评论 (人工粘贴, 一行一条)
输出: 分类统计 + 高频问题 → 选题建议 + 回流 topic_planner 的标准格式

分类体系:
  - 共鸣: 表达同感、认同 ("我也是""太对了")
  - 提问: 询问信息 ("多少钱""在哪里""能洗XX吗")
  - 质疑: 怀疑或不信任 ("真的吗""骗人的吧")
  - 求教程: 想知道怎么做 ("能不能出一个教程")
  - 求资源: 要链接/地址/联系方式 ("地址在哪""有链接吗")
  - 延展选题: 评论本身就是一个话题 ("XX材质怎么保养")
  - 其他: 无法归类的

v2.0: LLM 分类 + 本地统计 + 选题回流
"""

import json
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

# 回流 topic_planner 的输出路径
TOPIC_POOL_PATH = Path(__file__).parent.parent / "outputs" / "topic_pool.jsonl"

CATEGORY_LABELS = ["共鸣", "提问", "质疑", "求教程", "求资源", "延展选题", "其他"]

CATEGORY_EXAMPLES = {
    "共鸣": "我也是这样 / 太对了 / 跟我的一样 / 确实 / 同意",
    "提问": "多少钱 / 在哪里 / 能洗XX吗 / 有XX吗 / 怎么弄的",
    "质疑": "真的吗 / 假的吧 / 骗人的 / 不信 / 不可能",
    "求教程": "出个教程 / 教一下 / 怎么做到的 / 想看过程",
    "求资源": "地址在哪 / 有链接吗 / 怎么联系 / 电话多少",
    "延展选题": "XX材质怎么保养 / XX鞋能修吗 / 为什么XX / 能不能讲一下XX",
}


@dataclass
class CommentItem:
    text: str
    category: str = ""       # 评论分类
    sentiment: str = ""      # positive / negative / neutral
    is_question: bool = False
    topic_idea: str = ""     # 如果可转化为选题, 提炼一句话


@dataclass
class MiningResult:
    source: str = ""                   # 视频链接/来源
    source_title: str = ""
    total_comments: int = 0
    categorized: dict = field(default_factory=dict)  # {category: count}
    questions: list = field(default_factory=list)     # 高频提问 (合并相似后)
    topic_ideas: list = field(default_factory=list)   # 可转化的选题列表
    raw_output: str = ""               # LLM 原始输出
    mined_at: str = ""


def build_mining_prompt(comments_text: str, video_context: str = "") -> str:
    """构造评论挖掘 prompt。"""
    return f"""你是短视频内容研究员。请分析以下视频的评论区, 挖掘隐藏的选题机会。

{video_context}

【评论区原文 (一行一条)】
{comments_text[:3000]}

请完成以下分析 (Markdown 格式):

## 1. 分类统计
将每条评论归类到: 共鸣 / 提问 / 质疑 / 求教程 / 求资源 / 延展选题 / 其他
统计每类数量。

## 2. 高频提问 TOP 5
把"提问"类型的问题去重归并, 列出最常被问的5个问题。
每个问题附出现次数。

## 3. 选题挖掘
从以下角度找出 3-5 个可转化为短视频选题的点:
- "提问"类中反复出现的问题 → 直接做成答疑视频
- "质疑"类中的怀疑 → 做成"验证"或"揭秘"视频
- "延展选题"类 → 已经是选题雏形
- "求教程"类 → 做成教程视频

每个选题写成一行: "[选题标题] | 来自评论: [原评论摘要] | 内容类型: [答疑/验证/教程/科普]"

## 4. 情绪总结
评论区整体情绪倾向? 用户最关心什么? 有什么未满足的需求? (2-3句话)"""


def parse_llm_output(raw: str) -> dict:
    """从 LLM 输出中提取结构化数据。"""
    result = {"questions": [], "topic_ideas": [], "summary": ""}

    # 尝试提取选题行 (格式: [标题] | 来自评论: xxx | 类型: xxx)
    topic_pattern = re.findall(r'\[(.+?)\]\s*\|\s*来自评论[：:]\s*(.+?)\s*\|\s*内容类型[：:]\s*(.+?)(?:\n|$)', raw)
    for title, source, ctype in topic_pattern:
        result["topic_ideas"].append({
            "title": title.strip(),
            "source_comment": source.strip(),
            "content_type": ctype.strip(),
        })

    # 尝试提取数字列表中的问题
    q_pattern = re.findall(r'\d+\.\s*\*?\*?"?(.+?[？?])"?\*?\*?\s*(?:\(|（)?(\d+)?次?(?:\)|）)?', raw)
    for q, count in q_pattern[:10]:
        result["questions"].append({
            "question": q.strip(),
            "frequency": int(count) if count else 1,
        })

    # 情绪总结: "情绪总结" 或 "4." 之后的内容
    summary_match = re.search(r'(?:情绪总结|情绪倾向)[\s\S]*?\n([\s\S]+?)$', raw)
    if summary_match:
        result["summary"] = summary_match.group(1).strip()[:200]

    return result


def mine_comments(
    comments_text: str,
    video_url: str = "",
    video_title: str = "",
    llm_call=None,  # 可注入 LLM 调用函数
) -> MiningResult:
    """
    主入口: 对评论做分类 + 挖掘选题。

    llm_call: async fn(prompt) -> str, 如果为 None 则只做本地统计
    """
    # 基础统计
    lines = [l.strip() for l in comments_text.split("\n") if l.strip()]
    # 去掉序号前缀 (如 "1. " "/ 用户: ")
    cleaned = []
    for l in lines:
        l = re.sub(r'^\d+[\.\、\s]+', '', l)
        l = re.sub(r'^[用户网友读者]+[：:]\s*', '', l)
        if len(l) >= 2:
            cleaned.append(l)

    result = MiningResult(
        source=video_url,
        source_title=video_title,
        total_comments=len(cleaned),
        mined_at=datetime.now().isoformat(),
    )

    if llm_call:
        context = f"视频: {video_title}" if video_title else ""
        prompt = build_mining_prompt(comments_text, context)
        try:
            raw = llm_call(prompt)
            result.raw_output = raw
            parsed = parse_llm_output(raw)
            result.questions = parsed["questions"]
            result.topic_ideas = parsed["topic_ideas"]
        except Exception as e:
            result.raw_output = f"LLM 调用失败: {e}"

    return result


def save_to_topic_pool(result: MiningResult) -> int:
    """
    将挖掘出的选题写入 topic_pool.jsonl, 供 topic_planner 消费。
    返回写入的选题数量。
    """
    TOPIC_POOL_PATH.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with open(TOPIC_POOL_PATH, "a", encoding="utf-8") as f:
        for idea in result.topic_ideas:
            record = {
                "title": idea.get("title", ""),
                "source": "comment_miner",
                "source_url": result.source,
                "source_title": result.source_title,
                "source_comment": idea.get("source_comment", ""),
                "content_type": idea.get("content_type", ""),
                "priority": "high" if idea.get("content_type") in ["答疑", "验证"] else "medium",
                "created_at": result.mined_at,
                "status": "new",
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    return count


def load_topic_pool(status: str = "new") -> list[dict]:
    """读取选题池。status: new / planned / produced (已产出的)"""
    if not TOPIC_POOL_PATH.exists():
        return []
    records = []
    with open(TOPIC_POOL_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    r = json.loads(line)
                    if status == "all" or r.get("status") == status:
                        records.append(r)
                except json.JSONDecodeError:
                    continue
    return records


# ════════════════════════════════════════════════════════
# 自测
# ════════════════════════════════════════════════════════

if __name__ == "__main__":
    sample = """
    1. 多少钱洗一双？
    2. 房山哪里有店？
    3. 翻毛皮的能洗吗？
    4. 太好用了！我上次洗完跟新的一样
    5. 能上门取送吗？
    6. 骗人的吧，怎么可能洗这么干净
    7. 能不能出一期AJ的保养教程
    8. 地址发一下
    9. 我也是这家洗的，确实不错
    10. 白鞋发黄能处理吗？
    11. 这个机器叫什么？
    12. 能不能讲讲怎么辨别真假皮
    13. 价格多少？贵不贵？
    14. 不敢相信这是洗完的效果
    """

    # 本地统计 (不调 LLM)
    result = mine_comments(sample, video_title="翻毛皮清洗效果展示")
    print(f"评论数: {result.total_comments}")

    # 模拟 LLM 输出解析
    mock_llm = """
## 1. 分类统计
共鸣: 2 | 提问: 7 | 质疑: 2 | 求教程: 1 | 求资源: 2 | 延展选题: 0

## 2. 高频提问 TOP 5
1. 多少钱/价格(3次)
2. 翻毛皮能洗吗(2次)
3. 地址在哪(2次)
4. 白鞋发黄能处理吗(1次)
5. 能上门取送吗(1次)

## 3. 选题挖掘
[翻毛皮到底能不能洗？一次说清楚] | 来自评论: 翻毛皮的能洗吗? | 内容类型: 答疑
[白鞋发黄怎么救？三个方法对比] | 来自评论: 白鞋发黄能处理吗? | 内容类型: 教程
[洗鞋价格为什么有贵有便宜？揭秘行业内幕] | 来自评论: 多少钱洗一双/贵不贵 | 内容类型: 科普
[真皮和假皮怎么一眼分辨] | 来自评论: 能不能讲讲怎么辨别真假皮 | 内容类型: 教程

## 4. 情绪总结
评论区以提问型为主, 用户最关心价格、地址和特殊材质处理能力。质疑类评论表明效果展示需要更多"过程可见"来建立信任。上门取送是未满足的便利性需求。
"""
    parsed = parse_llm_output(mock_llm)
    result.questions = parsed["questions"]
    result.topic_ideas = parsed["topic_ideas"]
    result.raw_output = mock_llm

    print(f"\n高频提问:")
    for q in result.questions[:5]:
        print(f"  - {q['question']} ({q['frequency']}次)")

    print(f"\n选题挖掘:")
    for idea in result.topic_ideas:
        print(f"  [{idea['content_type']}] {idea['title']}")
        print(f"    ← {idea['source_comment']}")

    # 写入选题池
    n = save_to_topic_pool(result)
    print(f"\n选题池: 写入 {n} 条 (共 {len(load_topic_pool('all'))} 条待规划)")
