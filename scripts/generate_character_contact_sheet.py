"""Generate a no-GPU character contact sheet from asset metadata.

This is a fallback for machines where Blender can import/export GLBs but cannot
render because no OpenGL vendor is available. The Blender-rendered sheet remains
available via scripts/blender/render_character_contact_sheet.py.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "characters"
OUT = ROOT / "docs" / "character_contact_sheet.png"


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _color_for(asset_id: str) -> tuple[int, int, int]:
    digest = hashlib.sha1(asset_id.encode("utf-8")).digest()
    return (
        80 + digest[0] % 120,
        80 + digest[1] % 120,
        80 + digest[2] % 120,
    )


def main() -> None:
    manifests = []
    for path in sorted(ASSETS.glob("*/asset.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("type") == "character" and data.get("path"):
            manifests.append(data)

    columns = 5
    tile_w, tile_h = 360, 220
    rows = (len(manifests) + columns - 1) // columns
    image = Image.new("RGB", (columns * tile_w, rows * tile_h), (28, 30, 34))
    draw = ImageDraw.Draw(image)
    title_font = _font(22)
    small_font = _font(15)

    for i, data in enumerate(manifests):
        col = i % columns
        row = i // columns
        x = col * tile_w
        y = row * tile_h
        color = _color_for(data["id"])
        draw.rounded_rectangle((x + 12, y + 12, x + tile_w - 12, y + tile_h - 12), radius=10, fill=(42, 45, 50), outline=color, width=4)
        draw.ellipse((x + 35, y + 35, x + 135, y + 135), fill=color)
        draw.rectangle((x + 78, y + 122, x + 92, y + 172), fill=color)
        draw.ellipse((x + 58, y + 70, x + 76, y + 88), fill=(245, 245, 230))
        draw.ellipse((x + 94, y + 70, x + 112, y + 88), fill=(245, 245, 230))
        draw.text((x + 155, y + 38), data["id"], fill=(245, 245, 245), font=title_font)
        draw.text((x + 155, y + 72), data.get("name", data["id"])[:28], fill=(210, 214, 220), font=small_font)
        metadata = data.get("metadata") or {}
        bones = metadata.get("bones") or []
        mouth = "Beak" if "Beak" in bones else "Jaw" if "Jaw" in bones else "none"
        draw.text((x + 155, y + 104), f"mouth: {mouth}", fill=(180, 185, 192), font=small_font)
        draw.text((x + 155, y + 130), "Idle / Talk / Walk" if mouth != "none" else "generic proxy", fill=(180, 185, 192), font=small_font)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
