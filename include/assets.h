#ifndef BRASSHOUND_ASSETS_H
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
#define TILE_WATER 43u
#define TILE_VOID 44u
#define TILE_CONTAINER 45u
#define TILE_PANEL_EDGE 46u
#define TILE_PANEL_SEAM 47u
#define TILE_GROUND 48u
#define TILE_GROUND_FILL 49u
#define TILE_WARNING 50u
#define TILE_PLATFORM_LEFT 51u
#define TILE_PLATFORM 52u
#define TILE_PLATFORM_RIGHT 53u
#define TILE_BUILDING 54u
#define TILE_WINDOW 55u
#define TILE_WINDOW_LIT 56u
#define TILE_SKYLINE 57u
#define TILE_SKYLINE_TOP 58u
#define TILE_SMOKE 59u
#define TILE_DEBRIS 60u
#define TILE_PIPE 61u
#define TILE_PIPE_VERTICAL 62u
#define TILE_PIPE_ELBOW 63u
#define TILE_CRATE 64u
#define TILE_CRATE_RUST 65u
#define TILE_WALL_BROKEN 66u
#define TILE_VENT 67u
#define TILE_HAZARD_STRIPE 68u
#define TILE_GRATE 69u
#define TILE_METAL_FLOOR 70u
#define TILE_LAMP 71u
#define TILE_WIRE 72u
#define TILE_CHEVRON 73u
#define TILE_HAZARD 74u
#define TILE_DOOR 75u
#define TILE_DOOR_TOP 76u
#define TILE_SIGN_B 77u
#define TILE_SIGN_F 78u
#define TILE_BARREL 79u
#define TILE_ROAD 80u
#define TILE_CHIMNEY 81u
#define TILE_SKYLINE_DETAIL 82u
#define TILE_RAILING 83u
#define TILE_SUPPORT 84u
#define TILE_MACHINERY 85u
#define TILE_EMBER 86u
#define TILE_SCAFFOLD 87u
#define TILE_PIPE_BROKEN 88u
#define TILE_BOLT_PANEL 89u
#define TILE_STEEL 90u
#define TILE_GEAR 91u
#define TILE_CONVEYOR 92u
#define TILE_CRACK 93u
#define TILE_CYAN_EDGE 94u
#define TILE_DARK_STEEL 95u
#define TILE_UI_HP_FULL 160u
#define TILE_UI_HP_EMPTY 161u
#define TILE_UI_PISTOL 162u
#define TILE_UI_MG 164u
#define TILE_UI_ROCKET 166u
#define TILE_UI_INFINITY 168u
#define TILE_UI_BAR_EMPTY 169u
#define TILE_UI_SCORE_0 178u
#define TILE_UI_LABEL_A 188u
#define TITLE_TILES_COUNT 206u
#define TITLE_PALETTES_COUNT 4u

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
