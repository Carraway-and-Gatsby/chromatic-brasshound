#!/usr/bin/env python3
"""Original BRASSHOUND title artwork authored at its native 160 x 144 pixels.

This drawing follows the selected ROOK IN THE SPOTLIGHT composition. The AI
concept is used only as a composition reference: no source image is sampled,
resized, traced, imported, or quantized. Every output pixel is drawn here.
Each 8 x 8 tile selects one of four native four-color GBC palettes.

Rows 40..47 and 120..143 are intentionally empty for runtime menu lettering.
Run with Python 3. Standard library only.
"""
from pathlib import Path
import json
import struct
import zlib

OUT = Path(__file__).resolve().parent
WIDTH, HEIGHT = 160, 144
DARK = [12, 20, 32]
PALETTES = [
    [DARK, [63, 81, 92], [227, 174, 56], [244, 235, 197]],
    [DARK, [24, 39, 56], [46, 65, 80], [82, 103, 112]],
    [DARK, [155, 104, 52], [227, 174, 56], [244, 235, 197]],
    [DARK, [34, 47, 59], [68, 83, 90], [137, 149, 142]],
]
pixels = [[0] * WIDTH for _ in range(HEIGHT)]
attributes = [[0] * (WIDTH // 8) for _ in range(HEIGHT // 8)]


def palette_rect(x0, y0, x1, y1, palette):
    """Choose tile palettes; coordinates must follow the native tile grid."""
    assert x0 % 8 == y0 % 8 == (x1 + 1) % 8 == (y1 + 1) % 8 == 0
    for y in range(y0 // 8, (y1 + 1) // 8):
        for x in range(x0 // 8, (x1 + 1) // 8):
            attributes[y][x] = palette


def dot(x, y, color):
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        pixels[y][x] = color


def rect(x0, y0, x1, y1, color):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            dot(x, y, color)


def line(x0, y0, x1, y1, color):
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = 1 if x0 < x1 else -1, 1 if y0 < y1 else -1
    error = dx + dy
    while True:
        dot(x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        twice = error * 2
        if twice >= dy:
            error += dy
            x0 += sx
        if twice <= dx:
            error += dx
            y0 += sy


def polygon(points, color):
    # Integer scan conversion at native pixel centers. No antialiasing.
    x0, x1 = min(p[0] for p in points), max(p[0] for p in points)
    y0, y1 = min(p[1] for p in points), max(p[1] for p in points)
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            inside = False
            previous = points[-1]
            for current in points:
                ax, ay = previous
                bx, by = current
                if (ay > y) != (by > y):
                    if x < ax + (y - ay) * (bx - ax) / (by - ay):
                        inside = not inside
                previous = current
            if inside:
                dot(x, y, color)
    for a, b in zip(points, points[1:] + points[:1]):
        line(*a, *b, color)


# A custom heavy wordmark, not the body font. Six-column letter masters have
# doubled stems, square counters and 2 x 3 native pixel blocks. Repeated S and
# repeated straight stems reuse identical tile patterns in the ROM converter.
LETTER = {
    'B': ['111110', '110011', '110011', '111110', '110011', '110011', '111110'],
    'R': ['111110', '110011', '110011', '111110', '111100', '110110', '110011'],
    'A': ['001100', '011110', '110011', '110011', '111111', '110011', '110011'],
    'S': ['011111', '110000', '110000', '011110', '000011', '000011', '111110'],
    'H': ['110011', '110011', '110011', '111111', '110011', '110011', '110011'],
    'O': ['011110', '110011', '110011', '110011', '110011', '110011', '011110'],
    'U': ['110011', '110011', '110011', '110011', '110011', '110011', '011110'],
    'N': ['110011', '111011', '111011', '110111', '110111', '110011', '110011'],
    'D': ['111100', '110110', '110011', '110011', '110011', '110110', '111100'],
}
logo = set()
for i, letter in enumerate('BRASSHOUND'):
    for row, bits in enumerate(LETTER[letter]):
        for column, bit in enumerate(bits):
            if bit == '1':
                for dy in range(3):
                    for dx in range(2):
                        logo.add((11 + i * 14 + column * 2 + dx, 9 + row * 3 + dy))
# A single steel rim keeps the gold letters distinct on the navy background.
for x, y in logo:
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            dot(x + dx, y + dy, 1)
for x, y in logo:
    dot(x, y, 3 if y == 9 else 2)

# The native scene is deliberately quiet around its central lit doorway.
palette_rect(0, 56, 159, 119, 1)
palette_rect(48, 56, 111, 119, 2)
palette_rect(112, 80, 119, 87, 2)  # A gold gun barrel crosses the steel bay.
palette_rect(0, 112, 47, 119, 3)
palette_rect(112, 112, 159, 119, 3)

# Cool structural columns and sparse rivets: tile-aligned repeated modules.
for x in (8, 32, 120, 144):
    rect(x, 56, x + 7, 111, 1)
    rect(x + 1, 56, x + 2, 111, 2)
    line(x + 5, 56, x + 5, 111, 2)
    for y in (59, 75, 91, 107):
        rect(x + 4, y, x + 5, y + 1, 3)
rect(16, 58, 29, 61, 1)
rect(17, 58, 28, 58, 2)
rect(18, 61, 19, 86, 1)
rect(24, 61, 25, 86, 1)
rect(112, 61, 143, 64, 1)
line(113, 62, 142, 91, 2)
line(142, 62, 113, 91, 2)
rect(112, 91, 143, 94, 1)
rect(112, 93, 143, 94, 2)

# A broad black frame makes the warm vertical doorway read at handheld scale.
rect(44, 56, 87, 111, 0)
rect(46, 56, 83, 57, 1)
rect(48, 58, 79, 111, 2)
rect(55, 59, 77, 110, 3)
rect(79, 58, 81, 111, 1)
rect(82, 58, 83, 111, 2)
rect(48, 58, 53, 111, 1)
# Functional caution markings only on the machinery's doorway jamb.
for y in range(58, 111):
    for x in range(49, 54):
        if (y - x) % 12 < 5:
            dot(x, y, 2)

# Vent/crate bays form a low foreground frame without matching the hero's gold.
rect(8, 88, 31, 110, 1)
rect(8, 88, 31, 89, 3)
rect(10, 91, 29, 107, 0)
for y in (92, 96, 100, 104):
    rect(11, y, 28, y + 1, 2)
rect(120, 96, 143, 110, 1)
rect(120, 96, 143, 97, 3)
rect(123, 100, 139, 101, 0)
rect(123, 104, 139, 105, 0)
rect(123, 108, 139, 109, 0)

# Reserve the muzzle's palette tile. A warm palette must not recolor the cool
# crossed support behind it; its quiet negative space frames the weapon.
rect(112, 80, 119, 87, 0)

# Original ROOK portrait-scale pose. Helmet, visor, backpack, armor, forearm,
# weapon and splayed stance are authored here, not scaled from the tiny sprite.
# Each solid warm silhouette is cut with a one/two native pixel navy contour.
polygon([(71, 64), (76, 61), (88, 61), (92, 65), (92, 76),
         (88, 80), (73, 80), (71, 77)], 0)
rect(74, 64, 88, 76, 2)
rect(76, 64, 88, 65, 3)
rect(76, 66, 78, 67, 1)
rect(72, 68, 73, 74, 1)
rect(81, 68, 91, 71, 0)
rect(80, 69, 89, 70, 1)
rect(80, 69, 82, 69, 3)
rect(88, 73, 91, 76, 1)
rect(75, 77, 87, 77, 1)
rect(76, 78, 84, 81, 0)

# Pack and separate shoulder/arm remain legible against the bright door.
rect(63, 78, 72, 96, 0)
rect(65, 80, 70, 93, 1)
rect(65, 80, 70, 82, 2)
rect(65, 88, 68, 91, 0)
polygon([(72, 78), (80, 79), (88, 81), (86, 96), (75, 99),
         (70, 92), (70, 82)], 0)
rect(73, 81, 81, 93, 2)
rect(74, 85, 82, 93, 1)
rect(73, 81, 79, 82, 3)
rect(78, 80, 80, 94, 0)
rect(73, 94, 85, 96, 1)
rect(74, 95, 77, 96, 2)
rect(83, 79, 104, 87, 0)
rect(84, 81, 102, 84, 2)
rect(87, 83, 96, 85, 1)
rect(99, 81, 102, 82, 3)

# Compact squared rifle and a bright muzzle cap.
rect(100, 77, 112, 86, 0)
rect(102, 79, 109, 83, 1)
rect(103, 79, 109, 80, 2)
rect(104, 84, 107, 88, 0)
rect(105, 85, 106, 86, 1)
rect(110, 79, 118, 83, 0)
rect(111, 80, 116, 81, 2)
rect(116, 80, 117, 81, 3)

# Both boots meet the floor; the left leg bends back in a ready stance.
polygon([(75, 96), (82, 97), (80, 104), (75, 110), (63, 110),
         (63, 106), (70, 106), (72, 99)], 0)
polygon([(75, 98), (78, 99), (76, 103), (72, 107), (66, 107),
         (71, 105)], 1)
rect(64, 108, 73, 109, 1)
rect(65, 108, 70, 108, 2)
polygon([(81, 96), (86, 96), (88, 101), (89, 106), (95, 106),
         (97, 110), (83, 110), (81, 104)], 0)
polygon([(83, 98), (85, 99), (85, 103), (86, 107), (93, 107),
         (94, 108), (85, 108), (83, 103)], 1)
rect(84, 99, 85, 102, 2)

# Riveted floor with a short pool of doorway light. Repeated plates save tiles.
for x in range(0, 160, 8):
    rect(x, 112, x + 7, 113, 2)
    rect(x, 114, x + 7, 119, 1)
    dot(x + 2, 116, 0)
    dot(x + 5, 118, 0)
polygon([(54, 112), (80, 112), (99, 119), (76, 119)], 2)
polygon([(55, 112), (68, 112), (83, 117), (70, 117)], 3)
rect(0, 119, 159, 119, 0)


def write_png(path, rgb):
    h, w = len(rgb), len(rgb[0])
    raw = b''.join(b'\0' + bytes(channel for pixel in row for channel in pixel)
                   for row in rgb)
    def chunk(kind, body):
        return (struct.pack('>I', len(body)) + kind + body +
                struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' +
                     chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
                     chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def tile_keys():
    return {tuple(pixels[y + dy][x + dx]
                  for dy in range(8) for dx in range(8))
            for y in range(0, HEIGHT, 8) for x in range(0, WIDTH, 8)}


def main():
    OUT.mkdir(exist_ok=True)
    assert all(value == 0 for row in pixels[40:48] for value in row)
    assert all(value == 0 for row in pixels[120:144] for value in row)
    count = len(tile_keys())
    assert count <= 210, f'{count} tile patterns exceed the native art budget'
    data = {'width': WIDTH, 'height': HEIGHT, 'palettes': PALETTES,
            'pixels': pixels, 'attributes': attributes}
    (OUT / 'title-native.json').write_text(json.dumps(data, separators=(',', ':')) + '\n')
    rgb = [[PALETTES[attributes[y // 8][x // 8]][pixels[y][x]]
            for x in range(WIDTH)] for y in range(HEIGHT)]
    write_png(OUT / 'title-native.png', rgb)
    write_png(OUT / 'title-native-preview.png',
              [[color for color in row for _ in range(6)]
               for row in rgb for _ in range(6)])
    print(f'Native title: {WIDTH} x {HEIGHT}, {count} unique 8 x 8 patterns, '
          f'{len(PALETTES)} four-color palettes')


if __name__ == '__main__':
    main()
