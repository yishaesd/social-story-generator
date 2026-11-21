# src/ —— B 的地盘

这里放网站代码。A 不改这里，AI 走 A 线任务时也不碰这里。

## 技术栈（B 自己定，建议）

- Vite + 原生 JS 或 React，纯静态，别上后端。
- 数据直接读仓库里的 JSON（Vite 支持 `import ... from '../content/scenes/medication.json'`，
  或者用 `import.meta.glob('../content/scenes/*.json', { eager: true })` 批量读）。
- 图片放 `public/` 下或直接用 `shots/` 目录的相对路径（构建时要能被 copy 进去）。

## 三个硬要求

1. 常量从 `content/rules.json` 读，不自己写阈值。
2. 移动端优先，375px 宽度下必须好看。
3. 部署目标：Qoder Sites，静态构建产物即可。

## 结构建议

```
src/
├── main.js          入口 + 路由（hash 路由就行，静态站别用 history 路由）
├── data.js          读 content/scenes/*.json、注入 slot、拼图片路径
├── reader.js        阅读器：翻页、进度、预加载下一页
├── custom.js        自定义：变量表单 + 字数限制 + 首页预览
├── shelf.js         书架：localStorage
└── demo.js          演示模式：全屏 + 自动翻页 + 叠字
```

`content/schema.md` 是接口文档，先看那个再动手。
