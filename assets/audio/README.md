# BRASSHOUND audio source

All music and sound effects were composed for BRASSHOUND. No commercial
game music, samples, recordings, or third-party tracker files are used.
The score and effect source lives in `src/audio.c`, with a public interface
in `include/audio.h`. Playback writes the standard Game Boy APU registers
directly and runs once per game frame. There is no external runtime driver.

Channel ownership is fixed:

| Channel | Owner | Sound |
| --- | --- | --- |
| Pulse 1 | Music | Original melody, 50% duty; quieter 25% dock pulse |
| Pulse 2 | Effects | Reports, slides, pickup arpeggio, interface chirps |
| Wave 3 | Music | Soft triangle bass, half output volume |
| Noise 4 | Effects | Weapon reports, impact, rocket roar, explosion, damage |

Both output sides receive all four channels, so mono speakers retain every
cue. Effects have independent priorities on pulse 2 and noise 4. Loud damage
and explosion cues can finish when lower-priority gunfire is retriggered.
Music never takes an effect channel. Effects never replace the music score.

The six original 32-step scores are:

| Music mode | Name | Harmony and rhythm |
| --- | --- | --- |
| 0 | Silence | Stops the melody and bass; effects remain available |
| 1 | Brasshound signal | E minor; 12 frames per step; spacious title motif |
| 2 | Foundry pursuit | E minor; 7 frames per step; driving repeated motif |
| 3 | Iron jaws | E minor; 6 frames per step; octave pedal and descending roots |
| 4 | Clear skies | C major; 10 frames per step; bright fanfare response |
| 5 | Slipway clock | A minor; 11 frames per step; low, spaced industrial dock pulse |
| 6 | Core countdown | E harmonic minor; 5 frames per step; urgent arpeggios and a rising leading tone |

The title and campaign screens use mode 1. Cinder Foundry uses mode 2,
the dock mission uses mode 5, and the reactor mission uses mode 6. Every
boss uses mode 3; the campaign ending uses mode 4. Dock melody volume is
lower with a slower decay; the reactor melody is brighter and more urgent.
Adding these mission themes leaves the existing four scores and all ten
effects unchanged.

Pitches are integer APU periods for equal temperament with A4 at 440 Hz.
The wave bass is an original 32-sample triangle, encoded as 16 packed bytes.
All phrases loop, and melody notes leave a short gap for clear articulation.

| Sound ID | Constant | Cue | Priority |
| --- | --- | --- | --- |
| 0 | `SFX_PISTOL` | Sharp five-frame pulse and noise report | 1 |
| 1 | `SFX_MG` | Three-frame dry crack, suitable for rapid retriggering | 1 |
| 2 | `SFX_ROCKET` | Twelve-frame falling launch roar | 2 |
| 3 | `SFX_IMPACT` | Four-frame gritty metal noise | 1 |
| 4 | `SFX_EXPLOSION` | Twenty-frame low pulse and noise rumble | 3 |
| 5 | `SFX_DAMAGE` | Twelve-frame descending warning | 4 |
| 6 | `SFX_PICKUP` | Sixteen-frame C5–E5–G5–C6 arpeggio | 2 |
| 7 | `SFX_MENU` | Four-frame high interface click | 2 |
| 8 | `SFX_VICTORY` | Twenty-four-frame G4–C5–E5–G5–C6–E5 fanfare | 3 |
| 9 | `SFX_JUMP` | Eight-frame upward pulse chirp | 1 |

Call `audio_init()` once. Call `audio_tick()` once per approximately 60 Hz
frame, including menu and victory frames. `audio_music(mode)` changes the
score and resets its position; selecting the current mode keeps its place.
`audio_pause(1)` freezes score/effect timers and mutes routing.
`audio_pause(0)` resumes at the stored position and rearticulates active
notes/effects. New effects requested during pause are ignored.

This source works on the Game Boy Color APU and the compatible Chromatic
audio hardware. Wave RAM is only written while the wave DAC is disabled.
