"""
视频结构模板 — 对标视频和二创脚本的叙事骨架

v0.2: 对比冲击型 + 知识科普型
后续从对标库中归纳更多模式
"""

STRUCTURES = {
    # ── 结构1: 对比冲击型 (效果展示的核心模板) ──
    "contrast": {
        "name": "对比冲击型",
        "segments": [
            {"time": "0-3秒",   "role": "钩子",    "desc": "脏鞋特写 / 脏→净瞬切", "info_density": 1},
            {"time": "3-8秒",   "role": "展示",    "desc": "多角度清洗过程、慢动作关键步骤", "info_density": 2},
            {"time": "8-12秒",  "role": "效果",    "desc": "干净成品展示、细节特写", "info_density": 1},
            {"time": "12-15秒", "role": "CTA",     "desc": "引导评论“还有什么鞋想洗的?”", "info_density": 1},
        ],
        "emotion_map": "好奇(0-3s) → 投入(3-8s) → 满足(8-12s) → 行动意愿(12-15s)",
        "best_for": ["效果展示", "球鞋修复", "深度清洗"],
        "platform": "首选抖音，次选小红书",
    },

    # ── 结构2: 知识科普型 (建立专业度的核心模板) ──
    "knowledge": {
        "name": "知识科普型",
        "segments": [
            {"time": "0-3秒",   "role": "钩子",    "desc": "反常识/揭秘/提问", "info_density": 1},
            {"time": "3-10秒",  "role": "科普",    "desc": "为什么、怎么做、常见误区", "info_density": 3},
            {"time": "10-18秒", "role": "例子",    "desc": "实际案例或前后对比", "info_density": 2},
            {"time": "18-20秒", "role": "CTA",     "desc": "“还有不懂的评论区问”", "info_density": 1},
        ],
        "emotion_map": "好奇/焦虑(0-3s) → 求知(3-10s) → 恍然大悟(10-18s) → 信任(18-20s)",
        "best_for": ["材质科普", "保养知识", "鉴别内容", "行业揭秘"],
        "platform": "全平台通用，视频号可延长到 1-2 分钟",
    },
}


def list_structures():
    return [(k, v["name"], v["best_for"]) for k, v in STRUCTURES.items()]


def get_structure(structure_id: str) -> dict | None:
    return STRUCTURES.get(structure_id)
