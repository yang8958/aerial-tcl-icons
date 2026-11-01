#!/usr/bin/env python3
"""Turn an app's own icon into an Aerial home-tile picture (1280x720, 16:9).

Aerial draws a tile from the app's launcher icon by putting the icon in the middle of a
16:9 tile and repeating its edge pixels sideways. On apps whose icon is a square plate
that reads as a square stuck inside a rectangle, with a visible seam. These recipes
rebuild the tile the way a hand-drawn one looks: the brand colour fills the whole tile
and the logo sits on top of it, with no plate, no card and no border.

Two shapes of icon are handled:

  white    a coloured plate with a white logo   -> brand-coloured gradient + white logo
  colored  a white plate with a coloured logo   -> white tile + the logo in its own colours

Usage:
    python make_tile.py white   source.png out.png
    python make_tile.py colored source.png out.png
    python make_tile.py lockup  logo.png  out.png --bg "#ffffff" --width 0.78

`source.png` is the 16:9 tile Aerial already draws, downloaded from
    http://<tv>:8790/<token>/tile/<package>
or any picture with the icon centred in a square box. `lockup` takes a ready-made
horizontal logo (icon + wordmark) and centres it on a flat colour, the way 云视听极光's
tile is laid out.

Requires: pillow, numpy
"""
import argparse
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT_W, OUT_H = 1280, 720
S = 720  # the icon is taken from the middle square of the source tile


def drop_specks(mask: np.ndarray, min_frac: float = 0.10, min_area: int = 900) -> np.ndarray:
    """Keep only connected blobs big enough to be part of the logo.

    Careful: a design that uses small detached marks (viewfinder corners, for instance)
    loses them here. Pass --keep-specks for those.
    """
    h, w = mask.shape
    b = mask > 128
    seen = np.zeros((h, w), bool)
    keep = np.zeros((h, w), bool)
    total = max(1, int(b.sum()))
    threshold = max(min_area, int(total * min_frac))
    for y0 in range(h):
        for x0 in np.nonzero(b[y0] & ~seen[y0])[0]:
            if seen[y0, x0]:
                continue
            stack = [(y0, int(x0))]
            seen[y0, x0] = True
            comp = []
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and b[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            if len(comp) >= threshold:
                for y, x in comp:
                    keep[y, x] = True
    return (keep.astype(np.uint8) * 255)


def centre_icon(path: str) -> Image.Image:
    """The middle square of a 16:9 tile, upscaled to S x S."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    side = h
    left = (w - side) // 2
    return im.crop((left, 0, left + side, side)).resize((S, S), Image.LANCZOS)


def brand_gradient(icon: Image.Image):
    """Top and bottom colour of the tile's own surround, i.e. the colour Aerial chose."""
    a = np.asarray(icon)
    cols = list(range(3, 12)) + list(range(S - 12, S - 3))
    top = a[3:40][:, cols].reshape(-1, 3).mean(axis=0)
    bottom = a[S - 40:S - 3][:, cols].reshape(-1, 3).mean(axis=0)
    return top, bottom


def gradient_canvas(top, bottom) -> Image.Image:
    t = np.linspace(0, 1, OUT_H)[:, None, None]
    rows = top[None, None, :] * (1 - t) + bottom[None, None, :] * t
    return Image.fromarray(np.clip(np.repeat(rows, OUT_W, axis=1), 0, 255).astype(np.uint8))


def place(canvas: Image.Image, glyph: Image.Image, mask: Image.Image, height_frac=0.52, max_w=0.76):
    target = int(OUT_H * height_frac)
    scale = target / glyph.height
    if glyph.width * scale > OUT_W * max_w:
        scale = (OUT_W * max_w) / glyph.width
    nw, nh = max(1, int(glyph.width * scale)), max(1, int(glyph.height * scale))
    glyph = glyph.resize((nw, nh), Image.LANCZOS)
    mask = mask.resize((nw, nh), Image.LANCZOS)
    canvas.paste(glyph, ((OUT_W - nw) // 2, (OUT_H - nh) // 2), mask)
    return canvas


def hsv(icon: Image.Image):
    arr = np.asarray(icon).astype(np.float32) / 255.0
    hi = arr.max(axis=2)
    lo = arr.min(axis=2)
    sat = np.where(hi > 1e-5, (hi - lo) / np.maximum(hi, 1e-5), 0)
    return arr, sat, hi


def make_white(src: str, dst: str, keep_specks: bool):
    """Coloured plate, white logo -> brand gradient, logo in white."""
    icon = centre_icon(src)
    _, sat, val = hsv(icon)
    mask = ((sat < 0.22) & (val > 0.82)).astype(np.uint8) * 255
    if not keep_specks:
        mask = drop_specks(mask)
    m = Image.fromarray(mask).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    box = m.point(lambda v: 255 if v > 60 else 0).getbbox()
    if not box:
        sys.exit("no white logo found in %s" % src)
    glyph = Image.new("RGB", (S, S), (255, 255, 255)).crop(box)
    mask = m.crop(box)
    top, bottom = brand_gradient(icon)
    place(gradient_canvas(top, bottom), glyph, mask).save(dst)


def make_colored(src: str, dst: str, keep_specks: bool):
    """White plate, coloured logo -> white tile, logo keeps its own colours."""
    icon = centre_icon(src)
    _, sat, val = hsv(icon)
    mask = ((sat > 0.28) & (val > 0.22)).astype(np.uint8) * 255
    if not keep_specks:
        mask = drop_specks(mask)
    keep = Image.new("L", (S, S), 0)
    ImageDraw.Draw(keep).rounded_rectangle(
        [int(S * 0.08), int(S * 0.08), int(S * 0.92), int(S * 0.92)], radius=int(S * 0.08), fill=255
    )
    m = Image.fromarray(mask).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    m = Image.composite(m, Image.new("L", (S, S), 0), keep)
    box = m.point(lambda v: 255 if v > 60 else 0).getbbox()
    if not box:
        sys.exit("no coloured logo found in %s" % src)
    glyph = icon.crop(box)
    mask = m.crop(box)
    canvas = Image.new("RGB", (OUT_W, OUT_H), (252, 252, 252))
    place(canvas, glyph, mask, height_frac=0.50, max_w=0.70).save(dst)


def make_lockup(src: str, dst: str, bg: str, width_frac: float):
    """A ready-made horizontal logo (icon + wordmark) centred on a flat colour."""
    logo = Image.open(src).convert("RGB")
    a = np.asarray(logo).astype(int)
    mask = np.abs(a - 255).sum(axis=2) > 40
    ys, xs = np.where(mask)
    if len(xs) == 0:
        sys.exit("the lockup is blank")
    logo = logo.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    target = int(OUT_W * width_frac)
    scale = target / logo.width
    logo = logo.resize((target, max(1, int(logo.height * scale))), Image.LANCZOS)
    canvas = Image.new("RGB", (OUT_W, OUT_H), bg)
    canvas.paste(logo, ((OUT_W - logo.width) // 2, (OUT_H - logo.height) // 2))
    canvas.save(dst)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["white", "colored", "lockup"])
    p.add_argument("source")
    p.add_argument("output")
    p.add_argument("--keep-specks", action="store_true",
                   help="keep small detached marks (viewfinder corners and the like)")
    p.add_argument("--bg", default="#ffffff", help="lockup mode: background colour")
    p.add_argument("--width", type=float, default=0.78, help="lockup mode: logo width as a fraction of the tile")
    a = p.parse_args()

    if a.mode == "white":
        make_white(a.source, a.output, a.keep_specks)
    elif a.mode == "colored":
        make_colored(a.source, a.output, a.keep_specks)
    else:
        make_lockup(a.source, a.output, a.bg, a.width)
    print("wrote", a.output)


if __name__ == "__main__":
    main()
