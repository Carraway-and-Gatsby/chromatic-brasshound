#ifndef BRASSHOUND_AUDIO_H
#define BRASSHOUND_AUDIO_H

#include <stdint.h>

enum {
    SFX_PISTOL = 0,
    SFX_MG,
    SFX_ROCKET,
    SFX_IMPACT,
    SFX_EXPLOSION,
    SFX_DAMAGE,
    SFX_PICKUP,
    SFX_MENU,
    SFX_VICTORY,
    SFX_JUMP,
    SFX_COUNT
};

enum {
    MUSIC_SILENCE = 0,
    MUSIC_TITLE,
    MUSIC_LEVEL,
    MUSIC_BOSS,
    MUSIC_VICTORY,
    MUSIC_DOCKS,
    MUSIC_REACTOR
};

/* Call once, then audio_tick() once per game frame (approximately 60 Hz).
 * Channel 1 and wave channel 3 belong to music; channel 2 and noise 4
 * belong to effects. No interrupt handler or external driver is required. */
void audio_init(void);
void audio_tick(void);
void audio_sfx(uint8_t id);
void audio_music(uint8_t mode);
/* Freezes score/effect time, mutes output, then resumes the retained state. */
void audio_pause(uint8_t paused);

#endif
