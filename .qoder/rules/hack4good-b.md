# B 线：开发与部署

- globs: src/**, index.html, package.json, vite.config.*, .github/**
- `content/` `docs/` `shots/` 只读，不改。需要改文案就告诉 A。

## 接口

- 场景数据从 `content/scenes/*.json` 读，字段见 `content/schema.md`。
- 常量从 `content/rules.json` 读（`import ... from '../content/rules.json'`），不要自己写一份阈值。
- 图片路径 = `<image_pool>/<img>`，如 `shots/medication/01.webp`；缺图时显示占位块 + `alt`，不要白屏。

## 必须实现的页面

1. **列表**：四个场景卡片（图标 + 场景名 + 一句话说明）。
2. **阅读器**：6 页，一页一句一图，左右翻页；键盘方向键、点按都能翻；准备进度条。
3. **自定义**：填 3-4 个变量（孩子小名 / 谁陪 / 什么时候 / 在哪里），有 `max` 字数限制，
   填完实时预览第 1 页。
4. **书架**：生成过的故事留一份（localStorage 即可），能再次打开。
5. **演示模式**：一键全屏、自动翻页（每页停留 ~8 秒）、顶部留白区域叠大字幕。

## 约束

- 纯前端静态站点，能部署到 Qoder Sites；不要后端、不要数据库、不要登录。
- 移动端优先：评委八成用手机看，先保证 375px 宽度好看。
- 图片体积控制：每张 ≤200KB（webp），首屏不要一次加载 24 张，按需加载。
- 不许改 `content/rules.json` 数值；不许 `git commit` / `git push`。
- 部署前自测：手机真机走一遍「首页 → 列表 → 阅读器 → 翻页到底 → 返回」，全程不白屏、不报错。
