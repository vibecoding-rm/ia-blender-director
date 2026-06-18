"""Gráficos de broadcast para "El Noticiero de La Cotorra".

Genera overlays con canal alpha (lower-third del presentador, ticker
desplazable y bug de esquina "EN VIVO / ÚLTIMA HORA") como PNG y los compone
sobre el video final con `ffmpeg overlay`. Esto es lo que hace que el resultado
se lea como un noticiero de verdad y no como un render aislado.

Cada overlay estático se dibuja sobre un lienzo del tamaño completo del frame
(transparente salvo el elemento) para superponerlo con `overlay=x=0:y=0` sin
matemática de posicionamiento en ffmpeg. El ticker es la excepción: su texto se
dibuja en una tira tan ancha como el texto y se desplaza con una expresión.
"""

from __future__ import annotations

import sys
from pathlib import Path

import ffmpeg
from PIL import Image, ImageDraw, ImageFont

# Paleta coherente con branding.py (gancho)
RED = (180, 16, 24, 255)         # rojo "breaking news"
DARK = (12, 12, 16, 235)         # barra oscura semitransparente
WHITE = (255, 255, 255, 255)
ACCENT = (255, 214, 0, 255)      # amarillo titular
LABEL_BG = (200, 20, 28, 255)

TICKER_SPEED_PX_S = 130          # velocidad de desplazamiento del ticker


# ── Render de overlays (PIL) ─────────────────────────────────────────────────

def render_lower_third(name: str, role: str, resolution: tuple[int, int]) -> Image.Image:
    """Lower-third del presentador: barra inferior con nombre y cargo."""
    width, height = resolution
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    band_h = int(height * 0.13)
    band_top = int(height * 0.70)
    margin = int(width * 0.05)

    # Bloque de acento + barra principal
    accent_w = int(width * 0.018)
    draw.rectangle([margin, band_top, margin + accent_w, band_top + band_h], fill=ACCENT)
    draw.rectangle([margin + accent_w, band_top, width - margin, band_top + band_h], fill=DARK)

    name_font = _fit_font(draw, name.upper(), width - 2 * margin - accent_w - 40, int(band_h * 0.42), bold=True)
    role_font = _font(int(band_h * 0.24))
    text_x = margin + accent_w + int(width * 0.02)
    draw.text((text_x, band_top + band_h * 0.30), name.upper(), font=name_font, fill=WHITE, anchor="lm")
    draw.text((text_x, band_top + band_h * 0.72), role.upper(), font=role_font, fill=ACCENT, anchor="lm")
    return img


def render_corner_bug(text: str, resolution: tuple[int, int]) -> Image.Image:
    """Bug de esquina superior izquierda: 'ÚLTIMA HORA' / 'EN VIVO'."""
    width, height = resolution
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = int(width * 0.045)
    top = int(height * 0.045)
    pad = int(height * 0.012)
    font = _font(int(height * 0.028), bold=True)
    label = text.upper()
    tw = draw.textlength(label, font=font)
    th = font.size
    dot_r = int(th * 0.32)

    box = [margin, top, margin + dot_r * 3 + tw + pad * 3, top + th + pad * 2]
    draw.rectangle(box, fill=RED)
    cy = top + (th + pad * 2) / 2
    draw.ellipse([margin + pad, cy - dot_r, margin + pad + 2 * dot_r, cy + dot_r], fill=WHITE)
    draw.text((margin + pad + 2 * dot_r + pad, cy), label, font=font, fill=WHITE, anchor="lm")
    return img


def render_ticker(text: str, resolution: tuple[int, int]) -> tuple[Image.Image, Image.Image, int]:
    """Devuelve (fondo_full_frame, tira_texto, ancho_texto) para el ticker."""
    width, height = resolution
    ticker_h = int(height * 0.058)
    ticker_top = height - ticker_h

    # Fondo: barra inferior + etiqueta roja a la izquierda
    bg = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    bgd = ImageDraw.Draw(bg)
    bgd.rectangle([0, ticker_top, width, height], fill=DARK)
    label_font = _font(int(ticker_h * 0.5), bold=True)
    label = "  AL MINUTO  "
    label_w = int(bgd.textlength(label, font=label_font)) + int(width * 0.01)
    bgd.rectangle([0, ticker_top, label_w, height], fill=LABEL_BG)
    bgd.text((label_w / 2, ticker_top + ticker_h / 2), label.strip(), font=label_font, fill=WHITE, anchor="mm")

    # Tira de texto: tan ancha como el contenido (se desplaza por encima)
    sep = "     •     "
    crawl = (sep.join([text.upper()] * 3)) + sep
    text_font = _font(int(ticker_h * 0.46))
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    text_w = int(tmp.textlength(crawl, font=text_font)) + width
    strip = Image.new("RGBA", (max(text_w, width + 1), ticker_h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(strip)
    sd.text((0, ticker_h / 2), crawl, font=text_font, fill=WHITE, anchor="lm")
    return bg, strip, strip.width


# ── Composición sobre el video (ffmpeg) ──────────────────────────────────────

def apply_overlays(
    video,
    work_dir: Path,
    stem: str,
    *,
    resolution: tuple[int, int],
    fps: int,
    video_duration: float,
    lower_third: tuple[str, str] | None = None,
    ticker_text: str | None = None,
    corner_bug: str | None = None,
):
    """Compone los overlays de broadcast sobre el stream de video de ffmpeg.

    Devuelve el nuevo stream. Si no se pide ningún overlay, devuelve `video`
    sin tocar (el grafo no cambia).
    """
    width, height = resolution
    current = video
    duration = max(video_duration, 0.1)

    def _image_input(img: Image.Image, suffix: str):
        path = work_dir / f"{stem}_{suffix}.png"
        img.save(path)
        return ffmpeg.input(str(path), loop=1, framerate=fps, t=duration)

    if ticker_text:
        bg, strip, strip_w = render_ticker(ticker_text, resolution)
        bg_in = _image_input(bg, "ticker_bg")
        strip_in = _image_input(strip, "ticker_strip")
        current = ffmpeg.filter([current, bg_in], "overlay", x=0, y=0, shortest=1)
        ticker_h = int(height * 0.058)
        scroll_x = f"W-mod(t*{TICKER_SPEED_PX_S}\\,{strip_w})"
        current = ffmpeg.filter(
            [current, strip_in], "overlay", x=scroll_x, y=height - ticker_h, shortest=1
        )

    if lower_third:
        name, role = lower_third
        lt_in = _image_input(render_lower_third(name, role, resolution), "lower_third")
        current = ffmpeg.filter([current, lt_in], "overlay", x=0, y=0, shortest=1)

    if corner_bug:
        bug_in = _image_input(render_corner_bug(corner_bug, resolution), "corner_bug")
        current = ffmpeg.filter([current, bug_in], "overlay", x=0, y=0, shortest=1)

    return current


# ── Fuentes (cross-platform) ─────────────────────────────────────────────────

_FONT_CANDIDATES = {
    True: (  # bold
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ),
    False: (  # regular
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ),
}


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    for candidate in _FONT_CANDIDATES[bold]:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    try:
        return ImageFont.load_default(size)
    except TypeError:  # Pillow < 10
        return ImageFont.load_default()


def _fit_font(
    draw: ImageDraw.ImageDraw, text: str, max_width: float, start_size: int, *, bold: bool = False
) -> ImageFont.FreeTypeFont:
    size = start_size
    while size > 10:
        font = _font(size, bold=bold)
        if draw.textlength(text, font=font) <= max_width:
            return font
        size = int(size * 0.92)
    return _font(size, bold=bold)
