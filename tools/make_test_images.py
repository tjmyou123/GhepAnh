"""Tao anh mau ngau nhien de thu nghiem.

    python tools/make_test_images.py 47   -> tao thu muc test_input_47 voi 47 anh
"""

import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def make(n: int, root: Path) -> Path:
    folder = root / f"test_input_{n}"
    folder.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    sizes = [(800, 600), (600, 800), (1200, 800), (800, 1200),
             (1000, 1000), (1600, 900), (900, 1600), (2000, 800)]
    for i in range(1, n + 1):
        w, h = rng.choice(sizes)
        color = (rng.randrange(40, 255), rng.randrange(40, 255), rng.randrange(40, 255))
        img = Image.new("RGB", (w, h), color)
        d = ImageDraw.Draw(img)
        d.rectangle([8, 8, w - 8, h - 8], outline=(0, 0, 0), width=6)
        d.text((w // 2 - 20, h // 2 - 10), str(i), fill=(0, 0, 0))
        img.save(folder / f"anh_{i:03d}.jpg", quality=90)
    return folder


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    out = make(n, Path(__file__).resolve().parent.parent / "test_data")
    print(out)
