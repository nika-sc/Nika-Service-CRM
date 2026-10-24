"""Rebuild the Nika Service installer artwork from packaging/windows/nika-service-logo.jpg.

Run from the repository root on a machine with Pillow:

    python scripts/windows/build-installer-artwork.py

It overwrites wizard-large.bmp, wizard-small.bmp, installer-hero.bmp and
nika-service.ico next to the source logo. The installer build only reads those
files, so this script is not part of build-offline-bundle.ps1.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PACKAGING = Path(__file__).resolve().parents[2] / "packaging" / "windows"
SRC = PACKAGING / "nika-service-logo.jpg"
BOLD = r"C:\Windows\Fonts\segoeuib.ttf"
REGULAR = r"C:\Windows\Fonts\segoeui.ttf"
ORANGE = (242, 107, 35)

# Crops inside the 1184x592 source logo.
BOX_MARK = (110, 8, 622, 186)
BOX_CONTACTS = (645, 5, 1180, 252)


def white_mark(crop):
    """Orange/black JPEG mark -> white shape with a soft alpha edge."""
    crop = crop.convert("RGB")
    width, height = crop.size
    out = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    source = crop.load()
    target = out.load()
    for y in range(height):
        for x in range(width):
            r, g, b = source[x, y]
            alpha = int(max(0.0, min(255.0, (255 - min(r, g, b)) * 4.0)))
            if alpha:
                target[x, y] = (255, 255, 255, alpha)
    return out


def fit(image, width=None, height=None):
    w, h = image.size
    ratio = (width / w) if width else (height / h)
    return image.resize((max(1, int(w * ratio)), max(1, int(h * ratio))), Image.LANCZOS)


def badge(size, mark, radius_ratio=0.19, logo_width_ratio=0.78):
    card = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=int(size * radius_ratio), fill=ORANGE + (255,))
    scaled = fit(mark, width=int(size * logo_width_ratio))
    card.alpha_composite(scaled, ((size - scaled.width) // 2, (size - scaled.height) // 2))
    return card


def main():
    logo = Image.open(SRC).convert("RGB")
    mark = white_mark(logo.crop(BOX_MARK))

    large = Image.new("RGB", (164, 314), (255, 255, 255))
    draw = ImageDraw.Draw(large)
    top = fit(logo.crop((40, 5, 622, 248)), width=148)
    large.paste(top, ((164 - top.width) // 2, 14))
    draw.rectangle([0, 118, 164, 314], fill=ORANGE)
    y = 136
    for text, font, gap in (
        ("СЕРВИСНЫЙ ЦЕНТР", ImageFont.truetype(BOLD, 11), 16),
        ("«НИКА»", ImageFont.truetype(BOLD, 13), 12),
        ("Сочи, Молокова 20/73", ImageFont.truetype(REGULAR, 10), 14),
        ("nika-sc.ru", ImageFont.truetype(BOLD, 11), 0),
    ):
        box = draw.textbbox((0, 0), text, font=font)
        draw.text(((164 - (box[2] - box[0])) // 2, y), text, font=font, fill=(255, 255, 255))
        y += (box[3] - box[1]) + gap
    large.save(PACKAGING / "wizard-large.bmp")

    badge(55, mark, radius_ratio=0.22, logo_width_ratio=0.82).save(
        PACKAGING / "wizard-small.png")

    hero = Image.new("RGB", (640, 170), (255, 255, 255))
    draw = ImageDraw.Draw(hero)
    left = fit(logo.crop((40, 5, 622, 248)), height=104)
    hero.paste(left, (18, 14))
    right = fit(logo.crop(BOX_CONTACTS), height=110)
    hero.paste(right, (640 - right.width - 16, 10))
    draw.rectangle([0, 136, 640, 170], fill=ORANGE)
    font = ImageFont.truetype(BOLD, 17)
    text = "Сервисный центр «Ника» · Сочи · nika-sc.ru"
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((640 - (box[2] - box[0])) // 2, 136 + (34 - (box[3] - box[1])) // 2 - 2),
              text, font=font, fill=(255, 255, 255))
    hero.save(PACKAGING / "installer-hero.bmp")

    badge(256, mark).save(
        PACKAGING / "nika-service.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    main()
