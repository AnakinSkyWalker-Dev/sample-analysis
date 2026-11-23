from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


TILE_SIZE = (480, 480)
GAP = 1
MARGIN = 0
BACKGROUND = (255, 255, 255)


def compose_montage(
    paths: list[Path],
    rotations: dict[str, int] | None = None,
) -> Image.Image:
    if len(paths) != 6:
        raise ValueError("A montagem precisa de exatamente 6 imagens.")

    width = MARGIN * 2 + TILE_SIZE[0] * 3 + GAP * 2
    height = MARGIN * 2 + TILE_SIZE[1] * 2 + GAP
    montage = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(montage)
    font_path = Path(r"C:\Windows\Fonts\arial.ttf")
    try:
        font = ImageFont.truetype(str(font_path), 38)
    except OSError:
        font = ImageFont.load_default()

    for index, path in enumerate(paths):
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
        rotation = (rotations or {}).get(str(path), 0) % 360
        if rotation:
            image = image.rotate(-rotation, expand=True)
        image = ImageOps.fit(
            image,
            TILE_SIZE,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        column, row = index % 3, index // 3
        tile_x = MARGIN + column * (TILE_SIZE[0] + GAP)
        tile_y = MARGIN + row * (TILE_SIZE[1] + GAP)
        x, y = tile_x, tile_y
        montage.paste(image, (x, y))

        label = chr(ord("A") + index)
        box = draw.textbbox((0, 0), label, font=font)
        label_width = box[2] - box[0]
        label_height = box[3] - box[1]
        padding = 9
        right, top = x + image.width - 16, y + 16
        draw.rounded_rectangle(
            (
                right - label_width - padding * 2,
                top,
                right,
                top + label_height + padding * 2,
            ),
            radius=5,
            fill=(0, 0, 0),
        )
        draw.text(
            (right - label_width - padding, top + padding - box[1]),
            label,
            fill=(255, 255, 255),
            font=font,
        )
    return montage
