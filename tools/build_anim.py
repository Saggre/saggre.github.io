"""The Mosely snowflake turning while it is carved, iteration by iteration.

    python3 tools/build_anim.py [outdir]      # default: preview

Every iteration of the fractal lives in the same 27-cube grid, so the shape
refines in place instead of changing size: level l asks the rule about the
cell's coarser address, i // 3**(TOP - l). The levels nest, S0 > S1 > S2 > S3,
so going from one to the next only ever removes cells and the carve can be
shown happening rather than cut to.

The sequence holds each level, then dissolves the cells that iteration kills,
corners first, since the corners are precisely what a Mosely iteration takes.
After the last one it fills back in to the solid cube, which both closes the
loop seamlessly and gives the eye the construction in reverse.

Rotation is continuous throughout and covers 270 degrees, a multiple of the
shape's 90-degree symmetry, so the orientation matches across the loop too.
"""
import math
import pathlib
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from animation import canvas_for, flat_palette, save_loop
from spin import KEY, RAMP, exposed, geometry

TOP = 3                     # deepest iteration shown
GRID = 3 ** TOP             # every level is drawn in this grid
SCALE = 4.6
HOLD, CARVE, REBUILD = 25, 40, 60
TOTAL_TURN = 270.0
PROGRESS_EVERY = 40


def mosely_at(i, j, k, level):
    """Membership in iteration `level`, asked at this grid's resolution."""
    if level == 0:
        return True
    step = 3 ** (TOP - level)
    a, b, c = i // step, j // step, k // step
    for _ in range(level):
        if 1 not in (a % 3, b % 3, c % 3):
            return False
        a, b, c = a // 3, b // 3, c // 3
    return True


def level_cells(level):
    """Every cell alive at one iteration."""
    return {(i, j, k)
            for i in range(GRID) for j in range(GRID) for k in range(GRID)
            if mosely_at(i, j, k, level)}


def distance_from_centre(cell):
    """How far out a cell sits, as the largest of its three offsets.

    Corners score highest, which is the order an iteration takes them in.
    """
    centre = (GRID - 1) / 2.0
    return max(abs(cell[0] - centre), abs(cell[1] - centre), abs(cell[2] - centre))


def carve_order(older, newer):
    """The cells one iteration kills, outermost first."""
    return sorted(older - newer, key=distance_from_centre, reverse=True)


def rebuild_order(sparsest, solid):
    """The cells that fill the shape back in, innermost first."""
    return sorted(solid - sparsest, key=distance_from_centre)


def dissolve(cells, doomed, steps):
    """One voxel set per frame, taking `doomed` away a slice at a time."""
    return [cells - set(doomed[:round(len(doomed) * (f + 1) / steps)])
            for f in range(steps)]


def accumulate(cells, arriving, steps):
    """One voxel set per frame, adding `arriving` a slice at a time."""
    return [cells | set(arriving[:round(len(arriving) * (f + 1) / steps)])
            for f in range(steps)]


def timeline(levels):
    """The voxel set for every frame of the loop, in order."""
    frames = []
    for level in range(TOP):
        frames += [levels[level]] * HOLD
        frames += dissolve(levels[level],
                           carve_order(levels[level], levels[level + 1]), CARVE)

    frames += [levels[TOP]] * HOLD
    frames += accumulate(levels[TOP],
                         rebuild_order(levels[TOP], levels[0]), REBUILD)
    return frames


def angle_at(frame, count):
    """The rotation of one frame, in radians."""
    return math.radians(TOTAL_TURN) * frame / count


def draw_frame(cells, t, canvas, palette):
    """One frame of the carve, as an indexed-colour image."""
    width, height, offset_x, offset_y = canvas
    image = Image.new('P', (width, height), 0)
    image.putpalette(palette)
    pen = ImageDraw.Draw(image)

    for (_, points, tone) in geometry(exposed(cells), GRID / 2.0, t, SCALE):
        pen.polygon([(round(x + offset_x), round(y + offset_y))
                     for (x, y) in points], fill=tone)
    return image


def render(sequence):
    """Every frame of the loop, on a canvas sized to hold all of them."""
    count = len(sequence)
    solid = exposed(sequence[0])
    canvas = canvas_for([point
                         for f in range(count)
                         for (_, points, _) in geometry(solid, GRID / 2.0,
                                                        angle_at(f, count), SCALE)
                         for point in points])
    print(f'canvas {canvas[0]}x{canvas[1]}')

    palette = flat_palette([KEY, *RAMP])
    frames = []
    for (f, cells) in enumerate(sequence):
        frames.append(draw_frame(cells, angle_at(f, count), canvas, palette))
        if f % PROGRESS_EVERY == 0:
            print(f'  frame {f}/{count}', flush=True)
    return frames


def main(argv):
    levels = [level_cells(level) for level in range(TOP + 1)]
    for level in range(TOP):
        assert levels[level + 1] <= levels[level], \
            'levels must nest for the carve to work'
    print('voxels per level:', [len(cells) for cells in levels])

    sequence = timeline(levels)
    print(f'{len(sequence)} frames, {TOTAL_TURN / len(sequence):.3f} deg per frame')

    outdir = pathlib.Path(argv[1] if len(argv) > 1 else 'preview')
    outdir.mkdir(parents=True, exist_ok=True)
    base = outdir / 'mosely-build'

    sizes = save_loop(base, render(sequence))
    print(f'wrote {base}.webp {sizes["webp"]} KB, {base}.gif {sizes["gif"]} KB')


if __name__ == '__main__':
    main(sys.argv)
