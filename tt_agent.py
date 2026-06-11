"""
tt_agent — 短视频内容情报 + 生产工具

v0.2 最小闭环:
  逐字稿 → 五层拆解 → 脚本二创 → Guardrail 检查 → 输出

用法:
  python tt_agent.py                                    # 交互式输入逐字稿
  python tt_agent.py --input sample_transcript.txt      # 从文件读取
  python tt_agent.py --deconstruct-only                  # 只拆解, 不二创

输出:
  outputs/draft_*.md          LLM 原始响应 (human-in-the-loop 确认用)
  outputs/*.md                最终脚本
  outputs/corpus.jsonl        对标库追加
"""

import sys
from pathlib import Path
from datetime import datetime

# 项目根
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from analyst.deconstructor import deconstruct, parse_transcript
from strategist.guardrail import run_guardrail, format_guardrail_report
from strategist.script_writer import (
    build_deconstruct_prompt,
    build_rewrite_prompt,
    format_script_output,
    save_script,
    save_raw_llm_response,
)
from store.corpus import save_deconstruction


def step1_deconstruct(transcript: str, source_url: str = "") -> dict:
    """Step 1-2: 拆解 (先本地解析 + 生成 LLM prompt)"""
    print("=" * 60)
    print("[Step 1-2] 视频理解 + 结构拆解")

    # 本地解析
    segments = parse_transcript(transcript)
    print(f"  解析出 {len(segments)} 个片段")

    # 生成拆解 prompt (供 LLM 使用)
    llm_prompt = build_deconstruct_prompt(transcript)

    # 基础结构
    result = deconstruct(transcript, source_url=source_url)

    result["_llm_prompt"] = llm_prompt
    result["_segments"] = segments

    print("  拆解 prompt 已生成 (待 LLM 填充)")
    return result


def step2_rewrite(deconstruct_result: dict) -> dict:
    """Step 5: 脚本二创 (生成 prompt + 保存草稿)"""
    print("=" * 60)
    print("[Step 5] 选题规划 + 脚本二创")

    llm_prompt = build_rewrite_prompt(
        deconstruct_result,
        hook_id="A1",
        structure_id="contrast",
        target_platform="抖音",
    )

    script = format_script_output(
        deconstruct_result,
        hook_id="A1",
        structure_id="contrast",
        target_platform="抖音",
        llm_response="",
    )

    script["_llm_prompt"] = llm_prompt
    script["_deconstruct_result"] = deconstruct_result

    print("  二创 prompt 已生成 (待 LLM 填充)")
    return script


def step3_guardrail(final_text: str) -> dict:
    """Guardrail 检查"""
    print("=" * 60)
    print("[Guardrail] 合规与风险过滤")
    result = run_guardrail(final_text)
    print(format_guardrail_report(result))
    return {"passed": result.passed, "issues": result.suggestions}


def run_pipeline(transcript: str, source_url: str = "") -> dict:
    """完整流水线: 拆解 → 二创 → Guardrail → 保存"""
    print("\n" + "=" * 60)
    print("  tt_agent v0.2 — 短视频内容生产管线")
    print("=" * 60)
    print(f"  输入长度: {len(transcript)} 字符")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Step 1-2: 拆解
    decon = step1_deconstruct(transcript, source_url)

    # Step 5: 二创
    script = step2_rewrite(decon)

    # 保存对标记录
    decon_id = save_deconstruction({
        "source_url": source_url or "manual_transcript",
        "platform": decon.get("platform", "抖音"),
        "title": decon.get("title", ""),
        "hook_type": "",
        "structure_type": "",
        "emotion_curve": [],
        "viral_hypothesis": "",
        "migrate_score": 0,
        "tags": [],
    })
    print(f"\n  对标记录已保存: corpus.jsonl (id={decon_id})")

    # 保存 LLM prompt 文件 (用户复制到 LLM 执行后回填)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    decon_prompt_path = ROOT / "outputs" / f"prompt_deconstruct_{ts}.md"
    decon_prompt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(decon_prompt_path, "w", encoding="utf-8") as f:
        f.write(f"# 拆解 Prompt\n\n{decon['_llm_prompt']}")
    print(f"  拆解 prompt 已保存: {decon_prompt_path}")

    rewrite_prompt_path = ROOT / "outputs" / f"prompt_rewrite_{ts}.md"
    with open(rewrite_prompt_path, "w", encoding="utf-8") as f:
        f.write(f"# 二创 Prompt\n\n{script['_llm_prompt']}")
    print(f"  二创 prompt 已保存: {rewrite_prompt_path}")

    print("\n" + "=" * 60)
    print("  管线完成。")
    print(f"  下一步: 将 prompt 复制到 LLM (Claude/GPT) 执行,")
    print(f"  回填结果后运行 python tt_agent.py --finalize")
    print("=" * 60)

    return {
        "deconstruction": decon,
        "script_draft": script,
        "corpus_id": decon_id,
    }


def interactive():
    """交互式输入逐字稿"""
    print("=" * 60)
    print("  tt_agent v0.2 — 交互模式")
    print("  粘贴视频逐字稿 (输入空行结束) Ctrl+D 退出)")
    print("=" * 60)

    lines = []
    source_url = input("对标视频链接 (直接回车跳过): ").strip()

    print("\n粘贴逐字稿:")
    try:
        while True:
            line = input()
            if line.strip() == "":
                if lines and lines[-1].strip() == "":
                    break
            lines.append(line)
    except (EOFError, KeyboardInterrupt):
        pass

    transcript = "\n".join(lines).strip()
    if not transcript:
        print("未输入逐字稿, 退出。")
        return

    return run_pipeline(transcript, source_url)


if __name__ == "__main__":
    if "--input" in sys.argv:
        idx = sys.argv.index("--input")
        filepath = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        if not filepath or not Path(filepath).exists():
            print(f"文件不存在: {filepath}")
            sys.exit(1)
        transcript = Path(filepath).read_text(encoding="utf-8")
        source = sys.argv[sys.argv.index("--source") + 1] if "--source" in sys.argv else ""
        run_pipeline(transcript, source)
    else:
        interactive()
