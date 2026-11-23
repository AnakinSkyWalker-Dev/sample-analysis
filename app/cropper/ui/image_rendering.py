from __future__ import annotations

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def fit_preview(
    image: Image.Image,
    size: tuple[int, int],
    mode: str,
) -> Image.Image:
    resampling = (
        Image.Resampling.LANCZOS
        if mode == "quality"
        else Image.Resampling.BILINEAR
    )
    preview = ImageOps.contain(image, size, method=resampling)
    if mode == "quality" and preview.size != image.size:
        preview = preview.filter(
            ImageFilter.UnsharpMask(radius=0.7, percent=115, threshold=3)
        )
    return preview


def resize_preview(
    image: Image.Image,
    size: tuple[int, int],
    mode: str,
) -> Image.Image:
    resampling = (
        Image.Resampling.LANCZOS
        if mode == "quality"
        else Image.Resampling.BILINEAR
    )
    preview = image.resize(size, resampling)
    if mode == "quality" and preview.size != image.size:
        preview = ImageEnhance.Sharpness(preview).enhance(1.12)
    return preview
