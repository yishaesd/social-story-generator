"""可跑的 agent 循环（离线演示版）。

真实使用时把 FakePlanner 换成调模型：模型必须只输出 spec.md 里的五种工具 JSON，
然后这一层的 guard 会兜底。用 python loop.py 看三段对话。

    python loop.py            # 跑内置演示
    python loop.py --json     # 打印每一步的原始 action
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field

# Windows 的 GBK 控制台会把中文打成乱码，先切到 UTF-8
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from guard import sanitize, check, dumps

# 演示用的卡片（真实项目里来自 cards/*.json，都是人审过、机检过的）
CARDS = {
    "calm_place_01": "找一个安静的地方：走廊尽头那间空教室，坐两分钟。",
    "calm_place_02": "戴上耳机，开到第三格，听你存好的那首歌。",
    "tell_trusted_01": "告诉一个你信得过的人：班主任、姑姑，或者门口保安。",
    "avoid_person_01": "绕开他会走的那条楼梯，从另一边上去。",
    "enter_class_01": "进教室前在门口站十秒，看清楚座位再走。",
}


@dataclass
class State:
    turns: int = 0
    history: list[str] = field(default_factory=list)


class FakePlanner:
    """演示用：按关键词给动作。换成真模型时，只要实现 plan() 就行。"""

    def plan(self, child: str, state: State) -> dict:
        t = child.strip()

        if any(w in t for w in ["太吵", "吵", "声音大"]):
            return {
                "tool": "clarify",
                "question": "现在最想躲开哪一样？",
                "options": ["声音", "人多", "灯光"],
            }

        if t in ("声音", "人多", "灯光"):
            return {
                "tool": "show_cards",
                "card_ids": ["calm_place_01", "calm_place_02"],
            }

        if "不想去" in t:
            return {
                "tool": "clarify",
                "question": "是不想去，还是怕遇到什么？",
                "options": ["不想去", "怕遇到人", "累"],
            }

        if "怕遇到" in t:
            return {
                "tool": "show_cards",
                "card_ids": ["avoid_person_01", "tell_trusted_01"],
            }

        if any(w in t for w in ["堵我", "威胁", "打我"]):
            # 故意先给一个不合格的"安慰"，演示 guard 会把它改成 escalate
            return {
                "tool": "say",
                "text": "别怕，没什么大事，你会没事的。",
                "next_action": {"type": "options", "items": ["好", "嗯"]},
            }

        if "问我" in t or "叫我回答" in t:
            return {
                "tool": "say",
                "text": "被叫起来时，可以说「我还没想好」。",
                "next_action": {"type": "cards", "ids": ["enter_class_01"]},
            }

        if "没好" in t or "还是" in t:
            return {
                "tool": "say",
                "text": "要不要现在找个人陪你待一会儿？",
                "next_action": {"type": "contact", "label": "联系姑姑"},
            }

        return {
            "tool": "clarify",
            "question": "现在最想先解决哪一件？",
            "options": ["太吵", "有人", "不想去"],
        }


def render(action: dict) -> str:
    tool = action.get("tool")
    if tool == "say":
        lines = ["agent：" + action.get("text", "")]
        na = action.get("next_action") or {}
        if na.get("type") == "options":
            lines.append("  〔选项〕" + " / ".join(na["items"]))
        elif na.get("type") == "cards":
            lines.append("  〔卡片〕" + " / ".join(CARDS.get(c, c) for c in na["ids"]))
        elif na.get("type") == "contact":
            lines.append("  〔按钮〕" + na["label"])
        return "\n".join(lines)
    if tool == "clarify":
        return "agent：" + action["question"] + "\n  〔选项〕" + " / ".join(action["options"])
    if tool == "show_cards":
        body = "\n".join("  〔卡〕" + CARDS.get(c, c) for c in action["card_ids"])
        return "agent：（给了几张卡）\n" + body
    if tool == "escalate":
        return "agent：我现在帮你联系你信任的人。\n  〔已通知〕姑姑（按你设置的方式）"
    if tool == "remind":
        return f"agent：（{action.get('after_minutes', 30)} 分钟后会再问一次）"
    return "agent：…"


def run(transcript: list[str], planner: FakePlanner | None = None, echo_json: bool = False) -> None:
    planner = planner or FakePlanner()
    state = State()
    for child in transcript:
        print("\n孩子：" + child)
        raw = planner.plan(child, state)
        if echo_json:
            print("  raw   " + dumps(raw))
        report = check(raw, child)
        final = sanitize(raw, child)
        if report.issues:
            tags = ", ".join(f"{i.code}({i.level})" for i in report.issues)
            print("  guard " + tags)
        if final is not raw and not echo_json:
            print("  guard 改写为：" + final["tool"])
        print(render(final))
        state.turns += 1
        state.history.append(final.get("tool", ""))


DEMOS = [
    ("太吵了，我不想上课", ["声音", "还是很难受"]),
    ("今天不想去学校", ["怕遇到人"]),
    ("放学有人要堵我", []),
    ("老师叫我回答问题", []),
]


if __name__ == "__main__":
    echo = "--json" in sys.argv
    for i, (first, follow) in enumerate(DEMOS, 1):
        print("=" * 56)
        print(f"场景 {i}")
        run([first] + follow, echo_json=echo)
