"""把 Qoder 生图工作区里的原始 PNG 收进仓库，转 webp 压缩（保留原文件名）。

用法：python tools/import_qoder_raw.py <Qoder 日期目录> [输出目录]
例：  python tools/import_qoder_raw.py "C:\\Users\\19573\\Documents\\Qoder\\2026-11-21"
"""

import os
import sys

from PIL import Image

src = sys.argv[1] if len(sys.argv) > 1 else ""
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "docs", "qoder", "originals"
)
if not src or not os.path.isdir(src):
    print("need a directory:", src)
    raise SystemExit(2)

os.makedirs(out, exist_ok=True)
n = 0
total = 0
for root, _dirs, files in os.walk(src):
    for name in sorted(files):
        if not name.lower().endswith(".png"):
            continue
        path = os.path.join(root, name)
        target = os.path.join(out, os.path.splitext(name)[0] + ".webp")
        if os.path.exists(target):
            continue
        im = Image.open(path).convert("RGB")
        im.save(target, "WEBP", quality=82, method=6)
        size = os.path.getsize(target)
        total += size
        n += 1
        print("%-70s %dx%d %dKB" % (name[:70], im.size[0], im.size[1], size // 1024))
print("DONE", n, "files,", round(total / 1024 / 1024, 1), "MB")
