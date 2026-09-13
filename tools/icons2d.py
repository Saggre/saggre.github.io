"""The site's icon set drawn flat, in the palette's green and violet.

    python3 tools/icons2d.py          # writes symbols-icons2d.svg here

Isometric shears every outline, which is why a ring or a taper needs a lot of
voxels in tools/icons.py before it reads. Flat drawing has the opposite
economics: the silhouette is the whole icon and survives at twelve pixels a
side, but there is no form, so everything has to be said with shape alone.

Each icon is a grid, one character per pixel:

    #  --px-1, the lit body        +  --px-2, shade
    -  --px-3, deep shade          .  nothing
    %  --px-a, the violet          *  --px-a2, violet shade

Twelve by twelve throughout, so the set has one weight and one rhythm.
"""
import pathlib

SYMBOL_PREFIX = 'px2'
OUTPUT = 'symbols-icons2d.svg'

# Painted darkest first so a lighter tone is never buried under a darker one.
TONES = (('-', 'px-3'), ('+', 'px-2'), ('#', 'px-1'), ('*', 'px-a2'), ('%', 'px-a'))
INK = ''.join(character for (character, _) in TONES)

ICONS = {
    # building: a mallet seen side on
    'hammer': [
        '............',
        '.#########..',
        '.#########..',
        '.##+++++##..',
        '.#########..',
        '.....%*.....',
        '.....%*.....',
        '.....%*.....',
        '.....%*.....',
        '.....%*.....',
        '.....%*.....',
        '............'],

    # legacy rescue: a pick, arms swept down
    'pick': [
        '............',
        '.##......##.',
        '..##....##..',
        '...##..##...',
        '...######...',
        '....####....',
        '.....##.....',
        '.....##.....',
        '.....##.....',
        '.....##.....',
        '.....##.....',
        '............'],

    # security review: the shape flat drawing is best at
    'shield': [
        '............',
        '.##########.',
        '.##########.',
        '.###%%%%###.',
        '.###%**%###.',
        '.##########.',
        '..########..',
        '..########..',
        '...######...',
        '....####....',
        '.....##.....',
        '............'],

    # incident response
    'flame': [
        '.....##.....',
        '....####....',
        '....####....',
        '...######...',
        '...##++##...',
        '..##++++##..',
        '..##++++##..',
        '.##++--++##.',
        '.##++--++##.',
        '.##++++++##.',
        '..########..',
        '...####.....'],

    # regulatory reporting: a sheet with a roll at each end
    'scroll': [
        '............',
        '.##########.',
        '.##########.',
        '.#--------#.',
        '.#-######-#.',
        '.#-######-#.',
        '.#-######-#.',
        '.#-######-#.',
        '.#--------#.',
        '.##########.',
        '.##########.',
        '............'],

    # performance: a flask
    'potion': [
        '....####....',
        '....#..#....',
        '....#..#....',
        '....#..#....',
        '...##..##...',
        '..##....##..',
        '..#++++++#..',
        '.##++++++##.',
        '.#++++++++#.',
        '.#++++++++#.',
        '..########..',
        '............'],

    # pipelines: an ingot
    'ingot': [
        '............',
        '............',
        '............',
        '...######...',
        '..########..',
        '.##++++++##.',
        '.##++++++##.',
        '.##########.',
        '............',
        '............',
        '............',
        '............'],

    # code review: the other shape flat drawing is best at
    'lens': [
        '...####.....',
        '..##++##....',
        '.##++++##...',
        '.##+..++##..',
        '.##+..++##..',
        '.##++++##...',
        '..##++##....',
        '...######...',
        '......####..',
        '.......####.',
        '........###.',
        '............'],

    # AI and agents: a standing stone with a mark cut into it
    'rune': [
        '............',
        '...######...',
        '..########..',
        '..##%##%##..',
        '..##%##%##..',
        '..###%#%##..',
        '..##%#%###..',
        '..##%##%##..',
        '..########..',
        '..########..',
        '...######...',
        '............'],

    # integrations: two links, one through the other
    'chain': [
        '..####......',
        '.##++##.....',
        '.##..##.....',
        '.##..##.....',
        '..####......',
        '...####.....',
        '....%%**%%..',
        '....%%..%%..',
        '.....%%..%%.',
        '.....%%..%%.',
        '......%%%%..',
        '............'],

    # the plain solid
    'cube': [
        '............',
        '....####....',
        '..########..',
        '.##########.',
        '.##++++++##.',
        '.##++++++##.',
        '.##++++++##.',
        '.##++++++##.',
        '.##########.',
        '..########..',
        '....####....',
        '............'],

    # stacked plates
    'slabs': [
        '............',
        '.##########.',
        '.##++++++##.',
        '.##########.',
        '............',
        '.##########.',
        '.##++++++##.',
        '.##########.',
        '............',
        '.##########.',
        '.##++++++##.',
        '.##########.'],

    # a small crawling thing
    'bug': [
        '............',
        '..#......#..',
        '...#....#...',
        '....####....',
        '..########..',
        '.##--##--##.',
        '.##########.',
        '#####++#####',
        '.##########.',
        '..########..',
        '..#......#..',
        '............'],
}


def size_of(rows):
    """@returns: (width, height) of an icon grid."""
    return len(rows[0]), len(rows)


def is_rectangular(rows):
    """Whether every row of an icon is the same length."""
    return len({len(row) for row in rows}) == 1


def count_ink(rows):
    """How many cells of an icon are painted rather than left empty."""
    return sum(row.count(character) for row in rows for character in INK)


def runs_in_row(row, character):
    """The horizontal runs of one character.

    Runs rather than single cells because a row of twelve identical pixels is
    one rect instead of twelve, which is most of the file size.

    @returns: (start, length) pairs, left to right.
    """
    found, x = [], 0
    while x < len(row):
        if row[x] != character:
            x += 1
            continue
        length = 1
        while x + length < len(row) and row[x + length] == character:
            length += 1
        found.append((x, length))
        x += length
    return found


def rects_for_tone(rows, character, token):
    """One SVG rect per run of `character`, coloured by its palette token."""
    return [f'<rect x="{x}" y="{y}" width="{length}" height="1" '
            f'fill="var(--{token})"/>'
            for (y, row) in enumerate(rows)
            for (x, length) in runs_in_row(row, character)]


def to_symbol(name, rows):
    """One icon grid as an SVG <symbol>."""
    width, height = size_of(rows)
    rects = [rect
             for (character, token) in TONES
             for rect in rects_for_tone(rows, character, token)]
    return (f'<symbol id="{SYMBOL_PREFIX}-{name}" viewBox="0 0 {width} {height}">'
            f'{"".join(rects)}</symbol>')


def build_sheet(icons):
    """Every icon as one sheet of symbols, reporting each as it is drawn."""
    symbols = []
    for (name, rows) in icons.items():
        assert is_rectangular(rows), f'{name}: ragged rows'
        symbol = to_symbol(name, rows)
        symbols.append(symbol)
        width, height = size_of(rows)
        print(f'{SYMBOL_PREFIX}-{name:8} {width}x{height}  '
              f'{count_ink(rows):3} pixels  {len(symbol) / 1024:4.1f} KB')
    return symbols


def main():
    symbols = build_sheet(ICONS)
    pathlib.Path(OUTPUT).write_text('\n'.join(symbols))
    print(f'\nwrote {OUTPUT}, {len(symbols)} icons')


if __name__ == '__main__':
    main()
