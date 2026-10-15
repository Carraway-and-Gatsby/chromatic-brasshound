#ifndef BRASSHOUND_GAME_H
#define BRASSHOUND_GAME_H
#include <stdint.h>
#define WORLD_WIDTH 3456
#define ARENA_LEFT 3296
#define BOSS_X 3392
#define FLOOR_Y 120
#define MAX_FOES 3
#define MAX_SHOTS 8
#define MAX_HOSTILE 5
enum { TITLE, PLAY, PAUSED, DYING, GAMEOVER, VICTORY, BOSS_DYING, STAGE_CLEAR };
enum { INFANTRY, TURRET, DRONE, CRATE, ITEM_MG, ITEM_ROCKET, ITEM_HEAL };
enum { PISTOL, MACHINEGUN, ROCKET };
typedef struct { int16_t x, y; int8_t dx,dy; uint8_t life,damage,type; } Shot;
typedef struct { int16_t x,home; int8_t y,dir; uint8_t type,hp,timer,hit,active,anim,drop; } Foe;
typedef struct { int16_t x; uint8_t y,life; } Effect;
typedef struct { uint16_t x; uint8_t y,type,drop; } Encounter;
typedef struct { uint16_t x; uint8_t width,y; } Platform;
extern volatile uint8_t game_state, hp, boss_hp, checkpoint, weapon;
extern volatile int16_t player_x, player_y;
extern volatile uint16_t frame;
extern uint16_t ammo[3];
extern Shot shots[MAX_SHOTS], hostile[MAX_HOSTILE];
extern Foe foes[MAX_FOES];
#endif
