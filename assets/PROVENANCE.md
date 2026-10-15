# BRASSHOUND asset provenance

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
screenshots. Gameplay uses 214 BG tiles and 128 OBJ tiles. HUD tiles 160..213
provide three health pips, three weapon silhouettes, infinity, a 96px continuous
boss bar and dim secondary text. The HUD remains two tile rows at screen y128.
The title uses 206 deduplicated BG patterns, two 360-byte maps
and four RGB555 palettes. It replaces only the BG atlas while visible; every
mission restores world/HUD patterns before reloading its boss. Actor patterns
in VRAM 0x8000..0x87FF remain intact. Total graphics payload is
12,080 bytes.
