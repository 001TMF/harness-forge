"""Generate the Harness Forge title banner — pixel letters + stepped 3D double-outline shadow.

    python assets/make_title.py        # writes assets/title.png

Pure Pillow, no external fonts (the glyphs are a built-in 5x7 bitmap font), so it is fully
reproducible. Tweak CELL / OFF1 / OFF2 / colors to restyle.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

FONT = {
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "N": ["10001", "11001", "10101", "10101", "10101", "10011", "10001"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "G": ["01111", "10000", "10000", "10111", "10001", "10001", "01110"],
    " ": ["00000"] * 7,
}

TEXT = "HARNESS FORGE"
CELL = 22          # pixel-cell size
LSP = 1            # cells between letters
SPACE = 3          # cells for a space
PAD = 48           # margin
OFF1, OFF2 = (7, 7), (13, 13)   # the two stepped 3D-shadow offsets (down-right)
GRID = (95, 95, 95, 255)        # faint internal grid colour


def render() -> Image.Image:
    cols = sum((5 if ch != " " else SPACE) + LSP for ch in TEXT) - LSP
    w = cols * CELL + 2 * PAD + OFF2[0]
    h = 7 * CELL + 2 * PAD + OFF2[1]

    sil = Image.new("L", (w, h), 0)
    ds = ImageDraw.Draw(sil)
    front = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    df = ImageDraw.Draw(front)

    x = PAD
    for ch in TEXT:
        glyph = FONT[ch]
        width = 5 if ch != " " else SPACE
        for r, row in enumerate(glyph):
            for c, on in enumerate(row):
                if on == "1":
                    px, py = x + c * CELL, PAD + r * CELL
                    ds.rectangle([px, py, px + CELL, py + CELL], fill=255)
                    df.rectangle([px, py, px + CELL, py + CELL], fill=(255, 255, 255, 255))
        x += (width + LSP) * CELL

    # faint internal grid, clipped to the letters
    grid = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dg = ImageDraw.Draw(grid)
    gx = PAD
    while gx <= w:
        dg.line([(gx, 0), (gx, h)], fill=GRID, width=1)
        gx += CELL
    gy = PAD
    while gy <= h:
        dg.line([(0, gy), (w, gy)], fill=GRID, width=1)
        gy += CELL
    grid_clipped = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    grid_clipped.paste(grid, (0, 0), mask=sil)

    # 1px outer contour -> stepped double 3D outline behind the letters
    ring = ImageChops.subtract(sil.filter(ImageFilter.MaxFilter(3)), sil)
    ring_w = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    ring_w.putalpha(ring)

    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    canvas.alpha_composite(ring_w, OFF2)
    canvas.alpha_composite(ring_w, OFF1)
    canvas.alpha_composite(front)
    canvas.alpha_composite(grid_clipped)
    return canvas.convert("RGB")


if __name__ == "__main__":
    out = Path(__file__).parent / "title.png"
    render().save(out)
    print(f"wrote {out}")
