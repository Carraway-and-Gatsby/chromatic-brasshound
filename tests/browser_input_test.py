#!/usr/bin/env python3
"""Check back-to-back browser input updates against the actual ROM emulator."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web"))
from server import Emulator
from rom_harness import read_symbols


def run(rom):
    symbols = read_symbols(Path(rom).with_suffix(".noi"))
    emulator = Emulator(rom)

    def read(name, width=1):
        with emulator.lock:
            address = symbols[name]
            return int.from_bytes(bytes(emulator.pyboy.memory[address:address+width]), "little")

    def wait(predicate, label, seconds=6):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if emulator.error:
                raise AssertionError(emulator.error)
            if predicate():
                return
            time.sleep(0.005)
        raise AssertionError(f"Timed out waiting for {label}; state={read('game_state')}")

    def instantaneous_tap(button):
        # Exactly the race caused by keydown and keyup HTTP requests landing
        # before the emulator worker next ticks. No intentional hold or wait.
        emulator.set_buttons([button])
        emulator.set_buttons([])

    report = {"emulator": "PyBoy 2.8.1", "rom": str(Path(rom).resolve()),
              "sha256": emulator.rom_sha256, "bytes": emulator.rom_size, "checks": {}}
    try:
        wait(lambda: read("game_state") == 0 and read("frame", 2) >= 5, "title boot")
        instantaneous_tap("start")
        wait(lambda: read("game_state") == 1 and read("play_frames", 2) >= 4, "instant START")
        wait(lambda: read("previous_key") & 128 == 0, "START release")
        report["checks"]["back_to_back_start_enters_game"] = True

        instantaneous_tap("start")
        wait(lambda: read("game_state") == 2, "instant pause")
        wait(lambda: read("previous_key") & 128 == 0, "pause release")
        paused_frame = read("play_frames", 2)
        time.sleep(0.075)
        assert read("play_frames", 2) == paused_frame, "Game continued while paused"
        report["checks"]["back_to_back_start_pauses"] = True

        instantaneous_tap("start")
        wait(lambda: read("game_state") == 1, "instant resume")
        wait(lambda: read("play_frames", 2) > paused_frame, "game resumes")
        wait(lambda: read("previous_key") & 128 == 0, "resume release")
        report["checks"]["back_to_back_start_resumes"] = True

        before = read("player_x", 2)
        instantaneous_tap("right")
        wait(lambda: read("player_x", 2) > before, "instant movement")
        report["checks"]["back_to_back_right_moves_player"] = True
        report["passed"] = True
        return report
    finally:
        emulator.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", default="build/BRASSHOUND.gbc")
    parser.add_argument("--output", default="build/test-artifacts/browser-input-report.json")
    args = parser.parse_args()
    report = run(args.rom)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
