# 社交故事器 · Hack4Good

家长填三个变量（谁陪、什么时候、在哪里），选一个场景，生成一本 **6 页的社交故事**，
一页一句、一页一图，可以念给孩子听。

不是绘本库，是**生成器**。核心闭环：

```
选场景 → 填变量 → 套模板 → 跑规则检查 → 只重写不合格的那几页 → 出图 → 翻页读
```

> 一句话讲给评委：**我们不是让 AI 写故事，是让 AI 写能过检查的故事。**

## 为什么需要它

自闭症谱系和低龄孩子对"看病、打针、理发、上幼儿园"这类事容易焦虑。
Carol Gray 的 Social Stories 用第一人称、具体、非命令的短句预告"会发生什么"，
让孩子在事情发生前先在故事里经历一遍。手工写一本要 20-40 分钟，写字还容易写成
"你必须勇敢"这种反而加压的话。这个工具把"写"和"检查"分开：机器负责套模板和查规则，
家长负责最后那一下判断。

## 两个人在干什么

| | A：内容与体验 | B：开发与部署 |
|---|---|---|
| 拥有目录 | `content/` `docs/` `shots/` | `src/` |
| 干什么 | 规则、场景模板、24 条生图提示词、演示脚本、答辩 | 阅读器、列表、自定义、书架、演示模式，接内容数据，部署 |
| 不碰 | `src/` 里的代码 | `content/` 里的文案（要改找 A） |

目录所有权是硬边界：`content/` 归 A、`src/` 归 B，互不越界。这是两个人同时用 AI 写代码
不打架的唯一办法。

## 快速开始

```bash
# 内容机检（A 每次改完必跑）
python check_social_story.py "content/scenes/*.json"

# 通过的样子
# === PASS  medication.json  《早上七点，我要吃药》 6 页 / 6 句 [模板] ===
# 合计 ERROR 0 条
```

跑起来（前端是纯静态的，必须用本地服务器打开，`file://` 读不了 JSON）：

```bash
python -m http.server 8000
# 浏览器开 http://127.0.0.1:8000/index.html
# 手机上开 http://<电脑的局域网 IP>:8000/index.html
```

五个界面：列表 → 选场景 →（填四个空 / 直接读）→ 阅读器（点左半屏上一页、右半屏下一页，支持左右滑）→ 演示模式（自动翻页 + 开头那个"提醒"卡片）→ 书架（存过的故事，localStorage）。

装 git 钩子（提交前自动跑机检，不过就拦下）：

```bash
git config core.hooksPath .githooks
```

## 克隆（给 B）

```bash
git clone https://github.com/yishaesd/social-story-generator.git
cd social-story-generator
git config core.hooksPath .githooks   # 必做，否则提交前的机检钩子不生效
```

国内网络下 github.com:443 可能连不上，给 git 挂本地代理（端口按自己客户端改）：
`git config http.https://github.com.proxy http://127.0.0.1:7892`

## 目录

```
content/          规则唯一真相源 + 四个场景模板 + 生图提示词
content/schema.md 数据契约（B 照着这个渲染）
docs/             设计与分工、A 的执行手册、Qoder 任务包、答辩脚本
shots/            图片资产，shots/<场景>/01..06.webp（1024x730，水印已裁）
tools/            crop_watermark.py：统一裁掉生图工具烘焙的底部水印条
samples/          一好一坏两份样例（给人看"什么算过"）
src/              前端代码（原生 ES module，无构建）：app.js / style.css / validate.js / scenes.js
```

### 图片资产约定

- 全部 1024×730（4:3 去掉底部 38px），渲染时按 4:3 容器 `object-fit: cover` 裁切。
- 水印由 `python tools/crop_watermark.py` 统一裁掉；原图备份在仓库外的 `_shots_orig/`，不提交。
- 孩子固定形象：齐耳黑短发、明黄色连帽卫衣、深蓝色长裤、白色球鞋，简化绘本脸。
- 成年人只出背影/侧影，**头部不入画**（避免"没有五官的空白脸"）。

## 四个场景

吃药 · 打针 · 理发 · 上幼儿园 —— 覆盖四类焦虑：怕疼、怕身体被摆布、怕分离、怕陌生流程。

## 状态

- [x] 规则 R1-R6 落地（`content/rules.json`）
- [x] 四个场景模板通过机检（ERROR 0）
- [x] 24 条生图提示词
- [x] 24 张图生成并筛选（medication / injection / haircut / kindergarten 各 6 张已入库）
- [x] 列表 / 阅读器 / 自定义填空 / 书架 / 演示模式（index.html + src/）
- [ ] 部署 + 手机真机测试
- [ ] 答辩排练

## 许可

比赛作品，暂不对外授权。
