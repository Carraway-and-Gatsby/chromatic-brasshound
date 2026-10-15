"""Actual CGB CPU emulation plus symbol-aware testing helpers.

Memory writes are supported for isolated fixtures and must be identified as
fixture-assisted in test reports. Ordinary input tests use press/release only.
"""
import io
import json
import re
import wave
from pathlib import Path

import numpy as np
from pyboy import PyBoy


def read_symbols(path):
    symbols = {}
    for line in Path(path).read_text().splitlines():
        match = re.match(r"DEF\s+(\S+)\s+0x([0-9A-Fa-f]+)", line)
        if match:
            symbols[match[1].lstrip("_")] = int(match[2], 16) & 0xFFFF
    return symbols


class Harness:
    def __init__(self, rom="build/BRASSHOUND.gbc", symbols=None, output="build/test-artifacts"):
        self.rom = Path(rom)
        self.symbols = read_symbols(symbols or self.rom.with_suffix(".noi"))
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.pyboy = PyBoy(str(self.rom), window="null", cgb=True,
                          sound_emulated=True, sound_sample_rate=24000,
                          ram_file=io.BytesIO(), rtc_file=io.BytesIO(), log_level="ERROR")
        self.pyboy.set_emulation_speed(0)
        self.audio = []
        self.emulated_frames = 0
        self.fixture_writes = []
        self.peak_oam = 0
        self.peak_scanline = 0
        self.sprite_overflow_frames = 0

    def address(self, name, offset=0):
        return self.symbols[name] + offset

    def read(self, name, width=1, signed=False, offset=0):
        address = self.address(name, offset)
        data = bytes(self.pyboy.memory[address:address + width])
        return int.from_bytes(data, "little", signed=signed)

    def write(self, name, value, width=1, signed=False, offset=0):
        address = self.address(name, offset)
        data = int(value).to_bytes(width, "little", signed=signed)
        for i, byte in enumerate(data):
            self.pyboy.memory[address + i] = byte
        self.fixture_writes.append({"symbol": name, "offset": offset, "value": value, "width": width})

    def press(self, *buttons):
        for button in buttons:
            self.pyboy.button_press(button)

    def release(self, *buttons):
        for button in buttons:
            self.pyboy.button_release(button)

    def release_all(self):
        self.release("left", "right", "up", "down", "a", "b", "start", "select")

    def tick(self, frames=1, capture_audio=True):
        for _ in range(frames):
            assert self.pyboy.tick(1, True, capture_audio), "Emulation stopped unexpectedly"
            self.emulated_frames += 1
            if self.pyboy.memory[0xFF40] & 2:
                usage = self.sprite_usage()
                self.peak_oam = max(self.peak_oam, usage["active_oam"])
                self.peak_scanline = max(self.peak_scanline, usage["peak_per_scanline"])
                if usage["overloaded_scanlines"]:
                    self.sprite_overflow_frames += 1
            if capture_audio:
                self.audio.append(self.pyboy.sound.ndarray.copy())

    def tap(self, button, frames=3):
        self.press(button)
        self.tick(frames)
        self.release(button)
        self.tick(frames)

    def boot(self, frames=180):
        self.tick(frames)

    def wait(self, predicate, timeout=300, label="condition"):
        for _ in range(timeout):
            if predicate():
                return
            self.tick()
        raise AssertionError(f"Timed out waiting for {label}; {self.snapshot()}")

    def logical(self, frames, timeout=None):
        before = self.read("frame", 2)
        self.wait(lambda: ((self.read("frame", 2) - before) & 0xFFFF) >= frames,
                  timeout or max(300, frames * 4), f"{frames} logical frames")

    def screenshot(self, name):
        path = self.output / (name + ".png")
        self.pyboy.screen.image.save(path)
        return str(path.resolve())

    def snapshot(self):
        widths = {"player_x": 2, "player_y": 2, "camera_x": 2, "frame": 2,
                  "score": 2, "boss_timer": 1, "boss_hp": 1}
        names = ("game_state", "mission_index", "player_x", "player_y", "camera_x", "hp", "frame", "weapon",
                 "checkpoint", "boss_hp", "boss_active", "boss_timer", "score", "invuln")
        return {name: self.read(name, widths.get(name, 1), signed=name in ("player_x", "player_y"))
                for name in names if name in self.symbols}

    def sprite_usage(self):
        """Count OAM sprites eligible for each scanline, including offscreen X.

        The GBC ten-sprite selection limit checks Y first; this catches objects
        hidden incorrectly by changing X only. BG tiles do not consume OAM.
        """
        height = 16 if self.pyboy.memory[0xFF40] & 4 else 8
        scanlines = [0] * 144
        active = 0
        for index in range(40):
            y = self.pyboy.memory[0xFE00 + 4 * index] - 16
            if y + height > 0 and y < 144:
                active += 1
                for row in range(max(0, y), min(144, y + height)):
                    scanlines[row] += 1
        return {"active_oam": active, "peak_per_scanline": max(scanlines), "sprite_height": height,
                "overloaded_scanlines": [i for i, count in enumerate(scanlines) if count > 10]}

    def save_audio(self, name="gameplay"):
        data = np.concatenate(self.audio, axis=0) if self.audio else np.empty((0, 2), dtype=np.int8)
        path = self.output / (name + ".wav")
        with wave.open(str(path), "wb") as output:
            output.setnchannels(2)
            output.setsampwidth(2)
            output.setframerate(self.pyboy.sound.sample_rate)
            output.writeframes((data.astype(np.int16) * 256).astype("<i2").tobytes())
        return {"path": str(path.resolve()), "samples": len(data),
                "min": int(data.min()) if len(data) else 0,
                "max": int(data.max()) if len(data) else 0,
                "nonzero": int(np.count_nonzero(data)),
                "sample_rate": self.pyboy.sound.sample_rate}

    def stop(self):
        self.pyboy.stop(save=False)


def write_report(path, report):
    Path(path).write_text(json.dumps(report, indent=2) + "\n")
