# BRASSHOUND — campaign design

## Throughline

ROOK disables BLACKFORGE's network in three continuous missions. CINDER clears
the occupied city; TIDEBREAK shuts down the harbor's automated pumps and weapons;
BLACKOUT destroys the command reactor. A short result screen connects missions
without dialogue sequences. A advances; the final result replays the campaign.

Scores and inventory carry between missions. Mission entry restores three HP
and supplies at least 50 MG rounds/four rockets. Each mission records its entry
inventory and score so an early death retries its own beginning. Every boss has
a checkpoint with three HP, 100 MG rounds and eight rockets. No saves persist
after returning to title or powering off.

## Mission layouts

| Mission | Sections / local world coordinates | Traversal and combat |
|---|---|---|
| CINDER — 3456 px | Ash Quarter 0–959; Furnace Street 960–1727; Blackforge Gate 1728–3295; arena 3296–3455 | Original introductory progression, 12 platforms, four pits, two vents; checkpoint 3200 |
| TIDEBREAK — 2816 px | Dock Apron 0–863; Canal Bridges 864–1791; Pump Station 1792–2655; arena 2656–2815 | Harbor water gaps, 11 suspended platforms, four pits, three vents, elevated turret/infantry; checkpoint 2560 |
| BLACKOUT — 3200 px | Cooling Tunnels 0–959; Induction Hall 960–2111; Command Vault 2112–3039; arena 3040–3199 | Enclosed reactor, 13 platforms, four pits, three vents and denser drone/ground combinations; checkpoint 2944 |

Enemy, pickup, platform, gap and vent placement is authored in `src/missions.c`.
The active slots remain capped at three encounters, eight friendly shots and five
hostile shots. Elevated defenses change projectile height and reward jumping or
upward aiming. Stages use the same proven controls and enemy archetypes.

Platforms can be jumped through from below and landed on from above. Harbor's
higher canal bridge can be reached from its lower approach platform. Warning caps
mark gap edges. Falling costs one immediate hit and recovers on playable ground,
including while invulnerable. Vents have a safe interval, visible warning and
active interval; their authored positions differ per mission.

## Bosses

All bosses have 48 HP and open weak points in the y80–99 corridor. Grounded fire
hits armor. Jump during an open window and land shots at core height. Cores close
12 updates before firing; all attacks are bounded by the same hostile-shot pool.
At half HP, armor changes color and attacks become more aggressive.

| Boss | Phase 1 | Phase 2 |
|---|---|---|
| IRONMAW | Slow low cannon every 104 updates | Three-height pattern every 78 updates |
| DREDGER | Low cannon every112 updates; alternating cycles drop a depth charge | Cannon, descending diagonal and depth charge every 86 updates |
| NULLCORE | Beam at a height locked12 updates before firing, every 108 updates | Height-locked beam plus low/descending shots every 82 updates |

DREDGER locks a ground target before its falling charge; a red overhead warning
and the slow descent leave time to sidestep. NULLCORE locks a height before firing,
so changing height after the cue avoids its fast horizontal beam. These attacks
reward different movement decisions within the familiar open-core timing loop.

Each boss occupies 64 background tiles and no OAM entries. IRONMAW has a treaded
armored hull; DREDGER has a pump, gantry and dock feet; NULLCORE has a reactor pillar
and conduits. New boss patterns and silhouette changes do not raise sprite limits.

## Architecture

`include/missions.h` defines a mission descriptor: encounter/platform/gap/vent
arrays, section thresholds, labels, checkpoint, arena, boss and health. `load_mission`
caches these values and swaps only the 64 boss tiles and stage RGB555 palettes.
The selected title/HUD adds native UI patterns: gameplay now uses 214 BG / 128
OBJ tiles, while the title temporarily replaces BG with 206 patterns. The
world/HUD atlas is restored at every mission entry. The campaign still fits a 32 KiB
CGB-only ROM, with no mapper, SRAM, floats, allocation or online dependency.

The integer/Q4 movement, three encounter slots, shot/effect pools, circular
background streaming and bottom-window HUD are shared. Each actual scanline
stays under the ten-sprite limit through conservative eight-line occupancy bands.
Equal-priority bullets rotate rendering order while collision remains active.
Rendering commits a complete shadow OAM layout with interrupts masked during
that bounded operation, so VBlank DMA cannot copy a mixed old/new pose.

ROOK is authored at 16x24, with 16x16 crouch/death. Four hardware sprites draw
the taller poses: a 16px upper block plus an 8px lower block padded with eight
transparent rows. Four shared lower blocks and three extra upper blocks use
OBJ IDs100..127. The complete OBJ atlas ends at 0x87FF, before signed BG patterns
at 0x8800. Four running phases alternate stride/passing/other-foot poses; the
recoil upper block preserves the leg cycle. Original jump/ground/platform
physics and torso/leg collision bounds remain. Upward shots originate at the
exposed vertical rifle tip; vertical tracer glyphs reuse each projectile frame's
previously empty right hardware pair, still one OAM slot per projectile.

States: TITLE, PLAY, PAUSED, DYING, GAMEOVER, VICTORY, BOSS_DYING, STAGE_CLEAR.
STAGE_CLEAR leads to the next descriptor; only the third boss leads to VICTORY.
Loads clear old shots, entities and pending VRAM writes. Stage retry reloads its
own boss art/palette and restores the correct checkpoint rather than the city.

Music owns pulse 1/wave 3, prioritized effects own pulse 2/noise 4. The harbor uses
its own A-minor industrial loop; the reactor uses an urgent E-harmonic-minor loop.
Music and simulation pause together. Original assets remain reproducible through
`tools/generate_assets.py` and their editable indexed source.
