#ifndef BRASSHOUND_MISSIONS_H
#define BRASSHOUND_MISSIONS_H
#include "game.h"
#define MISSION_COUNT 3
typedef struct {
 const Encounter *encounters;
 const Platform *platforms;
 const uint16_t *pits;
 const uint8_t *pit_widths;
 const uint16_t *vents;
 const char *operation;
 const char *section_names[3];
 const char *boss_name;
 uint16_t width, arena_left, boss_x, checkpoint_x, section_b, section_c;
 uint8_t encounter_count, platform_count, pit_count, vent_count, boss_health;
} Mission;
extern const Mission missions[MISSION_COUNT];
extern volatile uint8_t mission_index;
extern const Mission *mission;
#endif
