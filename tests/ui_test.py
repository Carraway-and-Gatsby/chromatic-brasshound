#!/usr/bin/env python3
"""Cartridge UI regressions; controlled display fixtures are labeled as such."""
import argparse
import json
import re
from pathlib import Path

from rom_harness import Harness
from playtest import setup_boss
from verify_rom import verify


def run(rom, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    header = Path('include/assets.h').read_text()
    obj_end = 0x8000 + 16*int(re.search(r'#define SPRITE_TILES_COUNT (\d+)u', header)[1])
    assert obj_end <= 0x8800, 'OBJ patterns overlap signed background storage'
    tiles = {name: int(value) for name, value in
             re.findall(r'#define (TILE_\w+) (\d+)u', header)}
    report = {'rom_validation': verify(rom), 'mode': 'memory-assisted UI fixtures',
              'checks': [], 'screenshots': {}, 'fixture_write_count': 0, 'passed': False}
    h = Harness(rom, output=output)
    try:
        h.boot()
        assert h.read('game_state') == 0
        report['screenshots']['title'] = h.screenshot('title')
        original_title = h.pyboy.screen.image.copy()
        original_obj = bytes(h.pyboy.memory[0, 0x8000:obj_end])
        h.tap('start')
        h.wait(lambda: h.read('game_state') == 1 and h.read('play_frames', 2) >= 5)
        report['screenshots']['entry'] = h.screenshot('entry')
        assert h.pyboy.memory[0xFF4A] == 128 and h.pyboy.memory[0xFF4B] == 7
        assert bytes(h.pyboy.memory[0, 0x8000:obj_end]) == original_obj
        report['checks'].append('title art preserves OBJ patterns and 128px action area')

        def refresh():
            h.write('hud_dirty', 1)
            h.logical(4)

        def hud_tiles():
            # Test what reached hardware VRAM, not just a deferred RAM buffer.
            return list(h.pyboy.memory[0, 0x9C00:0x9C14]) + list(h.pyboy.memory[0, 0x9C20:0x9C34])

        for hp in (3, 2, 1, 0):
            h.write('hp', hp)
            refresh()
            assert hud_tiles()[1:4] == [tiles['TILE_UI_HP_FULL'] if i < hp
                                       else tiles['TILE_UI_HP_EMPTY'] for i in range(3)]
        h.write('hp', 2)
        h.write('score', 1900, 2)
        h.write('weapon', 0)
        refresh()
        assert hud_tiles()[17] == tiles['TILE_UI_INFINITY']
        assert hud_tiles()[7:12] == [tiles['TILE_UI_SCORE_0'] + n for n in (0,1,9,0,0)]
        for weapon, ammo in ((1, 85), (1, 300), (1, 999), (2, 8)):
            h.write('weapon', weapon)
            h.write('ammo', ammo, 2, offset=2*weapon)
            refresh()
            row = hud_tiles()
            assert row[13:15] == [tiles['TILE_UI_PISTOL'] + 2*weapon + i for i in range(2)]
            assert row[16:19] == [27+ammo//100, 27+(ammo//10)%10, 27+ammo%10]
        report['checks'].append('hardware health 0..3, three weapon silhouettes, infinity, score, ammo 008..999')

        for mission in range(3):
            report['fixture_write_count'] += len(h.fixture_writes)
            h.stop()
            h = Harness(rom, output=output)
            setup_boss(h, mission)
            h.write('hp', 2)
            h.write('weapon', 1)
            h.write('ammo', 85, 2, offset=2)
            h.write('score', 1900, 2)
            h.write('invuln', 0)
            for hp in (48, 47, 32, 1):
                h.write('boss_hp', hp)
                h.write('boss_timer', 90)
                refresh()
                bar = hud_tiles()[28:40]
                assert sum(t - tiles['TILE_UI_BAR_EMPTY'] for t in bar) == 2*hp
                assert all(tiles['TILE_UI_BAR_EMPTY'] <= t <= tiles['TILE_UI_BAR_EMPTY']+8 for t in bar)
                if hp == 32:
                    report['screenshots'][f'boss{mission}'] = h.screenshot(f'boss{mission}')
            report['checks'].append(f'mission {mission}: 96px boss bar at full, 47, 32 and one HP')
            h.tap('start')
            h.wait(lambda: h.read('game_state') == 2)
            frozen = h.read('play_frames', 2)
            h.tick(20)
            assert h.read('play_frames', 2) == frozen
            h.tap('start')
            h.wait(lambda: h.read('game_state') == 1)
            h.logical(4)
            assert all(a == 7 for a in h.pyboy.memory[1, 0x9C00:0x9C14])
            assert h.pyboy.memory[0xFF4A] == 128
            report['checks'].append(f'mission {mission}: pause/resume restores HUD positions and attributes')

            # Controlled result entry then ordinary START/A exercise title atlas
            # replacement and full mission-atlas restoration on the next boot.
            h.release_all()
            h.tick(3)
            h.write('game_state', 4)
            h.tap('start')
            h.wait(lambda: h.read('game_state') == 0)
            h.logical(3)
            assert h.pyboy.screen.image.tobytes() == original_title.tobytes()
            h.tap('a')
            h.wait(lambda: h.read('game_state') == 1 and h.read('play_frames', 2) >= 5)
            for tile in (48, 96, 160, 168, 177, 187):
                addr = 0x9000+tile*16 if tile < 128 else 0x8800+(tile-128)*16
                expected = h.pyboy.memory[h.address('bg_tiles', tile*16):h.address('bg_tiles', tile*16)+16]
                assert h.pyboy.memory[0, addr:addr+16] == expected
            assert bytes(h.pyboy.memory[0, 0x8000:obj_end]) == original_obj
            report['checks'].append(f'mission {mission}: title return, A start, world/boss/HUD/OBJ atlas integrity')
        report['passed'] = True
    finally:
        report['fixture_write_count'] += len(h.fixture_writes)
        h.stop()
        (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', default='build/BRASSHOUND.gbc')
    parser.add_argument('--output', default='build/ui-test-artifacts/display')
    args = parser.parse_args()
    result = run(args.rom, args.output)
    print(json.dumps({'passed': result['passed'], 'checks': len(result['checks']),
                      'report': str(Path(args.output).resolve()/'report.json')}, indent=2))
