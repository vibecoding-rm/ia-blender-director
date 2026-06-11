"""Genera las texturas de las pantallas del estudio de noticias (PIL → PNG).

Las imágenes se guardan en assets/branding/screens/ y render_shot.py las
aplica como materiales emisivos en las pantallas del set "news studio".
Regenerar: python3 scripts/generate_screen_textures.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "branding" / "screens"
SIZE = (1024, 600)

RED = (185, 18, 26)
DARK = (12, 14, 24)
BLUE = (10, 40, 110)
YELLOW = (255, 214, 0)
WHITE = (245, 245, 245)


def _font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size)


def screen_logo() -> Image.Image:
    """Pantalla central: logo del noticiero."""
    img = Image.new("RGB", SIZE, BLUE)
    draw = ImageDraw.Draw(img)
    for y in range(0, SIZE[1], 4):  # scanlines sutiles de pantalla
        draw.line([(0, y), (SIZE[0], y)], fill=(8, 34, 95), width=1)
    draw.ellipse([SIZE[0] / 2 - 150, 60, SIZE[0] / 2 + 150, 360], fill=RED)
    draw.ellipse([SIZE[0] / 2 - 130, 80, SIZE[0] / 2 + 130, 340], fill=DARK)
    draw.text((SIZE[0] / 2, 210), "LC", font=_font(150), fill=YELLOW, anchor="mm")
    draw.text((SIZE[0] / 2, 430), "EL NOTICIERO", font=_font(72), fill=WHITE, anchor="mm")
    draw.text((SIZE[0] / 2, 510), "DE LA COTORRA", font=_font(72), fill=YELLOW, anchor="mm")
    return img


def screen_ultima_hora() -> Image.Image:
    """Pantalla lateral: banner de última hora."""
    img = Image.new("RGB", SIZE, RED)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, SIZE[0], 110], fill=DARK)
    draw.rectangle([0, SIZE[1] - 110, SIZE[0], SIZE[1]], fill=DARK)
    draw.text((SIZE[0] / 2, 55), "● EN VIVO ●", font=_font(56), fill=RED, anchor="mm")
    draw.text((SIZE[0] / 2, SIZE[1] / 2 - 40), "ÚLTIMA", font=_font(150), fill=WHITE, anchor="mm")
    draw.text((SIZE[0] / 2, SIZE[1] / 2 + 110), "HORA", font=_font(150), fill=YELLOW, anchor="mm")
    draw.text((SIZE[0] / 2, SIZE[1] - 55), "noticias 100% oficiales*", font=_font(40), fill=WHITE, anchor="mm")
    return img


def screen_mapa() -> Image.Image:
    """Pantalla lateral: mapa estilizado de Cuba con 'zonas de normalidad'."""
    img = Image.new("RGB", SIZE, (8, 24, 60))
    draw = ImageDraw.Draw(img)
    for y in range(0, SIZE[1], 4):
        draw.line([(0, y), (SIZE[0], y)], fill=(6, 20, 52), width=1)
    # Silueta MUY estilizada de la isla (polígono alargado tipo caimán)
    island = [
        (90, 330), (200, 280), (340, 260), (480, 250), (610, 255),
        (730, 280), (860, 330), (930, 380), (860, 400), (730, 380),
        (600, 370), (470, 365), (340, 370), (210, 380), (120, 370),
    ]
    draw.polygon(island, fill=(20, 130, 60), outline=(120, 220, 140))
    # Puntos "calientes" parpadeando de normalidad absoluta
    for x, y in [(250, 320), (470, 305), (700, 330), (840, 365)]:
        draw.ellipse([x - 14, y - 14, x + 14, y + 14], fill=RED)
        draw.ellipse([x - 6, y - 6, x + 6, y + 6], fill=YELLOW)
    draw.text((SIZE[0] / 2, 80), "ZONAS DE NORMALIDAD", font=_font(58), fill=WHITE, anchor="mm")
    draw.text((SIZE[0] / 2, 150), "(todas, según el parte oficial)", font=_font(40), fill=YELLOW, anchor="mm")
    draw.text((SIZE[0] / 2, 520), "100% DE COBERTURA*", font=_font(48), fill=WHITE, anchor="mm")
    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    screen_logo().save(OUT_DIR / "screen_center.png")
    screen_ultima_hora().save(OUT_DIR / "screen_left.png")
    screen_mapa().save(OUT_DIR / "screen_right.png")
    print(f"Texturas generadas en {OUT_DIR}")


if __name__ == "__main__":
    main()
