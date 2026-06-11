"""
视频拆解器 — v0.2: 输入逐字稿文本, 输出五层拆解结构化 dict

输入格式支持:
  纯文本 (无时间戳): "你看这双鞋进来的样子..."
  带时间戳: "[0:00-0:03] 【画面】...\n【口播】..."

输出 schema 见 CLAUDE.md 拆解维度章节
"""

from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class EmotionPoint:
    pct: str          # e.g. "0-25"
    emotion: str      # e.g. "好奇"


@dataclass
class DeconstructionResult:
    source_url: str = ""
    platform: str = ""
    title: str = ""
    deconstructed_at: str = ""
    hook_type: str = ""
    structure_type: str = ""
    emotion_curve: list = field(default_factory=list)
    speaking_style: dict = field(default_factory=dict)
    viral_hypothesis: str = ""
    migrate_score: int = 0
    migrate_notes: str = ""
    tags: list = field(default_factory=list)
    raw_transcript: str = ""


def deconstruct(
    transcript: str,
    source_url: str = "manual_transcript",
    platform: str = "抖音",
    title: str = "",
) -> dict:
    """
    主入口: 对一段逐字稿做五层拆解。

    当前版本: 返回结构化空壳 + 调用 LLM 实际拆解的逻辑见 tt_agent.py
    这里提供解析和 schema 验证。
    """
    result = DeconstructionResult(
        source_url=source_url,
        platform=platform,
        title=title or _guess_title(transcript),
        deconstructed_at=datetime.now().isoformat(),
        raw_transcript=transcript,
    )
    return asdict(result)


def parse_transcript(raw: str) -> list[dict]:
    """
    解析带格式的逐字稿, 按时间戳切段。
    返回 [{"time": "0-3s", "visual": "...", "voiceover": "..."}, ...]
    """
    if "【口播】" not in raw and "【画面】" not in raw:
        # 纯文本, 不做切分
        return [{"time": "full", "visual": "", "voiceover": raw}]

    segments = []
    # 简单按行解析
    current = {"time": "", "visual": "", "voiceover": ""}
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("[") and "]" in line[:15]:
            if current["voiceover"] or current["visual"]:
                segments.append(current)
            current = {"time": "", "visual": "", "voiceover": ""}
            time_part = line[1:].split("]")[0] if "]" in line else ""
            current["time"] = time_part
            rest = line[line.index("]")+1:].strip()
            if "【画面】" in rest:
                current["visual"] = rest.replace("【画面】", "").strip()
            elif "【口播】" in rest:
                current["voiceover"] = rest.replace("【口播】", "").strip()
        elif "【画面】" in line:
            current["visual"] = line.replace("【画面】", "").strip()
        elif "【口播】" in line:
            current["voiceover"] = line.replace("【口播】", "").strip()
    if current["voiceover"] or current["visual"]:
        segments.append(current)
    return segments


def _guess_title(transcript: str) -> str:
    """从逐字稿第一句话提取标题"""
    first_line = transcript.strip().split("\n")[0]
    if len(first_line) > 60:
        first_line = first_line[:60] + "..."
    return first_line if first_line else "未命名"


def count_sentence_lengths(segments: list[dict]) -> dict:
    """统计口播的单句长度分布"""
    all_text = " ".join(s.get("voiceover", "") for s in segments)
    # 按中文标点切句
    sentences = []
    for sep in ["。", "？", "！", "，"]:
        if not all_text:
            break
        parts = all_text.split(sep)
        if len(parts) > 1:
            sentences.extend(p for p in parts if p.strip())
            all_text = ""
    if not sentences:
        sentences = [all_text] if all_text.strip() else []

    lengths = [len(s) for s in sentences]
    if not lengths:
        return {"avg": 0, "min": 0, "max": 0, "count": 0}

    return {
        "avg": round(sum(lengths) / len(lengths), 1),
        "min": min(lengths),
        "max": max(lengths),
        "count": len(lengths),
    }


if __name__ == "__main__":
    sample = """
[0:00-0:03] 【画面】脏鞋特写，慢推镜头
【口播】你看这双鞋进来的样子...
[0:03-0:08] 【画面】清洗过程，手部特写
【口播】我们先用这个软化一下皮面，你看这个脏东西慢慢就出来了
"""

    segs = parse_transcript(sample)
    print(f"Parsed {len(segs)} segments:")
    for s in segs:
        print(f"  {s['time']}: 画面={s['visual'][:20]}... 口播={s['voiceover'][:30]}...")

    stats = count_sentence_lengths(segs)
    print(f"\nSentence stats: {stats}")

    result = deconstruct(sample, title="洗鞋效果对比")
    print(f"\nDeconstruction result keys: {list(result.keys())}")
