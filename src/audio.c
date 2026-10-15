#include <gb/gb.h>
#include "audio.h"

#define REST 255u
#define C4 0u
#define D4 2u
#define E4 4u
#define G4 7u
#define A4 9u
#define B4 11u
#define C5 12u
#define D5 14u
#define DS5 15u
#define E5 16u
#define FS5 18u
#define G5 19u
#define A5 21u
#define B5 23u
#define C6 24u

/* Equal-tempered A=440 Hz register values; all six scores are original.
 * An E-minor identity, a spacious dock pulse and a tense reactor response. */
static const uint16_t pitches[25] = {
    1547,1575,1602,1627,1650,1673,1694,1714,1732,1750,1767,1783,
    1798,1812,1825,1837,1849,1860,1871,1881,1890,1899,1907,1915,1923
};
static const uint16_t bass_pitches[12] = {
    1253,1297,1339,1379,1417,1452,1486,1517,1547,1575,1602,1627
};
static const uint8_t scores[6][32] = {
    { E4,REST,B4,E5,G5,E5,D5,B4, A4,REST,E5,A5,G5,E5,D5,A4,
      C5,REST,G5,E5,D5,C5,B4,G4, B4,D5,E5,B4,G4,A4,B4,REST },
    { E5,E5,REST,B4,E5,G5,E5,D5, E5,REST,B4,D5,E5,B4,G4,B4,
      A4,A4,C5,E5,G5,E5,C5,A4, B4,D5,B4,A4,G4,B4,D5,REST },
    { E4,E5,E4,B4,E4,G5,E4,B4, D4,D5,D4,A4,D4,E5,D4,A4,
      C4,C5,C4,G4,C4,E5,C4,G4, B4,REST,B5,A5,G5,E5,D5,B4 },
    { C5,E5,G5,C6,REST,G5,E5,C5, D5,E5,G5,A5,G5,E5,D5,REST,
      C5,E5,G5,C6,B5,G5,E5,G5, A5,G5,E5,D5,C5,REST,C5,REST },
    { A4,REST,E4,A4,C5,REST,B4,A4, G4,REST,D4,G4,B4,REST,A4,G4,
      C5,REST,E5,D5,C5,G4,E4,REST, A4,C5,B4,A4,G4,E4,A4,REST },
    { E5,B4,E5,FS5,G5,E5,B5,FS5, D5,A4,D5,FS5,A5,FS5,E5,D5,
      C5,G4,C5,E5,G5,E5,FS5,E5, B4,DS5,FS5,B5,A5,FS5,DS5,B4 }
};
/* Wave pitch indices start at E2; one bass note accompanies four steps. */
static const uint8_t bass_scores[6][8] = {
    {0,0,5,5,8,8,7,7}, {0,0,0,0,5,5,7,7},
    {0,0,10,10,8,8,7,7}, {8,8,3,3,8,8,5,8},
    {5,5,3,3,8,8,0,5}, {0,7,10,5,8,3,7,7}
};
static const uint8_t tempos[6] = {12,7,6,10,11,5};
static const uint8_t bass_wave[16] = {
    0x89,0xAB,0xCD,0xEF,0xFE,0xDC,0xBA,0x98,
    0x76,0x54,0x32,0x10,0x01,0x23,0x45,0x67
};

typedef struct {
    uint16_t tone;
    int8_t slide;
    uint8_t envelope;
    uint8_t duty;
    uint8_t noise;
    uint8_t noise_envelope;
    uint8_t frames;
    uint8_t priority;
} Effect;

/* Effects may claim either or both effect channels. A lower-priority
 * shot cannot erase a damage cue or an explosion already in progress. */
static const Effect effects[SFX_COUNT] = {
    {1900,-28,0xF1,0x80,0x13,0xF1, 5,1}, /* pistol: sharp report */
    {1770,-20,0xD1,0x40,0x11,0xD1, 3,1}, /* MG: tight dry crack */
    {1560,-18,0xE2,0x80,0x44,0xF2,12,2}, /* rocket: descending roar */
    {   0,  0,0x00,0x00,0x23,0xA1, 4,1}, /* impact: metal grit */
    {1250,-12,0xD2,0xC0,0x56,0xF2,20,3}, /* explosion: low rumble */
    {1640,-32,0xF2,0x40,0x24,0xC2,12,4}, /* damage: falling alarm */
    {1798,  0,0xD1,0x80,0x00,0x00,16,2}, /* pickup: major arpeggio */
    {1881,  0,0xB1,0x80,0x00,0x00, 4,2}, /* menu: short click */
    {1714,  0,0xE2,0x80,0x00,0x00,24,3}, /* victory: six-note fanfare */
    {1430, 25,0xB1,0x40,0x00,0x00, 8,1}  /* jump: upward chirp */
};
static const uint16_t pickup_notes[4] = {1798,1849,1881,1923};
static const uint16_t victory_notes[6] = {1714,1798,1849,1881,1923,1849};

static uint8_t music_mode, music_step, music_delay, is_paused;
static uint8_t tone_id, tone_frames, noise_id, noise_frames;
static uint16_t tone_pitch;

static void tone_write(uint8_t trigger) {
    NR23_REG = (uint8_t)tone_pitch;
    NR24_REG = (uint8_t)(tone_pitch >> 8) | trigger;
}

static void music_note(uint8_t step) {
    uint8_t song = music_mode - 1u;
    uint8_t note = scores[song][step];
    uint16_t pitch;
    if (note == REST) NR12_REG = 0;
    else {
        pitch = pitches[note];
        NR11_REG = (music_mode == MUSIC_DOCKS) ? 0x40 : 0x80;
        NR12_REG = (music_mode == MUSIC_DOCKS) ? 0x72 :
            ((music_mode == MUSIC_BOSS || music_mode == MUSIC_REACTOR) ? 0xA1 : 0x91);
        NR13_REG = (uint8_t)pitch;
        NR14_REG = (uint8_t)(pitch >> 8) | 0x80;
    }
    /* Wave RAM is initialized while its DAC is off, and never touched
     * while playing, so this also works on the original DMG hardware. */
    pitch = bass_pitches[bass_scores[song][step >> 2]];
    NR30_REG = 0x80;
    NR32_REG = 0x40;
    NR33_REG = (uint8_t)pitch;
    NR34_REG = (uint8_t)(pitch >> 8) | 0x80;
}

void audio_init(void) {
    uint8_t i;
    NR52_REG = 0;
    NR52_REG = 0x80;
    NR50_REG = 0x77;
    NR51_REG = 0xFF;
    NR10_REG = 0;
    NR12_REG = NR22_REG = NR42_REG = 0;
    NR30_REG = 0;
    NR31_REG = 0;
    NR41_REG = 0;
    for (i = 0; i != 16u; ++i) AUD3WAVE[i] = bass_wave[i];
    music_mode = music_step = music_delay = is_paused = 0;
    tone_frames = noise_frames = 0;
}

void audio_music(uint8_t mode) {
    if (mode > MUSIC_REACTOR) mode = MUSIC_SILENCE;
    if (mode == music_mode) return;
    music_mode = mode;
    music_step = music_delay = 0;
    NR12_REG = 0;
    NR30_REG = 0;
}

void audio_sfx(uint8_t id) {
    const Effect *effect;
    if (id >= SFX_COUNT || is_paused) return;
    effect = &effects[id];
    if (effect->tone && (!tone_frames ||
            effect->priority >= effects[tone_id].priority)) {
        tone_id = id;
        tone_frames = effect->frames;
        tone_pitch = effect->tone;
        NR21_REG = effect->duty;
        NR22_REG = effect->envelope;
        tone_write(0x80);
    }
    if (effect->noise_envelope && (!noise_frames ||
            effect->priority >= effects[noise_id].priority)) {
        noise_id = id;
        noise_frames = effect->frames;
        NR42_REG = effect->noise_envelope;
        NR43_REG = effect->noise;
        NR44_REG = 0x80;
    }
}

void audio_tick(void) {
    uint8_t elapsed;
    if (is_paused) return;
    if (music_mode) {
        if (!music_delay) {
            music_note(music_step);
            music_step = (music_step + 1u) & 31u;
            music_delay = tempos[music_mode - 1u];
        }
        --music_delay;
        if (music_delay == 1u) { NR12_REG = 0; NR30_REG = 0; }
    }
    if (tone_frames) {
        --tone_frames;
        if (!tone_frames) NR22_REG = 0;
        else {
            elapsed = effects[tone_id].frames - tone_frames;
            if (tone_id == SFX_PICKUP || tone_id == SFX_VICTORY) {
                if (!(elapsed & 3u)) {
                    tone_pitch = (tone_id == SFX_PICKUP) ?
                        pickup_notes[elapsed >> 2] : victory_notes[elapsed >> 2];
                    NR22_REG = effects[tone_id].envelope;
                    tone_write(0x80);
                }
            } else {
                tone_pitch += effects[tone_id].slide;
                tone_write(0);
            }
        }
    }
    if (noise_frames) {
        --noise_frames;
        if (!noise_frames) NR42_REG = 0;
        else if (noise_frames == (effects[noise_id].frames >> 1))
            NR43_REG = effects[noise_id].noise + 0x10u;
    }
}

void audio_pause(uint8_t paused) {
    paused = !!paused;
    if (paused == is_paused) return;
    is_paused = paused;
    if (paused) NR51_REG = 0;
    else {
        /* APU envelopes run independently while muted. Rearticulate the
         * frozen score and effects so a long pause cannot swallow them. */
        if (music_mode && music_delay > 1u)
            music_note((music_step - 1u) & 31u);
        if (tone_frames) {
            NR22_REG = effects[tone_id].envelope;
            tone_write(0x80);
        }
        if (noise_frames) {
            NR42_REG = effects[noise_id].noise_envelope;
            NR44_REG = 0x80;
        }
        NR51_REG = 0xFF;
    }
}
