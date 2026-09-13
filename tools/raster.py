"""Turning polygons into pixel grids, and pixel grids into SVG rects.

The voxel generators all paint isometric faces into a grid of tone names and
then emit one rect per horizontal run. Runs rather than single cells because a
row of twelve identical pixels is one rect instead of twelve, which is most of
the file size.

A grid is a list of rows, each a list of cell values, with None for nothing.
"""


def fill_polygon(grid, polygon, value):
    """Paints a convex polygon into a grid by scanline, in place.

    A face is filled where a scanline crosses its edges an odd number of times,
    which needs no winding rules for the quads these generators draw.

    @param grid: rows of cells, modified in place.
    @param polygon: (x, y) corners in order.
    @param value: what to write into each covered cell.
    """
    height, width = len(grid), len(grid[0])
    ys = [y for (_, y) in polygon]

    for y in range(max(0, min(ys)), min(height, max(ys) + 1)):
        crossings = sorted(_crossings_at(polygon, y))
        for i in range(0, len(crossings) - 1, 2):
            left, right = crossings[i], crossings[i + 1]
            for x in range(max(0, int(left)), min(width, int(right) + 1)):
                grid[y][x] = value


def _crossings_at(polygon, y):
    """Where one scanline cuts the edges of a polygon.

    An edge counts when the scanline is within its half-open vertical span, so
    a corner shared by two edges is counted once rather than twice.

    @returns: x positions, unsorted.
    """
    found = []
    for i in range(len(polygon)):
        (x1, y1), (x2, y2) = polygon[i], polygon[(i + 1) % len(polygon)]
        if (y1 <= y < y2) or (y2 <= y < y1):
            found.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    return found


def bounding_box(grid):
    """The smallest box holding every painted cell.

    @returns: (x0, x1, y0, y1), inclusive.
    """
    painted = [(x, y)
               for (y, row) in enumerate(grid)
               for (x, cell) in enumerate(row)
               if cell is not None]
    xs = [x for (x, _) in painted]
    ys = [y for (_, y) in painted]
    return min(xs), max(xs), min(ys), max(ys)


def runs_of_value(row, value):
    """The horizontal runs of one value in a row.

    @returns: (start, length) pairs, left to right.
    """
    found, x = [], 0
    while x < len(row):
        if row[x] != value:
            x += 1
            continue
        length = 1
        while x + length < len(row) and row[x + length] == value:
            length += 1
        found.append((x, length))
        x += length
    return found


def runs_of_equal(row):
    """The horizontal runs of every value in a row, skipping unpainted cells.

    @returns: (start, length, value) triples, left to right.
    """
    found, x = [], 0
    while x < len(row):
        value = row[x]
        if value is None:
            x += 1
            continue
        length = 1
        while x + length < len(row) and row[x + length] == value:
            length += 1
        found.append((x, length, value))
        x += length
    return found


def svg_rect(x, y, length, fill):
    """One pixel-high rect, the only shape any of these sheets uses."""
    return f'<rect x="{x}" y="{y}" width="{length}" height="1" fill="{fill}"/>'
