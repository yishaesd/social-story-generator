# Agent 规格（16–18 岁 · 对话档 B）

> 定位：不是陪聊，是"帮你做下一步"的 agent。
> 它可以用自然语言说话，但**一句话要么带一个可点的动作，要么就别说**。

## 1. 循环

```
turns: [
  child_msg   -- 孩子说的话 / 点到的选项 / 跳过的动作
  planner     -- 模型决定：调哪个工具、参数是什么
  guard       -- 输出闸：长度 / 禁词 / 禁型 / 必须带下一步 / 危机转手
  render      -- 说话气泡 + 选项 + 卡片 + 一个主按钮
  remember    -- 写入孩子档案（偏好、触发点、用过的卡）
]
```

## 2. 工具（action space）

模型只能输出下面五种之一，别的都算越界，guard 直接改成 `say_cards` 兜底。

| 工具 | 签名 | 用途 | 约束 |
|---|---|---|---|
| `clarify` | `(question, options[1..3])` | 问一个短问题 | 一次只能问一个；选项 ≤3；每个选项 ≤10 字 |
| `show_cards` | `(card_ids[1..6])` | 展示预设卡（预演/步骤/求助） | 卡片必须已发布且过机检 |
| `say` | `(text, next_action)` | 说一两句，附一个动作 | 正文 ≤30 可见字 或 ≤2 句；`next_action` 必填 |
| `escalate` | `(reason)` | 切固定卡「联系你信任的人」+ 通知 | 命中危机词时必须用它，且不再多说 |
| `remind` | `(after_minutes, question)` | 过一会儿再问一次 | 单次 ≤1 条；不叠加 |

`next_action` 只能是：`{type:"options", items:[…]}`、`{type:"cards", ids:[…]}`、`{type:"contact", label:"联系…"}`。
没有动作的纯安慰、纯解释 → 不合规。

## 3. 状态与记忆

```json
{
  "profile": {
    "age": 17,
    "voice": "off",
    "font_scale": 1.1,
    "motion": "reduced"
  },
  "triggers": ["走廊人多", "点名回答问题"],
  "trusted_adults": [{"name": "姑姑", "phone": "…", "notify": true}],
  "used_cards": {"avoid_person_01": 3, "calm_place_01": 1},
  "visibility": {"crisis": "trusted_only", "daily": "local_only"}
}
```

记忆只存"下一次能用到"的东西：偏好、触发点、哪个卡真被点过。
**不存**：聊天原文、情绪判断、可识别的第三人信息。

## 4. 输出闸（guard）规则

按顺序检查，任一 error 则整条输出被改写：

| 码 | 规则 | 级别 |
|---|---|---|
| `LEN` | 正文 > 30 可见字，或 > 2 句 | error |
| `BANNED` | 命中诊断/疗效/训练/变正常类词 | error |
| `IMPERATIVE` | 出现「你应该 / 你必须 / 你要」 | error |
| `MULTI_Q` | 问号 > 1（连问） | error |
| `NO_NEXT` | `say` 没有 `next_action` | error |
| `CRISIS` | 命中危机词却没调 `escalate` | error |
| `ESCORT` | escalate 时夹带安慰或「应该/必须」 | error |
| `SOOTHE` | 只安慰（"没事的""别怕""会好的"）且无动作 | warn |
| `JARGON` | 出现术语（ABA/干预/谱系障碍） | warn |

改写策略：error → 降级成 `show_cards(["calm_place_01","tell_trusted_01"])` + 一句模板话，绝不空回。

## 5. 系统提示词（全文见 `system_prompt.md`）

要点四条：

1. 你的目标不是让孩子舒服，是让他**知道下一步做什么**。
2. 不诊断、不评估、不谈疗效、不评价进步。
3. 一次只说一件事，一次只问一个问题。
4. 危机词一律 `escalate`，不加解释、不加安慰。

## 6. 评测（答辩要能现场跑）

- `test_guard.py`：30+ 条用例，覆盖每条规则的正例与反例；
- 真实语句集 `eval/cases.jsonl`：收集 200 条孩子可能的说法（含错字、口语、脏话），看输出合规率；
- 指标：**越界输出拦截率 = 100%**（硬要求）、误拦率 < 10%、平均决策轮数 ≤ 2。

## 7. 不做的事

- 不做"随时都在"的陪伴承诺；
- 不做心理疏导、不做危机谈判；
- 不做社交技巧训练评分；
- 不在没有 `next_action` 的情况下输出任何一句话。
