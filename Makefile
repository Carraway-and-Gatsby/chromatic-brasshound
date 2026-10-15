GBDK_HOME ?= $(CURDIR)/tools/gbdk
LCC := $(GBDK_HOME)/bin/lcc
CFLAGS := -Iinclude -Wm-yC -Wm-ynBRASSHOUND -Wl-m -Wl-j
SOURCES := src/main.c src/missions.c src/assets.c src/audio.c
.PHONY: all assets test clean serve play setup
all: build/BRASSHOUND.gbc
assets:
	python3 assets/ui/title-recipe.py
	python3 tools/generate_assets.py
build/BRASSHOUND.gbc: $(SOURCES) $(wildcard include/*.h)
	@mkdir -p build
	$(LCC) $(CFLAGS) -o $@ $(SOURCES)
test: all
	tools/emulator-venv/bin/python tests/playtest.py --output build/campaign-test-artifacts
	tools/emulator-venv/bin/python tests/browser_input_test.py --output build/campaign-test-artifacts/browser-input-report.json
	tools/emulator-venv/bin/python tests/ui_test.py
	tools/emulator-venv/bin/python tests/rook_test.py
serve: all
	tools/emulator-venv/bin/python web/server.py
play: serve
setup:
	sh tools/setup.sh
clean:
	rm -f build/BRASSHOUND.gbc build/BRASSHOUND.map build/BRASSHOUND.noi build/BRASSHOUND.ihx
