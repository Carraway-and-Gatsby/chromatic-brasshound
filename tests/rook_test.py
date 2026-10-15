#!/usr/bin/env python3
"""Actual-PPU ROOK pose, muzzle and original hurtbox regressions.

Ordinary input evidence and controlled collision fixtures are labeled separately.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw
from rom_harness import Harness
from playtest import new_game, shots, write_record, clear_array, SHOT_FORMAT


def oam(h):
    return [{'x':h.pyboy.memory[0xFE01+4*i]-8,
             'y':h.pyboy.memory[0xFE00+4*i]-16,
             'tile':h.pyboy.memory[0xFE02+4*i],
             'flags':h.pyboy.memory[0xFE03+4*i]} for i in range(40)
            if 0 < h.pyboy.memory[0xFE00+4*i] < 144]


def crop(h):
    x=h.read('player_x',2,True)-h.read('camera_x',2)
    y=h.read('player_y',2,True)>>4
    return h.pyboy.screen.image.crop((x-8,y-12,x+24,y+20)).resize((256,256),Image.Resampling.NEAREST)


def run(rom, output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    result={'sha256':hashlib.sha256(Path(rom).read_bytes()).hexdigest(),
            'ordinary':{'fixture_writes':0,'screens':{},'checks':[]},
            'collision_fixtures':{'fixture_writes':0,'screens':{},'checks':[]},'passed':False}
    h=Harness(rom,output=output)
    try:
        new_game(h);h.logical(120)
        base=h.read('player_y',2,True)>>4
        objs=oam(h)
        assert [(o['y'],o['tile']) for o in objs[:4]]==[(base-8,0),(base-8,2),(base+8,100),(base+8,102)],objs
        assert base+16==120
        result['ordinary']['screens']['idle']=h.screenshot('idle-live')
        result['ordinary']['checks'].append('16x24 standing ROOK; four hardware objects; original y120 foot anchor')
        h.press('right');run_tiles=set();frames=[]
        for _ in range(48):
            h.tick();frames.append(crop(h));run_tiles.add(oam(h)[0]['tile'])
        h.release('right')
        assert {4,8,116,120} <= run_tiles,run_tiles
        frames[0].save(output/'run-live.gif',save_all=True,append_images=frames[1:],duration=40,loop=0)
        result['ordinary']['checks'].append('four distinct running phases reach hardware OAM with ordinary right input')
        result['ordinary']['screens']['run']=h.screenshot('run-live')
        h.logical(4)
        # Right-facing normal fire: projectile y is the rifle barrel's row.
        h.press('b');h.tick(5)
        assert any(s[4] and s[1]==base+7 and s[3]==0 for s in shots(h))
        assert any(o['tile']==124 for o in oam(h))
        assert any(o['tile']==96 and o['y']==base-1 for o in oam(h))
        result['ordinary']['screens']['fire']=h.screenshot('fire-live')
        h.release('b');h.logical(16)
        h.press('up','b');h.tick(4)
        live=[s for s in shots(h) if s[4] and s[3]==-4]
        assert live and all(s[1]+4*(45-s[4])==base-8 for s in live),live
        assert any(o['tile']==82 for o in oam(h))
        assert any(o['tile']==96 and o['y']==base-16 for o in oam(h))
        result['ordinary']['screens']['aim']=h.screenshot('aim-live')
        result['ordinary']['checks'].append('horizontal/recoil and vertical-shot glyphs originate at native rifle muzzles')
        assert not h.fixture_writes and h.sprite_overflow_frames==0
        first_peak={'oam':h.peak_oam,'scanline':h.peak_scanline}
        # Restart through the cartridge title so left/crouch/jump observations
        # cannot be obscured by a sentry's later damage flash. No RAM writes.
        h.stop();h=Harness(rom,output=output)
        new_game(h);h.logical(120)
        h.press('left');h.logical(3);h.release('left');h.logical(3)
        objs=oam(h)
        assert [o['tile'] for o in objs[:4]]==[2,0,102,100]
        assert all(o['flags'] & 0x20 for o in objs[:4])
        result['ordinary']['screens']['left']=h.screenshot('left-live')
        result['ordinary']['checks'].append('left-facing upper/lower pairs swap and flip without moving the feet')
        h.press('up','b');h.tick(4)
        assert any(s[4] and s[3]==-4 and s[0]==h.read('player_x',2,True)+8 for s in shots(h))
        result['ordinary']['screens']['aim-left']=h.screenshot('aim-left-live')
        h.release('up','b');h.logical(16)
        h.press('down');h.logical(4)
        assert [o['tile'] for o in oam(h)[:2]]==[18,16]
        assert h.read('crouched') and h.read('player_y',2,True)>>4==base
        result['ordinary']['screens']['crouch']=h.screenshot('crouch-live')
        h.release('down');h.tap('a');h.logical(6)
        assert h.read('player_y',2,True)>>4<base and not h.read('grounded')
        assert oam(h)[0]['tile'] in (12,14)
        result['ordinary']['screens']['jump']=h.screenshot('jump-live')
        h.wait(lambda:h.read('grounded'),180,'original jump landing');h.logical(4)
        assert h.read('player_y',2,True)>>4==base
        result['ordinary']['checks'].append('compact crouch and tucked jump preserve original platform/ground physics')
        assert not h.fixture_writes
        result['ordinary']['sprite_peak']={'oam':max(h.peak_oam,first_peak['oam']),
                                          'scanline':max(h.peak_scanline,first_peak['scanline']),
                                          'overflow':h.sprite_overflow_frames}
        assert h.sprite_overflow_frames==0
    finally:h.stop()
    # Fresh no-enemy scene: isolated collision cases do not claim normal play.
    h=Harness(rom,output=output)
    try:
        new_game(h);h.logical(120)
        x=h.read('player_x',2,True)
        def shot(y):
            h.write('invuln',0)
            write_record(h,'hostile',0,SHOT_FORMAT,(x+5,y,0,0,12,1,0))
            h.logical(3)
        shot(98);assert h.read('hp')==3,'Cosmetic helmet enlarged original hurtbox'
        clear_array(h,'hostile',5,9)
        h.press('down');h.logical(3)
        shot(108);assert h.read('hp')==3,'Crouch no longer clears waist-height fire'
        clear_array(h,'hostile',5,9)
        h.release('down');h.logical(3)
        shot(108);assert h.read('hp')==2,'Torso shot missed'
        assert oam(h)[0]['tile']==20, 'Damage did not render the hurt pose'
        assert h.read('recoil')==0, 'Damage incorrectly triggered firing recoil'
        result['collision_fixtures']['screens']['hurt']=h.screenshot('hurt-fixture')
        h.write('hp',1);shot(108)
        assert h.read('game_state')==3
        assert oam(h)[0]['tile']==24, 'Death did not render the collapsed pose'
        result['collision_fixtures']['screens']['down']=h.screenshot('down-fixture')
        result['collision_fixtures']['checks'].append('original forgiving torso hurtbox, crouch avoidance, damage and death poses')
        result['collision_fixtures']['fixture_writes']=len(h.fixture_writes)
        result['passed']=True
    finally:
        h.stop()
        (output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    # Equal-scale original cartridge crops, aligned at the same foot anchor.
    before=output.parent/'before'
    if (before/'idle-live.png').exists():
        sheet=Image.new('RGB',(640,344),(12,20,32));d=ImageDraw.Draw(sheet)
        for i,(name,folder) in enumerate((('BEFORE / 16 X 16',before),('AFTER / 16 X 24',output))):
            im=Image.open(folder/'idle-live.png').convert('RGB')
            sheet.paste(im.resize((320,288),Image.Resampling.NEAREST),(i*320,24))
            d.text((i*320+8,8),name,fill=(244,235,197))
        d.text((8,324),'ACTUAL GBC FRAMEBUFFER / SAME NATIVE SCALE',fill=(149,169,151))
        sheet.save(output.parent/'rook-before-after.png')
        close=Image.new('RGB',(512,288),(12,20,32));d=ImageDraw.Draw(close)
        for i,(name,folder) in enumerate((('BEFORE',before),('AFTER',output))):
            im=Image.open(folder/'idle-live.png').convert('RGB')
            close.paste(im.crop((16,92,48,124)).resize((256,256),Image.Resampling.NEAREST),(i*256,24))
            d.text((i*256+8,8),name,fill=(244,235,197))
        close.save(output.parent/'rook-detail-before-after.png')
    poses=('idle','run','fire','aim','left','crouch','jump','aim-left')
    sheet=Image.new('RGB',(640,4*308),(12,20,32));d=ImageDraw.Draw(sheet)
    for i,pose in enumerate(poses):
        im=Image.open(result['ordinary']['screens'][pose]).convert('RGB')
        x,y=(i%2)*320,(i//2)*308
        sheet.paste(im.resize((320,288),Image.Resampling.NEAREST),(x,y+20))
        d.text((x+8,y+5),'ROOK / '+pose.upper(),fill=(244,235,197))
    sheet.save(output/'ordinary-poses.png')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',default='build/BRASSHOUND.gbc')
    p.add_argument('--output',default='build/rook-review/2026-10-15/after')
    a=p.parse_args();r=run(a.rom,a.output)
    print(json.dumps({'passed':r['passed'],'checks':sum(len(r[k]['checks']) for k in ('ordinary','collision_fixtures')),'report':str(Path(a.output).resolve()/'report.json')}))
