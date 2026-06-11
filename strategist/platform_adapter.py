"""
平台分发适配器 — 一条脚本, 三平台版本

输入: 抖音版脚本 (默认格式)
输出: 抖音 / 小红书 / 视频号 三个平台的适配版本

差异:
  抖音:   15-30秒, 强钩子, 大字幕, POI定位, 口语化
  小红书:  图文为主或短小视频, 封面决定点击, 标题含关键词, 收藏>点赞
  视频号:  1-3分钟, 观点密度高, 转发>点赞, 开头可温和, IP信任>内容刺激

v2.0: LLM 适配 + 本地规则校验
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"


PLATFORM_RULES = {
    "抖音": {
        "max_duration": "30秒",
        "hook_rule": "前3秒必须有强钩子, 第一句话决定生死",
        "subtitle": "大字 (手机竖屏, 小字看不清)",
        "cta": "评论区互动 / 引导关注",
        "extra": "带POI定位, 善用1-2秒停顿增加完播率",
        "tone": "口语化, 直给, 不需要铺垫",
    },
    "小红书": {
        "max_duration": "60秒视频或图文",
        "hook_rule": "封面决定点击率 (对比图 > 过程图 > 单图)",
        "subtitle": "标题含关键词 (被搜索的入口), 前5行是展开前的钩子",
        "cta": "引导收藏 (收藏=深度认同, 比点赞值钱)",
        "extra": "标签: 1-2热搜词 + 2-3精准词 + 1长尾词",
        "tone": "真实经验分享, 种草语气, 拒绝硬广感",
    },
    "视频号": {
        "max_duration": "1-3分钟",
        "hook_rule": "开头可以温和, 不需要抖音级刺激",
        "subtitle": "标题需要观点感 (让人想转发给朋友看)",
        "cta": "引导转发 (转发>点赞, 朋友圈扩散逻辑)",
        "extra": "内容可以更长更有深度, IP信任比内容刺激更重要",
        "tone": "从容, 有观点, 像一个懂行的朋友在分享",
    },
}


def build_adapt_prompt(script_text: str, target_platform: str) -> str:
    """构造平台适配 prompt。"""
    rules = PLATFORM_RULES.get(target_platform, PLATFORM_RULES["抖音"])

    return f"""你是短视频多平台分发专家。请将以下抖音版脚本, 适配为{target_platform}版本。

【原始脚本】
{script_text[:1500]}

【{target_platform}平台规则】
- 时长: {rules['max_duration']}
- 开头: {rules['hook_rule']}
- 视觉: {rules['subtitle']}
- 转化: {rules['cta']}
- 附加: {rules['extra']}
- 口吻: {rules['tone']}

【人设约束 — 三平台通用】
- 芮玛鞋城, 房山本地十余年鞋城
- 老板娘真人出镜, 店员手机拍摄
- 禁用: 家人们/宝子们/绝绝子/最好/第一/100%
- 口吻: 北京本地口语

请输出适配后的{target_platform}版本:
## {target_platform}版标题
## 正文/口播
## 标签/话题 (3-5个)
## 发布建议 (时间/频率/注意事项)"""


def adapt_to_platforms(
    script_text: str,
    platforms: list[str] | None = None,
    llm_call=None,
) -> dict[str, str]:
    """
    一条脚本 → 多平台版本。

    返回 {平台名: 适配后文本}
    """
    platforms = platforms or ["抖音", "小红书", "视频号"]
    results = {}

    for plat in platforms:
        if llm_call:
            prompt = build_adapt_prompt(script_text, plat)
            try:
                results[plat] = llm_call(prompt)
            except Exception as e:
                results[plat] = f"适配失败: {e}"
        else:
            results[plat] = f"(待 LLM 填充) {plat}版本提示词已生成"

    return results


def validate_platform_rules(text: str, platform: str) -> list[str]:
    """对适配后的文本做基本规则校验。"""
    issues = []
    rules = PLATFORM_RULES.get(platform, {})

    if platform == "小红书":
        if "收藏" not in text and "点赞" not in text:
            issues.append("小红书: 缺少收藏/点赞引导")
        if "#" not in text:
            issues.append("小红书: 缺少话题标签")

    if platform == "抖音":
        if "评论" not in text and "关注" not in text:
            issues.append("抖音: 缺少互动引导 (评论/关注)")

    if platform == "视频号":
        if "转发" not in text and "分享" not in text:
            issues.append("视频号: 缺少转发引导")

    return issues


def save_adapted_versions(
    original_title: str,
    versions: dict[str, str],
) -> list[str]:
    """保存多平台版本到文件。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    files = []

    for plat, text in versions.items():
        safe_plat = plat.replace("/", "-")
        filename = f"adapted_{safe_plat}_{ts}.md"
        filepath = OUTPUT_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {original_title} | {plat}版本\n\n")
            f.write(f"生成时间: {ts}\n\n---\n\n")
            f.write(text)
        files.append(str(filepath))

    return files


# ════════════════════════════════════════════════════════
# 自测
# ════════════════════════════════════════════════════════

if __name__ == "__main__":
    sample_script = """
【分镜脚本】
0-3秒: 脏鞋特写 | 你看这双鞋进来的样子...
3-8秒: 清洗过程 | 我们先用这个软化一下皮面
8-12秒: 干净成品 | 洗完以后你看, 跟新的差不多了
12-15秒: CTA | 还有什么鞋想洗的? 评论区告诉我

【帖子文案】
一双穿了三年的鞋, 洗完变化有多大? 👟
#洗鞋 #房山 #球鞋修复
"""

    # 无 LLM 模式: 只看 prompt 生成
    for plat in ["小红书", "视频号"]:
        prompt = build_adapt_prompt(sample_script, plat)
        print(f"\n{'='*40}")
        print(f"=== {plat}适配 Prompt (前 300 字) ===")
        print(prompt[:300])
        print("...")

    # 规则校验
    print("\n=== 规则校验测试 ===")
    test_xhs = "来看看这双鞋洗完之后的效果 #洗鞋 #房山 #球鞋修复 赶紧收藏学起来"
    issues = validate_platform_rules(test_xhs, "小红书")
    print(f"小红书: {issues if issues else '全部通过 ✅'}")

    test_dy = "这双鞋洗完真不错"
    issues = validate_platform_rules(test_dy, "抖音")
    print(f"抖音: {issues}")
