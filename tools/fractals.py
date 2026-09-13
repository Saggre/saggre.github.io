"""Isometric voxel sprites for 3D fractals, computed from their definitions.

Not part of the site build. This is a one-off generator, run by hand when a new
sprite is wanted, and its output is pasted into the sprite sheet. Needs Pillow.

    python3 tools/fractals.py          # writes symbols-fractals.svg here

Every shape is drawn in the same three-tone cube vocabulary as the rest of the
sheet, which is what lets these sit beside the hand-drawn sprites: top face
--px-1, left face --px-2, right face --px-3, painted back to front.

Two families of recipe. A digit rule walks the base-b digits of (i, j, k) and
decides per level, which suits anything built on a cube subdivision. A forward
IFS builds the solid by replacing one shape with scaled copies of itself, which
suits shapes that are not axis-aligned boxes, such as octahedra and pyramids.
"""
import pathlib
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from raster import runs_of_value, svg_rect

SYMBOL_PREFIX = 'px'
OUTPUT = 'symbols-fractals.svg'

# Faces are painted in these marker colours and read back afterwards, which is
# cheaper than tracking which face covered which pixel while drawing.
TOP, LEFT, RIGHT = (255, 0, 0), (0, 255, 0), (0, 0, 255)
TONE = {TOP: 'px-1', LEFT: 'px-2', RIGHT: 'px-3'}

# Painted darkest first so a lighter face is never buried under a darker one.
TONE_ORDER = ('px-3', 'px-2', 'px-1')

CANVAS_PAD = 2


def digits(i, j, k, base, level):
    """The base-`base` digits of a cell's address, least significant first."""
    for _ in range(level):
        yield (i % base, j % base, k % base)
        i, j, k = i // base, j // base, k // base


# --- digit rules ------------------------------------------------------------

def menger(i, j, k, lv):
    return all(sum(1 for d in t if d == 1) < 2 for t in digits(i, j, k, 3, lv))


def vicsek(i, j, k, lv):
    return all(sum(1 for d in t if d == 1) >= 2 for t in digits(i, j, k, 3, lv))


def dust(i, j, k, lv):
    return all(1 not in t for t in digits(i, j, k, 3, lv))


def mosely(i, j, k, lv):
    return all(1 in t for t in digits(i, j, k, 3, lv))


def tetrix(i, j, k, lv):
    return all((a ^ b ^ c) == 0 for (a, b, c) in digits(i, j, k, 2, lv))


def carpet(i, j, k, lv):
    return all(not (a == 1 and c == 1) for (a, _, c) in digits(i, j, k, 3, lv))


def cross(i, j, k, lv):
    return all(sum(1 for d in t if d == 1) == 2 for t in digits(i, j, k, 3, lv))


def menger5(i, j, k, lv):
    return all(sum(1 for d in t if d == 2) < 2 for t in digits(i, j, k, 5, lv))


def jerusalem(i, j, k, lv):
    return all(sum(1 for d in t if d in (1, 2, 3)) < 2
               for t in digits(i, j, k, 5, lv))


def cantor_bar(i, j, k, lv):
    return all(a != 1 and c != 1 for (a, _, c) in digits(i, j, k, 3, lv))


# --- forward IFS ------------------------------------------------------------

def ifs_octahedron(n, level):
    """Six half-scale octahedra at the vertices of the parent, repeated."""
    shapes = [(n / 2, n / 2, n / 2, n / 2)]
    for _ in range(level):
        shapes = [(cx + dx * (r / 2), cy + dy * (r / 2), cz + dz * (r / 2), r / 2)
                  for (cx, cy, cz, r) in shapes
                  for (dx, dy, dz) in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                                       (0, -1, 0), (0, 0, 1), (0, 0, -1))]

    cells = set()
    for (cx, cy, cz, r) in shapes:
        for i in range(max(0, int(cx - r) - 1), min(n, int(cx + r) + 2)):
            for j in range(max(0, int(cy - r) - 1), min(n, int(cy + r) + 2)):
                for k in range(max(0, int(cz - r) - 1), min(n, int(cz + r) + 2)):
                    if abs(i + .5 - cx) + abs(j + .5 - cy) + abs(k + .5 - cz) <= r:
                        cells.add((i, j, k))
    return cells


def ifs_pyramid(n, level):
    """Square-base pyramid replaced by four at its base corners plus one on top."""
    shapes = [(n / 2, 0.0, n / 2, n / 2, n)]        # cx, base y, cz, half-width, height
    for _ in range(level):
        grown = []
        for (cx, by, cz, r, height) in shapes:
            half_r, half_h = r / 2, height / 2
            grown += [(cx + dx * half_r, by, cz + dz * half_r, half_r, half_h)
                      for (dx, dz) in ((-1, -1), (-1, 1), (1, -1), (1, 1))]
            grown.append((cx, by + half_h, cz, half_r, half_h))
        shapes = grown

    cells = set()
    for (cx, by, cz, r, height) in shapes:
        for j in range(max(0, int(by)), min(n, int(by + height) + 1)):
            up = (j + .5 - by) / height
            if not 0 <= up <= 1:
                continue
            half_width = r * (1 - up)
            for i in range(max(0, int(cx - half_width)), min(n, int(cx + half_width) + 1)):
                for k in range(max(0, int(cz - half_width)), min(n, int(cz + half_width) + 1)):
                    if abs(i + .5 - cx) <= half_width and abs(k + .5 - cz) <= half_width:
                        cells.add((i, j, k))
    return cells


SETS = [
    ('menger-2',  ('rule', menger,     3, 2), 5),
    ('menger-3',  ('rule', menger,     3, 3), 2),
    ('vicsek',    ('rule', vicsek,     3, 3), 2),
    ('dust',      ('rule', dust,       3, 3), 2),
    ('mosely',    ('rule', mosely,     3, 2), 5),
    ('tetrix',    ('rule', tetrix,     2, 4), 3),
    ('carpet',    ('rule', carpet,     3, 2), 5),
    ('cross',     ('rule', cross,      3, 3), 2),
    ('menger5',   ('rule', menger5,    5, 2), 2),
    ('jerusalem', ('rule', jerusalem,  5, 2), 2),
    ('bars',      ('rule', cantor_bar, 3, 2), 5),
    ('octa',      ('ifs', ifs_octahedron, 48, 3), 2),
    ('pyramid',   ('ifs', ifs_pyramid,  48, 3), 2),
]


def voxels(spec):
    """The occupied cells of one recipe, and the grid size they live in.

    @returns: (cells, grid size).
    """
    if spec[0] == 'rule':
        _, rule, base, lv = spec
        n = base ** lv
        return {(i, j, k)
                for i in range(n) for j in range(n) for k in range(n)
                if rule(i, j, k, lv)}, n
    _, build, n, lv = spec
    return build(n, lv), n


def faces_of(sx, sy, w, h, v):
    """The three visible faces of one cube, as polygons in screen space.

    @returns: (polygon, marker colour) pairs.
    """
    return (
        ([(sx, sy - h), (sx + w, sy), (sx, sy + h), (sx - w, sy)], TOP),
        ([(sx - w, sy), (sx, sy + h), (sx, sy + h + v), (sx - w, sy + v)], LEFT),
        ([(sx + w, sy), (sx, sy + h), (sx, sy + h + v), (sx + w, sy + v)], RIGHT),
    )


def painters_order(cells):
    """Cells sorted so a nearer cube is always painted over a farther one."""
    return sorted(cells, key=lambda c: c[0] + c[1] + c[2])


def draw(cells, n, w):
    """Paints a shape back to front into an image of marker colours."""
    h, v = max(1, w // 2), w
    width = 2 * n * w + w * 4
    height = 2 * n * h + n * v + v * 4

    image = Image.new('RGB', (width, height), (0, 0, 0))
    pen = ImageDraw.Draw(image)
    ox, oy = n * w + CANVAS_PAD * w, CANVAS_PAD * v

    for (i, j, k) in painters_order(cells):
        sx = ox + (i - k) * w
        sy = oy + (i + k) * h - j * v + n * v
        for (polygon, colour) in faces_of(sx, sy, w, h, v):
            pen.polygon(polygon, fill=colour)

    return image


def tones_from(image):
    """Reads the marker colours back as tone names, keyed by pixel.

    @returns: {(x, y): tone name} for every painted pixel.
    """
    pixels = image.load()
    width, height = image.size
    return {(x, y): TONE[pixels[x, y]]
            for y in range(height)
            for x in range(width)
            if pixels[x, y] in TONE}


def trim(cells):
    """Moves painted pixels onto their own origin.

    @returns: (cells, width, height).
    """
    xs = [x for (x, _) in cells]
    ys = [y for (_, y) in cells]
    ox, oy = min(xs), min(ys)
    moved = {(x - ox, y - oy): tone for ((x, y), tone) in cells.items()}
    return moved, max(xs) - ox + 1, max(ys) - oy + 1


def rows_of(cells, width, height):
    """The pixel map as rows, so runs can be read off a row at a time."""
    rows = [[None] * width for _ in range(height)]
    for ((x, y), tone) in cells.items():
        rows[y][x] = tone
    return rows


def to_symbol(name, image):
    """One drawn shape as an SVG <symbol>, or None when nothing was painted.

    @returns: (symbol, width, height) or None.
    """
    cells = tones_from(image)
    if not cells:
        return None

    cells, width, height = trim(cells)
    rows = rows_of(cells, width, height)
    rects = [svg_rect(x, y, length, f'var(--{tone})')
             for tone in TONE_ORDER
             for (y, row) in enumerate(rows)
             for (x, length) in runs_of_value(row, tone)]

    symbol = (f'<symbol id="{SYMBOL_PREFIX}-{name}" viewBox="0 0 {width} {height}">'
              f'{"".join(rects)}</symbol>')
    return symbol, width, height


def build_sheet(sets):
    """Every recipe as one sheet of symbols, reporting each as it is drawn."""
    symbols = []
    for (name, spec, w) in sets:
        cells, n = voxels(spec)
        drawn = to_symbol(name, draw(cells, n, w))
        if not drawn:
            print(f'{SYMBOL_PREFIX}-{name}: empty')
            continue
        symbol, width, height = drawn
        symbols.append(symbol)
        print(f'{SYMBOL_PREFIX}-{name:11} {len(cells):6} voxels  grid {n:3}  '
              f'{width}x{height}  {len(symbol) / 1024:6.1f} KB')
    return symbols


def main():
    symbols = build_sheet(SETS)
    pathlib.Path(OUTPUT).write_text('\n'.join(symbols))


if __name__ == '__main__':
    main()
