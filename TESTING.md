# BRASSHOUND campaign verification

## Build and evidence

- Three continuous missions: CINDER, TIDEBREAK, BLACKOUT.
- GBDK-2020 4.5.0; Python 3.12; PyBoy 2.8.1 actual CGB CPU/APU emulation.
- ROM: `build/BRASSHOUND.gbc`, 32,768 bytes, CGB-only header 0xC0, ROM-only type 0.
- Final hash, case results, ordinary-input campaign clear and sprite peaks are
  recorded in `build/campaign-test-artifacts/report.json`.

```sh
make
make test
python3 tests/verify_rom.py build/BRASSHOUND.gbc
make play
```

Tests preserve native 160×144 PNGs, APU-generated WAV recordings and JSON.
Input-only cases read telemetry to choose ordinary buttons without memory writes.
Isolated fixtures write WRAM only to reach collision/death/boss boundaries and
are labeled in the report. These fixtures do not claim ordinary progression.

The campaign suite checks controls, combat, damage, pickups and weapons, plus
current-mission retry, gap/checkpoint recovery, all three boss attacks/results,
all three checkpoint retries, and one complete input-only campaign.
A separate actual-emulator browser test checks instant START/pause/resume/movement.

## GitHub Actions self-check

`.github/workflows/rom-self-check.yml` runs on main pushes, pull requests and
manual dispatch with Python3.12 and GBDK4.5.0 on Ubuntu24.04. It regenerates
native asset sources, builds the ROM, checks the cartridge header/checksums and
runs the existing18 gameplay cases,4 browser input checks,11 UI checks and6
ROOK checks. Original project logic and assertions remain the validation source.

On success or failure, the run keeps the ROM, debug symbols, JSON reports,
160x144 screenshots and APU recordings as an artifact for 14 days. A missing
report is shown as not produced rather than as a pass. Read the failed step
logs and report traceback before making a fix, then rerun the same workflow.
CI does not automatically change source or weaken failed checks.

Header/logo/size/checksum validation and every-frame OAM/scanline occupancy are
mandatory. Boss-transition checks cover clearing old bullets, preserving score
and inventory, resupply, resetting local coordinates/camera/checkpoint, stage
art/palette loads, correct retry mission, final completion and replay from zero.

## Final results — ROOK native asset refinement

- Tested ROM SHA-256: `940e6b886e5576c5aaa2910192939e9b471b5705ba6a71cd3978657540265d63`.
- Header/logo/CGB/size/checksums: PASS; 32,768 bytes, ROM-only, no cartridge RAM.
- All 18 gameplay/campaign cases, four browser quick-tap checks, 11 UI checks
  and six ROOK pose/collision checks: PASS.
- Input-only campaign: 13,492 display frames / **225.89 seconds**,
  mission indices 0→1→2, 0 retries, zero WRAM writes.
- Per-stage traversal/boss time: CINDER 81.62s,
  TIDEBREAK 67.42s, BLACKOUT 72.45s.
- Every-frame OAM peak 15; scanline peak 10;
  0 overflow frames.
- Title/HUD regressions verify all 128 OBJ patterns through mission/title
  transitions; the atlas ends at 0x87FF, before signed BG storage at 0x8800.
- ROOK checks inspect actual hardware OAM for 16x24 geometry/foot anchoring,
  all four running phases, braced fire, vertical muzzle/tracer alignment,
  both directions, crouch, jump/landing, damage and death. The five ordinary
  pose checks use only button inputs. The sixth uses explicitly labeled WRAM
  fixtures for original torso collision, crouch avoidance and lethal damage.
  Screens and GIF are under `build/rook-review/2026-10-15/after/`.
- Three sections and each boss were recaptured through ordinary-input campaign
  progression under `after/stages/`, with zero stage/position/inventory writes.
- Native palette/index assertions pass: 214 gameplay BG, 128 OBJ, 206 title BG
  patterns, three visible sprite colors plus transparency. The ROM remains 32KiB.
- Actual in-app browser Reset/START loads the tested hash; `/health` has no error.
  The saved browser screenshot shows the new ROOK. Console warning/error review
  returned no entries.
- [ROOK review](docs/rook-review.md) and [stage review](docs/stage-asset-review.md)
  record the published visual review.

The campaign bot uses an informed route. Collision/UI boundary fixtures write
WRAM and are labeled separately. Busy updates can still miss VBlanks; timing is
not a locked60Hz claim. Chromatic hardware remains untested; no cartridge was
flashed. Published evidence is under `docs/verification/`; local historical archives and
large emulator recordings remain under ignored `build/`.

## Manual campaign checks

1. START the campaign. Move, jump with B held, crouch-fire and aim upward. Collect
   MG, use SELECT, collect rockets and empty a weapon to check pistol fallback.
2. Cross CINDER's platforms/pits and defeat IRONMAW. On Mission Complete, press A:
   TIDEBREAK must start with different harbor scenery, local x24, three HP, carried
   score/weapon inventory, entry resupply and a fresh checkpoint state.
3. Reach the lower harbor bridge before its higher span. Fire upward or jump
   against elevated defenders. Watch warning caps on water gaps and vent cues.
   Die before the checkpoint: A must retry TIDEBREAK, not return to CINDER.
4. Reach DREDGER's checkpoint. Sidestep the falling depth-charge target; jump/fire
   at the cyan core when open. Die in either phase and A must retry this boss with
   boss HP48/player HP3/MG100/rockets8. Clear it and A must enter BLACKOUT.
5. Verify reactor scenery and music. Repeat platform/vent and mixed drone defense
   encounters. NULLCORE's scan shot locks a height before firing: change height
   after its cue. At half health confirm the projectile fan.
6. Defeat NULLCORE while shots are in flight. Hostile shots stop, explosions run,
   and Campaign Complete appears. A must reset mission 0, score and inventory.
7. Pause while each boss is active and resume. Inputs, shots, health and timers
   must freeze during pause. Test quick browser/touch taps as well as held keys.

Busy updates may miss VBlanks; no locked 60 Hz claim is made. Native physical
hardware and first-human-playthrough pacing remain manual checks. The original
single-mission build/report/source are preserved under `build/releases/`.

## Physical Chromatic procedure — pending

No physical device was tested or flashed, and no matching Chromatic USB entry
was found in the available USB inventory. The official plugin was not exposed;
plugin search returned no match, so its hardware commands could not be inspected.

Use the [official DevDay quickstart](https://support.modretro.com/en_us/chromatic-devday-edition-quickstart-guid-By1iOlcMg)
for the device/updater/plugin workflow. Its documented developer setup uses the
Chromatic Firmware Updater and the included activation code (Cmd-I on macOS).
The guide supports a live emulator stream for checking display, controls and
audio before cartridge writing. Streaming is not a native cartridge compatibility
verification. Cartridge flashing is a separate action requiring explicit approval.

Once the plugin and device are connected:

1. Select this existing `build/BRASSHOUND.gbc`; use the exposed plugin's documented
   preview/stream workflow to check controls, color readability and sound.
2. Before any cartridge overwrite, confirm the target cartridge and obtain
   explicit user approval. No flash action is authorized by this project setup.
3. After an approved flash, cold-boot the cartridge on the Chromatic, with the
   host/emulator disconnected, and repeat the manual checks above.
4. Record firmware/updater versions, device edition, ROM SHA-256, timing/sprite
   observations, audio results, retry/pause results and a full mission clear.

Native hardware compatibility remains unverified until these checks are performed.
