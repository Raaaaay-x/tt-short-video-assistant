"""
钩子模板库 — 前 3 秒的抓人方式

每个钩子返回 (hook_id, hook_description, example_opening, target_emotion)
v0.2: A/B/C/D 四类各 1 个，后续从对标库中持续扩充
"""

HOOKS = {
    # ── A类: 对比钩子 ──
    "A1": {
        "name": "脏→净瞬切",
        "category": "对比钩子",
        "opening_example": "你看这双鞋送进来的样子，洗完是这样——",
        "emotion": "好奇 → 满足",
        "visual_rule": "脏鞋特写 1 秒 → 干净成品 1 秒 → 停顿 1 秒",
        "best_for": ["效果展示", "球鞋修复", "深度清洗"],
    },

    # ── B类: 反常识钩子 ──
    "B1": {
        "name": "材质误区",
        "category": "反常识钩子",
        "opening_example": "你的翻毛皮鞋，可能早就被你洗坏了。",
        "emotion": "轻度焦虑 → 求知",
        "visual_rule": "材质特写 → 慢动作 → 文字弹出“为什么”",
        "best_for": ["材质科普", "保养知识", "鉴别内容"],
    },

    # ── C类: 身份认同钩子 ──
    "C1": {
        "name": "本地归属",
        "category": "身份认同钩子",
        "opening_example": "房山的姐妹应该都认识我们家，今儿来了一双有故事的鞋。",
        "emotion": "熟悉感 → 好奇",
        "visual_rule": "店门口 / 门口招牌 → 自然过渡到鞋",
        "best_for": ["客户故事", "日常经营", "本地互动"],
    },

    # ── D类: 教学/展示钩子 ──
    "D1": {
        "name": "完整过程预览",
        "category": "教学/展示钩子",
        "opening_example": "这双鞋怎么从这样变成这样的？我拍给你看。",
        "emotion": "期待 → 满足",
        "visual_rule": "开始状态的脏鞋 → 手指镜头引导 → 过程画面",
        "best_for": ["效果展示", "教程", "工具展示"],
    },
}


def list_hooks():
    """列出所有可用钩子。"""
    return [(k, v["name"], v["category"]) for k, v in HOOKS.items()]


def get_hook(hook_id: str) -> dict | None:
    return HOOKS.get(hook_id)
