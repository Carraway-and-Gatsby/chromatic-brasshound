#!/usr/bin/env python3
"""Repeatable tests of the compiled cartridge in genuine CGB emulation.

Input-only checks and isolated, memory-assisted fixtures are reported separately.
Memory fixtures exercise hard-to-reach boundaries, never claim normal progression.
"""
import argparse
import json
import struct
import traceback
from pathlib import Path

from rom_harness import Harness, write_report
from verify_rom import verify

SHOT_FORMAT = '<hhbbBBB'
FOE_FORMAT = '<hhbbBBBBBBB'
MISSIONS = (
    {'name': 'CINDER', 'boss': 'IRONMAW', 'width': 3456, 'arena': 3296, 'boss_x': 3392,
     'checkpoint': 3200, 'pits': [712, 1512, 2200, 2928], 'climb': []},
    {'name': 'TIDEBREAK', 'boss': 'DREDGER', 'width': 2816, 'arena': 2656, 'boss_x': 2752,
     'checkpoint': 2560, 'pits': [464, 1008, 1600, 2200],
     'climb': [(864,96), (960,80), (1536,96), (1664,80)]},
    {'name': 'BLACKOUT', 'boss': 'NULLCORE', 'width': 3200, 'arena': 3040, 'boss_x': 3136,
     'checkpoint': 2944, 'pits': [552, 1224, 2000, 2640], 'climb': [(992,96), (1760,96)]},
)


def shots(h, name='shots', count=8):
    return [struct.unpack(SHOT_FORMAT, bytes(h.pyboy.memory[h.address(name, 9*i):h.address(name, 9*i)+9])) for i in range(count)]


def foes(h):
    return [struct.unpack(FOE_FORMAT, bytes(h.pyboy.memory[h.address('foes', 13*i):h.address('foes', 13*i)+13])) for i in range(3)]


def write_record(h, name, index, fmt, values):
    data = struct.pack(fmt, *values)
    for offset, value in enumerate(data):
        h.write(name, value, offset=len(data)*index+offset)


def clear_array(h, name, count, size):
    for offset in range(count*size):
        h.write(name, 0, offset=offset)


def new_game(h):
    h.boot()
    assert h.read('game_state') == 0, 'Title did not boot'
    h.tap('start')
    h.wait(lambda: h.read('game_state') == 1 and h.read('play_frames', 2) >= 4,
           180, 'mission load')


def fixture_load_mission(h, mission_index):
    """Enter a selected stage through the normal GAME OVER retry handler.

    This intentionally edits mission/state RAM to isolate later-stage tests;
    the complete campaign test below never calls this helper or writes RAM.
    """
    new_game(h)
    if mission_index:
        h.release_all()
        h.tick(3)
        h.write('checkpoint', 0)
        h.write('mission_index', mission_index)
        h.write('hp', 0)
        h.write('game_state', 4)
        h.tap('a')
        h.wait(lambda: h.read('mission_index') == mission_index and h.read('game_state') == 1,
               180, 'selected mission retry load')
        h.logical(5)
    assert h.read('mission_index') == mission_index


def continue_campaign(h, expected_index):
    h.release_all()
    h.tick(3)
    h.tap('a')
    h.wait(lambda: h.read('game_state') == 1 and h.read('mission_index') == expected_index,
           180, 'next mission entry')
    h.logical(5)


def input_controls(h, result):
    h.boot()
    assert h.read('game_state') == 0
    result['screenshots']['title'] = h.screenshot('title')
    h.tap('start')
    h.wait(lambda: h.read('play_frames', 2) >= 4, 180, 'mission load')
    x, y = h.read('player_x', 2, True), h.read('player_y', 2, True)
    h.press('right')
    h.logical(20)
    assert h.read('player_x', 2, True) > x
    h.press('a', 'b')
    h.logical(10)
    assert h.read('player_y', 2, True) < y-100
    assert any(s[4] for s in shots(h))
    result['screenshots']['jump_fire'] = h.screenshot('jump-fire')
    h.release('a', 'right', 'b')
    h.wait(lambda: h.read('grounded') and abs(h.read('player_y', 2, True)-1664) <= 8, 100, 'landing')
    h.press('down', 'b')
    h.logical(15)
    assert h.read('crouched') == 1
    assert any(s[4] and s[1] >= 114 for s in shots(h))
    result['screenshots']['crouch_fire'] = h.screenshot('crouch-fire')
    h.release('down', 'b')
    h.logical(15)
    h.press('up', 'b')
    h.logical(5)
    assert h.read('aiming') == 1
    assert any(s[4] and s[3] < 0 for s in shots(h))
    h.release('up')
    h.tap('start')
    h.wait(lambda: h.read('game_state') == 2)
    h.logical(3)
    position = (h.read('player_x', 2), h.read('player_y', 2), h.read('play_frames', 2))
    projectiles = shots(h) + shots(h, 'hostile', 5)
    h.tick(30)
    assert (h.read('player_x', 2), h.read('player_y', 2), h.read('play_frames', 2)) == position
    assert projectiles == shots(h) + shots(h, 'hostile', 5)
    result['screenshots']['pause'] = h.screenshot('pause')
    h.tap('start')
    h.wait(lambda: h.read('game_state') == 1)
    h.logical(5)
    assert h.read('play_frames', 2) > position[2]
    result['checks'] = ['title', 'START', 'movement', 'simultaneous movement/jump/fire',
                        'landing', 'crouch/fire', 'upward aim', 'pause freezes game', 'resume']


def input_combat(h, result):
    new_game(h)
    h.press('right', 'b')
    h.wait(lambda: h.read('score', 2) >= 100, 220, 'opening infantry defeat')
    assert h.read('hp') == 3
    assert h.read('weapon') == 0 and h.read('ammo', 2) == 0
    assert h.read('camera_x', 2) > 0
    result['screenshots']['combat'] = h.screenshot('combat')
    result['checks'] = ['pistol projectile hits and defeats infantry', 'unlimited pistol ammunition', 'camera follows']
    before, samples = h.read('frame', 2), 180
    h.tick(samples)
    result['performance'] = {'display_frames': samples, 'game_updates': (h.read('frame', 2)-before)&65535}


def input_damage(h, result):
    new_game(h)
    h.press('right')
    h.wait(lambda: h.read('hp') < 3, 300, 'ordinary enemy contact damage')
    h.release('right')
    hp = h.read('hp')
    assert hp == 2 and h.read('invuln') > 0
    h.logical(30)
    assert h.read('hp') == hp
    result['screenshots']['damage'] = h.screenshot('damage')
    result['checks'] = ['enemy contact causes one hit', '90-frame invulnerability prevents repeated damage']


def fixture_collision(h, result):
    new_game(h)
    h.write('next_encounter', 25)
    clear_array(h, 'foes', 3, 13)
    write_record(h, 'foes', 0, FOE_FORMAT, (100,100,104,-1,0,2,250,0,1,0,0))
    # Bullet width four touches x=101 exactly: strict overlap must not hit.
    write_record(h, 'shots', 0, SHOT_FORMAT, (97,111,0,0,40,1,0))
    h.logical(2)
    assert foes(h)[0][5] == 2
    h.write('shots', 98, width=2)
    h.logical(2)
    assert foes(h)[0][5] == 1
    h.press('b')
    h.wait(lambda: h.read('score', 2) >= 100, 70, 'infantry projectile defeat')
    # Crate turns into its configured weapon pickup.
    write_record(h, 'foes', 0, FOE_FORMAT, (100,100,104,-1,3,3,0,0,1,0,4))
    h.wait(lambda: foes(h)[0][4] == 4, 120, 'destructible crate drop')
    h.release('b')
    h.write('player_x', 100, 2, signed=True)
    h.logical(3)
    assert h.read('weapon') == 1 and h.read('ammo', 2, offset=2) == 100
    assert foes(h)[0][8] == 0
    h.write('hp', 1)
    write_record(h, 'foes', 0, FOE_FORMAT, (100,100,104,-1,6,1,0,0,1,0,0))
    h.logical(3)
    assert h.read('hp') == 3
    result['checks'] = ['strict projectile collision boundary', 'enemy health decrement',
                        'enemy death/score', 'destructible crate', 'machinegun drop/pickup', 'health pickup']


def fixture_weapons(h, result):
    new_game(h)
    h.write('ammo', 300, 2, offset=2)
    h.write('weapon', 1)
    h.write('hud_dirty', 1)
    h.logical(3)
    assert [h.read('ui_tiles', offset=i) for i in (16, 17, 18)] == [30, 27, 27], 'Ammo HUD truncated a 16-bit count'
    h.write('weapon', 0)
    h.write('ammo', 12, 2, offset=2)
    h.write('ammo', 2, 2, offset=4)
    h.tap('select')
    assert h.read('weapon') == 1
    h.press('b')
    h.logical(20)
    assert h.read('ammo', 2, offset=2) <= 8
    assert any(s[4] and s[6] == 1 for s in shots(h))
    h.release('b')
    h.tap('select')
    assert h.read('weapon') == 2
    h.press('b')
    h.logical(15)
    assert any(s[4] and s[6] == 2 and s[5] == 6 for s in shots(h))
    h.logical(75)
    assert h.read('ammo', 2, offset=4) == 0 and h.read('weapon') == 0
    result['checks'] = ['three-digit ammunition HUD above 255', 'SELECT cycles available weapons', 'machinegun faster fire/ammunition',
                        'rocket projectile damage six', 'empty weapon falls back to pistol']


def fixture_death_retry(h, result, mission_index=0):
    fixture_load_mission(h, mission_index)
    prefix = f'mission{mission_index}-' if mission_index else ''
    h.press('b')
    h.logical(15)
    h.write('hp', 1)
    h.write('invuln', 0)
    write_record(h, 'hostile', 0, SHOT_FORMAT,
                 (h.read('player_x', 2)+5, 108, 0, 0, 30, 1, 0))
    h.wait(lambda: h.read('game_state') == 3, 15, 'death during firing')
    assert h.read('hp') == 0
    result['screenshots']['death'] = h.screenshot(prefix+'death')
    h.wait(lambda: h.read('game_state') == 4, 120, 'GAME OVER')
    h.logical(3)
    result['screenshots']['gameover'] = h.screenshot(prefix+'gameover')
    h.release_all()
    h.tick(3)
    h.tap('a')
    h.wait(lambda: h.read('game_state') == 1 and h.read('play_frames', 2) >= 4, 180, 'retry')
    assert h.read('hp') == 3 and h.read('player_x', 2) == 24
    assert h.read('mission_index') == mission_index
    result['checks'] = ['hostile projectile damage', 'death during attack', 'HP reaches zero without wrapping',
                        'death animation to GAME OVER', 'A retry resets current mission', 'retry retains mission index']


def fixture_level(h, result, mission_index=0):
    fixture_load_mission(h, mission_index)
    spec = MISSIONS[mission_index]
    h.write('next_encounter', 255)
    clear_array(h, 'foes', 3, 13)
    h.write('invuln', 0)
    h.write('player_x', spec['pits'][0]-8, 2, signed=True)
    h.write('last_safe', spec['pits'][0]-32, 2, signed=True)
    h.press('right')
    h.wait(lambda: h.read('player_y', 2, True) > 120*16, 240, 'pit fall')
    h.wait(lambda: h.read('hp') == 2 and h.read('player_y', 2, True) < 120*16, 180, 'pit recovery')
    assert h.read('game_state') == 1
    result['screenshots']['pit_recovery'] = h.screenshot(f'mission{mission_index}-pit-recovery')
    h.release('right')
    h.write('player_x', spec['checkpoint'], 2, signed=True)
    h.wait(lambda: h.read('checkpoint') == 1, 240, 'boss checkpoint')
    assert h.read('hp') == 3 and h.read('ammo', 2, offset=2) == 100 and h.read('ammo', 2, offset=4) == 8
    result['checks'] = ['pit fall damages and recovers without softlock', 'checkpoint restores HP and ammunition']


def setup_boss(h, mission_index=0):
    fixture_load_mission(h, mission_index)
    spec = MISSIONS[mission_index]
    h.write('player_x', spec['arena']+16, 2, signed=True)
    h.write('next_encounter', 255)
    h.wait(lambda: h.read('boss_active') == 1, 300, 'arena entry')
    h.logical(5)
    h.write('invuln', 200)


def fixture_boss(h, result, mission_index=0):
    setup_boss(h, mission_index)
    spec = MISSIONS[mission_index]
    boss_x, player_x = spec['boss_x'], spec['arena']+16
    result['screenshots']['arena'] = h.screenshot(f'mission{mission_index}-boss-arena')
    h.write('boss_timer', 90)
    write_record(h, 'shots', 0, SHOT_FORMAT, (boss_x-5,90,5,0,30,1,0))
    h.logical(3)
    assert h.read('boss_hp') == 48
    h.write('boss_timer', 40)
    write_record(h, 'shots', 0, SHOT_FORMAT, (boss_x-5,110,5,0,30,1,0))
    h.logical(3)
    assert h.read('boss_hp') == 48
    h.write('boss_timer', 40)
    write_record(h, 'shots', 0, SHOT_FORMAT, (boss_x-5,90,5,0,30,6,2))
    h.logical(3)
    assert h.read('boss_hp') == 42
    clear_array(h, 'hostile', 5, 9)
    h.write('boss_timer', 1)
    h.logical(3)
    phase1 = [s for s in shots(h, 'hostile', 5) if s[4]]
    assert phase1
    if mission_index == 0:
        assert len(phase1) == 1
    h.write('boss_hp', 24)
    clear_array(h, 'hostile', 5, 9)
    h.write('boss_timer', 1)
    h.logical(3)
    assert h.read('boss_phase') == 2
    phase2 = [s for s in shots(h, 'hostile', 5) if s[4]]
    assert phase2
    if mission_index == 0:
        assert len(phase2) == 3
    result['boss_patterns'] = {'mission_index': mission_index,
                              'phase1': [{'x': s[0], 'y': s[1], 'dx': s[2], 'dy': s[3]} for s in phase1],
                              'phase2': [{'x': s[0], 'y': s[1], 'dx': s[2], 'dy': s[3]} for s in phase2]}
    result['screenshots']['phase2'] = h.screenshot(f'mission{mission_index}-boss-phase2')
    # Killing blow and a projectile on ROOK during the same update: death
    # clears hostile shots first, preventing postmortem simultaneous damage.
    h.write('boss_hp', 1)
    h.write('boss_timer', 25)
    h.write('hp', 1)
    h.write('invuln', 0)
    write_record(h, 'hostile', 0, SHOT_FORMAT, (player_x+5,108,0,0,30,1,0))
    write_record(h, 'shots', 0, SHOT_FORMAT, (boss_x-5,90,5,0,30,1,0))
    h.wait(lambda: h.read('game_state') == 6, 15, 'boss death')
    assert h.read('boss_hp') == 0 and h.read('hp') == 1
    assert not any(s[4] for s in shots(h, 'hostile', 5))
    destination = 5 if mission_index == 2 else 7
    h.wait(lambda: h.read('game_state') == destination, 220, 'boss result screen')
    h.logical(3)
    result['screenshots']['boss_result'] = h.screenshot(f'mission{mission_index}-boss-result')
    assert not any(s[4] for s in shots(h))
    assert not h.pyboy.memory[0xFF40] & 2, 'Sprites remain enabled on result screen'
    prior_score = h.read('score', 2)
    continue_campaign(h, 0 if mission_index == 2 else mission_index+1)
    assert h.read('checkpoint') == 0 and h.read('hp') == 3
    if mission_index < 2:
        assert h.read('score', 2) == prior_score, 'Score was lost between stages'
        assert h.read('ammo', 2, offset=2) >= 50 and h.read('ammo', 2, offset=4) >= 4
    result['checks'] = ['arena entry', 'closed core rejects hits', 'armor rejects hits',
                        'open core accepts rocket damage', 'phase one pattern', 'phase two pattern',
                        'boss defeat during attack clears hostile shots', 'explosion sequence to result screen',
                        'result hides sprites and clears projectiles',
                        'final replay returns to mission zero' if mission_index == 2 else 'A advances stage with score and resupply']


def fixture_checkpoint_retry(h, result, mission_index=0):
    setup_boss(h, mission_index)
    player_x = MISSIONS[mission_index]['arena']+16
    h.write('hp', 1)
    h.write('invuln', 0)
    write_record(h, 'hostile', 0, SHOT_FORMAT, (player_x+5,108,0,0,30,1,0))
    h.wait(lambda: h.read('game_state') == 4, 180, 'boss GAME OVER')
    assert h.read('checkpoint') == 1
    h.release_all()
    h.tick(3)
    h.tap('a')
    h.wait(lambda: h.read('game_state') == 1 and h.read('hp') == 3, 180, 'checkpoint retry')
    h.logical(6)
    assert h.read('player_x', 2) == player_x and h.read('boss_hp') == 48 and h.read('boss_active') == 1
    assert h.read('mission_index') == mission_index
    assert h.read('ammo', 2, offset=2) == 100 and h.read('ammo', 2, offset=4) == 8
    result['checks'] = ['boss death retains checkpoint', 'retry starts arena with health/boss/ammo reset']


def input_campaign(h, result):
    new_game(h)
    h.press('b')
    lastjump = -100
    retries = 0
    boss_selected = False
    boss_anchor = 0
    planned_cycle = -1
    retry_snapshots = []
    completed = []
    stats = {}
    result['campaign_progress'] = stats
    for iteration in range(42000):
        state = h.read('game_state')
        mission_index = h.read('mission_index')
        assert 0 <= mission_index < len(MISSIONS), 'Invalid campaign mission index'
        spec = MISSIONS[mission_index]
        if mission_index not in stats:
            stats[mission_index] = {'name': spec['name'], 'start_frame': h.emulated_frames,
                                    'seen_enemy_types': [], 'peak_x': 0, 'retries': 0,
                                    'boss_patterns': {}, 'boss_phase2_seen': False,
                                    'elevated_platform_seen': False}
            result['screenshots'][f'stage{mission_index}_opening'] = h.screenshot(f'stage{mission_index}-opening')
        stage = stats[mission_index]
        frame = h.read('play_frames', 2)
        x = h.read('player_x', 2, True)
        y = h.read('player_y', 2, True) >> 4
        stage['peak_x'] = max(x, stage['peak_x'])
        current_foes = foes(h)
        if h.read('grounded') and y < 98:
            stage['elevated_platform_seen'] = True
        stage['seen_enemy_types'] = sorted(set(stage['seen_enemy_types']) | {e[4] for e in current_foes if e[8]})
        if x >= spec['width']//2 and f'stage{mission_index}_midpoint' not in result['screenshots']:
            result['screenshots'][f'stage{mission_index}_midpoint'] = h.screenshot(f'stage{mission_index}-midpoint')
        if state == 1:
            if h.read('boss_active'):
                if not boss_selected:
                    h.release('b')
                    h.logical(3)
                    boss_anchor = spec['arena']+17
                    planned_cycle = -1
                    preferred = 1 if h.read('ammo', 2, offset=2) else (2 if h.read('ammo', 2, offset=4) else 0)
                    for _ in range(3):
                        if h.read('weapon') == preferred: break
                        h.tap('select')
                        h.logical(2)
                    assert h.read('weapon') == preferred, 'Could not select boss weapon'
                    result['screenshots'][f'stage{mission_index}_boss'] = h.screenshot(f'stage{mission_index}-boss')
                    boss_selected = True
                if mission_index == 1 and 0 < h.read('boss_timer') <= 11:
                    cycle = h.read('boss_cycle')
                    if planned_cycle != cycle:
                        target = h.read('boss_target_x', 2)
                        boss_anchor = spec['arena']+(56 if target < spec['arena']+50 else 17)
                        planned_cycle = cycle
                if x < boss_anchor-1:
                    h.release('left'); h.press('right')
                elif x > boss_anchor+1:
                    h.release('right'); h.press('left')
                else:
                    h.release('right', 'left')
                    if h.read('facing', signed=True) < 0 and h.read('boss_open'):
                        h.tap('right')
                        boss_anchor = h.read('player_x', 2, True)
                # Prefer the stocked machinegun, then available rockets, then
                # pistol. All weapon changes use ordinary SELECT button edges.
                if h.read('weapon') == 0 and (h.read('ammo', 2, offset=2) or h.read('ammo', 2, offset=4)):
                    h.release('b')
                    h.tap('select')
                weapon = h.read('weapon')
                travel = max(0, (spec['boss_x']-(x+16)) // (3 if weapon == 2 else 5))
                should_fire = h.read('boss_open') and 74 <= y <= 92 and h.read('boss_timer') > 14+travel
                if should_fire: h.press('b')
                else: h.release('b')
                hostile = [shot for shot in shots(h, 'hostile', 5) if shot[4]]
                threat = any(shot[2] < 0 and 0 < shot[0]-x < 42 and shot[1] >= 90 for shot in hostile)
                want_jump = threat or (h.read('boss_open') and 25 < h.read('boss_timer') < 65)
                phase = h.read('boss_phase')
                patterns = stage['boss_patterns'].setdefault(str(phase), [])
                for shot in hostile:
                    pattern = [shot[2], shot[3], shot[6]]
                    if pattern not in patterns: patterns.append(pattern)
                if h.read('boss_hp') <= 24:
                    stage['boss_phase2_seen'] = True
                    key = f'stage{mission_index}_phase2'
                    if key not in result['screenshots']:
                        result['screenshots'][key] = h.screenshot(f'stage{mission_index}-phase2')
            else:
                h.press('b')
                targets = [e for e in current_foes if e[8] and e[4] <= 3 and 10 < e[0]-x < 90]
                stop = any((e[4] != 2 and e[2] >= 100 and y >= 98) or e[4] == 2 or e[2] < 100 for e in targets)
                if stop: h.release('right')
                else: h.press('right')
                want_jump = (any(0 < left-(x+8) < 12 for left in spec['pits'])
                             or any(e[4] == 2 or e[2] < 100 for e in targets)
                             or any(0 < left-(x+8) < 20 and y+16 > height for left, height in spec['climb']))
            if h.read('grounded') and want_jump and ((frame-lastjump)&65535) > 36:
                h.press('a')
                lastjump = frame
            elif ((frame-lastjump)&65535) > 3:
                h.release('a')
        elif state == 4:
            retries += 1
            stage['retries'] += 1
            assert stage['retries'] <= 5, 'Input-only stage exceeded five retries'
            retry_snapshots.append(h.snapshot())
            h.release_all()
            h.tick(3)
            h.tap('a')
            h.wait(lambda: h.read('game_state') == 1 and h.read('hp') == 3, 180, 'natural retry')
            h.logical(5)
            assert h.read('mission_index') == mission_index, 'Retry changed the current mission'
            h.press('b')
            lastjump = -100
            boss_selected = False
        elif state == 7:
            assert mission_index in (0,1), 'Final boss produced a stage-clear screen'
            h.logical(3)
            result['screenshots'][f'stage{mission_index}_clear'] = h.screenshot(f'stage{mission_index}-clear')
            assert not any(shot[4] for shot in shots(h, 'hostile', 5))
            assert not any(shot[4] for shot in shots(h))
            assert not h.pyboy.memory[0xFF40] & 2
            stage['display_frames'] = h.emulated_frames-stage['start_frame']
            stage['seconds'] = round(stage['display_frames']*70224/4194304, 2)
            completed.append(mission_index)
            score = h.read('score', 2)
            continue_campaign(h, mission_index+1)
            assert h.read('score', 2) == score and h.read('hp') == 3 and h.read('checkpoint') == 0
            assert h.read('ammo', 2, offset=2) >= 50 and h.read('ammo', 2, offset=4) >= 4
            h.press('b')
            lastjump = -100
            boss_selected = False
        elif state == 5:
            assert mission_index == 2, 'Campaign victory appeared before the third boss'
            h.logical(3)
            result['screenshots']['victory'] = h.screenshot('input-only-campaign-victory')
            stage['display_frames'] = h.emulated_frames-stage['start_frame']
            stage['seconds'] = round(stage['display_frames']*70224/4194304, 2)
            completed.append(mission_index)
            result['checks'] = ['all three missions traversed with ordinary inputs',
                                'distinct level routes and enemy encounters', 'weapon pickups', 'pits crossed',
                                'boss checkpoint in every stage', 'all three bosses reached phase two',
                                'all bosses defeated by ordinary firing', 'stage-clear transitions',
                                'stage carryover score and resupply', 'final campaign victory']
            result['campaign'] = {'emulated_frames': h.emulated_frames,
                                   'approximate_seconds': round(h.emulated_frames*70224/4194304, 2),
                                   'retries': retries, 'completed_mission_indices': completed,
                                   'retry_snapshots': retry_snapshots, 'stages': stats,
                                   'peak_oam': h.peak_oam, 'peak_sprites_per_scanline': h.peak_scanline,
                                   'sprite_overflow_frames': h.sprite_overflow_frames}
            assert completed == [0,1,2]
            for index, entry in stats.items():
                assert {0,1,2}.issubset(entry['seen_enemy_types']), f'Mission {index} did not encounter all enemy types'
                assert entry['boss_phase2_seen'], f'Mission {index} did not exercise boss phase two'
            assert not h.fixture_writes
            assert h.peak_scanline <= 10 and h.peak_oam <= 40 and h.sprite_overflow_frames == 0
            return
        if iteration % 1200 == 0:
            result['screenshots'][f'campaign_{iteration}'] = h.screenshot(f'campaign-{iteration}')
        h.tick(2)
    raise AssertionError(f'Input-only campaign timed out; {h.snapshot()}')


CASES = [
    ('controls', input_controls, True, 'regression'),
    ('combat', input_combat, True, 'combat'),
    ('damage', input_damage, True, 'combat'),
    ('collision_pickups', fixture_collision, False, 'combat'),
    ('weapons', fixture_weapons, False, 'regression'),
    ('death_retry', fixture_death_retry, False, 'regression'),
    ('pit_checkpoint', fixture_level, False, 'level'),
    ('boss', fixture_boss, False, 'boss'),
    ('checkpoint_retry', fixture_checkpoint_retry, False, 'boss'),
    ('complete_campaign', input_campaign, True, 'mission'),
]


for mission_index in (1, 2):
    for name, test, group in (
        ('death_retry', fixture_death_retry, 'regression'),
        ('pit_checkpoint', fixture_level, 'level'),
        ('boss', fixture_boss, 'boss'),
        ('checkpoint_retry', fixture_checkpoint_retry, 'boss'),
    ):
        CASES.insert(-1, (f'mission{mission_index}_{name}',
                          lambda h, result, test=test, index=mission_index: test(h, result, index),
                          False, group))


def foundation(rom, output):
    h = Harness(rom, output=output)
    result = {'input_only': True, 'screenshots': {}}
    try:
        h.boot()
        assert h.read('game_state') == 0
        result['screenshots']['title'] = h.screenshot('title')
        h.tap('start')
        assert h.read('game_state') == 1
        x, y = h.read('player_x', 2, True), h.read('player_y', 2, True)
        h.press('right')
        h.tick(30)
        assert h.read('player_x', 2, True) > x
        h.release('right')
        h.press('a')
        h.tick(10)
        assert h.read('player_y', 2, True) < y
        h.release('a')
        result['screenshots']['jump'] = h.screenshot('jump')
        h.tick(90)
        assert h.read('player_y', 2, True) == y
        result['checks'] = ['title', 'START', 'movement', 'jump', 'landing']
        result['passed'] = True
        return result
    finally:
        h.stop()


def run(rom, output, stage='all'):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {'rom_validation': verify(rom), 'emulator': 'PyBoy 2.8.1 CGB', 'cases': {}}
    assert report['rom_validation']['passed'], 'Invalid cartridge header or checksum'
    if stage == 'foundation':
        report['cases']['foundation'] = foundation(rom, output)
    else:
        for name, test, input_only, group in CASES:
            if stage != 'all' and group != stage:
                continue
            h = Harness(rom, output=output)
            result = {'input_only': input_only, 'screenshots': {}}
            print(f'RUN {name} ({"ordinary inputs" if input_only else "memory-assisted fixture"})', flush=True)
            try:
                test(h, result)
                result['passed'] = True
            except Exception as error:
                result['passed'] = False
                result['error'] = str(error) or type(error).__name__
                result['failure_traceback'] = traceback.format_exc(limit=3)
                result['screenshots']['failure'] = h.screenshot(name+'-failure')
            finally:
                result['snapshot'] = h.snapshot()
                result['sprite_usage'] = h.sprite_usage()
                result['sprite_peaks_all_frames'] = {'oam': h.peak_oam, 'per_scanline': h.peak_scanline,
                                                     'overflow_frames': h.sprite_overflow_frames}
                result['fixture_write_count'] = len(h.fixture_writes)
                result['audio'] = h.save_audio(name)
                h.stop()
            report['cases'][name] = result
            print(f'{"PASS" if result["passed"] else "FAIL"} {name}' + (f': {result["error"]}' if not result['passed'] else ''), flush=True)
            write_report(output/'report.json', report)
    report['passed'] = report['rom_validation']['passed'] and all(case['passed'] for case in report['cases'].values())
    write_report(output/'report.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', default='build/BRASSHOUND.gbc')
    parser.add_argument('--output', default='build/test-artifacts')
    parser.add_argument('--stage', choices=['all','foundation','combat','level','boss','regression','mission'], default='all')
    args = parser.parse_args()
    result = run(args.rom, args.output, args.stage)
    print(json.dumps({'passed': result['passed'], 'report': str((Path(args.output)/'report.json').resolve())}, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
