"""裁掉 Qoder 生图烘焙在底部的水印条（"AI 生成"）。

用法：  python tools/crop_watermark.py [--bottom 38]
说明：  24 张统一裁，保证一致性；原图会先备份到仓库外的 _shots_orig/。
        裁完尺寸 1024x730，渲染时按 4:3 容器 cover 裁切即可。
"""

import os
import shutil
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "shots")
BACKUP = os.path.join(HERE, "..", "_shots_orig")
SCENES = ["medication", "injection", "haircut", "kindergarten"]

bottom = 38
if "--bottom" in sys.argv:
    bottom = int(sys.argv[sys.argv.index("--bottom") + 1])

total = 0
for scene in SCENES:
    os.makedirs(os.path.join(BACKUP, scene), exist_ok=True)
    for i in range(1, 7):
        path = os.path.join(ROOT, scene, "%02d.webp" % i)
        if not os.path.exists(path):
            print("MISSING", path)
            continue
        shutil.copy2(path, os.path.join(BACKUP, scene, "%02d.webp" % i))
        im = Image.open(path).convert("RGB")
        w, h = im.size
        im2 = im.crop((0, 0, w, h - bottom))
        im2.save(path, "WEBP", quality=86, method=6)
        total += 1
        print("%s/%02d.webp  %dx%d -> %dx%d  %dKB" % (
            scene, i, w, h, im2.size[0], im2.size[1], os.path.getsize(path) // 1024))
print("DONE", total)
