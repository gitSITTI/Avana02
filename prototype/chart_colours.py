"""Are the colours of a chart tellable apart by people who see colour differently, and do the marks stand out from the page?

The same rules as the data-visualisation palette check used while the charts were designed, in a form the tests can run without that tool:
  - every pair of colours must differ by at least 6 (OKLab distance x 100) as a person with protanopia or deuteranopia sees them (Machado, Oliveira and Fernandes 2009);
    6 to 8 is allowed only where something other than colour also tells the marks apart (a label, a shape, a pattern)
  - every pair must differ by at least 15 as a person with ordinary colour vision sees them
  - every mark must stand out from the page by 3 to 1 (WCAG 1.4.11), unless it is an outline drawn on purpose

Used by b20.py. Run on its own with colours:  python3 chart_colours.py '#4F8FE6,#1C5CAB,#1B6B3A,#C47A00'
"""
import itertools, math, sys

MACHADO = {
    'protan': ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    'deutan': ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    'tritan': ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}
CVD_TARGET, CVD_FLOOR, NORMAL_FLOOR, CONTRAST_MIN = 8.0, 6.0, 15.0, 3.0


def lin(hexcolour):
    h = hexcolour.strip().lstrip('#')
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return out


def oklab(rgb):
    r, g, b = rgb
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def simulate(rgb, kind):
    m = MACHADO[kind]
    return [max(0.0, min(1.0, sum(m[i][j] * rgb[j] for j in range(3)))) for i in range(3)]


def delta_e(a, b, kind=None):
    ra, rb = lin(a), lin(b)
    if kind:
        ra, rb = simulate(ra, kind), simulate(rb, kind)
    return 100 * math.dist(oklab(ra), oklab(rb))


def luminance(hexcolour):
    r, g, b = lin(hexcolour)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def check(colours, surface='#FFFFFF', outlines=()):
    """Returns (problems, notes). Colours are the fills of the marks; outlines are the colours of marks drawn only as an outline."""
    problems, notes = [], []
    for a, b in itertools.combinations(colours, 2):
        cvd = min(delta_e(a, b, 'protan'), delta_e(a, b, 'deutan'))
        normal = delta_e(a, b)
        if cvd < CVD_FLOOR:
            problems.append('%s and %s are %.1f apart for a person with red-green colour blindness, needs %g' % (a, b, cvd, CVD_FLOOR))
        elif cvd < CVD_TARGET:
            notes.append('%s and %s are %.1f apart for red-green colour blindness (6 to 8 is allowed because a label or pattern also tells them apart)' % (a, b, cvd))
        if normal < NORMAL_FLOOR:
            problems.append('%s and %s are %.1f apart for ordinary colour vision, needs %g' % (a, b, normal, NORMAL_FLOOR))
    for c in list(colours) + list(outlines):
        if contrast(c, surface) < CONTRAST_MIN:
            problems.append('%s is %.2f to 1 against the page, needs %g' % (c, contrast(c, surface), CONTRAST_MIN))
    return problems, notes


if __name__ == '__main__':
    cols = [c.strip() for c in (sys.argv[1] if len(sys.argv) > 1 else '').split(',') if c.strip()]
    probs, notes = check(cols)
    for n in notes: print('NOTE', n)
    for p in probs: print('FAIL', p)
    print('OK' if not probs else '%d problems' % len(probs))
    sys.exit(1 if probs else 0)
