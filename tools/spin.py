"""Rotating animations of the fractals in tools/fractals.py.

    python3 tools/spin.py [outdir]      # default: preview/anim

A small 3D renderer rather than a spun sprite: each voxel's corners are rotated
about the model's vertical axis, projected isometrically, and its visible faces
filled back to front. Faces are shaded from their own rotated normal against a
fixed light, so the light stays put while the solid turns. That is what makes
it read as an object instead of a rotating picture.

Two economies matter here. Faces shared with a neighbouring voxel are never
drawn, which on the dense shapes removes most of the work. And each shape is
tested for rotational symmetry about the vertical axis first: a shape invariant
under a quarter turn only needs a quarter turn rendered, and it still loops
seamlessly, so the file is a quarter of the size for free.

Every shape is written twice, at full scale and at a coarse one, so the same
sculpture is available as a fine drawing or a chunky pixelated one.
"""
import math
import pathlib
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from animation import canvas_for, flat_palette, save_loop
from fractals import SETS, voxels

KEY = (255, 0, 255)                                       # made transparent on save
RAMP = [(125, 255, 184), (63, 207, 133), (31, 143, 90)]   # --px-1, --px-2, --px-3
LIGHT = (-0.45, 0.82, -0.35)
VIEW = (1 / math.sqrt(3),) * 3
COS30, SIN30 = math.cos(math.radians(30)), 0.5
DEG_PER_FRAME = 0.75
MAX_FRAMES = 240
MIN_FRAMES = 40
SCALES = (('', 9.0), ('-lo', 4.0))

# Where each tone starts, as a fraction of full brightness.
LIT_THRESHOLD, MID_THRESHOLD = 0.72, 0.33

# Each face as its outward normal and the four corners of the unit cube it spans.
FACES = [
    ((0, 1, 0),  [(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)]),
    ((0, -1, 0), [(0, 0, 0), (0, 0, 1), (1, 0, 1), (1, 0, 0)]),
    ((1, 0, 0),  [(1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0)]),
    ((-1, 0, 0), [(0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1)]),
    ((0, 0, 1),  [(0, 0, 1), (0, 1, 1), (1, 1, 1), (1, 0, 1)]),
    ((0, 0, -1), [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]),
]


def span_degrees(cells, n):
    """The smallest turn that maps the shape onto itself, so the loop is short."""
    quarter = {(k, j, n - 1 - i) for (i, j, k) in cells}
    if quarter == cells:
        return 90
    half = {(n - 1 - i, j, n - 1 - k) for (i, j, k) in cells}
    return 180 if half == cells else 360


def exposed(cells):
    """Only faces without a neighbour behind them can ever be seen.

    @returns: (cell, visible faces) pairs, skipping fully buried cells.
    """
    out = []
    for (i, j, k) in cells:
        visible = [face for face in FACES
                   if (i + face[0][0], j + face[0][1], k + face[0][2]) not in cells]
        if visible:
            out.append(((i, j, k), visible))
    return out


def tone_index(normal):
    """Which of the three ramp tones a face takes, from its angle to the light."""
    lit = max(0.0, sum(a * b for (a, b) in zip(normal, LIGHT)))
    if lit > LIT_THRESHOLD:
        return 1
    return 2 if lit > MID_THRESHOLD else 3


def turned(x, z, centre, cos_t, sin_t):
    """A point turned about the model's vertical axis."""
    dx, dz = x - centre, z - centre
    return (centre + dx * cos_t - dz * sin_t,
            centre + dx * sin_t + dz * cos_t)


def project(x, y, z, scale):
    """World space to the isometric screen the whole site is drawn on."""
    return ((x - z) * COS30 * scale, ((x + z) * SIN30 - y) * scale)


def faces_toward_camera(normal, cos_t, sin_t):
    """The rotated normal, and whether it still points at the camera.

    @returns: (rotated normal, visible).
    """
    rotated = (normal[0] * cos_t - normal[2] * sin_t,
               normal[1],
               normal[0] * sin_t + normal[2] * cos_t)
    facing = sum(a * b for (a, b) in zip(rotated, VIEW)) > 0.001
    return rotated, facing


def geometry(surface, centre, t, scale):
    """Every face to draw for one frame, farthest first.

    @param surface: (cell, faces) pairs from exposed().
    @param t: rotation in radians.
    @returns: (depth, screen corners, tone index) triples.
    """
    cos_t, sin_t = math.cos(t), math.sin(t)
    quads = []

    for ((i, j, k), faces) in surface:
        cx, cz = turned(i + .5, k + .5, centre, cos_t, sin_t)
        depth = cx + j + cz
        for (normal, corners) in faces:
            rotated, facing = faces_toward_camera(normal, cos_t, sin_t)
            if not facing:
                continue
            points = []
            for (ox, oy, oz) in corners:
                wx, wz = turned(i + ox, k + oz, centre, cos_t, sin_t)
                points.append(project(wx, j + oy, wz, scale))
            quads.append((depth, points, tone_index(rotated)))

    quads.sort(key=lambda quad: quad[0])
    return quads


def frame_count(span):
    """How many frames one loop needs, at the pacing above."""
    return min(MAX_FRAMES, max(MIN_FRAMES, round(span / DEG_PER_FRAME)))


def frame_angles(span, count):
    """The rotation of each frame, in radians, over one loop."""
    return [math.radians(span) * f / count for f in range(count)]


def every_point(surface, centre, angles, scale):
    """Every screen point the model reaches over a whole loop."""
    return [point
            for t in angles
            for (_, points, _) in geometry(surface, centre, t, scale)
            for point in points]


def draw_frame(surface, centre, t, scale, canvas, palette):
    """One frame of the turn, as an indexed-colour image."""
    width, height, offset_x, offset_y = canvas
    image = Image.new('P', (width, height), 0)
    image.putpalette(palette)
    pen = ImageDraw.Draw(image)

    for (_, points, tone) in geometry(surface, centre, t, scale):
        pen.polygon([(round(x + offset_x), round(y + offset_y))
                     for (x, y) in points], fill=tone)
    return image


def animate(name, spec, scale, outdir):
    """Renders and writes one shape's loop at one scale."""
    cells, n = voxels(spec)
    surface = exposed(cells)
    span = span_degrees(cells, n)
    angles = frame_angles(span, frame_count(span))
    centre = n / 2.0

    canvas = canvas_for(every_point(surface, centre, angles, scale))
    palette = flat_palette([KEY, *RAMP])
    frames = [draw_frame(surface, centre, t, scale, canvas, palette)
              for t in angles]

    sizes = save_loop(outdir / name, frames, still=True)
    width, height, _, _ = canvas
    print(f'{name:22} {len(cells):6} vox  span {span:3}deg  {len(angles):3} frames  '
          f'{width}x{height}  webp {sizes["webp"]:4} KB  gif {sizes["gif"]:4} KB',
          flush=True)


def main(argv):
    outdir = pathlib.Path(argv[1] if len(argv) > 1 else 'preview/anim')
    outdir.mkdir(parents=True, exist_ok=True)
    for (name, spec, _) in SETS:
        for (suffix, scale) in SCALES:
            animate(name + suffix, spec, scale, outdir)


if __name__ == '__main__':
    main(sys.argv)
