"""把本仓库的场景（content/scenes/*.json + shots/）导出成 B 那套内容契约。

B 的契约（见 content/README.md）：
  stories/<id>.json      字段 id / order / title / coverImage / defaults / pages[]
  pages[].type           describe | process | perspective | directive | praise
  pages[].text           一句话，占位符形如 {companion}
  pages[].image          /assets/<id>/<两位序号>.png
  public/assets/<id>/    00.png 是封面，正文从 01.png 开始，正方形 1:1

本仓库的契约：content/scenes/<id>.json（slots + pages[].img/alt，4:3 的 1024x730）。
差异处理：
  - 句型名映射 descriptive→describe、affirmative→praise，其余同名；
  - 变量只用 {companion}（= who）留给 B 现场替换，child/when/where 直接按默认值写死进正文；
  - 图片按 1:1 居中补白到 1024x1024（不裁内容，避免切掉上方留给文字的留白）；
  - 封面 00.png 取该场景第 1 页的图（想换就手动替换同名文件）。

用法：
  python tools/export_b_schema.py <输出目录>
默认输出到 default-workspace/hack4good-B格式
"""

import json
import os
import sys

from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENES = os.path.join(REPO, "content", "scenes")

TYPE_MAP = {
    "descriptive": "describe",
    "process": "process",
    "perspective": "perspective",
    "directive": "directive",
    "affirmative": "praise",
    "praise": "praise",
    "describe": "describe",
}

ORDER = ["medication", "injection", "haircut", "kindergarten", "restaurant", "arrival", "handup", "line", "askhelp", "shopping"]


def fill(text, vars_):
    for k, v in vars_.items():
        text = text.replace("{%s}" % k, v)
    return text


def square(path, target, bg=(251, 247, 240)):
    """居中补成 1:1；上下的补白用边缘那一行的平均色，纯色平涂，不会出现拉丝。"""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    side = max(w, h)
    canvas = Image.new("RGB", (side, side), bg)
    dx, dy = (side - w) // 2, (side - h) // 2
    if dy > 0:
        paper = mean_color(im.crop((0, 0, w, 1)))  # 用顶部那一行的颜色当纸色，上下一致
        top = Image.new("RGB", (w, dy), paper)
        bottom = Image.new("RGB", (w, side - dy - h), paper)
        canvas.paste(top, (dx, 0))
        canvas.paste(bottom, (dx, dy + h))
    if dx > 0:
        left = Image.new("RGB", (dx, h), mean_color(im.crop((0, 0, 1, h))))
        right = Image.new("RGB", (side - dx - w, h), mean_color(im.crop((w - 1, 0, w, h))))
        canvas.paste(left, (0, dy))
        canvas.paste(right, (dx + w, dy))
    canvas.paste(im, (dx, dy))
    canvas.save(target, "PNG", optimize=True)
    return canvas.size


def blank(target, size=1024, paper=(248, 243, 234)):
    Image.new("RGB", (size, size), paper).save(target, "PNG", optimize=True)
    return size


def mean_color(strip):
    px = list(strip.convert("RGB").getdata())
    n = len(px) or 1
    return tuple(sum(c[i] for c in px) // n for i in range(3))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(REPO), "..", "default-workspace", "hack4good-B格式"
    )
    out = os.path.abspath(out)
    stories_dir = os.path.join(out, "content", "stories")
    assets_dir = os.path.join(out, "public", "assets")
    os.makedirs(stories_dir, exist_ok=True)

    for order, scene_id in enumerate(ORDER):
        src = os.path.join(SCENES, scene_id + ".json")
        if not os.path.exists(src):
            print("skip (missing)", src)
            continue
        scene = json.load(open(src, encoding="utf-8"))

        # 默认值：companion 用 who，其余直接写死进正文
        defaults = {}
        flat = {}
        for key, slot in scene["slots"].items():
            flat[key] = slot["default"]
        defaults["companion"] = flat.get("who", "妈妈")
        bake = {k: v for k, v in flat.items() if k != "who"}

        dst_assets = os.path.join(assets_dir, scene_id)
        os.makedirs(dst_assets, exist_ok=True)

        pages = []
        for i, page in enumerate(scene["pages"], start=1):
            name = "%02d.png" % i
            src_img = os.path.join(REPO, scene["image_pool"], page["img"])
            if os.path.exists(src_img):
                square(src_img, os.path.join(dst_assets, name))
            else:  # 图还没出：放一张纸色占位，别让加载器 404
                blank(os.path.join(dst_assets, name))
            pages.append({
                "type": TYPE_MAP.get(page["type"], "describe"),
                "text": fill(page["text"], bake).replace("{who}", "{companion}"),
                "image": "/assets/%s/%s" % (scene_id, name),
            })

        # 封面 = 第 1 页的图
        first = os.path.join(dst_assets, "01.png")
        cover = os.path.join(dst_assets, "00.png")
        if not os.path.exists(cover):
            Image.open(first).save(cover, "PNG", optimize=True)

        story = {
            "id": scene_id,
            "order": order,
            "title": fill(scene["title"], bake),
            "coverImage": "/assets/%s/00.png" % scene_id,
            "defaults": defaults,
            "pages": pages,
        }
        with open(os.path.join(stories_dir, scene_id + ".json"), "w", encoding="utf-8") as fh:
            json.dump(story, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("OK %-14s %d 页" % (scene_id, len(pages)))

    print("输出:", out)


if __name__ == "__main__":
    main()
