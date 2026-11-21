# 数据契约（B 线对接用）

渲染器只读 `content/`，不硬编码任何文案。下面这一份就是接口。

## 1. 目录约定

```
content/
├── rules.json              规则唯一真相源（前端校验也读它）
├── scenes/<scene-id>.json  每个场景一份故事模板
└── image-prompts.md        生图提示词（A 用，运行时不需要）
shots/<image_pool>/01.webp  … 每场景 6 张图，序号即页序
```

## 2. 场景文件结构

```jsonc
{
  "id": "medication",              // 唯一 id，= 文件名
  "name": "吃药",                   // 中文场景名，列表页显示
  "audience": "4-8",               // 目标年龄
  "voice": "first",                // 固定第一人称
  "image_pool": "shots/medication",// 图池目录（相对仓库根）
  "duration_sec": 60,              // 读完大概多久，演示用
  "title": "{when}，我要吃药",      // 标题模板，可含 slot
  "slots": {                       // 家长要填的变量
    "child": { "label": "孩子小名", "default": "宝宝", "max": 4 },
    "who":   { "label": "谁陪着",   "default": "妈妈", "max": 3 },
    "when":  { "label": "什么时候", "default": "早上七点", "max": 6 },
    "where": { "label": "在哪里",   "default": "桌前", "max": 4 }
  },
  "pages": [                       // 6 页，顺序即阅读顺序
    { "text": "{when}，{who}把水杯放在{where}。",
      "type": "descriptive",
      "img": "01.webp",
      "alt": "家长把一杯水放在孩子面前的桌上" }
  ]
}
```

`type` 只用四值：`descriptive` 描述句 / `perspective` 观点句 / `affirmative` 肯定句 / `directive` 引导句。

## 3. 渲染规则

1. **注入**：把 `text`、`title` 里的 `{slot}` 替换成家长填的值；没填就用 `default`。
2. **不截断**：变量长度已由 `check_social_story.py` 按 `max` 做过 worst-case 校验，前端不要自己截字，也不要因为超长就缩字号缩到看不清 —— 若真超长，说明内容有问题，回去改模板。
3. **一行一图**：第 n 页 = `pages[n-1]`，图片 = `<image_pool>/<img>`，不跨页复用。
4. **比例**：所有图 4:3 横构图，画面上方三分之一是留白（演示叠字用），渲染时不要裁掉。
5. **图片缺失**：图还没生成时显示浅色占位块 + 该页 `alt` 文案，不要报错白屏。演示前一天必须补齐。
6. **字号**：一页一句 ≤22 字，按 4:3 画布做两档字号即可（≤14 字一档、>14 字一档），不搞自动缩放到 8px。

## 4. 规则常量（前端校验用，不要抄数值）

```js
import rules from './content/rules.json' assert { type: 'json' };
// max_len / banned / directive_ratio / pages / types 全部从这里读
```

如果 B 侧要做"家长自己改文案"的入口，必须复用同一份 `rules.json`，不许另写一套阈值 —— 两套阈值一定会分叉，答辩现场被抓到就是扣分点。

## 5. 与 A 的接口（改内容的唯一通道）

- B 觉得某句要改 → 告诉 A，由 A 改 `content/scenes/*.json`，**B 不自己改 JSON**。
- A 改完必须本地跑一次机检，`ERROR 0 条` 再提交。
- 提交前 hook 会自动再跑一次（见 `.githooks/pre-commit`）。
