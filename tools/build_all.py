"""Every fractal, carved one iteration at a time while it turns.

    python3 tools/build_all.py [outdir] [shape ...]      # default: preview/anim

The same idea as build_anim.py, generalised over the whole recipe table in
tools/fractals.py.

For a digit rule, iteration l is the rule asked about a cell's coarser address,
i // base**(TOP - l), so every level lives in the finest grid and the shape
refines in place instead of changing size. Level 0 is therefore the solid cube
the fractal is carved out of. For a forward IFS, iteration l is simply the
construction stopped after l rounds.

Nesting is checked, never assumed: a transition animates removals and additions
separately, so a recipe whose levels do not nest still renders correctly rather
than silently dropping cells. The last transition fills back to level 0, which
closes the loop and shows the construction in reverse.

Rotation covers a whole number of the shape's symmetry spans, so orientation
matches across the loop as well.
"""
import math
import pathlib
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from animation import canvas_for, flat_palette, save_loop
from fractals import SETS
from spin import KEY, RAMP, exposed, geometry, span_degrees

HOLD, TRANS, REBUILD = 18, 30, 40
SCALE = 3.6
IFS_GRID = 36           # the IFS shapes are dense; 48 costs a lot for little

# A quarter-symmetric shape need only turn three quarters for the loop to close.
TURN_IF_QUARTER, TURN_OTHERWISE = 270.0, 360.0


def digit_levels(rule, base, lv):
    """Each iteration of a digit rule, all drawn in the finest grid.

    @returns: (levels from solid to sparsest, grid size).
    """
    n = base ** lv
    levels = [{(i, j, k) for i in range(n) for j in range(n) for k in range(n)}]
    for level in range(1, lv + 1):
        step = base ** (lv - level)
        levels.append({(i, j, k)
                       for i in range(n) for j in range(n) for k in range(n)
                       if rule(i // step, j // step, k // step, level)})
    return levels, n


def ifs_levels(build, lv):
    """Each iteration of a forward IFS, stopped after l rounds.

    @returns: (levels, grid size).
    """
    return [build(IFS_GRID, level) for level in range(lv + 1)], IFS_GRID


def levels_for(spec):
    """Each iteration of one recipe, whichever family it belongs to."""
    if spec[0] == 'rule':
        _, rule, base, lv = spec
        return digit_levels(rule, base, lv)
    _, build, _, lv = spec
    return ifs_levels(build, lv)


def outward_first(cell):
    """How far out a cell sits, as the largest of its three coordinates."""
    return max(abs(cell[0]), abs(cell[1]), abs(cell[2]))


def morph(older, newer, steps):
    """One voxel set per frame, turning one level into the next.

    Removals and additions are tracked separately, so a pair of levels that do
    not nest still animates correctly. Cells leave outermost first and arrive
    innermost first, which reads as carving rather than dissolving.
    """
    leaving = sorted(older - newer, key=outward_first, reverse=True)
    arriving = sorted(newer - older, key=outward_first)

    frames = []
    for f in range(steps):
        progress = (f + 1) / steps
        cells = set(older)
        cells -= set(leaving[:round(len(leaving) * progress)])
        cells |= set(arriving[:round(len(arriving) * progress)])
        frames.append(cells)
    return frames


def timeline(levels, hold=HOLD, trans=TRANS, rebuild=REBUILD):
    """The voxel set for every frame: hold, morph, hold, ... then back to level 0."""
    frames = []
    for level in range(len(levels) - 1):
        frames += [levels[level]] * hold
        frames += morph(levels[level], levels[level + 1], trans)

    frames += [levels[-1]] * hold
    frames += morph(levels[-1], levels[0], rebuild)
    return frames


def turn_for(levels, n):
    """How far the model turns, from the coarsest symmetry any level has."""
    span = max(span_degrees(cells, n) for cells in levels)
    return TURN_IF_QUARTER if span == 90 else TURN_OTHERWISE


def angle_at(frame, count, turn):
    """The rotation of one frame, in radians."""
    return math.radians(turn) * frame / count


def canvas_holding(levels, n, count, turn, scale=SCALE):
    """A canvas the solid never outgrows, probed over a whole turn."""
    solid = exposed(levels[0])
    return canvas_for([point
                       for f in range(count)
                       for (_, points, _) in geometry(solid, n / 2.0,
                                                      angle_at(f, count, turn), scale)
                       for point in points])


def draw_frame(cells, centre, t, canvas, palette, scale=SCALE):
    """One frame of the carve, as an indexed-colour image."""
    width, height, offset_x, offset_y = canvas
    image = Image.new('P', (width, height), 0)
    image.putpalette(palette)
    pen = ImageDraw.Draw(image)

    for (_, points, tone) in geometry(exposed(cells), centre, t, scale):
        pen.polygon([(round(x + offset_x), round(y + offset_y))
                     for (x, y) in points], fill=tone)
    return image


def nests(levels):
    """Whether every level is contained in the one before it."""
    return all(levels[i + 1] <= levels[i] for i in range(len(levels) - 1))


def render(name, spec, outdir):
    """Renders and writes one shape's carve."""
    levels, n = levels_for(spec)
    turn = turn_for(levels, n)
    sequence = timeline(levels)
    count = len(sequence)

    canvas = canvas_holding(levels, n, count, turn)
    palette = flat_palette([KEY, *RAMP])
    frames = [draw_frame(cells, n / 2.0, angle_at(f, count, turn), canvas, palette)
              for (f, cells) in enumerate(sequence)]

    base = outdir / (name + '-build')
    sizes = save_loop(base, frames)
    width, height, _, _ = canvas
    print(f'{name + "-build":22} {len(levels)} levels '
          f'{[len(cells) for cells in levels]}  nested {str(nests(levels)):5} '
          f'turn {turn:.0f}deg  {count:3} frames  {width}x{height}  '
          f'webp {sizes["webp"]:4} KB  gif {sizes["gif"]:4} KB', flush=True)


def render_all(outdir, only, render_one, label):
    """Renders each wanted shape, reporting rather than stopping on a failure."""
    for (name, spec, _) in SETS:
        if only and name not in only:
            continue
        try:
            render_one(name, spec, outdir)
        except Exception as error:
            print(f'{name + label:22} FAILED: {type(error).__name__}: {error}',
                  flush=True)


def main(argv):
    outdir = pathlib.Path(argv[1] if len(argv) > 1 else 'preview/anim')
    outdir.mkdir(parents=True, exist_ok=True)
    render_all(outdir, set(argv[2:]), render, '-build')


if __name__ == '__main__':
    main(sys.argv)
