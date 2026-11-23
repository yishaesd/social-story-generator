"""输出闸：决定 agent 这句话能不能发给孩子。

用法：
    from guard import check, sanitize
    r = check(action)          # action 是模型输出的 dict
    if not r.ok:  action = r.replacement

规则见 spec.md 第 4 节。纯标准库，无第三方依赖。
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------- 词表 ----------

# 命中即 error：诊断、疗效、训练、评价"正常"
HARD_BANNED = [
    "谱系", "自闭症的症状", "症状", "干预", "ABA", "行为治疗",
    "疗效", "治愈", "康复", "你会好起来", "会好起来的",
    "进步很大", "有进步", "变正常", "正常一点", "像个正常人",
    "训练你", "矫正",
]

# 只提醒：术语、口号式安慰
SOFT_BANNED = [
    "别怕", "没事的", "加油", "勇敢", "坚强", "你可以的",
    "放松点", "想开点",
]

# 命令式
IMPERATIVE_PATTERNS = [
    re.compile(r"你应该"), re.compile(r"你必须"), re.compile(r"你要(?![么怎])"),
]

# 危机词（命中必须 escalate）
CRISIS_WORDS = [
    "不想活", "自杀", "去死", "伤害自己", "割腕", "跳楼",
    "被打", "要打我", "堵我", "跟踪我", "威胁我",
    "找不到回家", "走失", "迷路了回不去",
    "发照片给他", "给我发照片", "见面", "来见我", "开房",
    "脱衣服", "看你的身体",
]

# 允许的工具
TOOLS = {"clarify", "show_cards", "say", "escalate", "remind"}

MAX_VISIBLE_CHARS = 30
MAX_SENTENCES = 2

FALLBACK = {
    "tool": "show_cards",
    "card_ids": ["calm_place_01", "tell_trusted_01"],
    "note": "guard fallback",
}

PUNCT = "，。！？、；：,.!?;:\"'“”‘’（）()《》〈〉…—-~· \t\n"


@dataclass
class Issue:
    code: str
    level: str  # "error" | "warn"
    detail: str


@dataclass
class Report:
    ok: bool
    issues: list[Issue] = field(default_factory=list)
    replacement: dict[str, Any] | None = None

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warns(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warn"]


# ---------- 工具函数 ----------

def visible_len(text: str) -> int:
    """去掉标点、空白、控制字符后的字数。"""
    text = unicodedata.normalize("NFKC", text)
    return sum(1 for ch in text if ch not in PUNCT and not ch.isspace())


def sentence_count(text: str) -> int:
    parts = [p for p in re.split(r"[。！？!?…]+", text) if p.strip(PUNCT + " ")]
    return max(1, len(parts))


def has_crisis(text: str) -> bool:
    return any(w in text for w in CRISIS_WORDS)


def _text_of(action: dict[str, Any]) -> str:
    parts = [action.get("text") or "", action.get("question") or "", action.get("reason") or ""]
    for opt in action.get("options") or []:
        parts.append(str(opt))
    return " ".join(p for p in parts if p)


def _has_next(action: dict[str, Any]) -> bool:
    na = action.get("next_action")
    if not isinstance(na, dict):
        return False
    kind = na.get("type")
    if kind == "options":
        items = na.get("items") or []
        return 1 <= len(items) <= 3 and all(len(str(i)) <= 10 for i in items)
    if kind == "cards":
        ids = na.get("ids") or []
        return 1 <= len(ids) <= 6
    if kind == "contact":
        return bool(na.get("label"))
    return False


# ---------- 主检查 ----------

def check(action: dict[str, Any], child_text: str = "") -> Report:
    issues: list[Issue] = []

    tool = action.get("tool")
    if tool not in TOOLS:
        issues.append(Issue("TOOL", "error", f"未知工具 {tool!r}"))
        return Report(False, issues, dict(FALLBACK))

    blob = _text_of(action)

    # 危机：孩子的话命中危机词
    if has_crisis(child_text) or has_crisis(blob):
        if tool != "escalate":
            issues.append(Issue("CRISIS", "error", "涉及危机内容但没有 escalate"))
            return Report(False, issues, {
                "tool": "escalate",
                "reason": "guard: crisis override",
                "text": "我现在帮你联系你信任的人。",
            })

    if tool == "escalate":
        # 危机时只许一句话，不加解释、不劝
        if visible_len(action.get("text") or "") > 20:
            issues.append(Issue("LEN", "warn", "escalate 附带的说明太长"))
        if any(w in blob for w in SOFT_BANNED) or any(p.search(blob) for p in IMPERATIVE_PATTERNS):
            issues.append(Issue("ESCORT", "error", "危机转手时不许夹带安慰或指令"))
        return Report(not [i for i in issues if i.level == "error"], issues,
                      None if not issues else dict(FALLBACK))

    # 长度
    if tool in ("say", "clarify"):
        n = visible_len(action.get("text") or action.get("question") or "")
        s = sentence_count(action.get("text") or action.get("question") or "")
        if n > MAX_VISIBLE_CHARS or s > MAX_SENTENCES:
            issues.append(Issue("LEN", "error", f"{n} 字 / {s} 句，上限 {MAX_VISIBLE_CHARS} 字、{MAX_SENTENCES} 句"))

    # 禁词
    for w in HARD_BANNED:
        if w in blob:
            issues.append(Issue("BANNED", "error", f"出现禁用表达「{w}」"))
    for w in SOFT_BANNED:
        if w in blob:
            issues.append(Issue("SOOTHE", "warn", f"口号式安慰「{w}」"))

    # 命令式
    for pat in IMPERATIVE_PATTERNS:
        if pat.search(blob):
            issues.append(Issue("IMPERATIVE", "error", f"命令式表达：{pat.pattern}"))

    # 连问
    if blob.count("？") + blob.count("?") > 1:
        issues.append(Issue("MULTI_Q", "error", "一次问了不止一个问题"))

    # 必须带下一步
    if tool == "say" and not _has_next(action):
        issues.append(Issue("NO_NEXT", "error", "say 没有带合法的 next_action"))

    if tool == "clarify":
        opts = action.get("options") or []
        if not (1 <= len(opts) <= 3):
            issues.append(Issue("NO_NEXT", "error", "clarify 的选项必须在 1–3 个"))
        elif any(len(str(o)) > 10 for o in opts):
            issues.append(Issue("NO_NEXT", "error", "clarify 的单个选项超过 10 字"))

    # 纯安慰且没动作 → warn（不阻断，但要求补动作）
    if tool == "say" and any(w in blob for w in SOFT_BANNED) and not _has_next(action):
        issues.append(Issue("SOOTHE", "warn", "只有安慰没有动作"))

    errors = [i for i in issues if i.level == "error"]
    return Report(not errors, issues, None if not errors else dict(FALLBACK))


def sanitize(action: dict[str, Any], child_text: str = "") -> dict[str, Any]:
    """检查不合格就换成兜底动作，保证永远有输出、且永远有下一步。"""
    r = check(action, child_text)
    return action if r.ok else r.replacement


def dumps(action: dict[str, Any]) -> str:
    return json.dumps(action, ensure_ascii=False)


def load_banned_from_rules(path: str | Path | None = None) -> list[str]:
    """可选：把 content/rules.json 的禁用词并进 HARD_BANNED。"""
    p = Path(path) if path else Path(__file__).resolve().parent.parent / "content" / "rules.json"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return list(data.get("banned", []))
    except Exception:
        return []
