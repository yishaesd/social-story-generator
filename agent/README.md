# agent（16–18 岁 · 对话档 B）

一个能说话、但每句话都必须带下一步的 agent。三条硬约束：

1. **只能调五种工具**（`clarify` / `show_cards` / `say` / `escalate` / `remind`），工具之外没有动作。
2. **每次输出过闸**：长度、禁词、禁命令、不连问、必须带下一步；危机词强制转手。
3. **模型不直接对孩子说话**，中间永远隔着 `guard.py`。

## 文件

| 文件 | 作用 |
|---|---|
| `spec.md` | 工具签名、状态机、记忆字段、guard 规则、评测 |
| `system_prompt.md` | 可直接用的系统提示词（含"绝对不许"清单） |
| `guard.py` | 输出闸（纯标准库）：`check()` 给完整报告，`sanitize()` 不合格就换兜底动作 |
| `test_guard.py` | 23 条单元测试，覆盖每条规则的正反例 |
| `loop.py` | 可跑的循环 + 离线演示（FakePlanner 按关键词出动作） |

## 跑一下

```bash
cd agent
python test_guard.py     # 23 passed
python loop.py           # 四段演示对话
python loop.py --json    # 同时打印每一步的原始 action
```

## 接真模型

`loop.py` 里 `FakePlanner.plan(child, state)` 换成一次模型调用即可，要求模型**只输出一个 JSON 对象**：

```json
{"tool":"say","text":"…","next_action":{"type":"options","items":["…","…"]}}
```

返回值直接丢给 `guard.sanitize(action, child_text)`，不合格会被换成兜底动作（两张求助卡），不会出现空回，也不会出现裸安慰。

## 演示里能看到的三个点

1. **正常路径**：先 `clarify` 收窄（三选一），再 `show_cards` 给具体动作，不一次给五个选择。
2. **危机路径**：孩子说「放学有人要堵我」→ 模型给的是一句安慰 → guard 判 `CRISIS` → 强制改成 `escalate`，并把安慰删掉。这是答辩最该演的一段。
3. **收敛路径**：孩子说「还是很难受」→ 不再追问，直接给 `contact`（联系信任的人）。

## 还没做

- 真模型的 JSON 约束（建议用 function calling / 结构化输出，而不是提示词祈祷）；
- `eval/cases.jsonl` 的 200 条真实语料；
- 卡片库 `cards/*.json`（现在演示里是硬编码的 5 张）；
- 记忆落盘（现在只在内存里）。
