#!/usr/bin/env python3
"""Serve the real CGB ROM through a local PyBoy emulator. No network needed.

The browser displays the emulator framebuffer and sampled Game Boy audio.
All gameplay, physics, graphics and audio run in the compiled cartridge code.
"""
import argparse
import base64
import hashlib
import io
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
from pyboy import PyBoy

BUTTONS = frozenset(("left", "right", "up", "down", "a", "b", "start", "select"))
FRAME_SECONDS = 70224 / 4194304


class Emulator:
    def __init__(self, rom):
        self.rom = Path(rom).resolve()
        self.lock = threading.Lock()
        self.buttons = set()
        self.applied_buttons = set()
        self.press_deadlines = {}
        self.audio = []
        self.latest_png = b""
        self.frames = 0
        self.running = True
        self.error = None
        self.reset_requested = False
        self.pyboy = self.create()
        self.worker = threading.Thread(target=self.run, daemon=True)
        self.worker.start()

    def create(self):
        cartridge = self.rom.read_bytes()
        self.rom_sha256 = hashlib.sha256(cartridge).hexdigest()
        self.rom_size = len(cartridge)
        emulator = PyBoy(io.BytesIO(cartridge), window="null", cgb=True,
                        sound_emulated=True, sound_sample_rate=24000,
                        ram_file=io.BytesIO(), rtc_file=io.BytesIO(), log_level="ERROR")
        emulator.set_emulation_speed(0)
        return emulator

    def run(self):
        deadline = time.monotonic()
        try:
            while self.running:
                with self.lock:
                    if self.reset_requested:
                        self.pyboy.stop(save=False)
                        self.pyboy = self.create()
                        self.reset_requested = False
                        self.buttons.clear()
                        self.applied_buttons.clear()
                        self.press_deadlines.clear()
                        self.audio.clear()
                        self.frames = 0
                    # HTTP down/up can both arrive between two emulator
                    # frames. Retain every new press for three frames so
                    # the cartridge's joypad polling sees the edge.
                    latched = {button for button, until in self.press_deadlines.items()
                               if self.frames < until}
                    effective_buttons = self.buttons | latched
                    for button in effective_buttons - self.applied_buttons:
                        self.pyboy.button_press(button)
                    for button in self.applied_buttons - effective_buttons:
                        self.pyboy.button_release(button)
                    self.applied_buttons = effective_buttons
                    if not self.pyboy.tick(1, True, True):
                        raise RuntimeError("CGB emulator stopped")
                    self.frames += 1
                    self.press_deadlines = {button: until for button, until in self.press_deadlines.items()
                                            if self.frames < until}
                    self.audio.append(self.pyboy.sound.ndarray.copy())
                    # Bound audio buffering when the browser is not polling.
                    if len(self.audio) > 12:
                        self.audio = self.audio[-12:]
                    output = io.BytesIO()
                    self.pyboy.screen.image.save(output, "PNG")
                    self.latest_png = output.getvalue()
                deadline += FRAME_SECONDS
                delay = deadline - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
                elif delay < -FRAME_SECONDS * 4:
                    deadline = time.monotonic()
        except Exception as error:
            self.error = str(error)
            self.running = False

    def get_frame(self):
        with self.lock:
            audio = np.concatenate(self.audio, axis=0) if self.audio else np.empty((0, 2), dtype=np.int8)
            self.audio.clear()
            return {"png": base64.b64encode(self.latest_png).decode(),
                    "pcm": base64.b64encode(audio.tobytes()).decode(),
                    "sample_rate": 24000, "frame": self.frames, "error": self.error}

    def set_buttons(self, buttons):
        if not isinstance(buttons, list) or not all(button in BUTTONS for button in buttons):
            raise ValueError("Expected an array of Game Boy buttons")
        with self.lock:
            requested = set(buttons)
            for button in requested - self.buttons:
                self.press_deadlines[button] = self.frames + 3
            self.buttons = requested

    def reset(self):
        with self.lock:
            self.reset_requested = True

    def stop(self):
        self.running = False
        self.worker.join(timeout=2)
        self.pyboy.stop(save=False)


def handler_for(emulator):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            if args and str(args[0]).startswith(("POST /input", "GET /frame")):
                return
            super().log_message(format, *args)

        def respond(self, payload, kind="application/json", status=200):
            if isinstance(payload, dict):
                payload = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", len(payload))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                self.respond(Path(__file__).with_name("index.html").read_bytes(), "text/html; charset=utf-8")
            elif path == "/frame":
                self.respond(emulator.get_frame())
            elif path == "/health":
                self.respond({"emulator": "PyBoy", "rom": str(emulator.rom),
                              "sha256": emulator.rom_sha256, "bytes": emulator.rom_size,
                              "cgb": True, "frames": emulator.frames, "error": emulator.error})
            else:
                self.respond({"error": "Not found"}, status=404)

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 1024:
                    raise ValueError("Input payload is too large")
                if self.path == "/input":
                    emulator.set_buttons(json.loads(self.rfile.read(length)))
                    self.respond({"ok": True})
                elif self.path == "/reset":
                    emulator.reset()
                    self.respond({"ok": True})
                else:
                    self.respond({"error": "Not found"}, status=404)
            except (ValueError, TypeError) as error:
                self.respond({"error": str(error)}, status=400)
    return Handler


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", default="build/BRASSHOUND.gbc")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not Path(args.rom).is_file():
        parser.error(f"ROM does not exist: {args.rom}. Build it first with make.")
    emulator = Emulator(args.rom)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(emulator))
    print(f"BRASSHOUND real CGB emulation at http://127.0.0.1:{args.port}", flush=True)
    print("Arrows: move/aim/crouch · Z: jump · X: fire · Enter: start/pause · Shift: weapon", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        emulator.stop()
