"""Favicon: the Mosely snowflake in three dimensions, seen from the usual angle.

    python3 tools/favicon.py

One iteration, not two. Level 1 is nineteen cubes of a possible twenty-seven,
the eight corners gone, and at sixteen pixels that is already near the limit of
what reads. Level 2 would be truer to the hero and unrecognisable in a tab.

Drawn with the same isometric projection and three-tone ramp as the sprite
sheet, so the icon and the site are plainly the same object: top face --px-1,
left face --px-2, right face --px-3, painted back to front.

Written straight into public/, which Vite copies to the site root untouched, so
the icons land in place wherever the generator is run from. favicon.ico sits at
the root because that is the path a browser asks for unprompted; the rest are
named by the <link> tags in each page's head.
"""
import pathlib
import struct
import sys
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from raster import bounding_box, fill_polygon, runs_of_equal, svg_rect

GRID, LEVEL = 3, 1
BG = (6, 18, 27)                                          # --bg
RAMP = [(125, 255, 184), (63, 207, 133), (31, 143, 90)]   # --px-1, --px-2, --px-3

VECTOR_CELL = 64          # the SVG is drawn large; it scales without resampling
ICO_SIZES = (16, 32)
PNG_SIZES = (32, 180)

PUBLIC = pathlib.Path(__file__).resolve().parent.parent / 'public'
ICONS = PUBLIC / 'assets' / 'icons'


def cell_for(size):
    """The half-width that draws this shape at `size` pixels exactly.

    An isometric cube of half-width w makes art about 8w across, so a target of
    S pixels wants w = S / 8 and lands on the grid. Resampling one fixed
    rendering down to 16 px instead turns the shape to mush, which is the whole
    problem with a detailed favicon.
    """
    return max(1, round(size / 8))


def keep(i, j, k, level=LEVEL):
    """Mosely: a cell lives while every digit triple still holds a middle digit."""
    for _ in range(level):
        if 1 not in (i % 3, j % 3, k % 3):
            return False
        i, j, k = i // 3, j // 3, k // 3
    return True


CELLS = [(i, j, k)
         for i in range(GRID) for j in range(GRID) for k in range(GRID)
         if keep(i, j, k)]


def faces_of(sx, sy, w, h, v):
    """The three visible faces of one cube, as polygons in screen space.

    @returns: (polygon, colour) pairs.
    """
    return (
        ([(sx, sy - h), (sx + w, sy), (sx, sy + h), (sx - w, sy)], RAMP[0]),
        ([(sx - w, sy), (sx, sy + h), (sx, sy + h + v), (sx - w, sy + v)], RAMP[1]),
        ([(sx + w, sy), (sx, sy + h), (sx, sy + h + v), (sx + w, sy + v)], RAMP[2]),
    )


def painters_order(cells):
    """Cells sorted so a nearer cube is always painted over a farther one."""
    return sorted(cells, key=lambda c: c[0] + c[1] + c[2])


def paint(half_cell):
    """Paints the snowflake back to front into a grid of colours."""
    w, h, v = half_cell, max(1, half_cell // 2), half_cell
    span = 2 * GRID * w + w * 2
    tall = 2 * GRID * h + GRID * v + v * 2
    grid = [[None] * span for _ in range(tall)]
    ox, oy = GRID * w + w, v

    for (i, j, k) in painters_order(CELLS):
        sx = ox + (i - k) * w
        sy = oy + (i + k) * h - j * v + GRID * v
        for (polygon, colour) in faces_of(sx, sy, w, h, v):
            fill_polygon(grid, polygon, colour)

    return grid


def square_off(art, half_cell):
    """Centres the art in a square canvas so no size crops the shape.

    At a half-cell of three or less there is no room to spare, so the art is
    squared without the extra margin.
    """
    art_width, art_height = len(art[0]), len(art)
    side = max(art_width, art_height)
    if half_cell > 3:
        side += 2

    squared = [[None] * side for _ in range(side)]
    left, top = (side - art_width) // 2, (side - art_height) // 2
    for y in range(art_height):
        for x in range(art_width):
            squared[top + y][left + x] = art[y][x]
    return squared


def render(half_cell):
    """The snowflake as a square grid of colours, drawn for this cell size."""
    grid = paint(half_cell)
    x0, x1, y0, y1 = bounding_box(grid)
    art = [[grid[y][x] for x in range(x0, x1 + 1)] for y in range(y0, y1 + 1)]
    return square_off(art, half_cell)


ART = render(cell_for(VECTOR_CELL))
SIDE = len(ART)


def hex_colour(colour):
    """An RGB triple as the #rrggbb SVG and CSS want."""
    return '#{:02x}{:02x}{:02x}'.format(*colour)


def svg_bytes(art):
    """The art as an SVG of one rect per run, on the site's background."""
    rects = [svg_rect(x, y, length, hex_colour(colour))
             for (y, row) in enumerate(art)
             for (x, length, colour) in runs_of_equal(row)]
    side = len(art)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {side} {side}" '
            f'shape-rendering="crispEdges">'
            f'<rect width="{side}" height="{side}" fill="{hex_colour(BG)}"/>'
            f'{"".join(rects)}</svg>\n')


def sample(art, size):
    """Nearest-neighbour sampling of the art down to a square of `size`.

    Unpainted cells become the background, since these formats have no alpha.

    @returns: rows of RGB triples.
    """
    side = len(art)
    return [[art[row * side // size][col * side // size] or BG
             for col in range(size)]
            for row in range(size)]


def png_chunk(tag, data):
    """One PNG chunk: length, tag, payload, CRC."""
    tagged = tag + data
    return struct.pack('>I', len(data)) + tagged + struct.pack('>I', zlib.crc32(tagged))


def png_bytes(size):
    """A truecolour PNG of the art at `size`, built without an image library."""
    art = render(cell_for(size))        # drawn for this size, not scaled down to it
    raw = b''
    for row in sample(art, size):
        raw += b'\x00'                  # filter byte: none
        for colour in row:
            raw += bytes(colour)

    return (b'\x89PNG\r\n\x1a\n'
            + png_chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
            + png_chunk(b'IDAT', zlib.compress(raw, 9))
            + png_chunk(b'IEND', b''))


def ico_bytes(sizes=ICO_SIZES):
    """An ICO wrapping one PNG per size, which every current browser reads."""
    images = [(size, png_bytes(size)) for size in sizes]

    header = struct.pack('<HHH', 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries, blob = b'', b''
    for (size, data) in images:
        entries += struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32,
                               len(data), offset)
        blob += data
        offset += len(data)

    return header + entries + blob


def write(path, data):
    """Writes text or bytes, reporting the size the way main() prints it."""
    path = pathlib.Path(path)
    path.write_bytes(data.encode() if isinstance(data, str) else data)
    return len(data)


def main():
    ICONS.mkdir(parents=True, exist_ok=True)
    print(f'{len(CELLS)} of {GRID ** 3} cubes')
    for size in (16, 32, 180):
        print(f'  art for {size}px: cell {cell_for(size)} -> '
              f'{len(render(cell_for(size)))} units')

    written = [
        ('favicon.svg     ', ICONS / 'favicon.svg', svg_bytes(ART)),
        ('favicon-32.png  ', ICONS / 'favicon-32.png', png_bytes(32)),
        ('favicon.ico     ', PUBLIC / 'favicon.ico', ico_bytes()),
        ('apple-touch-icon', ICONS / 'apple-touch-icon.png', png_bytes(180)),
    ]
    for (label, path, data) in written:
        print(label, write(path, data), 'bytes')


if __name__ == '__main__':
    main()
