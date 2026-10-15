#!/usr/bin/env python3
"""Capture actual cartridge stages through an ordinary-input campaign route.

No stage/position/inventory RAM writes. Uses the tested input bot as a route,
reads telemetry to capture stable landmarks, and exports nearest-neighbor sheets.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tests'))
from rom_harness import Harness
from playtest import input_campaign

LANDMARKS = ((256, 1104, 2384), (440, 992, 2064), (400, 1544, 2496))
NAMES = ('CINDER', 'TIDEBREAK', 'BLACKOUT')


class Capture(Harness):
    def __init__(self, rom, output):
        super().__init__(rom, output=output)
        self.captures = {}

    def tick(self, frames=1, capture_audio=False):
        for _ in range(frames):
            super().tick(1, capture_audio=False)
            if self.read('game_state') != 1:
                continue
            stage = self.read('mission_index')
            if stage >= 3:
                continue
            x = self.read('player_x', 2, True)
            invuln = self.read('invuln')
            if invuln and invuln & 4:
                continue
            candidates = [(str(i+1), target) for i, target in enumerate(LANDMARKS[stage])]
            for label, target in candidates:
                key = f'stage{stage}-{label}'
                if key not in self.captures and target <= x < target+24:
                    self.captures[key] = {'path': self.screenshot(key), 'snapshot': self.snapshot()}
            key = f'stage{stage}-boss'
            if self.read('boss_active') and key not in self.captures and not invuln:
                self.captures[key] = {'path': self.screenshot(key), 'snapshot': self.snapshot()}


def capture(rom, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    h = Capture(rom, output)
    result = {'input_only': True, 'screenshots': {}}
    try:
        input_campaign(h, result)
        assert not h.fixture_writes
        assert all(f'stage{s}-{label}' in h.captures for s in range(3)
                   for label in ('1','2','3','boss')), h.captures.keys()
        result['landmarks'] = h.captures
        result['fixture_write_count'] = 0
        result['rom_sha256'] = hashlib.sha256(Path(rom).read_bytes()).hexdigest()
        result['passed'] = True
        for stage, name in enumerate(NAMES):
            sheet = Image.new('RGB', (1280, 308), (12,20,32))
            draw = ImageDraw.Draw(sheet)
            grid = Image.new('RGB', (640,616), (12,20,32))
            grid_draw = ImageDraw.Draw(grid)
            for i, label in enumerate(('1','2','3','boss')):
                path = h.captures[f'stage{stage}-{label}']['path']
                im = Image.open(path).convert('RGB')
                assert im.size == (160,144)
                sheet.paste(im.resize((320,288),Image.Resampling.NEAREST),(320*i,20))
                draw.text((320*i+8,5),name+' / '+('BOSS' if label=='boss' else 'SECTION '+label),fill=(244,235,197))
                gx,gy=(i%2)*320,(i//2)*308
                grid.paste(im.resize((320,288),Image.Resampling.NEAREST),(gx,gy+20))
                grid_draw.text((gx+8,gy+5),name+' / '+('BOSS' if label=='boss' else 'SECTION '+label),fill=(244,235,197))
            sheet.save(output/(name.lower()+'-screens.png'))
            grid.save(output/(name.lower()+'-grid.png'))
        (output/'capture-report.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'passed':True,'sha256':result['rom_sha256'],'screens':len(h.captures),
                          'output':str(output.resolve())}))
    finally:
        h.stop()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', default='build/BRASSHOUND.gbc')
    parser.add_argument('--output', default='build/stage-screens')
    args=parser.parse_args()
    capture(args.rom,args.output)
