# Third-party tooling

BRASSHOUND game logic, levels, indexed art recipes and APU music/effect data are
project sources. Building and previewing use external development tools:

| Tool | Version | Use | Upstream |
|---|---|---|---|
| GBDK-2020 | 4.5.0 | C compiler, linker, runtime libraries | [GBDK-2020](https://github.com/gbdk-2020/gbdk-2020) |
| PyBoy | 2.8.1 | Actual CGB CPU/PPU/APU emulation | [PyBoy](https://github.com/Baekalfen/PyBoy) |
| Pillow | 12.3.0 | Cartridge screenshot/GIF export | [Pillow](https://github.com/python-pillow/Pillow) |
| NumPy | 2.5.4 | Emulator audio measurements/export | [NumPy](https://github.com/numpy/numpy) |

Downloaded GBDK executables, headers/libraries and the Python virtual environment
are not versioned or included in source releases. `tools/setup.sh` downloads
GBDK from its official pinned release and installs the pinned Python packages.
Each dependency retains its own upstream licensing terms.

GBDK's [distribution FAQ](https://gbdk-2020.github.io/gbdk-2020/docs/api/docs_faq.html)
distinguishes a compiled game ROM from redistribution of the development
kit. The GBDK library GPLv2 linking-exception notice and crash-handler notice
from the installed 4.5.0 distribution are preserved under `third_party/gbdk/`
for reference; these do not select a license for BRASSHOUND's project code/art.

Platform and product names identify compatibility targets. This is an
independent game project. Physical Chromatic hardware has not been tested.
