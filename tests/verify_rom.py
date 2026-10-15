#!/usr/bin/env python3
"""Verify a compiled cartridge image without third-party dependencies."""
import argparse
import hashlib
import json
from pathlib import Path

NINTENDO_LOGO = bytes.fromhex(
    "CE ED 66 66 CC 0D 00 0B 03 73 00 83 00 0C 00 0D"
    " 00 08 11 1F 88 89 00 0E DC CC 6E E6 DD DD D9 99"
    " BB BB 67 63 6E 0E EC CC DD DC 99 9F BB B9 33 3E"
)
ROM_SIZES = {n: 32768 << n for n in range(9)} | {0x52: 72 * 16384, 0x53: 80 * 16384, 0x54: 96 * 16384}


def verify(path):
    data = Path(path).read_bytes()
    if len(data) < 0x150:
        raise AssertionError("ROM is smaller than its cartridge header")
    checksum = 0
    for byte in data[0x134:0x14D]:
        checksum = (checksum - byte - 1) & 0xFF
    stored_global = int.from_bytes(data[0x14E:0x150], "big")
    calculated_global = (sum(data) - data[0x14E] - data[0x14F]) & 0xFFFF
    checks = {
        "nintendo_logo": data[0x104:0x134] == NINTENDO_LOGO,
        "cgb_enabled": bool(data[0x143] & 0x80),
        "size_matches_header": len(data) == ROM_SIZES.get(data[0x148]),
        "header_checksum": checksum == data[0x14D],
        "global_checksum": calculated_global == stored_global,
    }
    report = {
        "rom": str(Path(path).resolve()),
        "title": data[0x134:0x143].rstrip(b"\0").decode("ascii", errors="replace"),
        "bytes": len(data),
        "cgb_flag": hex(data[0x143]),
        "cartridge_type": hex(data[0x147]),
        "rom_size_code": hex(data[0x148]),
        "ram_size_code": hex(data[0x149]),
        "sha256": hashlib.sha256(data).hexdigest(),
        "checks": checks,
        "passed": all(checks.values()),
    }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", default="build/BRASSHOUND.gbc")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = verify(args.rom)
    text = json.dumps(result, indent=2)
    print(text)
    if args.output:
        Path(args.output).write_text(text + "\n")
    raise SystemExit(0 if result["passed"] else 1)
