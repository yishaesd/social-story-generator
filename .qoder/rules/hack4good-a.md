# A 线：内容与体验

- globs: content/**, docs/**, shots/**
- 只在这些目录里工作。`src/` 一个字都不要动。

## 交付标准

1. 改完任何 `content/scenes/*.json`，必须运行：
   `python check_social_story.py "content/scenes/*.json"`
   ERROR 必须是 0；warn 可以留，但要在回复里说明为什么可以留。
2. 报错时只改报错的那一页，不要整篇重写，不要动没让你改的页。
3. 不许改 `content/rules.json` 里的任何数值（max_len / title_max / banned / directive_ratio / pages / types）。
   发现规则本身有问题，说出来，由人决定。
4. 不许新增场景、不许新增页；页数保持 6。
5. 不许 `git commit` / `git push`，改完就停。

## 生图

- 提示词只从 `content/image-prompts.md` 里取，一次只发一条 prompt、只生成一张。
- 先生成的图不合格，只重试那一张，最多 3 次，然后记录问题换图，不要无限重试。
- 存到 `shots/<image_pool>/<img>`，文件名必须和 JSON 里的 `img` 完全一致（01.webp … 06.webp）。

## 文案风格（改句子时守）

- 第一人称「我」，现在时，不出现「你」「您」。
- 一页一句，可见字数 ≤22（模板自写 ≤18，留 4 字给家长变量）。
- 具体：每页至少含时间、动作、地点之一；不写"要勇敢""别害怕"这类抽象鼓励。
- 禁词：应该 必须 不许 不准 不能 总是 永远 乖 听话 勇敢 加油 一定要 记住。
- 结尾落在肯定句，不落在指令句。
