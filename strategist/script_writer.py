"""
脚本二创器 — 输入拆解结果 + 人设约束, 输出可直接拍摄的分镜脚本

v0.2: LLM 调用由 tt_agent.py 编排, 这里提供 prompt 构造和输出格式化
"""

from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime

from templates.hooks import HOOKS
from templates.structures import STRUCTURES


# ── 人设约束 (从 CLAUDE.md 提取, 后续统一读到 config) ──

PERSONA_CONSTRAINTS = """
【人设约束 — 脚本必须遵守】
1. 开场第一句话必须是「我们家」「我们店里」「房山这边」三选一
2. 每 10 句话里至少出现一次「你看」/「你看这个」(引导视线)
3. 口播单句不超过 15 字, 超过时必须拆成两句
4. 禁止书面语和专业术语堆砌 —— 说人话
5. 禁止「家人们」「宝子们」「绝绝子」「冲」「yyds」
6. 情绪词用北京口语风格: 「真不错」「可以看看」「挺值的」「还行」
7. 拍摄场景只在店内 (操作台、货架、前台), 拒绝棚拍感
8. 提到鞋名时带上本地消费者的叫法, 不要太专业
"""


@dataclass
class ScriptOutput:
    title: str = ""
    inspiration_url: str = ""
    target_platform: str = "抖音"
    content_type: str = ""
    estimated_duration: str = ""
    hook_type: str = ""
    structure_type: str = ""
    segments: list = field(default_factory=list)      # 分镜表
    voiceover_full: str = ""                            # 完整口播
    caption: str = ""                                   # 帖子文案
    guardrail_result: dict = field(default_factory=dict)
    created_at: str = ""


def build_deconstruct_prompt(transcript: str) -> str:
    """构造拆解 prompt (给 LLM 的五层拆解指令)。"""
    return f"""你是资深短视频内容研究员。请对以下视频逐字稿做五层拆解。

{transcript}

请输出 (直接给内容, 不用解释):

1. 钩子类型: 前3秒用了什么钩子? 属于哪类 (对比/反常识/身份认同/教学展示)? 为什么有效?

2. 叙事结构: 时间线分段 (0-3s做什么, 3-8s做什么...), 每段的信息密度 (1-3分)

3. 情绪曲线: 0-25%什么情绪? 25-75%什么情绪? 75-100%什么情绪?

4. 口播节奏: 平均单句长度? 停顿位置? 语气变化点?

5. 爆款假设 (最重要): 这条能火, 核心原因是什么? 给一个可证伪的假设。这个点搬到鞋店/洗鞋行业可行吗?"""


def build_rewrite_prompt(
    deconstruct_result: dict,
    hook_id: str = "A1",
    structure_id: str = "contrast",
    target_platform: str = "抖音",
) -> str:
    """构造二创 prompt (基于拆解结果 + 人设约束)。"""
    hook = HOOKS.get(hook_id, HOOKS["A1"])
    structure = STRUCTURES.get(structure_id, STRUCTURES["contrast"])

    segments_desc = "\n".join(
        f"  {s['time']} {s['role']}: {s['desc']} (信息密度: {s['info_density']})"
        for s in structure["segments"]
    )

    return f"""你是芮玛鞋城的短视频编导。账号背景: 房山本地经营十余年的多品牌鞋城, 老板娘真人出镜, 店员手机拍摄。

请根据以下对标分析, 为芮玛鞋城二创一条短视频脚本。

【对标视频拆解】
- 钩子类型: {deconstruct_result.get('hook_type', '未知')}
- 叙事结构: {deconstruct_result.get('structure_type', '未知')}
- 情绪曲线: {deconstruct_result.get('emotion_curve', [])}
- 爆款假设: {deconstruct_result.get('viral_hypothesis', '')}
- 原视频逐字稿: {deconstruct_result.get('raw_transcript', '')[:500]}...

【二创要求】
- 使用钩子: {hook['name']} (示例开头: {hook['opening_example']})
- 使用结构: {structure['name']}
- 结构模板:
{segments_desc}
- 情绪线: {structure['emotion_map']}
- 目标平台: {target_platform}
- 内容类型: 洗鞋/鞋类相关内容

{PERSONA_CONSTRAINTS}

请输出完整的二创脚本, 格式:
### 分镜脚本
| 时间段 | 画面 | 口播 | 字幕/特效 |

### 完整口播逐字稿
(连续文本)

### 帖子文案
(含3-5个hashtag)"""


def format_script_output(
    deconstruct_result: dict,
    hook_id: str,
    structure_id: str,
    target_platform: str,
    llm_response: str,
) -> dict:
    """将 LLM 输出包装为 ScriptOutput。"""
    hook = HOOKS.get(hook_id, {})
    structure = STRUCTURES.get(structure_id, {})

    return {
        "title": deconstruct_result.get("title", "") + " [二创]",
        "inspiration_url": deconstruct_result.get("source_url", ""),
        "target_platform": target_platform,
        "content_type": structure.get("best_for", [""])[0] if structure.get("best_for") else "",
        "estimated_duration": structure.get("segments", [{}])[-1].get("time", "").split("-")[-1] if structure.get("segments") else "15秒",
        "hook_type": f"{hook_id} ({hook.get('name', '')})",
        "structure_type": f"{structure_id} ({structure.get('name', '')})",
        "segments": [],  # 从 llm_response 中解析, 第一版手工确认
        "voiceover_full": "",
        "caption": "",
        "created_at": datetime.now().isoformat(),
    }


def save_script(script: dict, output_dir: str | None = None) -> str:
    """保存脚本到 outputs/"""
    out = Path(output_dir) if output_dir else Path(__file__).parent.parent / "outputs"
    out.mkdir(parents=True, exist_ok=True)

    title = script.get("title", "untitled").replace(" ", "_").replace("/", "-")[:40]
    filename = f"{title}_{script.get('created_at', '')[:10]}.md"
    filepath = out / filename

    lines = [
        f"# {script.get('title', '')}",
        "",
        f"- 灵感来源: {script.get('inspiration_url', '')}",
        f"- 目标平台: {script.get('target_platform', '')}",
        f"- 内容类型: {script.get('content_type', '')}",
        f"- 预计时长: {script.get('estimated_duration', '')}",
        f"- 钩子: {script.get('hook_type', '')}",
        f"- 结构: {script.get('structure_type', '')}",
        f"- 生成时间: {script.get('created_at', '')}",
        "",
        "---",
        "",
        "## 分镜脚本",
        script.get("voiceover_full", "(LLM response to be filled)"),
        "",
        "## 帖子文案",
        script.get("caption", ""),
        "",
        "---",
        "",
        "*本脚本由 tt_agent 自动生成, 发布前请人工确认。*",
    ]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return str(filepath)


def save_raw_llm_response(response: str, deconstruct_result: dict, output_dir: str | None = None) -> str:
    """保存 LLM 原始响应 (用于 human-in-the-loop 确认前查看)。"""
    out = Path(output_dir) if output_dir else Path(__file__).parent.parent / "outputs"
    out.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    filepath = out / f"draft_{ts}.md"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# 二创草稿 | {ts}\n\n")
        f.write(f"## 对标信息\n")
        f.write(f"- 来源: {deconstruct_result.get('source_url', '')}\n")
        f.write(f"- 平台: {deconstruct_result.get('platform', '')}\n")
        f.write(f"- 钩子: {deconstruct_result.get('hook_type', '')}\n")
        f.write(f"- 结构: {deconstruct_result.get('structure_type', '')}\n")
        f.write(f"- 爆款假设: {deconstruct_result.get('viral_hypothesis', '')}\n")
        f.write(f"\n---\n\n")
        f.write(response)

    return str(filepath)
