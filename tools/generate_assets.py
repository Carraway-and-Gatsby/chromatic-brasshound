#!/usr/bin/env python3
"""Generate original BRASSHOUND graphics as native Game Boy Color 2bpp tiles.

Every silhouette, tile motif, palette and glyph is authored below. No imported
images, game assets, font files or generative-image dependencies are used.
Run with Python 3; PNG export uses only the standard library.
"""
from pathlib import Path
import json
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)

# RGB source palettes; output converts to the GBC's 15-bit BGR register layout.
BG_COLORS = [
    [(12, 20, 32), (25, 37, 53), (40, 55, 71), (68, 87, 102)],
    [(16, 24, 34), (44, 48, 54), (79, 88, 93), (134, 146, 140)],
    [(27, 25, 30), (70, 45, 39), (133, 72, 44), (194, 128, 59)],
    [(18, 24, 31), (69, 67, 55), (128, 115, 66), (227, 184, 65)],
    [(14, 24, 34), (33, 54, 65), (75, 98, 102), (149, 169, 151)],
    [(13, 21, 30), (48, 57, 63), (101, 115, 115), (171, 166, 133)],
    [(20, 24, 34), (89, 40, 36), (213, 91, 33), (255, 218, 103)],
    [(12, 20, 32), (112, 128, 138), (227, 174, 56), (244, 235, 197)],
]
# Harbor uses wet blue steel, faded ochre dock markings and a cyan pump core.
# The blackout palette separates violet containment armor from a red reactor.
# Palette roles remain identical so the engine can reuse the environmental atlas.
TIDEBREAK_COLORS = [
    [(10, 22, 35), (24, 50, 67), (39, 78, 93), (83, 128, 142)],
    [(10, 24, 37), (31, 57, 70), (74, 102, 111), (144, 175, 173)],
    [(22, 30, 39), (69, 52, 45), (130, 90, 58), (208, 153, 77)],
    [(12, 26, 38), (64, 81, 78), (127, 137, 99), (239, 203, 102)],
    [(10, 24, 37), (25, 62, 72), (64, 121, 126), (138, 198, 185)],
    [(10, 24, 37), (32, 65, 80), (86, 141, 150), (175, 217, 202)],
    [(10, 24, 37), (18, 78, 88), (38, 190, 196), (211, 255, 226)],
    BG_COLORS[7],
]
BLACKOUT_COLORS = [
    [(18, 13, 30), (40, 28, 60), (66, 46, 88), (114, 82, 128)],
    [(18, 13, 30), (46, 35, 55), (89, 72, 97), (149, 130, 153)],
    [(25, 16, 33), (80, 35, 46), (154, 65, 70), (224, 129, 94)],
    [(18, 13, 30), (68, 50, 59), (134, 100, 83), (236, 180, 97)],
    [(18, 13, 30), (36, 32, 60), (67, 61, 93), (140, 128, 162)],
    [(18, 13, 30), (52, 40, 77), (117, 90, 151), (211, 179, 223)],
    [(18, 13, 30), (105, 25, 48), (230, 69, 101), (255, 215, 164)],
    BG_COLORS[7],
]
OBJ_COLORS = [
    [(12, 20, 32), (29, 40, 48), (163, 111, 56), (249, 211, 105)],
    [(12, 20, 32), (15, 23, 32), (121, 142, 149), (237, 89, 66)],
    [(12, 20, 32), (14, 24, 32), (90, 113, 117), (222, 175, 73)],
    [(12, 20, 32), (15, 25, 35), (84, 135, 147), (122, 232, 218)],
    [(12, 20, 32), (16, 25, 35), (82, 102, 106), (244, 198, 82)],
    [(12, 20, 32), (163, 54, 28), (247, 132, 32), (255, 235, 137)],
    [(12, 20, 32), (111, 83, 37), (248, 185, 54), (255, 243, 168)],
    [(12, 20, 32), (84, 28, 30), (238, 80, 49), (255, 194, 103)],
]

# BG index zero is opaque on GBC. Share each stage's darkest ink so an empty
# boss, pipe or crate pixel cannot reveal a differently colored tile rectangle.
for stage_palettes in (BG_COLORS, TIDEBREAK_COLORS, BLACKOUT_COLORS):
    for palette in stage_palettes[:7]:
        palette[0] = stage_palettes[0][0]


def canvas(w=8, h=8):
    return [[0] * w for _ in range(h)]


def dot(p, x, y, c):
    if 0 <= y < len(p) and 0 <= x < len(p[0]):
        p[y][x] = c


def rect(p, x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            dot(p, x, y, c)


def line(p, x0, y0, x1, y1, c):
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = 1 if x0 < x1 else -1, 1 if y0 < y1 else -1
    error = dx + dy
    while True:
        dot(p, x0, y0, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * error
        if e2 >= dy:
            error += dy
            x0 += sx
        if e2 <= dx:
            error += dx
            y0 += sy


def ellipse(p, x0, y0, x1, y1, c):
    # Integer ellipse equation keeps all generated output deterministic.
    a, b = x1 - x0, y1 - y0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if (2*x-x0-x1)**2*b*b + (2*y-y0-y1)**2*a*a <= a*a*b*b:
                dot(p, x, y, c)


def ascii_art(rows):
    assert len(set(map(len, rows))) == 1
    return [[".osg".index(ch) for ch in row] for row in rows]


def encode_tile(p):
    data = []
    for row in p:
        lo = hi = 0
        for c in row:
            lo = (lo << 1) | (c & 1)
            hi = (hi << 1) | (c >> 1)
        data.extend((lo, hi))
    return data


def cut(p, x, y):
    return [row[x:x+8] for row in p[y:y+8]]


def png(path, pixels):
    h, w = len(pixels), len(pixels[0])
    raw = b"".join(b"\0" + bytes(sum((list(rgb) for rgb in row), [])) for row in pixels)
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def rgb_image(p, palette, scale=1):
    return [[palette[c] for c in row for _ in range(scale)] for row in p for _ in range(scale)]


def blit(dst, source, x, y):
    for yy, row in enumerate(source):
        for xx, value in enumerate(row):
            if 0 <= y + yy < len(dst) and 0 <= x + xx < len(dst[0]):
                dst[y + yy][x + xx] = value


# Five-pixel, seven-row handwritten monospace glyphs with one-pixel margins.
FONT = {
    'A': [14,17,17,31,17,17,17], 'B': [30,17,17,30,17,17,30],
    'C': [14,17,16,16,16,17,14], 'D': [30,17,17,17,17,17,30],
    'E': [31,16,16,30,16,16,31], 'F': [31,16,16,30,16,16,16],
    'G': [14,17,16,23,17,17,15], 'H': [17,17,17,31,17,17,17],
    'I': [14,4,4,4,4,4,14], 'J': [7,2,2,2,18,18,12],
    'K': [17,18,20,24,20,18,17], 'L': [16,16,16,16,16,16,31],
    'M': [17,27,21,21,17,17,17], 'N': [17,25,25,21,19,19,17],
    'O': [14,17,17,17,17,17,14], 'P': [30,17,17,30,16,16,16],
    'Q': [14,17,17,17,21,18,13], 'R': [30,17,17,30,20,18,17],
    'S': [15,16,16,14,1,1,30], 'T': [31,4,4,4,4,4,4],
    'U': [17,17,17,17,17,17,14], 'V': [17,17,17,17,17,10,4],
    'W': [17,17,17,21,21,27,17], 'X': [17,17,10,4,10,17,17],
    'Y': [17,17,10,4,4,4,4], 'Z': [31,1,2,4,8,16,31],
    '0': [14,17,19,21,25,17,14], '1': [4,12,4,4,4,4,14],
    '2': [14,17,1,2,4,8,31], '3': [30,1,1,14,1,1,30],
    '4': [2,6,10,18,31,2,2], '5': [31,16,16,30,1,1,30],
    '6': [14,16,16,30,17,17,14], '7': [31,1,2,4,8,8,8],
    '8': [14,17,17,14,17,17,14], '9': [14,17,17,15,1,1,14],
    '-': [0,0,0,31,0,0,0], ':': [0,4,4,0,4,4,0],
    '*': [0,10,31,31,14,4,0], '.': [0,0,0,0,0,6,6],
    '/': [1,1,2,4,8,16,16], '!': [4,4,4,4,4,0,4],
}


def glyph(ch):
    p = canvas()
    for y, row in enumerate(FONT[ch]):
        for x in range(5):
            if row & (1 << (4-x)):
                dot(p, x+1, y, 3)
    return p


bg = [canvas() for _ in range(214)]
for index, ch in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-:*./!', 1):
    bg[index] = glyph(ch)

TILES = {
    "WATER":43, "VOID":44, "CONTAINER":45, "PANEL_EDGE":46, "PANEL_SEAM":47,
    "GROUND":48, "GROUND_FILL":49, "WARNING":50, "PLATFORM_LEFT":51,
    "PLATFORM":52, "PLATFORM_RIGHT":53, "BUILDING":54, "WINDOW":55,
    "WINDOW_LIT":56, "SKYLINE":57, "SKYLINE_TOP":58, "SMOKE":59,
    "DEBRIS":60, "PIPE":61, "PIPE_VERTICAL":62, "PIPE_ELBOW":63,
    "CRATE":64, "CRATE_RUST":65, "WALL_BROKEN":66, "VENT":67,
    "HAZARD_STRIPE":68, "GRATE":69, "METAL_FLOOR":70, "LAMP":71,
    "WIRE":72, "CHEVRON":73, "HAZARD":74, "DOOR":75, "DOOR_TOP":76,
    "SIGN_B":77, "SIGN_F":78, "BARREL":79, "ROAD":80, "CHIMNEY":81,
    "SKYLINE_DETAIL":82, "RAILING":83, "SUPPORT":84, "MACHINERY":85,
    "EMBER":86, "SCAFFOLD":87, "PIPE_BROKEN":88, "BOLT_PANEL":89,
    "STEEL":90, "GEAR":91, "CONVEYOR":92, "CRACK":93, "CYAN_EDGE":94,
    "DARK_STEEL":95,
}
env_palette = {}


def env(name, rows, pal):
    bg[TILES[name]] = ascii_art(rows)
    env_palette[TILES[name]] = pal


env('GROUND', ['gggggggg','ssssssss','oooooooo','ssosssso','soossoos','ssssssso','ossossso','sssssoss'], 3)
env('GROUND_FILL', ['ossssoss','ssossosso'[:8],'ssossoss','oossssso','ssssosso','sossooss','ssossoss','oossssss'], 1)
env('WARNING', ['gggggggg','ssssssss','oooooggo','ooogggoo','ogggoooo','ggooooog','oooooggg','oooooooo'], 3)
env('PLATFORM_LEFT', ['.ggggggg','osssssss','osoooooo','osgsssss','osoooooo','os..os..','os..os..','oo..oo..'], 4)
env('PLATFORM', ['gggggggg','ssssssss','oooooooo','ssgssgss','oooooooo','..os....','..os....','..oo....'], 4)
env('PLATFORM_RIGHT', ['ggggggg.','ssssssso','ooooooso','ssssgsso','ooooooso','..so..so','..so..so','..oo..oo'], 4)
env('BUILDING', ['oooooooo','ssssssss','ssssssso','ssssssso','ssssssss','ssssssss','osssssss','osssssss'], 1)
env('WINDOW', ['ssssssss','soooooos','sosossos','sosoosos','sossosos','sosoosos','soooooos','ssssssss'], 1)
env('WINDOW_LIT', ['ssssssss','soggggos','soggsgos','soggggos','sosssgos','sogsggos','soooooos','ssssssss'], 2)
env('SKYLINE', ['oooooooo','oosoooso','oosoooso','oooooooo','oooooooo','ooooosoo','ooooosoo','oooooooo'], 0)
env('SKYLINE_TOP', ['........','..o.....','..o...o.','ooooooo.','ooooooo.','oooooooo','oooooooo','oooooooo'], 0)
env('SMOKE', ['........','..oo....','.oooo...','..oooo..','....oo..','.....oo.','...oooo.','..ooo...'], 0)
env('DEBRIS', ['........','........','........','..o.....','.osso...','oosso.oo','ssossoos','oooooooo'], 2)
env('PIPE', ['oooooooo','ssosssss','ggosgggg','ssosssss','oooooooo','........','........','........'], 4)
env('PIPE_VERTICAL', ['.osgso..','.osgso..','.osgso..','.ooooo..','.osgso..','.osgso..','.osgso..','.osgso..'], 4)
env('PIPE_ELBOW', ['.ooooo..','.osgso..','.osgso..','.osgsooo','.osggsss','.ossgggg','..oooooo','........'], 4)
env('CRATE', ['oooooooo','ogsssggo','ososooso','ossoosso','ossoosso','osoososo','oggsssgo','oooooooo'], 4)
env('CRATE_RUST', ['oooooooo','ogssssso','osgossso','ossoosso','osssooso','ossssgoo','osssssgo','oooooooo'], 2)
env('WALL_BROKEN', ['ssso....','sssso...','sosso...','ssssso..','ssssso..','osssoo..','ssso....','sso.....'], 1)
env('VENT', ['ssssssss','soooooos','soggggos','sosssgos','soggggos','sosssgos','soooooos','ssssssss'], 4)
env('HAZARD_STRIPE', ['ooogggoo','oogggooo','ogggoooo','gggoooog','ggoooogg','gooooggg','oooogggo','ooogggoo'], 3)
env('GRATE', ['gggggggg','oooooooo','sosssoss','sosssoss','sosssoss','sosssoss','oooooooo','ssssssss'], 1)
env('METAL_FLOOR', ['gggggggg','ssssssss','oogooogo','ssssssss','ssoossso','ssssssss','ogooogoo','oooooooo'], 4)
env('LAMP', ['...oo...','..osso..','.osggso.','oosggsoo','..osso..','...oo...','...oo...','...oo...'], 3)
env('WIRE', ['........','oooo....','...oo...','....oo..','.....ooo','........','........','........'], 4)
env('CHEVRON', ['oooooggo','ooooggoo','oooggooo','ooggoooo','oooggooo','ooooggoo','oooooggo','oooooooo'], 3)
env('HAZARD', ['........','........','........','..o..o..','..s..s..','.ogoogo.','.ssosso.','oooooooo'], 3)
env('DOOR', ['ssooooss','ssooooss','ssooooss','ssooosss','ssooooss','ssooooss','ssooooss','ssooooss'], 1)
env('DOOR_TOP', ['ssssssss','sggggggs','ssssssss','ssooooss','ssooooss','ssooooss','ssooooss','ssooooss'], 4)
env('SIGN_B', ['ssssssss','soggggos','sogssgos','soggggos','sogssgos','soggggos','soooooos','ssssssss'], 3)
env('SIGN_F', ['ssssssss','soggggos','sogsssss','soggggss','sogsssss','sogsssss','soooooos','ssssssss'], 3)
env('BARREL', ['.oooooo.','.osggso.','.osssso.','.oooooo.','.osgoso.','.osssso.','.osggso.','.oooooo.'], 2)
env('ROAD', ['ssssssso','sssossss','ssssssss','ssssssss','ssssssss','osssssss','ssssssss','ssssssso'], 1)
env('CHIMNEY', ['..oooo..','..ssso..','..osso..','..osso..','..osso..','..osso..','..osso..','..osso..'], 0)
env('SKYLINE_DETAIL', ['oooooooo','oossooso','oossooso','oooooooo','oooooooo','oossooso','oossooso','oooooooo'], 0)
env('RAILING', ['gggggggg','ooooooos','..so..so','..so..so','..so..so','..so..so','..so..so','..oo..oo'], 4)
env('SUPPORT', ['..osso..','..ogso..','..osso..','..osso..','..osso..','..ogso..','..osso..','..oooo..'], 4)
env('MACHINERY', ['osssssso','sggooggso'[:8],'sgoooogs','sooogoos','soogooos','sggooogs','sggooggso'[:8],'osssssso'], 2)
env('EMBER', ['........','........','.....g..','..s.....','...g....','.....s..','.s......','........'], 6)
env('SCAFFOLD', ['os....so','os....so','osso..so','os.os.so','os..soso','os...sso','os....so','os....so'], 4)
env('PIPE_BROKEN', ['oooooooo','ssosss..','ggosg...','ssoss...','oooooo..','......s.','.......s','........'], 4)
env('BOLT_PANEL', ['ssssssss','sgooooos','soooooos','soooooos','soooooos','soooooos','sooooogs','ssssssss'], 4)
env('STEEL', ['ssssssss','ssooooos','ssooooos','ssooooos','ssooooos','ssooooos','ssooooos','ssssssss'], 5)
env('GEAR', ['...ss...','.ssggss.','.sgssgs.','sgsoosgs','sgsoosgs','.sgssgs.','.ssggss.','...ss...'], 4)
env('CONVEYOR', ['gggggggg','oooooooo','ssgssgss','ssosssos','ssssssss','soososoo','ssssssss','oooooooo'], 4)
env('CRACK', ['ssssssss','ssssosss','sssossss','ssssooss','sssssoss','sssoosss','sssossss','ssssssss'], 1)
env('CYAN_EDGE', ['gggggggg','ssssssss','oooooooo','oooooooo','oooooooo','oooooooo','oooooooo','oooooooo'], 4)
env('DARK_STEEL', ['oooooooo','oooooooo','oooooooo','oooooooo','oooooooo','oooooooo','oooooooo','oooooooo'], 5)
env('WATER', ['........','........','..oooo..','.ss..ss.','........','oooo....','...sss..','........'], 0)
env('VOID', ['........','........','........','........','........','........','..o.....','.....o..'], 0)
env('CONTAINER', ['osssosss','osssosss','osssosss','osssosss','osssosss','osssosss','osssosss','osssosss'], 1)
env('PANEL_EDGE', ['ooooooo.','ooooooo.','oooooso.','ooooooo.','ooooooo.','oooooso.','ooooooo.','ooooooo.'], 0)
env('PANEL_SEAM', ['........','oooooooo','osooooso','oooooooo','oooooooo','oooooooo','oooooooo','oooooooo'], 0)


# ROOK is drawn directly on a 16x24 indexed grid. The foot anchor remains the
# old 16px actor's bottom; four shared lower blocks keep OBJ below tile 128.
def rook(kind):
    p = canvas(16, 24)
    # Crested brass helmet, recessed charcoal visor and short armored chin.
    rect(p,5,0,9,0,1);rect(p,5,1,9,1,3)
    rect(p,3,2,10,4,1);rect(p,4,2,9,3,2)
    line(p,5,2,9,2,3);dot(p,4,3,3)
    rect(p,4,4,10,4,1);dot(p,9,4,3)
    rect(p,5,5,9,6,1);rect(p,6,5,9,5,2);dot(p,8,5,3)
    rect(p,5,7,8,7,1);dot(p,6,7,2)
    # Pack, brass shoulder and an inset dark chest plate stay separate from
    # the face and rifle. A small scarf tail creates an asymmetric silhouette.
    rect(p,1,8,3,14,1);rect(p,1,9,2,12,2);dot(p,1,9,3)
    rect(p,4,8,9,15,1);rect(p,5,9,8,14,2)
    rect(p,4,8,8,8,3);rect(p,4,9,5,10,3)
    rect(p,6,10,8,12,1);dot(p,7,10,2)
    rect(p,2,7,4,7,2);dot(p,2,8,3)
    # Forward forearm, supporting glove and a compact horizontal rifle.
    rect(p,9,10,11,12,1);rect(p,9,10,10,11,2);dot(p,9,10,3)
    rect(p,8,12,12,13,2);dot(p,11,12,3)
    rect(p,10,14,15,15,1);rect(p,11,14,14,14,2)
    dot(p,13,13,1);dot(p,14,14,3)
    rect(p,7,14,9,15,1);dot(p,8,14,3)
    if kind in ('run2','run4'):
        # Passing poses compress the shoulders by one pixel, not the feet.
        q=canvas(16,24)
        for y in range(15):q[y+1]=p[y][:]
        p=q
    elif kind == 'run3':
        q=canvas(16,24)
        for y in range(16):
            for x,c in enumerate(p[y]):
                if c:dot(q,x+1 if y<8 else x,y,c)
        p=q
    elif kind == 'shoot':
        # Braced recoil: head/pack draw back; the barrel keeps its world anchor.
        for y in range(8):p[y]=p[y][1:]+[0]
        rect(p,8,10,11,11,1);rect(p,8,10,10,10,3)
        rect(p,8,12,12,13,2);dot(p,11,12,3)
    elif kind == 'hurt':
        for y in range(14):p[y]=p[y][1:]+[0]
        line(p,0,11,3,9,1);dot(p,0,11,2);dot(p,1,10,3)
    elif kind == 'aim':
        # Move the helmet aside so the vertical rifle has an exposed muzzle.
        for y in range(8):p[y]=p[y][2:]+[0,0]
        rect(p,9,10,15,15,0)
        rect(p,7,0,8,10,1);line(p,7,1,7,7,2);dot(p,7,1,3)
        rect(p,8,9,10,12,1);rect(p,8,9,9,11,2);dot(p,9,9,3)
        line(p,6,12,8,10,2);rect(p,6,13,8,14,1)
    # Belt and near/far legs. The four lower patterns occupy only eight rows.
    rect(p,4,16,10,17,1);rect(p,5,16,9,16,2);dot(p,7,16,3)
    if kind in ('idle','aim','hurt','shoot'):
        rect(p,4,18,6,22,1);rect(p,5,18,6,20,2);dot(p,5,18,3)
        rect(p,8,18,10,22,1);rect(p,8,18,9,21,2);dot(p,8,19,3)
        rect(p,3,22,6,23,1);line(p,3,22,5,22,2)
        rect(p,8,22,12,23,1);line(p,9,22,11,22,2)
    elif kind in ('run1','run3'):
        line(p,5,18,2,21,1);line(p,6,18,3,21,2);dot(p,5,18,3)
        rect(p,0,21,3,22,1);line(p,0,21,2,21,2)
        line(p,8,18,11,21,1);line(p,9,18,12,21,2);dot(p,10,20,3)
        rect(p,11,22,15,23,1);line(p,12,22,14,22,2)
    elif kind in ('run2','run4'):
        line(p,5,18,8,20,1);line(p,6,18,9,20,2)
        rect(p,8,20,11,21,1);dot(p,10,20,2)
        rect(p,6,18,8,22,1);line(p,7,19,7,22,2);dot(p,7,20,3)
        rect(p,5,22,9,23,1);line(p,6,22,8,22,2)
    elif kind == 'jump':
        rect(p,3,18,6,20,1);rect(p,4,18,6,19,2);dot(p,4,18,3)
        rect(p,1,20,5,21,1);line(p,2,20,4,20,2)
        rect(p,8,18,11,20,1);rect(p,9,18,10,19,2);dot(p,9,18,3)
        rect(p,9,21,13,22,1);line(p,10,21,12,21,2)
    if kind in ('run3','run4'):
        for y in range(16,24):p[y]=p[y][::-1]
    if kind == 'crouch':
        q=canvas(16,16)
        for y in range(7):q[y+4]=p[y][:]
        rect(q,2,10,9,14,1);rect(q,3,11,8,13,2)
        rect(q,3,10,7,10,3);rect(q,1,11,2,13,2)
        rect(q,9,11,12,12,2);dot(q,10,11,3)
        rect(q,10,12,15,13,1);rect(q,12,12,14,12,2)
        rect(q,3,14,8,15,1);rect(q,9,14,12,15,1)
        dot(q,4,14,2);dot(q,10,14,2)
        p=q
    return p


def infantry(second=False):
    p = canvas(16,16)
    rect(p,5,1,10,5,1); rect(p,6,2,9,4,2)
    rect(p,7,3,10,3,3); dot(p,10,4,1)
    rect(p,4,6,11,10,1); rect(p,5,7,10,9,2)
    rect(p,5,6,10,6,2); dot(p,8,8,3)
    rect(p,2,7,4,10,1); rect(p,2,8,3,9,2)
    rect(p,11,7,15,8,1); rect(p,12,7,14,7,2)
    rect(p,10,8,12,9,2)
    if second:
        line(p,5,11,3,14,1); line(p,6,11,4,14,2)
        line(p,9,11,11,14,1); line(p,8,11,10,14,2)
        rect(p,2,15,5,15,1); rect(p,10,15,13,15,1)
    else:
        rect(p,5,11,6,14,2); rect(p,8,11,9,14,2)
        line(p,4,11,4,14,1); line(p,10,11,10,14,1)
        rect(p,4,15,7,15,1); rect(p,8,15,11,15,1)
    return p


def turret():
    p = canvas(16,16)
    rect(p,3,4,10,8,1); rect(p,4,5,9,7,2)
    rect(p,4,5,8,5,3); dot(p,8,7,3)
    rect(p,0,5,4,6,1); rect(p,0,5,3,5,2)
    rect(p,10,6,13,7,1); rect(p,11,6,12,6,3)
    rect(p,6,9,8,12,1); rect(p,7,9,7,11,2)
    line(p,6,11,3,14,1); line(p,8,11,11,14,1)
    rect(p,1,14,13,15,1); rect(p,2,14,12,14,2)
    return p


def drone(second=False):
    p=canvas(16,16)
    y=3 if second else 2
    rect(p,0,y,5,y,1); rect(p,9,y,15,y,1)
    dot(p,2,y-1,2); dot(p,12,y-1,2)
    rect(p,3,y+1,3,5,2); rect(p,11,y+1,11,5,2)
    rect(p,4,5,11,9,1); rect(p,5,6,10,8,2)
    rect(p,6,6,9,6,3); dot(p,8,8,3)
    line(p,4,8,1,10,1); line(p,11,8,14,10,1)
    rect(p,1,10,3,11,2); rect(p,12,10,14,11,2)
    rect(p,6,10,9,11,1); dot(p,7,11,3)
    if second: dot(p,7,13,3); dot(p,8,14,2)
    return p


def supply_crate():
    p = canvas(16,16)
    rect(p,1,2,14,15,1); rect(p,2,3,13,14,2)
    rect(p,2,5,13,5,1);rect(p,3,6,4,13,1);rect(p,11,6,12,13,1)
    rect(p,6,3,9,4,3);rect(p,6,8,9,11,1);rect(p,7,9,8,10,3)
    for x,y in [(2,3),(13,3),(2,14),(13,14)]:dot(p,x,y,3)
    return p


def pickup(kind):
    p = canvas(16,16)
    # Field cases share a metal silhouette, latch and handle with the supply
    # crate. The stencil identifies contents; no floating treasure sparkles.
    rect(p,5,1,10,2,1);rect(p,6,1,9,1,2)
    rect(p,2,3,13,15,1);rect(p,3,4,12,14,2)
    rect(p,4,4,11,4,1);rect(p,6,4,9,4,3)
    rect(p,4,6,11,10,1)
    if kind=='mg':
        rect(p,3,7,12,7,3);rect(p,6,6,8,6,3)
        rect(p,3,8,4,8,3);rect(p,6,8,7,9,3);dot(p,10,8,3)
    elif kind=='rocket':
        # An upright missile reads differently from the MG's long rifle.
        rect(p,7,5,8,9,3);rect(p,6,6,9,8,3)
        dot(p,5,10,3);dot(p,6,9,3);dot(p,9,9,3);dot(p,10,10,3)
    else:
        rect(p,7,5,8,10,3); rect(p,5,7,10,8,3)
    return p


def explosion(frame):
    p=canvas(16,16)
    if frame==0:
        ellipse(p,4,4,11,11,1); ellipse(p,5,5,10,10,2)
        ellipse(p,6,6,9,9,3)
        for x,y in [(2,3),(12,2),(1,10),(13,12)]: dot(p,x,y,3)
        line(p,2,13,4,11,2); line(p,12,5,14,3,2)
    elif frame==1:
        ellipse(p,1,2,14,13,1); ellipse(p,3,3,12,12,2)
        ellipse(p,5,5,10,10,3)
        for x,y in [(3,0),(11,0),(0,4),(15,7),(1,14),(13,15)]:
            line(p,x,y,7,7,2)
        rect(p,7,6,9,8,3); rect(p,5,7,8,9,3)
    else:
        for x,y in [(2,1),(11,1),(0,8),(14,6),(3,14),(13,14)]:
            ellipse(p,x,y,x+2,y+1,1); dot(p,x+1,y,2)
        ellipse(p,3,3,12,12,1); ellipse(p,5,5,10,10,0)
        rect(p,3,6,4,8,2); rect(p,10,9,11,10,2)
    return p


def bullet(kind):
    p=canvas(16,16)
    # Horizontal glyph on the left, vertical glyph on the right. The engine
    # selects one 8x16 pair per shot; direction does not add an OAM slot.
    if kind=='pistol':
        rect(p,1,7,6,8,2); rect(p,2,7,5,7,3)
    elif kind=='mg':
        rect(p,0,7,7,8,2); rect(p,2,7,7,7,3)
    elif kind=='rocket':
        rect(p,1,6,5,9,1); rect(p,2,7,6,8,2)
        rect(p,3,7,5,7,3); dot(p,0,7,3); dot(p,0,8,2)
        dot(p,1,5,2); dot(p,1,10,2)
    elif kind=='enemy':
        ellipse(p,1,5,6,10,1); ellipse(p,2,6,5,9,2); rect(p,3,7,4,8,3)
    else:
        for x,y in [(1,3),(6,4),(0,8),(6,11),(2,12)]: line(p,3,8,x,y,2)
        ellipse(p,1,6,6,10,3); dot(p,7,8,2)
    if kind in ('pistol','mg','rocket'):
        # Rotate the left glyph around its native muzzle row into the right OBJ.
        for y in range(16):
            for x in range(8):
                if p[y][x]:dot(p,11+y-7,7-x,p[y][x])
    return p


death = ascii_art([
    '................','................','................','................',
    '................','................','................','................',
    '................','................','...oooo.........','..ogggso........',
    '.ossoosooossoo..','.osssoogssssssoo','..oooooosooooooo','........oooo....',
])
rook_full = [rook(k) for k in ['idle','run1','run2','jump','crouch','hurt']]
rook_full += [death,rook('aim')]
rook_extra = [rook(k) for k in ['run3','run4','shoot']]
sprite_images = [p[:16] for p in rook_full]
sprite_images += [infantry(),infantry(True),turret(),drone(),drone(True),supply_crate(),pickup('mg'),pickup('rocket'),pickup('heal')]
sprite_images += [explosion(i) for i in range(3)]
sprite_images += [bullet(k) for k in ['pistol','mg','rocket','enemy','muzzle']]
sprite_names = ['ROOK IDLE','ROOK RUN A','ROOK RUN B','ROOK JUMP','ROOK CROUCH','ROOK HURT','ROOK DOWN','ROOK AIM','SENTRY A','SENTRY B','TURRET','DRONE A','DRONE B','CRATE','MG SUPPLY','ROCKET SUPPLY','MEDKIT','BLAST A','BLAST B','BLAST C','PISTOL','MG','ROCKET','HOSTILE','MUZZLE']
sprite_pal_ids = [0]*8+[1,1,2,3,3,4,4,4,3,5,5,5,6,6,6,7,6]
# Lower halves share idle, stride, passing and tucked patterns. Transparent
# padding is necessary because each hardware OBJ is 8x16, even for an 8px foot.
rook_feet = [p[16:]+canvas(16,8) for p in rook_full[:4]]
packed_images = sprite_images + rook_feet + [p[:16] for p in rook_extra]
preview_images = rook_full + sprite_images[8:] + rook_extra
preview_names = sprite_names + ['ROOK RUN C','ROOK RUN D','ROOK SHOOT']
preview_pal_ids = sprite_pal_ids + [0]*3


# IRONMAW, 64x64 background composition. Two heavy tracks, swept plated turret,
# enormous left-facing barrel, vent cheeks and concentric furnace weak point.
boss=canvas(64,64)
rect(boss,17,16,58,40,1)
rect(boss,20,13,52,17,1); rect(boss,23,11,47,13,1)
rect(boss,24,12,46,12,3); rect(boss,21,14,51,15,2)
rect(boss,18,18,58,38,2); line(boss,20,17,56,17,3)
# The recessed barrel points left and leaves a clear gap above the track nose.
rect(boss,0,16,25,23,1); rect(boss,1,17,24,21,2)
rect(boss,1,17,21,17,3); rect(boss,0,17,2,22,1)
rect(boss,6,16,7,23,1); rect(boss,16,16,17,23,1)
rect(boss,18,17,24,20,3); rect(boss,23,14,29,25,1)
rect(boss,24,15,28,24,2); line(boss,24,15,27,15,3)
# Slanted side armor, rivets, hatch, industrial exhaust vents.
line(boss,58,18,61,27,1); line(boss,59,18,62,27,1)
rect(boss,59,26,62,39,1); rect(boss,59,27,60,37,2)
rect(boss,33,17,47,19,1); rect(boss,34,17,46,18,2)
for x in [20,30,50,57]:
    dot(boss,x,19,1); dot(boss,x+1,19,3)
for y in [24,27,30,33]:
    rect(boss,50,y,57,y+1,1); line(boss,50,y,56,y,3)
line(boss,19,34,28,34,1); line(boss,20,35,29,35,3)
line(boss,19,36,27,36,1); line(boss,29,20,29,33,1)
# Huge belly, rivet seams and diagonal industrial warning bumper.
rect(boss,10,39,61,49,1); rect(boss,11,40,60,46,2)
line(boss,12,40,59,40,3); line(boss,11,46,60,46,1)
rect(boss,17,42,57,45,1)
for x in range(18,57,8):
    line(boss,x,44,x+2,42,3); line(boss,x+1,44,x+3,42,3)
for x in [12,29,46,58]: dot(boss,x,41,1)
# Main crawler track silhouettes and their individually highlighted tread shoes.
rect(boss,6,49,60,59,1); rect(boss,8,48,58,60,1)
line(boss,8,49,58,49,3); line(boss,8,59,58,59,2)
for x in range(8,59,6):
    rect(boss,x,50,x+3,50,2); rect(boss,x,58,x+3,58,3)
for x in [12,24,36,48,56]:
    ellipse(boss,x-4,51,x+3,57,2); ellipse(boss,x-2,52,x+1,56,1)
    dot(boss,x,53,3)
rect(boss,5,52,7,56,2); rect(boss,60,51,62,56,2)
# Small rear exhaust stack and exposed cable add asymmetry to the silhouette.
rect(boss,54,6,59,13,1); rect(boss,55,7,57,12,2); dot(boss,56,7,3)
line(boss,55,5,58,5,1); line(boss,53,6,60,6,1)
line(boss,30,35,33,39,1); line(boss,31,35,34,39,3)
# Furnace core is on the front armor, below the cannon. It uses a different
# palette on complete tiles (16..31,24..39), the engine's weak-point rectangle.
ellipse(boss,16,24,31,39,1)
ellipse(boss,17,25,30,38,2)
ellipse(boss,19,27,28,36,1)
ellipse(boss,20,28,27,35,3)
rect(boss,23,26,24,37,2); rect(boss,18,31,29,32,2)
rect(boss,23,29,24,34,3)

# DREDGER: a harbor gantry with a hanging grab claw, cylindrical pressure pump,
# reinforced elbow plumbing and two large dock stabilizers. The horizontal
# crane crown distinguishes this unit from IRONMAW's low tracked silhouette.
dredger=canvas(64,64)
# Angular braced gantry beam and vertical counterweighted tower.
rect(dredger,5,3,53,10,1); rect(dredger,6,4,52,5,3)
rect(dredger,6,9,52,9,2)
for x in range(7,49,8):
    line(dredger,x,8,x+3,5,2); line(dredger,x+3,5,x+6,8,2)
rect(dredger,44,10,52,31,1); rect(dredger,45,11,50,30,2)
line(dredger,46,11,49,29,1); line(dredger,49,11,46,29,3)
rect(dredger,53,7,61,16,1); rect(dredger,54,8,60,15,2)
rect(dredger,54,8,60,9,3); line(dredger,57,10,57,14,1)
# Two-pixel hoist cable with a block and a separated, recognizably open claw.
line(dredger,8,10,8,21,2); line(dredger,9,10,9,21,1)
rect(dredger,5,20,12,24,1); rect(dredger,6,21,11,22,3)
line(dredger,5,23,1,27,1); line(dredger,6,24,2,28,2)
line(dredger,1,27,4,30,1); line(dredger,2,28,4,29,3)
line(dredger,12,23,15,27,1); line(dredger,11,24,14,28,2)
line(dredger,15,27,12,30,1); line(dredger,14,28,12,29,3)
# Bulky pump pressure vessel and capped rear casing.
rect(dredger,32,21,53,45,1); rect(dredger,33,22,51,44,2)
line(dredger,34,22,49,22,3); line(dredger,48,24,48,42,1)
ellipse(dredger,13,19,44,47,1); ellipse(dredger,15,20,41,45,2)
line(dredger,21,20,35,20,3); line(dredger,35,21,39,24,3)
for x,y in [(17,23),(36,23),(14,33),(38,33),(17,42),(35,42)]:
    dot(dredger,x,y,1); dot(dredger,x+1,y,3)
for y in [27,31,35,39]:
    line(dredger,36,y,44,y,1); line(dredger,37,y+1,43,y+1,3)
# Thick elbow and horizontal pressure nozzle below the weak point corridor.
rect(dredger,48,29,60,37,1); rect(dredger,49,30,59,35,2)
line(dredger,50,30,58,30,3)
rect(dredger,54,34,60,50,1); rect(dredger,55,35,59,49,2)
line(dredger,55,36,55,47,3); rect(dredger,53,41,61,44,1)
rect(dredger,0,41,17,46,1); rect(dredger,1,42,16,44,2)
line(dredger,3,42,14,42,3); rect(dredger,0,41,2,46,1)
rect(dredger,6,41,7,46,1)
# Deck lip, large stabilizer feet, and contrasting triangular bracing.
rect(dredger,9,47,62,53,1); rect(dredger,10,48,61,51,2)
line(dredger,10,48,61,48,3)
for x in range(12,59,7):
    line(dredger,x,51,x+2,49,1); dot(dredger,x+3,50,3)
for x in [12,43]:
    rect(dredger,x,53,x+14,60,1); rect(dredger,x+1,54,x+13,57,2)
    line(dredger,x+1,54,x+13,54,3); rect(dredger,x-2,59,x+16,62,1)
    line(dredger,x-1,60,x+15,60,3); line(dredger,x+3,58,x+6,55,1)
    line(dredger,x+7,55,x+10,58,3)
# Concentric cyan pressure-eye with a diagonal impeller and bright center.
ellipse(dredger,16,24,31,39,1); ellipse(dredger,17,25,30,38,2)
ellipse(dredger,19,27,28,36,1); ellipse(dredger,20,28,27,35,3)
line(dredger,20,28,27,35,2); line(dredger,20,35,27,28,2)
rect(dredger,22,30,25,33,3); dot(dredger,23,31,2)

# NULLCORE: vertical command reactor, separate terminal arm and a containment
# column behind its exposed red crystal. The tall ribbed shaft, antenna crown
# and rectangular energy conduits form a different silhouette from both tanks.
nullcore=canvas(64,64)
# Narrow antenna crown and the enormous ribbed containment column.
rect(nullcore,42,0,46,3,1); rect(nullcore,43,0,44,2,3)
rect(nullcore,34,3,56,8,1); rect(nullcore,35,4,55,6,2)
line(nullcore,36,4,54,4,3)
rect(nullcore,38,8,52,55,1); rect(nullcore,39,9,51,54,2)
line(nullcore,40,9,40,53,3); line(nullcore,48,10,48,52,1)
for y in range(11,52,6):
    rect(nullcore,36,y,54,y+2,1); line(nullcore,37,y,53,y,3)
# Backward-facing command fins and cooling fins extend behind the shaft.
for y in [15,23,31,39]:
    rect(nullcore,53,y,61,y+2,1); line(nullcore,54,y,60,y,2)
rect(nullcore,59,16,62,42,1); line(nullcore,60,17,60,40,3)
# Upper horizontal conduit, shielded side branch, and lower containment collar.
rect(nullcore,8,13,37,18,1); rect(nullcore,9,14,36,16,2)
line(nullcore,10,14,35,14,3)
rect(nullcore,7,18,13,36,1); rect(nullcore,8,19,11,35,2)
line(nullcore,8,20,8,33,3)
rect(nullcore,6,20,14,23,1); rect(nullcore,6,29,14,32,1)
rect(nullcore,6,44,54,51,1); rect(nullcore,7,45,53,49,2)
line(nullcore,8,45,52,45,3)
for x in [10,18,26,34,42,50]:
    dot(nullcore,x,48,1); dot(nullcore,x+1,48,3)
# Containment housing with sloped corners and tiny control-line details.
rect(nullcore,15,21,36,43,1); rect(nullcore,13,24,38,40,1)
rect(nullcore,15,23,36,41,2); rect(nullcore,14,25,37,39,2)
line(nullcore,17,22,34,22,3); line(nullcore,35,24,35,39,1)
line(nullcore,33,25,33,38,3); line(nullcore,16,42,35,42,3)
# Terminal on a separate cantilevered arm: bright screen and physical buttons.
rect(nullcore,0,31,12,43,1); rect(nullcore,1,32,11,41,2)
rect(nullcore,2,33,10,38,1); rect(nullcore,3,34,9,36,3)
rect(nullcore,3,37,7,37,2); dot(nullcore,3,40,3); dot(nullcore,6,40,1)
dot(nullcore,9,40,3); rect(nullcore,9,42,15,45,1)
line(nullcore,10,42,14,42,3)
# Wide grounded plinth supports the column and leaves a clear left approach.
rect(nullcore,16,52,56,59,1); rect(nullcore,17,53,55,58,2)
line(nullcore,18,53,54,53,3)
for x in [20,32,44,52]:
    rect(nullcore,x,55,x+2,57,1); dot(nullcore,x+1,55,3)
rect(nullcore,12,59,60,63,1); line(nullcore,13,60,59,60,3)
line(nullcore,15,62,58,62,2)
# Tall faceted crystal in the four fixed core tiles. Index3 is the hot center;
# index2 edge facets and index1 border remain readable while palette6 flashes.
rect(nullcore,16,24,31,39,1)
for y in range(25,39):
    half=min(y-24,39-y,6)
    line(nullcore,23-half,y,24+half,y,2)
    if half>1: line(nullcore,23-(half//2),y,24+(half//2),y,3)
line(nullcore,23,26,23,37,3); line(nullcore,25,28,25,35,1)
dot(nullcore,29,25,3); dot(nullcore,18,37,3)

boss_map = []
boss_attrs = []
for ty in range(8):
    for tx in range(8):
        tile_id = 96 + ty*8 + tx
        bg[tile_id] = cut(boss,tx*8,ty*8)
        boss_map.append(tile_id)
        boss_attrs.append(6 if tx in (2,3) and ty in (3,4) else 5)

def boss_tiles(p):
    return sum((encode_tile(cut(p,x*8,y*8)) for y in range(8) for x in range(8)), [])


dredger_bytes=boss_tiles(dredger)
nullcore_bytes=boss_tiles(nullcore)
dredger_attrs=boss_attrs[:]
nullcore_attrs=boss_attrs[:]


def bgr15(rgb):
    r,g,b=rgb
    return (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)


# Native HUD marks: health is a shape, weapons are silhouettes, boss HP is a
# continuous 96-pixel instrument. The spare atlas range is stable across stages.
UI_TILES = {'HP_FULL':160, 'HP_EMPTY':161, 'PISTOL':162, 'MG':164,
            'ROCKET':166, 'INFINITY':168, 'BAR_EMPTY':169, 'SCORE_0':178,
            'LABEL_A':188}
for filled in (False, True):
    p = canvas()
    for y, (left, right) in enumerate([(3,4),(2,5),(1,6),(1,6),(1,6),(2,5),(3,4)], 1):
        for x in range(left, right+1):
            edge = x in (left,right) or y in (1,7)
            p[y][x] = (3 if y<3 else 2) if filled else (1 if edge else 0)
    bg[160 if filled else 161] = p
for tile, kind in [(162,'pistol'),(164,'mg'),(166,'rocket')]:
    p = canvas(16,8)
    if kind == 'pistol':
        rect(p,3,2,13,3,2);rect(p,3,4,7,4,2);rect(p,4,5,6,6,2)
        line(p,4,2,12,2,3)
    elif kind == 'mg':
        rect(p,1,3,14,4,2);rect(p,4,2,8,2,2)
        rect(p,1,4,3,5,2);rect(p,6,5,8,6,2);rect(p,10,5,11,6,2)
        line(p,5,2,8,2,3)
    else:
        rect(p,2,3,13,4,2);dot(p,14,3,3)
        rect(p,3,2,5,5,2);rect(p,7,5,8,6,2);line(p,6,3,12,3,3)
    bg[tile], bg[tile+1] = cut(p,0,0), cut(p,8,0)
bg[168] = ascii_art(['........','........','.gg..gg.','g..gg..g',
                     'g..gg..g','.gg..gg.','........','........'])
for fill in range(9):
    p = canvas()
    line(p,0,1,7,1,1);line(p,0,6,7,6,1)
    if fill:rect(p,0,2,fill-1,5,2)
    bg[169+fill] = p
for i in range(10):
    bg[178+i] = [[1 if c else 0 for c in row] for row in bg[27+i]]
for i in range(26):
    bg[188+i] = [[1 if c else 0 for c in row] for row in bg[1+i]]

# Title art is independently authored at 160x144, not resized from the design
# reference. Reserve the existing glyph IDs so software text works on the title.
title = json.loads((OUT/'ui'/'title-native.json').read_text())
assert (title['width'],title['height']) == (160,144)
assert len(title['pixels']) == 144 and all(len(row)==160 for row in title['pixels'])
assert len(title['attributes']) == 18 and all(len(row)==20 for row in title['attributes'])
assert 1 <= len(title['palettes']) <= 8
assert all(len(p)==4 and p[0]==[12,20,32] for p in title['palettes'])
assert all(c in range(4) for row in title['pixels'] for c in row)
assert all(a in range(len(title['palettes'])) for row in title['attributes'] for a in row)
# Six-pixel advance keeps the subordinate title copy optically smaller than
# the wordmark. Bake these static lines into native tiles, without HD scaling.
for text,y in [('MISSION CAMPAIGN',40),('PRESS START',120)]:
    x=(160-(len(text)*6-1))//2
    for ch in text:
        if ch in FONT:
            for yy,row in enumerate(FONT[ch]):
                for xx in range(5):
                    if row & (1 << (4-xx)):dot(title['pixels'],x+xx,y+yy,3)
        x+=6
for y in range(1,7):
    for x in range(1,min(y,7-y)+2):dot(title['pixels'],30+x,120+y,2)
title_patterns = bg[:43]
lookup = {tuple(c for row in p for c in row):i for i,p in enumerate(title_patterns)}
title_map=[]
for ty in range(18):
    for tx in range(20):
        p=cut(title['pixels'],tx*8,ty*8)
        key=tuple(c for row in p for c in row)
        if key not in lookup:
            lookup[key]=len(title_patterns);title_patterns.append(p)
        title_map.append(lookup[key])
assert len(title_patterns)<=255, f'Title requires {len(title_patterns)} tiles; limit 255'
title_bytes=sum((encode_tile(p) for p in title_patterns),[])
title_attrs=sum(title['attributes'],[])

bg_bytes = sum((encode_tile(p) for p in bg), [])
sprite_bytes = []
for p in packed_images:
    # 8x16 OBJ tile pairs: left upper/lower, then right upper/lower.
    for x,y in [(0,0),(0,8),(8,0),(8,8)]:
        sprite_bytes.extend(encode_tile(cut(p,x,y)))


def c_array(name, ctype, values, hexwidth=2):
    lines = [f'const {ctype} {name}[{len(values)}] = {{']
    for offset in range(0,len(values),16):
        lines.append('    '+', '.join(f'0x{v:0{hexwidth}X}' for v in values[offset:offset+16])+',')
    return '\n'.join(lines+['};',''])


source = '/* Generated by tools/generate_assets.py: original BRASSHOUND art. */\n#include "assets.h"\n\n'
source += c_array('bg_tiles','unsigned char',bg_bytes)
source += c_array('sprite_tiles','unsigned char',sprite_bytes)
source += c_array('bg_palettes','uint16_t',[bgr15(c) for p in BG_COLORS for c in p],4)
source += c_array('sprite_palettes','uint16_t',[bgr15(c) for p in OBJ_COLORS for c in p],4)
source += c_array('ironmaw_map','unsigned char',boss_map)
source += c_array('ironmaw_attrs','unsigned char',boss_attrs)
source += c_array('dredger_tiles','uint8_t',dredger_bytes)
source += c_array('nullcore_tiles','uint8_t',nullcore_bytes)
source += c_array('dredger_attrs','uint8_t',dredger_attrs)
source += c_array('nullcore_attrs','uint8_t',nullcore_attrs)
source += c_array('tidebreak_palettes','uint16_t',[bgr15(c) for p in TIDEBREAK_COLORS for c in p],4)
source += c_array('blackout_palettes','uint16_t',[bgr15(c) for p in BLACKOUT_COLORS for c in p],4)
source += c_array('title_tiles','uint8_t',title_bytes)
source += c_array('title_map','uint8_t',title_map)
source += c_array('title_attrs','uint8_t',title_attrs)
source += c_array('title_palettes','uint16_t',[bgr15(c) for p in title['palettes'] for c in p],4)
(ROOT/'src'/'assets.c').write_text(source)

header = '''#ifndef BRASSHOUND_ASSETS_H
#define BRASSHOUND_ASSETS_H
#include <stdint.h>

#define BG_TILES_COUNT 214u
#define SPRITE_TILES_COUNT 128u
#define TILE_BLANK 0u
#define TILE_SKY 0u
#define TILE_FONT_A 1u
#define TILE_FONT_0 27u
#define TILE_DASH 37u
#define TILE_COLON 38u
#define TILE_HEART 39u
#define TILE_DOT 40u
#define TILE_SLASH 41u
#define TILE_EXCLAMATION 42u
'''
for name,index in TILES.items(): header += f'#define TILE_{name} {index}u\n'
for name,index in UI_TILES.items(): header += f'#define TILE_UI_{name} {index}u\n'
header += f'#define TITLE_TILES_COUNT {len(title_patterns)}u\n'
header += f'#define TITLE_PALETTES_COUNT {len(title["palettes"])}u\n'
header += '''
#define IRONMAW_TILE_START 96u
#define BOSS_TILE_START 96u
#define BOSS_TILES_COUNT 64u
#define SPRITE_FRAME_TILES 4u
#define ROOK_FEET_IDLE 100u
#define ROOK_FEET_RUN 104u
#define ROOK_FEET_PASS 108u
#define ROOK_FEET_JUMP 112u
#define ROOK_RUN_C 116u
#define ROOK_RUN_D 120u
#define ROOK_SHOOT 124u
#define SPRITE_ROOK_IDLE 0u
#define SPRITE_ROOK_RUN1 1u
#define SPRITE_ROOK_RUN2 2u
#define SPRITE_ROOK_JUMP 3u
#define SPRITE_ROOK_CROUCH 4u
#define SPRITE_ROOK_HURT 5u
#define SPRITE_ROOK_DEATH 6u
#define SPRITE_ROOK_AIM 7u
#define SPRITE_INFANTRY1 8u
#define SPRITE_INFANTRY2 9u
#define SPRITE_TURRET 10u
#define SPRITE_DRONE1 11u
#define SPRITE_DRONE2 12u
#define SPRITE_CRATE 13u
#define SPRITE_PICKUP_MG 14u
#define SPRITE_PICKUP_ROCKET 15u
#define SPRITE_PICKUP_HEAL 16u
#define SPRITE_EXPLOSION1 17u
#define SPRITE_EXPLOSION2 18u
#define SPRITE_EXPLOSION3 19u
#define SPRITE_BULLET_PISTOL 20u
#define SPRITE_BULLET_MG 21u
#define SPRITE_BULLET_ROCKET 22u
#define SPRITE_BULLET_ENEMY 23u
#define SPRITE_MUZZLE 24u

/* Frame tile = frame * 4, left pair at +0, right pair at +2.
 * Sprite palette index zero is transparent; BG font ink is index three.
 * Palette themes: sky/building/rust/warning/machinery/boss/core/UI.
 */
extern const unsigned char bg_tiles[BG_TILES_COUNT * 16u];
extern const unsigned char sprite_tiles[SPRITE_TILES_COUNT * 16u];
extern const uint16_t bg_palettes[32];
extern const uint16_t sprite_palettes[32];
extern const unsigned char ironmaw_map[64];
extern const unsigned char ironmaw_attrs[64];
/* Missions reload only the shared 96..159 boss tile range. Core is x16..31,
 * y24..39 relative to the 64x64 composition, at BG palette six.
 */
extern const uint8_t dredger_tiles[1024];
extern const uint8_t nullcore_tiles[1024];
extern const uint8_t dredger_attrs[64];
extern const uint8_t nullcore_attrs[64];
extern const uint16_t tidebreak_palettes[32];
extern const uint16_t blackout_palettes[32];
/* Title patterns replace the BG atlas only while the title is visible. */
extern const uint8_t title_tiles[TITLE_TILES_COUNT * 16u];
extern const uint8_t title_map[360];
extern const uint8_t title_attrs[360];
extern const uint16_t title_palettes[TITLE_PALETTES_COUNT * 4u];
#endif
'''
(ROOT/'include'/'assets.h').write_text(header)

# Export the exact indexed source as readable JSON, plus unfiltered PNGs.
(OUT/'source_art.json').write_text(json.dumps({
    'format':'BRASSHOUND original indexed art; . transparent/dark, o=1 s=2 g=3',
    'tile_order':'OBJ left top,left bottom,right top,right bottom',
    'bg_palettes_rgb':BG_COLORS,'sprite_palettes_rgb':OBJ_COLORS,
    'tidebreak_palettes_rgb':TIDEBREAK_COLORS,'blackout_palettes_rgb':BLACKOUT_COLORS,
    'environment_ids':TILES,
    'ui_ids':UI_TILES,
    'ui_tiles':[[''.join('.osg'[c] for c in row) for row in p] for p in bg[160:]],
    'sprites':{name:[''.join('.osg'[c] for c in row) for row in p] for name,p in zip(preview_names,preview_images)},
    'rook_packing':{'upper_rows':16,'visible_lower_rows':8,
                    'feet_tiles':[100,104,108,112],'extra_top_tiles':[116,120,124],
                    'run_c_d_lower_flip':True},
    'ironmaw':[''.join('.osg'[c] for c in row) for row in boss],
    'dredger':[''.join('.osg'[c] for c in row) for row in dredger],
    'nullcore':[''.join('.osg'[c] for c in row) for row in nullcore],
},indent=2)+'\n')

def label(dst, text, x, y, color=(232,226,195)):
    for ch in text:
        if ch in FONT:
            for yy,bits in enumerate(FONT[ch]):
                for xx in range(5):
                    if bits & (1<<(4-xx)):
                        if 0<=y+yy<len(dst) and 0<=x+xx<len(dst[0]): dst[y+yy][x+xx]=color
        x+=6


sheet = [[(12,20,32)]*520 for _ in range(6*128+28)]
label(sheet,'ROOK 16 X 24   ACTORS 16 X 16   THREE VISIBLE COLORS',8,8)
for i,(p,name,pal) in enumerate(zip(preview_images,preview_names,preview_pal_ids)):
    x,y=(i%5)*104+8,(i//5)*128+27
    # Checker shows transparency without altering the underlying source.
    scaled=rgb_image(p,OBJ_COLORS[pal],4)
    for yy,row in enumerate(scaled):
        for xx in range(len(row)):
            if p[yy//4][xx//4]==0: row[xx]=(22,31,42) if ((xx//8+yy//8)%2) else (29,39,49)
    blit(sheet,scaled,x,y); label(sheet,name,x,y+102)
png(OUT/'sprites_contact.png',sheet)

sheet = [[(12,20,32)]*480 for _ in range(((len(TILES)+5)//6)*70+25)]
label(sheet,'OPERATION CINDER ENVIRONMENT   NATIVE 8 X 8 TILE MOTIFS',8,8)
for i,(name,tileid) in enumerate(TILES.items()):
    x,y=(i%6)*80+8,(i//6)*70+26
    blit(sheet,rgb_image(bg[tileid],BG_COLORS[env_palette[tileid]],4),x,y)
    label(sheet,str(tileid)+' '+name[:9],x,y+39)
png(OUT/'environment_contact.png',sheet)

boss_rgb=[[BG_COLORS[boss_attrs[(y//8)*8+x//8]][boss[y][x]] for x in range(64)] for y in range(64)]
png(OUT/'ironmaw.png',[[rgb for rgb in row for _ in range(4)] for row in boss_rgb for _ in range(4)])
boss_contact=[[(10,18,30)]*(3*272) for _ in range(305)]
for i,(name,mission,p,attrs,palettes) in enumerate([
    ('IRONMAW','OPERATION CINDER',boss,boss_attrs,BG_COLORS),
    ('DREDGER','OPERATION TIDEBREAK',dredger,dredger_attrs,TIDEBREAK_COLORS),
    ('NULLCORE','OPERATION BLACKOUT',nullcore,nullcore_attrs,BLACKOUT_COLORS),
]):
    rgb=[[palettes[attrs[(y//8)*8+x//8]][p[y][x]] for x in range(64)] for y in range(64)]
    scaled=[[c for c in row for _ in range(4)] for row in rgb for _ in range(4)]
    if i: png(OUT/(name.lower()+'.png'),scaled)
    blit(boss_contact,scaled,i*272+8,8)
    label(boss_contact,name,i*272+8,275)
    label(boss_contact,mission,i*272+8,289)
png(OUT/'campaign_bosses_contact.png',boss_contact)

# Recolored motif contact sheets demonstrate the palette role contract without
# duplicating environmental tile data in ROM. The map composer owns placement.
for name,palettes in [('tidebreak',TIDEBREAK_COLORS),('blackout',BLACKOUT_COLORS)]:
    contact=[[(12,20,32)]*480 for _ in range(((len(TILES)+5)//6)*70+25)]
    label(contact,name.upper()+' ENVIRONMENT   SHARED NATIVE TILE ATLAS',8,8)
    for i,(tile_name,tileid) in enumerate(TILES.items()):
        x,y=(i%6)*80+8,(i//6)*70+26
        blit(contact,rgb_image(bg[tileid],palettes[env_palette[tileid]],4),x,y)
        label(contact,str(tileid)+' '+tile_name[:9],x,y+39)
    png(OUT/(name+'_environment_contact.png'),contact)
png(OUT/'rook.png',rgb_image(rook_full[0],OBJ_COLORS[0],8))
png(OUT/'font.png',rgb_image([sum((bg[i][y] for i in range(1,43)),[]) for y in range(8)],BG_COLORS[7],2))

# A 160x144 illustrative composition uses exactly the exported tiles/palettes.
# This is an art preview; it is deliberately not presented as an emulator capture.
scene=[[BG_COLORS[0][0]]*160 for _ in range(144)]
def scene_tile(tileid,x,y,pal): blit(scene,rgb_image(bg[tileid],BG_COLORS[pal]),x,y)
for tx in range(20):
    for ty in range(3,16):
        if tx in (1,2,3,4,8,9,10,11,16,17,18) and ty>5:
            scene_tile(57,tx*8,ty*8,0)
    if tx%4==1: scene_tile(58,tx*8,40,0)
    scene_tile(48,tx*8,120,3)
for tx in range(6,15):
    for ty in range(9,16): scene_tile(54,tx*8,ty*8,1)
    scene_tile(68,tx*8,64,3)
for tx in [7,10,13]:
    scene_tile(56,tx*8,80,2); scene_tile(55,tx*8,96,1)
for tx in range(2,7): scene_tile(52,tx*8,96,4)
for tx in [2,6]:
    for ty in range(13,16): scene_tile(84,tx*8,ty*8,4)
for tx in [0,1,2]: scene_tile(61,tx*8,72,4)
for tx in [13,14,15]: scene_tile(60,tx*8,112,2)
for index,x,y in [(0,32,96),(8,102,104),(11,117,45),(13,65,104),(14,52,75)]:
    for yy,row in enumerate(preview_images[index]):
        for xx,c in enumerate(row):
            if c: dot(scene,x+xx,y+yy,OBJ_COLORS[sprite_pal_ids[index]][c])
rect(scene,0,128,159,143,BG_COLORS[7][0])
label(scene,'ROOK',2,131); label(scene,'CINDER',85,131)
for x in [33,41,49]:
    for yy,row in enumerate(bg[39]):
        for xx,c in enumerate(row):
            if c: dot(scene,x+xx,131+yy,BG_COLORS[7][2])
png(OUT/'operation_cinder_art_preview.png',[[c for c in row for _ in range(3)] for row in scene for _ in range(3)])

(OUT/'PROVENANCE.md').write_text(f'''# BRASSHOUND asset provenance

All graphics in this directory and `src/assets.c` are original BRASSHOUND art
authored specifically for this project. No visual assets, sprite sheets, fonts,
music, sound samples, level layouts or character designs from another game were
imported or traced.

The editable source is `tools/generate_assets.py`. `source_art.json` preserves
the indexed sprite drawings, campaign palette colors and boss drawings in a portable,
human-readable format. `ui/title-recipe.py` independently authors the native
160x144 title, saved in `ui/title-native.json`. Run `make assets` to reproduce
the art, C tile arrays, header and PNG previews using the Python standard library.

The selected image-generation concept is preserved as `ui/selected-concept.png`
for composition reference only. It is never resized, sampled or packed into the
ROM. Its ROOK/doorway composition and wordmark are redrawn on the native grid;
the real cartridge uses four-color tile palettes and authored 2bpp patterns.

The stage asset review replaces disconnected distant roofs with continuous
factory silhouettes, refines metal walls/containers, and uses spare tile IDs
43..47 for water, open shafts and panel seams. Stage BG palettes 0..6 share
their darkest color to avoid opaque tile padding appearing as dark rectangles.
Supplies are metal field cases with rifle/missile stencils; medical cases use
the existing cyan OBJ palette and a cross. No additional tiles, palettes, sprite
slots or collision/map changes are required by these refinements.

The player is ROOK, identified by a brass crested helmet, dark visor, short scarf
and square backpack. Machine sentries, tripod turret, paired-rotor drone and
IRONMAW's warning bumper / recessed cannon / furnace core are bespoke designs.
DREDGER combines a harbor gantry, grab claw, pressure vessel and stabilizer feet.
NULLCORE combines a ribbed command column, containment crystal and terminal arm.
Both new bosses and the Tidebreak / Blackout palettes are authored here from
pixel primitives and indexed drawings; no imported visual references are used.

Art is native 2bpp: background tiles are 8x8. Standing ROOK frames are 16x24,
assembled from four 8x16 hardware sprites with transparent foot padding.
Crouch/death and other actors remain 16x16, using two hardware sprites.
Four running phases reuse four lower patterns; recoil has its own upper pose.
The visible foot anchor stays at the original ground/platform level.
Each actor uses three visible colors and transparency. Collision keeps the
original forgiving torso/leg region; taller helmet pixels do not add damage area.
Palette values in C are quantized to the Game Boy Color RGB555 format. Each core
uses its own background palette on four full tiles at local x16..31 / y24..39;
no scanline tricks are used. All three bosses reuse background IDs 96..159;
mission loading replaces those 64 tile patterns and their palette values.

The art previews and contact sheets are illustrative compositions, not emulator
screenshots. Gameplay uses {len(bg)} BG tiles and 128 OBJ tiles. HUD tiles 160..213
provide three health pips, three weapon silhouettes, infinity, a 96px continuous
boss bar and dim secondary text. The HUD remains two tile rows at screen y128.
The title uses {len(title_patterns)} deduplicated BG patterns, two 360-byte maps
and four RGB555 palettes. It replaces only the BG atlas while visible; every
mission restores world/HUD patterns before reloading its boss. Actor patterns
in VRAM 0x8000..0x87FF remain intact. Total graphics payload is
{len(bg_bytes)+len(sprite_bytes)+2048+256+256+len(title_bytes)+720+len(title['palettes'])*8:,} bytes.
''')

assert len(bg_bytes)==214*16
assert len(sprite_bytes)==128*16
assert len(sprite_bytes)<=0x8800-0x8000
assert all(len(p)==24 for i,p in enumerate(rook_full) if i not in (4,6))
assert all(all(c==0 for c in row) for p in rook_feet for row in p[8:])
assert all(len(p)==16 and all(len(r)==16 for r in p) for p in packed_images)
assert all(0<=c<=3 for p in bg+packed_images+preview_images+[dredger,nullcore] for r in p for c in r)
assert all(all(c==0 for c in row[8:]) for p in sprite_images[23:] for row in p)
assert len(boss_map)==len(boss_attrs)==64
assert boss_map==list(range(96,160))
assert len(dredger_bytes)==len(nullcore_bytes)==1024
assert len(dredger_attrs)==len(nullcore_attrs)==64
assert [i for i,a in enumerate(boss_attrs) if a==6]==[26,27,34,35]
assert dredger_attrs==nullcore_attrs==boss_attrs
assert all(len(p)==8 and all(len(colors)==4 and all(len(rgb)==3 for rgb in colors) for colors in p)
           for p in [BG_COLORS,TIDEBREAK_COLORS,BLACKOUT_COLORS])
assert all(all(p[0]==palettes[0][0] for p in palettes[:7])
           for palettes in [BG_COLORS,TIDEBREAK_COLORS,BLACKOUT_COLORS])
assert all(any(c==3 for row in p[24:40] for c in row[16:32]) for p in [boss,dredger,nullcore])
print(f'Generated 214 gameplay BG tiles, 128 OBJ tiles, {len(title_patterns)} title BG tiles, three campaign bosses and native PNG previews.')
