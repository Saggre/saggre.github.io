"""The site's icon set, as isometric voxel models.

    python3 tools/icons.py            # writes symbols-icons.svg here

Same vocabulary as the fractal sprites and px-cube: an isometric grid, three
tones from the ramp, top face --px-1, left --px-2, right --px-3, painted back
to front. The hero is a voxel solid, so the icons are voxel solids too, rather
than flat pixel glyphs that happen to sit next to one.

Models are built from boxes rather than drawn cell by cell, which keeps them
short enough to read and to adjust. Coordinates are x right, y up, z toward the
viewer, and each model is normalised to its own bounding box at render time, so
there is no need to agree on a common grid.

Kept deliberately coarse. These are shown at 22 to 24 pixels, so a model much
past five or six units on a side turns to mush at the size it is actually used.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from raster import bounding_box, fill_polygon, runs_of_value, svg_rect

SYMBOL_PREFIX = 'px'
OUTPUT = 'symbols-icons.svg'
HALF_CELL = 2

# Painted darkest first so a lighter face is never buried under a darker one.
TONES = ('px-3', 'px-2', 'px-1')
TOP, LEFT, RIGHT = 'px-1', 'px-2', 'px-3'

# Curves need resolution to survive the isometric shear. A radius of two is a
# square with the corners off; a radius of four or five is legibly round, which
# is the whole difference between a lens and a smudge.
ROUNDNESS = 0.4


def box(x0, x1, y0, y1, z0, z1):
    """Every cell of a solid rectangular block, both ends inclusive."""
    return {(x, y, z)
            for x in range(x0, x1 + 1)
            for y in range(y0, y1 + 1)
            for z in range(z0, z1 + 1)}


def ring(cells_xy, z0, z1):
    """A flat outline extruded along z, for the round things."""
    return {(x, y, z) for (x, y) in cells_xy for z in range(z0, z1 + 1)}


def disc_xy(cx, cy, r, z0, z1, inner=0):
    """A disc in the xy plane extruded along z; `inner` hollows it into a ring."""
    return {(x, y, z)
            for x in range(cx - r, cx + r + 1)
            for y in range(cy - r, cy + r + 1)
            for z in range(z0, z1 + 1)
            if inner ** 2 <= (x - cx) ** 2 + (y - cy) ** 2 <= r ** 2 + r * ROUNDNESS}


def cyl_x(cy, cz, r, x0, x1, inner=0):
    """A tube lying along x, for anything rolled."""
    return {(x, y, z)
            for x in range(x0, x1 + 1)
            for y in range(cy - r, cy + r + 1)
            for z in range(cz - r, cz + r + 1)
            if inner ** 2 <= (y - cy) ** 2 + (z - cz) ** 2 <= r ** 2 + r * ROUNDNESS}


CIRCLE = [(1, 4), (2, 4), (3, 4), (0, 3), (4, 3), (0, 2), (4, 2),
          (0, 1), (4, 1), (1, 0), (2, 0), (3, 0)]

MODELS = {
    # a plain solid, the one the collection log already uses
    'cube': box(0, 4, 0, 4, 0, 4),

    # building: a mallet, head across the top of a handle
    'hammer': box(2, 2, 0, 4, 2, 2) | box(0, 4, 5, 6, 1, 3),

    # legacy rescue: a pick, its head swept down at both ends
    'pick': (box(2, 2, 0, 4, 2, 2) | box(0, 4, 5, 5, 2, 2)
             | box(0, 0, 4, 4, 2, 2) | box(4, 4, 4, 4, 2, 2)),

    # security review: a shield. Ten units tall so the shoulders can curve and
    # the taper can happen over several steps instead of one.
    'shield': ({(x, y, z)
                for x in range(0, 9) for y in range(0, 11) for z in range(0, 3)
                if (y >= 8 and 1 <= x <= 7)                    # shoulders, cut corners
                or (5 <= y < 8)                                 # full width body
                or (2 <= y < 5 and 1 <= x <= 7)                 # first taper
                or (y < 2 and 3 - y <= x <= 5 + y)}),           # point

    # incident response: a flame, narrowing and leaning as it rises
    'flame': (box(1, 3, 0, 1, 1, 3) | box(1, 2, 2, 2, 1, 2)
              | box(2, 2, 3, 3, 2, 2) | box(2, 2, 4, 4, 1, 1)),

    # regulatory reporting: a scroll, an actual rolled tube with the sheet
    # hanging out of it rather than two cubes on a plank
    'scroll': (cyl_x(4, 4, 3, 0, 9) | box(0, 9, 3, 4, 5, 9)),

    # performance: a flask with a narrow neck
    'potion': (box(1, 3, 0, 2, 1, 3) | box(2, 2, 3, 4, 2, 2) | box(1, 3, 5, 5, 2, 2)),

    # pipelines: an ingot, wider at the base than the top
    'ingot': box(0, 5, 0, 0, 1, 3) | box(1, 4, 1, 1, 1, 3),

    # code review: a lens. A ring of radius five, thick enough to hold together,
    # with a handle off the lower corner. At radius two this was noise.
    'lens': (disc_xy(6, 7, 5, 1, 2, inner=3)
             | {(x, y, z) for (x, y) in ((2, 3), (1, 2), (1, 1), (0, 1), (0, 0))
                for z in (1, 2)}),

    # AI and agents: a standing stone with a slot cut into its face
    'rune': box(1, 3, 0, 5, 1, 3) - box(2, 2, 2, 3, 3, 3),

    # agentic systems: a graph that branches. One trunk, a crossbar, a node on
    # each arm. Same grammar as the hammer, which is why it survives at 24 px:
    # a stem and a bar read as a silhouette where nodes and edges read as mush.
    'graph': (box(3, 4, 0, 5, 3, 5)
              | box(0, 7, 6, 7, 3, 5)
              | box(0, 1, 8, 10, 3, 5)
              | box(6, 7, 8, 10, 3, 5)),

    # integrations: two links, one passing through the other. Each ring needs a
    # hole big enough to read as a hole.
    'chain': (disc_xy(4, 7, 4, 2, 3, inner=2)          # upright link
              | {(x, y, z)                              # link lying through it
                 for x in range(1, 8) for y in range(0, 7) for z in range(0, 6)
                 if 2 ** 2 <= (x - 4) ** 2 + (z - 3) ** 2 <= 4 ** 2 + 1.6 and 2 <= y <= 3}),

    # stacked plates, offset so the stack reads as a stack
    'slabs': box(0, 4, 0, 0, 0, 4) | box(0, 3, 2, 2, 1, 4) | box(1, 4, 4, 4, 0, 3),

    # a small crawling thing, with a head and six legs rather than four stubs
    'bug': (disc_xy(4, 3, 3, 1, 4, inner=0)                     # shell
            | box(3, 5, 2, 4, 5, 6)                             # head
            | {(x, 0, z) for x in (0, 1, 7, 8) for z in (1, 3, 5)}   # legs
            | {(3, 5, 7), (5, 5, 7)}),                          # antennae
}


def grid_size(cells):
    """The extent a model occupies, in voxels along each axis."""
    return (max(x for (x, _, _) in cells) + 1,
            max(y for (_, y, _) in cells) + 1,
            max(z for (_, _, z) in cells) + 1)


def faces_of(sx, sy, w, h, v):
    """The three visible faces of one cube, as polygons in screen space.

    @param sx: screen x of the cube's top corner.
    @param sy: screen y of the same.
    @returns: (polygon, tone) pairs.
    """
    return (
        ([(sx, sy - h), (sx + w, sy), (sx, sy + h), (sx - w, sy)], TOP),
        ([(sx - w, sy), (sx, sy + h), (sx, sy + h + v), (sx - w, sy + v)], LEFT),
        ([(sx + w, sy), (sx, sy + h), (sx, sy + h + v), (sx + w, sy + v)], RIGHT),
    )


def painters_order(cells):
    """Cells sorted so a nearer cube is always painted over a farther one."""
    return sorted(cells, key=lambda c: c[0] + c[1] + c[2])


def draw(cells):
    """Paints a model back to front into a grid of tone names."""
    w = HALF_CELL
    h, v = max(1, HALF_CELL // 2), HALF_CELL
    nx, ny, nz = grid_size(cells)

    span = (nx + nz) * w + w * 2
    tall = (nx + nz) * h + ny * v + v * 2
    grid = [[None] * span for _ in range(tall)]
    ox, oy = nz * w + w, v

    for (i, j, k) in painters_order(cells):
        sx = ox + (i - k) * w
        sy = oy + (i + k) * h - j * v + ny * v
        for (polygon, tone) in faces_of(sx, sy, w, h, v):
            fill_polygon(grid, polygon, tone)

    return grid


def rects_for_tone(grid, tone, box):
    """One SVG rect per run of `tone`, positioned relative to the model's box."""
    x0, x1, y0, y1 = box
    return [svg_rect(x, y - y0, length, f'var(--{tone})')
            for y in range(y0, y1 + 1)
            for (x, length) in runs_of_value(grid[y][x0:x1 + 1], tone)]


def to_symbol(name, cells):
    """One model as an SVG <symbol>, trimmed to its own bounding box.

    @returns: (symbol, width, height)
    """
    grid = draw(cells)
    box = bounding_box(grid)
    x0, x1, y0, y1 = box
    width, height = x1 - x0 + 1, y1 - y0 + 1

    rects = [rect for tone in TONES for rect in rects_for_tone(grid, tone, box)]
    symbol = (f'<symbol id="{SYMBOL_PREFIX}-{name}" viewBox="0 0 {width} {height}">'
              f'{"".join(rects)}</symbol>')
    return symbol, width, height


def lift_onto_grid(cells):
    """Shifts a model up if it was drawn below zero, as the lens handle is."""
    lowest = min(y for (_, y, _) in cells)
    if lowest >= 0:
        return cells
    return {(x, y - lowest, z) for (x, y, z) in cells}


def build_sheet(models):
    """Every model as one sheet of symbols, reporting each as it is drawn."""
    symbols = []
    for (name, cells) in models.items():
        cells = lift_onto_grid(cells)
        symbol, width, height = to_symbol(name, cells)
        symbols.append(symbol)
        print(f'{SYMBOL_PREFIX}-{name:8} {len(cells):3} voxels  '
              f'{width:2}x{height:2}  {len(symbol) / 1024:4.1f} KB')
    return symbols


def main():
    symbols = build_sheet(MODELS)
    pathlib.Path(OUTPUT).write_text('\n'.join(symbols))
    print(f'\nwrote {OUTPUT}, {len(symbols)} icons')


if __name__ == '__main__':
    main()
