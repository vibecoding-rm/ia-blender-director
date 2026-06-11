"""Tarjeta de gancho (hook) para abrir los Shorts.

El primer frame decide si el espectador se queda: titular absurdo en texto
gigante de alto contraste con zoom de entrada. Se genera con PIL + ffmpeg
zoompan y se antepone al video.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BG_COLOR = (180, 16, 24)        # rojo "breaking news"
BAR_COLOR = (12, 12, 16)
TEXT_COLOR = (255, 255, 255)
ACCENT_COLOR = (255, 214, 0)    # amarillo titular
BRAND = "EL NOTICIERO DE LA COTORRA"


def make_hook_clip(
    title: str,
    output_mp4: Path,
    *,
    resolution: tuple[int, int],
    fps: int,
    duration: float = 1.4,
) -> bool:
    """Genera el clip de gancho: tarjeta de titular con zoom-in suave."""
    width, height = resolution
    card = _render_card(title, width, height)
    card_png = output_mp4.with_suffix(".png")
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    card.save(card_png)

    frames = max(2, int(duration * fps))
    # Zoom-out 1.10 → 1.0: movimiento inmediato y el frame final queda completo.
    # El texto vive en el 84% central (área segura), así el zoom nunca lo corta.
    zoom = (
        f"zoompan=z='1.10-0.10*on/{frames}':d={frames}"
        f":x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s={width}x{height}:fps={fps}"
    )
    result = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(card_png),
         "-vf", zoom, "-frames:v", str(frames),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output_mp4)],
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"error: hook clip falló: {result.stderr.decode(errors='replace')[-300:]}", file=sys.stderr)
        return False
    return output_mp4.exists()


def _render_card(title: str, width: int, height: int) -> Image.Image:
    img = Image.new("RGB", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    safe_width = width * 0.84  # el zoom recorta hasta ~10%: todo texto vive aquí

    # Banda superior de marca (más alta que el recorte máximo del zoom)
    bar_h = int(height * 0.10)
    draw.rectangle([0, 0, width, bar_h], fill=BAR_COLOR)
    brand_font = _fit_font(draw, BRAND, safe_width, int(bar_h * 0.40))
    draw.text((width / 2, bar_h * 0.62), BRAND, font=brand_font, fill=TEXT_COLOR, anchor="mm")

    # "ÚLTIMA HORA"
    tag_font = _font(int(height * 0.032))
    draw.text((width / 2, height * 0.30), "●  ÚLTIMA HORA  ●", font=tag_font, fill=TEXT_COLOR, anchor="mm")

    # Titular gigante (envuelto, ajustado al área segura)
    headline = title.upper()
    wrapped = textwrap.fill(headline, width=12)
    longest = max(wrapped.split("\n"), key=len)
    headline_font = _fit_font(draw, longest, safe_width, int(height * 0.058))
    draw.multiline_text(
        (width / 2, height * 0.50), wrapped, font=headline_font,
        fill=ACCENT_COLOR, anchor="mm", align="center",
        stroke_width=max(2, int(height * 0.004)), stroke_fill=(0, 0, 0),
    )

    # Banda inferior
    draw.rectangle([0, height - bar_h, width, height], fill=BAR_COLOR)
    foot_font = _font(int(bar_h * 0.30))
    draw.text((width / 2, height - bar_h * 0.62), "noticias 100% oficiales*",
              font=foot_font, fill=(200, 200, 200), anchor="mm")
    return img


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: float, start_size: int) -> ImageFont.FreeTypeFont:
    """Reduce el tamaño hasta que `text` quepa en `max_width`."""
    size = start_size
    while size > 10:
        font = _font(size)
        if draw.textlength(text, font=font) <= max_width:
            return font
        size = int(size * 0.92)
    return _font(size)


def _font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size)
