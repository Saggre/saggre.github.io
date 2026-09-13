"""Pieces shared by the voxel animation renderers.

Every renderer paints indexed-colour frames over a transparent key and saves the
same pair of files, so the canvas arithmetic, the palette layout and the encoder
settings belong here rather than in four copies.
"""
import pathlib

KEY_INDEX = 0
PALETTE_COLOURS = 256
GIF_FRAME_MS = 20
WEBP_FRAME_MS = 17
CANVAS_PAD = 4


def flat_palette(colours):
    """Colours as the flat RGB triples Pillow wants, padded to a full palette.

    The first colour is the key that later becomes transparent.

    @param colours: RGB tuples, key first.
    @returns: a list of PALETTE_COLOURS * 3 channel values.
    """
    channels = [channel for colour in colours for channel in colour]
    return channels + [0] * (PALETTE_COLOURS * 3 - len(channels))


def canvas_for(points, pad=CANVAS_PAD):
    """The canvas that holds every frame of a turn without the model drifting.

    Sized from every point of every frame at once. Sizing per frame would let
    the canvas breathe as the model turns.

    @param points: (x, y) pairs from every frame.
    @returns: (width, height, offset_x, offset_y).
    """
    xs = [x for (x, _) in points]
    ys = [y for (_, y) in points]
    width = int(max(xs) - min(xs)) + pad * 2
    height = int(max(ys) - min(ys)) + pad * 2
    return width, height, -min(xs) + pad, -min(ys) + pad


def to_rgba(frame):
    """A copy of an indexed frame with the key colour made fully transparent."""
    out = frame.convert('RGBA')
    target, source = out.load(), frame.load()
    width, height = frame.size
    for y in range(height):
        for x in range(width):
            if source[x, y] == KEY_INDEX:
                target[x, y] = (0, 0, 0, 0)
    return out


def kilobytes(path):
    """Size of a written file, rounded down."""
    return pathlib.Path(path).stat().st_size // 1024


def save_loop(base, frames, still=False):
    """Writes one animation as a GIF and a lossless WebP.

    The GIF keys out its transparency by palette index; the WebP needs real
    alpha, so the frames are converted first.

    @param base: path without an extension.
    @param frames: indexed-colour frames, at least one.
    @param still: also write the first frame as a PNG.
    @returns: {'gif': kb, 'webp': kb}
    """
    frames[0].save(f'{base}.gif', save_all=True, append_images=frames[1:],
                   duration=GIF_FRAME_MS, loop=0, optimize=True, disposal=2,
                   transparency=KEY_INDEX)

    alpha = [to_rgba(frame) for frame in frames]
    alpha[0].save(f'{base}.webp', save_all=True, append_images=alpha[1:],
                  duration=WEBP_FRAME_MS, loop=0, lossless=True, quality=100,
                  method=4)
    if still:
        alpha[0].save(f'{base}.png', optimize=True)

    return {extension: kilobytes(f'{base}.{extension}')
            for extension in ('gif', 'webp')}
