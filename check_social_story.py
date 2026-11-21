#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""社交故事器 —— 文案机检（R1-R6）

规则参数住在 content/rules.json（唯一真相源），前端校验器读同一份，别在两处改。

用法:
    python check_social_story.py content/scenes/*.json          # 模板场景（带 slots，按最坏情况算字数）
    python check_social_story.py samples/*.json                # 成品故事
    python check_social_story.py content/scenes/*.json --json  # 给 CI / 前端对齐

退出码:
    0  没有 ERROR（可能有 WARN）
    1  至少一条 ERROR

规则（对应手册 R1-R6）:
    R1  第一人称、现在时，不出现"你/您"
    R2  一页一句，每句 <= max_len 个可见字符（模板按 slot 最大长度填满后算）
    R3  引导句(directive) 数量 <= 描述类页数的一半
    R4  具体可见：每页至少一个时间/动作/地点线索（粗检）
    R5  禁词表
    R6  每页必须有图，且图不重复
"""
import argparse
import glob
import json
import os
import re
import sys

if sys.platform == "win32":
    try:
        import ctypes

        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_RULES = {
    "max_len": 22,
    "title_max": 12,
    "second_person": ["你", "您"],
    "banned": [
        "应该", "必须", "不许", "不准", "不能", "总是", "永远",
        "乖", "听话", "勇敢", "加油", "一定要", "记住",
    ],
    "directive_ratio": 0.5,
    "pages": {"min": 6, "max": 10},
    "types": ["descriptive", "perspective", "affirmative", "directive"],
    "punct": "，。！？、；：\"\"''（）《》…—·,.!?;:'\"()<>-",
    "sentence_end": ["。", "！", "？", "!", "?", "…"],
    "concrete": {
        "time": ["点", "早上", "中午", "晚上", "下午", "上午", "分钟", "今天", "昨天", "明天", "每天"],
        "action": ["拿", "放", "喝", "走", "坐", "站", "看", "摸", "说", "问", "打开", "关",
                   "递", "举", "推", "咽", "抱", "指", "翻", "端", "拧", "按", "穿", "擦",
                   "洗", "蹲", "躺", "闭上"],
        "place": ["家", "厨房", "客厅", "桌", "床边", "门口", "学校", "教室", "医院",
                  "车上", "杯子", "碗", "手心"],
    },
}

SLOT_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
FILLER = "囗"  # 一个可见字，用来占位算最坏字数


def load_rules(path=None):
    rules = json.loads(json.dumps(DEFAULT_RULES))
    candidates = [path] if path else [
        os.path.join(SCRIPT_DIR, "content", "rules.json"),
        os.path.join(SCRIPT_DIR, "rules.json"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            with open(c, "r", encoding="utf-8-sig") as f:
                loaded = json.load(f)
            for k, v in loaded.items():
                if not k.startswith("_"):
                    rules[k] = v
            rules["_source"] = os.path.basename(c)
            break
    rules.setdefault("_source", "(builtin)")
    return rules


def visible_len(text, punct):
    return len([c for c in text if c not in punct and not c.isspace()])


def count_sentences(text, ends):
    pattern = "[" + re.escape("".join(ends)) + "]+"
    return len([p for p in re.split(pattern, text) if p.strip()])


def has_concrete(text, rules):
    hits = []
    for kind, words in rules["concrete"].items():
        if any(w in text for w in words):
            hits.append(kind)
    return hits


def render_fill(text, slots, mode, tag, errors):
    """填模板。mode="max" 用 max 个占位字（最坏情况），mode="default" 用默认值（给人和评委看）。"""
    if "{" not in text:
        return text

    def repl(m):
        name = m.group(1)
        spec = slots.get(name)
        if not spec:
            if mode == "max":
                errors.append((tag, f"未知槽位 {{{name}}}，slots 里没有定义（拼错了？）"))
            return m.group(0)
        if mode == "default":
            return str(spec.get("default", FILLER))
        n = int(spec.get("max", 0) or 0)
        if n <= 0:
            errors.append((tag, f'槽位 {{{name}}} 缺 "max"，无法按最长情况校验字数'))
            return FILLER
        return FILLER * n

    return SLOT_RE.sub(repl, text)


def check(path, rules):
    errors, warns = [], []
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    name = os.path.basename(path)
    punct = rules["punct"]
    max_len = rules["max_len"]
    slots = data.get("slots") or {}
    is_template = bool(slots)
    pages = data.get("pages") or []

    # --- 场景结构（模板才有）---
    if is_template:
        for field in ("id", "name"):
            if not data.get(field):
                errors.append(("结构", f"缺少 {field}"))
        for sname, spec in slots.items():
            if not isinstance(spec, dict):
                errors.append((sname, "slot 必须是对象 {label, default, max}"))
                continue
            for k in ("label", "default", "max"):
                if k not in spec:
                    errors.append((sname, f'槽位缺 "{k}"'))
            if isinstance(spec.get("max"), int) and isinstance(spec.get("default"), str):
                if len(spec["default"]) > spec["max"]:
                    errors.append((sname, f'默认值 "{spec["default"]}" 比 max={spec["max"]} 还长'))

    # --- 标题 ---
    title_raw = str(data.get("title", "")).strip()
    title = render_fill(title_raw, slots, "default", "标题", errors)
    title_worst = render_fill(title_raw, slots, "max", "标题", errors)
    if not title_raw:
        errors.append(("标题", "缺少 title"))
    else:
        tl = visible_len(title_worst, punct)
        if tl > rules["title_max"]:
            errors.append(("标题", f"标题 {tl} 字（按最长变量算），超过 {rules['title_max']} 字：{title}"))

    # --- 人称 ---
    voice = str(data.get("voice", "first")).strip()
    if voice not in ("first", "third"):
        errors.append(("人称", f'voice 只能是 "first" 或 "third"，现在是 {voice!r}'))

    # --- 篇幅 ---
    lo, hi = rules["pages"]["min"], rules["pages"]["max"]
    if not (lo <= len(pages) <= hi):
        warns.append(("篇幅", f"共 {len(pages)} 页，建议 {lo}-{hi} 页（4 个场景 × 6 页 = 24 张图）"))

    seen_img = {}
    type_count = {t: 0 for t in rules["types"]}
    sentence_total = 0

    for i, page in enumerate(pages, 1):
        tag = f"第{i}页"
        raw = str(page.get("text", "")).strip()
        ptype = str(page.get("type", "")).strip()
        img = str(page.get("img", "")).strip()

        if not raw:
            errors.append((tag, "没有 text"))
            continue

        text = render_fill(raw, slots, "max", tag, errors)
        display = render_fill(raw, slots, "default", tag, errors)
        shown = display if display != raw else text

        if ptype not in rules["types"]:
            errors.append((tag, f'type 必须是 {"/".join(rules["types"])} 之一，现在是 {ptype!r}'))
        else:
            type_count[ptype] += 1

        n = count_sentences(text, rules["sentence_end"])
        sentence_total += n
        if n > 1:
            errors.append((tag, f"一页 {n} 句，R2 要求一页一句：{shown}"))

        ln = visible_len(text, punct)
        if ln > max_len:
            extra = "（按最长变量算）" if text != display else ""
            errors.append((tag, f"{ln} 字{extra}，超过 {max_len} 字：{shown}"))

        for w in rules["second_person"]:
            if w in text:
                errors.append((tag, f'出现第二人称"{w}"，社交故事不用指令口吻：{shown}'))

        for w in rules["banned"]:
            if w in text:
                errors.append((tag, f'禁词"{w}"：{shown}'))

        hits = has_concrete(text, rules)
        if not hits:
            warns.append((tag, f"没有时间/动作/地点线索，R4 要具体可见，别写成抽象评价：{shown}"))

        if not img:
            errors.append((tag, "没有 img，R6 一页一图"))
        elif img in seen_img:
            warns.append((tag, f"图 {img} 与第{seen_img[img]}页重复"))
        else:
            seen_img[img] = i

        if text.startswith("请"):
            errors.append((tag, f"开头是指令口吻：{shown}"))

    # --- 引导句比例 ---
    d = type_count["directive"]
    others = len(pages) - d
    ratio = rules["directive_ratio"]
    if d and others < ratio * 2 * d:
        errors.append(("比例", f"引导句 {d} 页 / 其他 {others} 页，R3 要求其他至少是引导句的 {int(1 / ratio) if ratio else 2} 倍"))
    if d == 0:
        warns.append(("比例", "一句引导句都没有，结尾可能缺少「接下来我可以…」"))

    if pages and str(pages[-1].get("type", "")) == "directive":
        warns.append(("结尾", "最后一句是引导句，建议以肯定句收尾，别停在命令上"))

    return name, title, len(pages), sentence_total, errors, warns, is_template


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="JSON 文件或通配符")
    ap.add_argument("--rules", help="规则文件路径（默认 content/rules.json）")
    ap.add_argument("--max-len", type=int, help="覆盖 rules.json 里的 max_len")
    ap.add_argument("--json", action="store_true", help="输出 JSON，供 CI / 前端对齐")
    args = ap.parse_args()

    rules = load_rules(args.rules)
    if args.max_len:
        rules["max_len"] = args.max_len

    paths = []
    for pattern in args.files:
        paths.extend(sorted(glob.glob(pattern)))
    if not paths:
        print("没找到文件：", args.files)
        return 2

    total_err = 0
    report = []
    for p in paths:
        try:
            name, title, npages, nsen, errors, warns, is_tpl = check(p, rules)
        except Exception as e:  # noqa: BLE001
            print(f"[读取失败] {p}: {e}")
            total_err += 1
            continue
        total_err += len(errors)
        report.append({"file": p, "id": os.path.splitext(name)[0], "template": is_tpl,
                       "title": title, "pages": npages, "sentences": nsen,
                       "errors": [{"where": w, "msg": m} for w, m in errors],
                       "warns": [{"where": w, "msg": m} for w, m in warns]})

        if not args.json:
            flag = "PASS" if not errors else "FAIL"
            kind = "模板" if is_tpl else "成品"
            print(f"\n=== {flag}  {name}  《{title}》 {npages} 页 / {nsen} 句 [{kind}] ===")
            for where, msg in errors:
                print(f"  [ERROR] {where}: {msg}")
            for where, msg in warns:
                print(f"  [warn ] {where}: {msg}")
            if not errors and not warns:
                print("  干净。")

    if args.json:
        print(json.dumps({"rules_source": rules["_source"], "max_len": rules["max_len"],
                          "files": report}, ensure_ascii=False, indent=2))
    else:
        print(f"\n规则来自 {rules['_source']}，每句上限 {rules['max_len']} 字")
        print(f"合计 ERROR {total_err} 条")
    return 1 if total_err else 0


if __name__ == "__main__":
    sys.exit(main())
