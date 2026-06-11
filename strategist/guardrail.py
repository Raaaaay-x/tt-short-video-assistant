"""
合规与风险过滤 — 脚本输出前的强制关卡

三道检查 (任何一道不通过即返回修改建议):
  1. 隐私安全检查
  2. 广告法合规检查
  3. 人设一致性检查
"""

from dataclasses import dataclass, field


# ── 禁用词库 ──

AD_LAW_FORBIDDEN = [
    "最好", "第一", "第一品牌", "100%", "彻底", "永久", "绝对", "唯一",
    "国家级", "世界级", "顶级", "极致", "最低价", "底价", "工厂底价",
    "全网最低", "史上最低", "最便宜", "保证", "包治", "根治",
]

PRIVACY_RED_FLAGS = [
    # 匹配后需要人工确认
    "儿子叫", "女儿叫", "孩子叫", "我家住", "我们家在",
    "手机号", "身份证", "几点下班", "几点关门", "一个人看店",
]

PERSONA_FORBIDDEN = [
    # 过度网感用词 —— 老板娘人设禁用
    "家人们", "宝子们", "绝绝子", "冲", "yyds", "绝了",
    "给我冲", "兄弟们", "姐妹们",
]

PERSONA_REQUIRED = [
    # 人设必须包含的元素 (至少出现一个)
    "我们家", "我们店里", "房山这边", "你看", "你看这个", "师傅",
]


@dataclass
class GuardrailResult:
    passed: bool = True
    privacy_issues: list = field(default_factory=list)
    ad_law_issues: list = field(default_factory=list)
    persona_issues: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)


def check_privacy(text: str) -> list[str]:
    """检查隐私风险"""
    issues = []
    for flag in PRIVACY_RED_FLAGS:
        if flag in text:
            issues.append(f"隐私风险: 文本包含「{flag}」, 建议模糊化处理")
    return issues


def check_ad_law(text: str) -> list[str]:
    """检查广告法合规"""
    issues = []
    for word in AD_LAW_FORBIDDEN:
        if word in text:
            issues.append(f"广告法风险: 使用了禁用词「{word}」, 建议替换")
    return issues


def check_persona(text: str) -> list[str]:
    """检查人设一致性"""
    issues = []

    # 检查禁用词
    for word in PERSONA_FORBIDDEN:
        if word in text:
            issues.append(f"人设风险: 使用了过度网感用词「{word}」, 不符合老板娘人设")

    # 检查必须元素
    has_required = any(req in text for req in PERSONA_REQUIRED)
    if not has_required:
        issues.append("人设风险: 脚本缺少本地/真人感元素 (我们家/我们店里/房山这边/你看), 可能不像真人")

    # 检查口播句长
    lines = [l for l in text.split("\n") if l.strip() and not l.startswith("[") and not l.startswith("#")]
    long_lines = [l for l in lines if len(l) > 15 and ("【口播】" in l or not l.startswith("【"))]
    if len(long_lines) > len(lines) * 0.3:
        issues.append("人设风险: 口播单句超过15字的比例较高, 建议拆分或缩短")

    return issues


def run_guardrail(script_text: str) -> GuardrailResult:
    """
    对脚本做三道检查, 返回 GuardrailResult。
    在 script_writer 输出后、最终保存前调用。
    """
    result = GuardrailResult()

    result.privacy_issues = check_privacy(script_text)
    result.ad_law_issues = check_ad_law(script_text)
    result.persona_issues = check_persona(script_text)

    all_issues = result.privacy_issues + result.ad_law_issues + result.persona_issues

    if all_issues:
        result.passed = False
        result.suggestions = all_issues

    return result


def format_guardrail_report(result: GuardrailResult) -> str:
    """格式化合规检查报告"""
    if result.passed:
        return "✅ Guardrail 检查通过"

    lines = ["⚠️  Guardrail 检查发现问题:"]
    for issue in result.suggestions:
        lines.append(f"  - {issue}")
    return "\n".join(lines)


if __name__ == "__main__":
    test_script = """
【口播】家人们！这双鞋我们店里洗得最好，100%干净！保证跟新的一样！
儿子叫小明，我们家在房山XX小区3号楼。
    """
    report = run_guardrail(test_script)
    print(format_guardrail_report(report))
