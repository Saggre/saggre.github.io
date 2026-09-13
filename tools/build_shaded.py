"""Shaded build-up animations: the px-cube treatment, plus ambient occlusion.

    python3 tools/build_shaded.py [outdir] [shape ...]      # default: preview/anim

Three differences from build_all.py, which is kept as it is.

Shading is continuous, which for a turning object it has to be. Sorting faces
into "top, left, right" the way px-cube does is right for a sprite and wrong
here: a side face crosses the left/right boundary exactly when it is most
face-on to the camera, so the largest face on screen would snap between two
tones in a single frame. Instead the rotated normal is shaded against a fixed
light and the result quantised into a long ramp, so a face darkens gradually as
it turns away. The ramp still runs through --px-3, --px-2 and --px-1, so the
palette is the sheet's palette; there are simply steps in between.

Ambient occlusion rides the same scale. Occlusion is the raw count of solid
neighbours around a face, nought to eight, applied as a smooth multiplier
rather than bucketed, so a carve does not make faces jump a whole tone at once.

Draw order is fully determined: faces sort by depth and then by coordinate, so
two faces at equal depth keep the same order from frame to frame. Ties broken
by set iteration order were a third source of shimmer, since the voxel set is
rebuilt on every frame of a carve.

One more iteration is shown wherever the grid it needs stays affordable, and
the whole sequence runs 50 percent longer by holding more frames rather than
by slowing the frame rate, so the motion stays as smooth as before.
"""
import math
import pathlib
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import build_all
from animation import canvas_for, flat_palette, save_loop
from build_all import angle_at, levels_for, render_all, turn_for
from spin import FACES, KEY, RAMP, geometry

SLOWER = 1.5
HOLD, TRANS, REBUILD = int(18 * SLOWER), int(30 * SLOWER), int(40 * SLOWER)
SCALE = 3.6
MAX_GRID = 40          # beyond this a level costs more than it shows

# Quantisation is what a turning face flickers on: hold a tone, then flip the
# whole face at once when the brightness crosses a step. Coplanar voxel faces
# share a normal, so a large flat region crosses on the same frame and pops in
# unison. Many small steps make each flip nearly invisible.
STEPS = 48
AMBIENT = 0.30         # floor brightness, so nothing goes fully black
AO_MAX = 0.40          # how much a fully boxed-in face darkens
NEIGHBOURS = 8         # cells around the one in front of a face

# A slight fade with distance. Two jobs: it gives the solid some depth, and it
# desynchronises the step crossings, so faces at different depths cross on
# different frames instead of a whole plane turning over together.
DEPTH_FADE = 0.16

# The camera sits at +x +y +z, so the light must too, or both visible side
# faces take max(0, n.L) = 0 and collapse to one tone. Dominant y keeps the top
# brightest; unequal x and z keep the two sides apart, the way px-cube has them.
LIGHT = (0.42, 0.86, 0.28)

DARKEST_FACTOR = 0.42  # how far below --px-3 the ramp starts
COS30, SIN30 = math.cos(math.radians(30)), 0.5


def mix(a, b, u):
    """A colour `u` of the way from a to b."""
    return tuple(round(a[i] + (b[i] - a[i]) * u) for i in range(3))


def build_ramp(steps):
    """A long ramp through the sheet's three tones, darkest first."""
    darkest = tuple(round(channel * DARKEST_FACTOR) for channel in RAMP[2])
    stops = [darkest, RAMP[2], RAMP[1], RAMP[0]]

    ramp = []
    for i in range(steps):
        position = i / (steps - 1) * (len(stops) - 1)
        low = min(int(position), len(stops) - 2)
        ramp.append(mix(stops[low], stops[low + 1], position - low))
    return ramp


SHADES = build_ramp(STEPS)
PALETTE = flat_palette([KEY, *SHADES])


def ring_around(normal):
    """The eight neighbours of the cell in front of a face.

    How many of those are solid is the occlusion for that face.
    """
    axis = [i for (i, v) in enumerate(normal) if v != 0][0]
    others = [i for i in range(3) if i != axis]

    offsets = []
    for a in (-1, 0, 1):
        for b in (-1, 0, 1):
            if a == 0 and b == 0:
                continue
            offset = [0, 0, 0]
            offset[axis] = normal[axis]
            offset[others[0]], offset[others[1]] = a, b
            offsets.append(tuple(offset))
    return offsets


RINGS = {normal: ring_around(normal) for (normal, _) in FACES}


def occlusion(cell, normal, cells):
    """How boxed in a face is, from 0 for open to 1 for fully surrounded."""
    i, j, k = cell
    solid = sum(1 for (dx, dy, dz) in RINGS[normal]
                if (i + dx, j + dy, k + dz) in cells)
    return solid / float(NEIGHBOURS)


def surface(cells):
    """Visible faces with their occlusion, computed once per level.

    Sorted so the set's iteration order can never reach the drawing.

    @returns: (cell, [(normal, corners, occlusion)]) pairs.
    """
    out = []
    for cell in sorted(cells):
        i, j, k = cell
        visible = [(normal, corners, occlusion(cell, normal, cells))
                   for (normal, corners) in FACES
                   if (i + normal[0], j + normal[1], k + normal[2]) not in cells]
        if visible:
            out.append((cell, visible))
    return out


def without_occlusion(surf):
    """The same surface in the plain shape geometry() expects."""
    return [(cell, [(normal, corners) for (normal, corners, _) in faces])
            for (cell, faces) in surf]


def turned(x, z, centre, cos_t, sin_t):
    """A point turned about the model's vertical axis."""
    dx, dz = x - centre, z - centre
    return (centre + dx * cos_t - dz * sin_t,
            centre + dx * sin_t + dz * cos_t)


def brightness(normal, occluded):
    """How lit a face is, before the depth fade.

    @param normal: the face's rotated normal.
    @param occluded: its occlusion, 0 to 1.
    """
    lit = max(0.0, sum(a * b for (a, b) in zip(normal, LIGHT)))
    return (AMBIENT + (1.0 - AMBIENT) * lit) * (1.0 - AO_MAX * occluded)


def faded(level, depth, grid):
    """Brightness after the depth fade, measured against the grid.

    Fixed against the grid, never against this frame's extents: per-frame
    normalisation slides the whole mapping as the model turns, which is a
    global shimmer rather than the local one it was meant to break up.
    """
    span = 3.0 * grid or 1.0
    near = min(1.0, max(0.0, depth / span))
    return level * (1.0 - DEPTH_FADE * (1.0 - near))


def shade_index(level):
    """Which palette entry a brightness lands on."""
    return 1 + max(0, min(STEPS - 1, round(level * (STEPS - 1))))


def quads_for(surf, centre, t, scale):
    """Every face to draw for one frame, in a fully determined order.

    Depth first, then coordinate, so equal-depth faces never swap order.

    @returns: (depth, screen corners, brightness) triples.
    """
    cos_t, sin_t = math.cos(t), math.sin(t)
    quads = []

    for ((i, j, k), faces) in surf:
        cx, cz = turned(i + .5, k + .5, centre, cos_t, sin_t)
        depth = cx + j + cz
        for (normal, corners, occluded) in faces:
            rotated = (normal[0] * cos_t - normal[2] * sin_t,
                       normal[1],
                       normal[0] * sin_t + normal[2] * cos_t)
            if sum(rotated) <= 0.001:            # facing away from the camera
                continue
            points = []
            for (ox, oy, oz) in corners:
                wx, wz = turned(i + ox, k + oz, centre, cos_t, sin_t)
                points.append(((wx - wz) * COS30 * scale,
                               ((wx + wz) * SIN30 - (j + oy)) * scale))
            quads.append((depth, i, j, k, points, brightness(rotated, occluded)))

    quads.sort(key=lambda quad: (quad[0], quad[1], quad[2], quad[3]))
    return [(depth, points, level) for (depth, _, _, _, points, level) in quads]


def draw_frame(surf, centre, t, scale, canvas, grid):
    """One frame of the turn, as an indexed-colour image."""
    width, height, offset_x, offset_y = canvas
    image = Image.new('P', (width, height), 0)
    image.putpalette(PALETTE)
    pen = ImageDraw.Draw(image)

    for (depth, points, level) in quads_for(surf, centre, t, scale):
        pen.polygon([(round(x + offset_x), round(y + offset_y))
                     for (x, y) in points],
                    fill=shade_index(faded(level, depth, grid)))
    return image


def deepen(spec):
    """One more iteration, when the grid it needs is still affordable."""
    if spec[0] == 'rule':
        _, rule, base, lv = spec
        return ('rule', rule, base, lv + 1) if base ** (lv + 1) <= MAX_GRID else spec
    _, build, n, lv = spec
    return ('ifs', build, n, lv + 1)


def cached_surfaces(sequence, keep=8):
    """The surface of each frame's voxel set, reusing it across the long holds.

    A carve rebuilds the set every frame, but a hold repeats one set for
    dozens, so a small cache removes most of the work.
    """
    cache = {}
    for cells in sequence:
        key = frozenset(cells)
        if key not in cache:
            cache[key] = surface(cells)
            if len(cache) > keep:
                cache.pop(next(iter(cache)))
        yield cache[key]


def render(name, spec, outdir):
    """Renders and writes one shape's shaded carve."""
    deeper = deepen(spec)
    levels, n = levels_for(deeper)
    turn = turn_for(levels, n)

    # Built here rather than in build_all so the slower pacing above applies
    # without changing that module.
    sequence = build_all.timeline(levels, HOLD, TRANS, REBUILD)
    count = len(sequence)
    centre = n / 2.0

    probe = without_occlusion(surface(levels[0]))
    canvas = canvas_for([point
                         for f in range(count)
                         for (_, points, _) in geometry(probe, centre,
                                                        angle_at(f, count, turn), SCALE)
                         for point in points])

    frames = [draw_frame(surf, centre, angle_at(f, count, turn), SCALE, canvas, n)
              for (f, surf) in enumerate(cached_surfaces(sequence))]

    base = outdir / (name + '-shaded')
    sizes = save_loop(base, frames)
    width, height, _, _ = canvas
    print(f'{name + "-shaded":22} grid {n:3} {len(levels)} levels '
          f'{str([len(cells) for cells in levels]):38} '
          f'{"deepened" if deeper != spec else "as before"}  {count:3} frames  '
          f'{width}x{height}  webp {sizes["webp"]:4} KB  gif {sizes["gif"]:4} KB',
          flush=True)


def main(argv):
    outdir = pathlib.Path(argv[1] if len(argv) > 1 else 'preview/anim')
    outdir.mkdir(parents=True, exist_ok=True)
    render_all(outdir, set(argv[2:]), render, '-shaded')


if __name__ == '__main__':
    main(sys.argv)
