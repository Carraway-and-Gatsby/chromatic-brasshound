/* BRASSHOUND / Operation Cinder. Original GBC game. Q4 vertical physics. */
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>
#include <string.h>
#include "game.h"
#include "missions.h"
#include "assets.h"
#include "audio.h"

volatile uint8_t game_state, hp, boss_hp, checkpoint, weapon;
volatile int16_t player_x, player_y;
volatile uint16_t frame;
uint16_t ammo[3];
Shot shots[MAX_SHOTS], hostile[MAX_HOSTILE];
Foe foes[MAX_FOES];
Effect effects[3];
uint16_t camera_x, score, play_frames, state_timer;
int16_t last_safe;
int8_t player_vy, facing;
uint8_t grounded, crouched, aiming, invuln, fire_timer, recoil;
uint8_t key, previous_key, pressed, next_encounter, boss_active, boss_timer;
uint8_t boss_open, boss_flash, boss_phase, banner, section, hud_dirty;
uint8_t oam_count, scanline_load[18], render_rotation, missed_frames;
uint16_t rendered_column;
uint8_t column_tiles[18], column_attrs[18], ui_tiles[40];
uint8_t core_color, column_pending, pending_bx, hud_pending, drawing_world;

/* Active mission data is cached once; gameplay uses bounded pools. */
volatile uint8_t mission_index;
const Mission *mission;
const Encounter *encounters;
const Platform *platforms;
const uint16_t *pit_left, *vents;
const uint8_t *pit_width, *boss_attributes;
uint16_t arena_left,boss_x,checkpoint_x,world_width,stage_entry_score;
uint16_t entry_ammo[3],boss_target_x;
uint8_t encounter_count,platform_count,pit_count,vent_count,entry_weapon;
uint8_t boss_cycle,boss_aim_y;

void load_mission(void) {
 if(mission_index>=MISSION_COUNT)mission_index=0;
 mission=&missions[mission_index];
 encounters=mission->encounters;platforms=mission->platforms;
 pit_left=mission->pits;pit_width=mission->pit_widths;vents=mission->vents;
 encounter_count=mission->encounter_count;platform_count=mission->platform_count;
 pit_count=mission->pit_count;vent_count=mission->vent_count;
 arena_left=mission->arena_left;boss_x=mission->boss_x;
 checkpoint_x=mission->checkpoint_x;world_width=mission->width;
 boss_attributes=mission_index==0?ironmaw_attrs:(mission_index==1?dredger_attrs:nullcore_attrs);
 set_bkg_palette(0,8,mission_index==0?bg_palettes:(mission_index==1?tidebreak_palettes:blackout_palettes));
 /* A title visit replaces the BG patterns. Always restore the complete world
  * and HUD atlas before loading this mission's shared boss range. */
 set_bkg_data(0,BG_TILES_COUNT,bg_tiles);
 if(mission_index)set_bkg_data(BOSS_TILE_START,BOSS_TILES_COUNT,mission_index==1?dredger_tiles:nullcore_tiles);
}
uint8_t in_pit(int16_t x) {
 uint8_t i;
 for(i=0;i<pit_count;i++) if(x>=pit_left[i] && x<pit_left[i]+pit_width[i])return 1;
 return 0;
}

uint8_t glyph(char c) {
 if(c>='A' && c<='Z') return c-'A'+1;
 if(c>='0' && c<='9') return c-'0'+27;
 if(c=='-') return 37;
 if(c==':') return 38;
 if(c=='+') return 39;
 if(c=='.') return 40;
 if(c=='/') return 41;
 if(c=='!') return 42;
 return 0;
}
void text_at(uint8_t x,uint8_t y,const char *s) {
 uint8_t a[20],n=0;
 while(*s && n<20-x) a[n++]=glyph(*s++);
 if(n) set_bkg_tiles(x,y,n,1,a);
}
void window_text(uint8_t x,uint8_t y,const char *s) {
 uint8_t a[20],n=0;
 while(*s && n<20-x) a[n++]=glyph(*s++);
 if(n) set_win_tiles(x,y,n,1,a);
}
void clear_window(uint8_t rows) {
 uint8_t x,y;
 hud_pending=0;
 memset(column_tiles,0,18); memset(column_attrs,7,18);
 for(y=0;y<rows;y++) {
  for(x=0;x<20;x++) {set_win_tile_xy(x,y,0);}
 }
 VBK_REG=1;
 for(y=0;y<rows;y++) for(x=0;x<20;x++) set_win_tile_xy(x,y,7);
 VBK_REG=0;
}
void screen_base(void) {
 uint8_t x,y,t;
 DISPLAY_OFF; HIDE_WIN; HIDE_SPRITES; move_bkg(0,0);
 column_pending=hud_pending=0;
 for(y=0;y<18;y++) for(x=0;x<20;x++) {
  t=0;
  if(y==1 || y==16) t=68;
  else if(x==0 || x==19) t=89;
  set_bkg_tile_xy(x,y,t);
 }
 VBK_REG=1;
 for(y=0;y<18;y++) for(x=0;x<20;x++) set_bkg_tile_xy(x,y,(y==1||y==16)?3:7);
 VBK_REG=0;
 SHOW_BKG; DISPLAY_ON;
}
void title_screen(void) {
 game_state=TITLE; checkpoint=0;mission_index=0;
 DISPLAY_OFF;HIDE_WIN;HIDE_SPRITES;move_bkg(0,0);
 column_pending=hud_pending=0;
 set_bkg_data(0,TITLE_TILES_COUNT,title_tiles);
 set_bkg_palette(0,TITLE_PALETTES_COUNT,title_palettes);
 set_bkg_tiles(0,0,20,18,title_map);
 VBK_REG=1;set_bkg_tiles(0,0,20,18,title_attrs);VBK_REG=0;
 SHOW_BKG;DISPLAY_ON;
 audio_music(1);
}
void result_screen(uint8_t win) {
 screen_base();
 if(win) {
  text_at(1,4,win==2?"MISSION COMPLETE":"CAMPAIGN COMPLETE");
  text_at(4,6,mission->boss_name);text_at(6,7,"OFFLINE");
  if(win==2) {
   text_at(4,8,"NEXT MISSION");text_at(5,9,missions[mission_index+1].operation+10);
   text_at(3,12,"A NEXT MISSION");
  } else {
   text_at(3,9,"NETWORK DISABLED");text_at(3,12,"A PLAY AGAIN");
  }
  audio_music(4);audio_sfx(SFX_VICTORY);
 } else {
  text_at(5,4,"ROOK DOWN");text_at(5,6,mission->operation+10);
  if(checkpoint)text_at(2,9,"A BOSS CHECKPOINT");else text_at(3,9,"A RETRY MISSION");
  text_at(3,12,"START TITLE");audio_music(0);
 }
}
/* A 32-column circular tile map streams only the newly visible column. */
void world_column(uint16_t col) {
 uint8_t y,t,a,i,bx=(uint8_t)(col&31),zone,platform_row=255,platform_tile=0;
 uint8_t c13=col%13,c17=col%17,c19=col%19,c7=col%7,c11=col%11,pit,vent=0,edge=0;
 uint16_t wx=col<<3;
 zone=wx<mission->section_b?0:(wx<mission->section_c?1:2);
 pit=in_pit(wx+4);
 for(i=0;i<vent_count;i++)if(wx==vents[i])vent=1;
 for(i=0;i<pit_count;i++)if(wx+8==pit_left[i]||wx==pit_left[i]+pit_width[i])edge=1;
 for(i=0;i<platform_count;i++) if(wx>=platforms[i].x && wx<platforms[i].x+platforms[i].width) {
  platform_row=platforms[i].y>>3;
  platform_tile=wx==platforms[i].x?51:(wx+8>=platforms[i].x+platforms[i].width?53:52);
  break;
 }
 for(y=0;y<18;y++) {
  t=0;a=0;
  /* Distant factories continue behind the near walls down to ground level.
   * A consistent roof row avoids the old floating, castle-like silhouette. */
  if(y>=5&&y<15&&c13<8){t=y==5?TILE_SKYLINE_TOP:((col&3)==1?TILE_SKYLINE_DETAIL:TILE_SKYLINE);}
  if(y<3) {if(((col+2*y)&31)==0) t=59;}
  else if(y<8) {
   if(y==4&&(c13==2||c13==6))t=TILE_CHIMNEY;
  } else if(y<15) {
   if(zone==0) {
    if(c17<11) {t=54;a=1;if((y&1)==1&&(col&3)==2)t=55;if(y==10&&c17==5)t=66;}
    if(y==14&&c7==0) {t=60;a=2;}
   } else if(zone==1) {
    t=80;a=1;
    if(y<13 && c19<13) {t=54;if(y==9&&(col&3)==1)t=56;}
    if(y==13 && c19<10) {t=61;a=4;}
    if(c19==10&&y>=10) {t=62;a=4;}
    if(y==14&&(col&7)==2){t=79;a=2;}
   } else {
    t=95;a=1;
    if((col&7)==0){t=84;a=4;}
    if(y==8){t=87;a=4;}
    if(y>9&&(col%12)>2&&(col%12)<8){t=90;a=1;if(y==11)t=91;}
    if(y==14&&c11==3){t=85;a=2;}
   }
  } else {t=y==15?48:49;a=3;}
  /* Tidebreak: open water, gantry cables, containers and suspended docks. */
  if(mission_index==1) {
   if(y<4){t=0;a=0;if(((col+2*y)&31)==0)t=59;}
   else if(y<8){t=0;a=0;if((col&15)==3){t=84;a=4;}if(y==4&&(col&15)<12){t=87;a=4;}}
   else if(y<13){
    t=0;a=0;
    if((col&15)<10 && y>=10){t=TILE_CONTAINER;a=1;if(y==10)t=89;}
    if((col&15)==3){t=62;a=4;}
    if(zone==1&&y==8){t=83;a=4;}
   } else if(y<15){t=y==13?61:80;a=4;}
   else {t=y==15?70:69;a=3;}
  }
  /* Blackout: an enclosed reactor hall with coolant pipes and consoles. */
  if(mission_index==2) {
   if(y<15){
    t=95;a=0;
    if((col&3)==3)t=TILE_PANEL_EDGE;
    if(y==4||y==11)t=TILE_PANEL_SEAM;
    if(y==1||y==7){t=61;a=4;}
    if((col&7)==0){t=62;a=4;}
    if(y>=9 && y<=13 && (col&15)>3 && (col&15)<12){t=90;a=1;}
    if(y==10&&(col&3)==2){t=56;a=2;}
    if(y==12&&(col&15)==7){t=91;a=2;}
    if(y==14&&(col&7)==3){t=85;a=2;}
   } else {t=y==15?92:49;a=3;}
  }
  /* A gap must not have a platform-like bright top edge. Harbor gaps show
   * recessed water ripples; city/reactor gaps remain open dark shafts. */
  if(pit && y>=15) {t=mission_index==1?TILE_WATER:TILE_VOID;a=0;}
  if(edge&&y==15){t=50;a=3;}
  if(y==platform_row){t=platform_tile;a=3;}
  if(vent&&y==14){t=67;a=3;}
  if(wx>=boss_x && wx<boss_x+64 && y>=7&&y<15) {
   i=(y-7)*8+((wx-boss_x)>>3);t=ironmaw_map[i];a=boss_attributes[i];
  }
  column_tiles[y]=t;column_attrs[y]=a;
 }
 if(drawing_world) {
  set_bkg_tiles(bx,0,1,18,column_tiles);
  VBK_REG=1;set_bkg_tiles(bx,0,1,18,column_attrs);VBK_REG=0;
 } else {pending_bx=bx;column_pending=1;}
}
void redraw_world(void) {
 uint8_t i;
 DISPLAY_OFF;drawing_world=1;column_pending=0;
 for(i=0;i<32;i++) world_column((camera_x>>3)+i);
 drawing_world=0;rendered_column=camera_x>>3;
 move_bkg((uint8_t)camera_x,0);
 DISPLAY_ON;
}
void update_camera(void) {
 uint16_t target,co;
 target=player_x>64?player_x-64:0;
 if(target>arena_left)target=arena_left;
 /* Forward progression is deliberate; permit 48px retreat within view. */
 if(target>camera_x) camera_x=target;
 co=camera_x>>3;
 if(co>rendered_column+4){redraw_world();return;}
 while(rendered_column<co) {rendered_column++;world_column(rendered_column+20);}
 move_bkg((uint8_t)camera_x,0);
}
uint8_t hud_glyph(char c) {
 if(c>='A'&&c<='Z')return TILE_UI_LABEL_A+c-'A';
 if(c>='0'&&c<='9')return TILE_UI_SCORE_0+c-'0';
 return glyph(c);
}
void hud(void) {
 uint8_t i,idx,fill;
 uint16_t h;
 memset(ui_tiles,0,40);
 for(i=0;i<3;i++)ui_tiles[1+i]=i<hp?TILE_UI_HP_FULL:TILE_UI_HP_EMPTY;
 ui_tiles[13]=TILE_UI_PISTOL+weapon*2;ui_tiles[14]=ui_tiles[13]+1;
 h=weapon?ammo[weapon]:0;
 if(weapon) {ui_tiles[16]=27+h/100;ui_tiles[17]=27+(h/10)%10;ui_tiles[18]=27+h%10;}
 else ui_tiles[17]=TILE_UI_INFINITY;
 ui_tiles[7]=TILE_UI_SCORE_0+score/10000;ui_tiles[8]=TILE_UI_SCORE_0+(score/1000)%10;
 ui_tiles[9]=TILE_UI_SCORE_0+(score/100)%10;ui_tiles[10]=TILE_UI_SCORE_0+(score/10)%10;ui_tiles[11]=TILE_UI_SCORE_0+score%10;
 if(boss_active) {
  const char *s=mission->boss_name;for(i=0;*s&&i<8;i++)ui_tiles[20+i]=hud_glyph(*s++);
  /* Scale to 96 pixels, rounding upward so a living boss never shows zero. */
  h=mission->boss_health==48?((uint16_t)boss_hp<<1):
    ((uint16_t)boss_hp*96u+mission->boss_health-1)/mission->boss_health;
  for(i=0;i<12;i++) {
   fill=h>8?8:(uint8_t)h;
   ui_tiles[28+i]=TILE_UI_BAR_EMPTY+fill;h-=fill;
  }
 } else {
  const char *s;
  if(banner)s=checkpoint?"CHECKPOINT - READY":mission->operation;
  else {ui_tiles[20]=27+mission_index+1;ui_tiles[21]=37;s=mission->section_names[section<3?section:2];}
  if(!banner){idx=22;}else idx=20;
  for(;*s&&idx<40;idx++)ui_tiles[idx]=hud_glyph(*s++);
 }
 hud_pending=1;hud_dirty=0;
}
void start_mission(uint8_t retry) {
 uint8_t i;
 DISPLAY_OFF;HIDE_SPRITES;HIDE_WIN;column_pending=hud_pending=0;
 load_mission();
 memset(shots,0,sizeof(shots));memset(hostile,0,sizeof(hostile));
 memset(foes,0,sizeof(foes));memset(effects,0,sizeof(effects));
 hp=3;facing=1;player_vy=0;grounded=1;crouched=0;aiming=0;
 invuln=100;fire_timer=0;recoil=0;boss_active=0;boss_hp=mission->boss_health;boss_timer=90;
 boss_phase=1;boss_open=0;boss_flash=0;core_color=255;boss_cycle=0;
 boss_target_x=arena_left+24;boss_aim_y=110;
 game_state=PLAY;state_timer=0;banner=100;hud_dirty=1;play_frames=0;
 if(!retry) {
  stage_entry_score=score;entry_weapon=weapon;
  for(i=0;i<3;i++)entry_ammo[i]=ammo[i];
 } else {
  score=stage_entry_score;weapon=entry_weapon;
  for(i=0;i<3;i++)ammo[i]=entry_ammo[i];
 }
 if(retry && checkpoint) {
  player_x=arena_left+16;camera_x=arena_left;next_encounter=encounter_count;section=3;
  ammo[MACHINEGUN]=100;ammo[ROCKET]=8;weapon=MACHINEGUN;boss_active=1;
 } else {
  checkpoint=0;player_x=24;camera_x=0;next_encounter=0;section=0;
 }
 player_y=(FLOOR_Y-16)<<4;last_safe=player_x;
 set_sprite_palette(0,8,sprite_palettes);
 for(i=0;i<40;i++)hide_sprite(i);
 clear_window(2);move_win(7,128);hud();
 redraw_world();SHOW_SPRITES;SHOW_WIN;audio_pause(0);
 audio_music(boss_active?MUSIC_BOSS:(mission_index==0?MUSIC_LEVEL:(mission_index==1?MUSIC_DOCKS:MUSIC_REACTOR)));
}
void begin_campaign(void) {
 mission_index=0;checkpoint=0;score=0;weapon=PISTOL;
 ammo[0]=ammo[1]=ammo[2]=0;
 start_mission(0);
}
void next_mission(void) {
 if(mission_index+1>=MISSION_COUNT)return;
 mission_index++;checkpoint=0;
 if(ammo[MACHINEGUN]<50)ammo[MACHINEGUN]=50;
 if(ammo[ROCKET]<4)ammo[ROCKET]=4;
 if(weapon==PISTOL || !ammo[weapon])weapon=MACHINEGUN;
 start_mission(0);
}
void effect(int16_t x,uint8_t y,uint8_t duration) {
 uint8_t i;
 for(i=0;i<3;i++)if(!effects[i].life){effects[i].x=x;effects[i].y=y;effects[i].life=duration;return;}
}
void hurt_player(void) {
 if(invuln || game_state!=PLAY)return;
 hp--;hud_dirty=1;invuln=90;audio_sfx(SFX_DAMAGE);recoil=0;
 if(hp==0){game_state=DYING;state_timer=54;player_vy=-32;audio_music(0);}
}
uint8_t overlaps(int16_t ax,int16_t ay,uint8_t aw,uint8_t ah,int16_t bx,int16_t by,uint8_t bw,uint8_t bh) {
 return ax<bx+bw && ax+aw>bx && ay<by+bh && ay+ah>by;
}
void add_hostile(int16_t x,int16_t y,int8_t dx,int8_t dy,uint8_t type) {
 uint8_t i;
 for(i=0;i<MAX_HOSTILE;i++)if(!hostile[i].life){
  hostile[i].x=x;hostile[i].y=y;hostile[i].dx=dx;hostile[i].dy=dy;
  hostile[i].life=100;hostile[i].type=type;hostile[i].damage=1;return;
 }
}
void fire(void) {
 uint8_t i;
 if(fire_timer || !(key&J_B)) return;
 if(weapon && !ammo[weapon]) {weapon=PISTOL;hud_dirty=1;}
 for(i=0;i<MAX_SHOTS;i++)if(!shots[i].life) {
  shots[i].x=player_x+(aiming?(facing>0?7:8):(facing>0?16:-5));
  shots[i].y=(player_y>>4)+(aiming?-8:(crouched?12:7));
  shots[i].dx=aiming?0:facing*(weapon==ROCKET?3:5);
  shots[i].dy=aiming?-4:0;
  shots[i].life=45;shots[i].type=weapon;
  shots[i].damage=weapon==ROCKET?6:1;
  fire_timer=weapon==PISTOL?13:(weapon==MACHINEGUN?5:28);
  recoil=4;if(weapon)ammo[weapon]--;
  audio_sfx(weapon==PISTOL?SFX_PISTOL:(weapon==MACHINEGUN?SFX_MG:SFX_ROCKET));hud_dirty=1;return;
 }
}
void move_player(void) {
 int16_t before,after,px,ground;
 const Platform *platform;
 uint8_t i;
 if(invuln)invuln--;if(fire_timer)fire_timer--;if(recoil)recoil--;
 crouched=(key&J_DOWN)&&grounded;
 aiming=(key&J_UP)&&!crouched;
 if(!crouched) {
  if(key&J_LEFT){player_x-=1+(play_frames&1);facing=-1;}
  if(key&J_RIGHT){player_x+=1+(play_frames&1);facing=1;}
 }
 if(player_x<camera_x+2)player_x=camera_x+2;
 if(boss_active && player_x>boss_x-18)player_x=boss_x-18;
 if((pressed&J_A)&&grounded){player_vy=-72;grounded=0;crouched=0;audio_sfx(SFX_JUMP);}
 before=(player_y>>4)+16;
 if(player_vy<64)player_vy+=4;
 player_y+=player_vy;after=(player_y>>4)+16;
 ground=200;px=player_x+8;
 if(!in_pit(px))ground=FLOOR_Y;
 if(player_vy>=0)for(platform=platforms;platform<platforms+platform_count;platform++) {
  if(before<=platform->y && after>=platform->y && platform->y<ground && px+5>platform->x && px-5<platform->x+platform->width) ground=platform->y;
 }
 grounded=0;
 if(player_vy>=0 && before<=ground && after>=ground) {
  player_y=(ground-16)<<4;player_vy=0;grounded=1;
  if(ground==FLOOR_Y && !in_pit(player_x-8) && !in_pit(player_x+24)) last_safe=player_x;
 }
 if((player_y>>4)>150) {
  /* Falls always recover; invulnerability does not block repositioning. */
  hurt_player();player_x=last_safe<camera_x+2?camera_x+2:last_safe;
  if(in_pit(player_x+8))player_x+=48;
  player_y=(FLOOR_Y-16)<<4;player_vy=0;grounded=1;
 }
 if((pressed&J_SELECT)) {
  for(i=1;i<=3;i++){uint8_t w=(weapon+i)%3;if(w==0||ammo[w]){weapon=w;break;}}
  hud_dirty=1;audio_sfx(SFX_MENU);
 }
 fire();
 /* Predictable steam vents: 96 safe frames, 32 active frames. */
 if((play_frames&127)>95 && grounded && (player_y>>4)>=100) {
  for(i=0;i<vent_count;i++)if(player_x+13>vents[i]&&player_x<vents[i]+8)hurt_player();
 }
}
void spawn_encounters(void) {
 uint8_t i;
 const Encounter *e;
 while(next_encounter<encounter_count) {
  e=&encounters[next_encounter];
  if(e->x>player_x+144)return;
  for(i=0;i<MAX_FOES;i++)if(!foes[i].active)break;
  if(i==MAX_FOES)return;
  foes[i].x=e->x;foes[i].home=e->x;foes[i].y=e->y;foes[i].type=e->type;
  foes[i].hp=e->type==TURRET?4:(e->type==CRATE?3:2);
  foes[i].active=1;foes[i].dir=-1;foes[i].timer=80+i*19;
  foes[i].hit=0;foes[i].anim=0;foes[i].drop=e->drop;
  next_encounter++;
 }
}
void defeat_foe(uint8_t i) {
 Foe *e=&foes[i];
 effect(e->x,e->y,24);score+=e->type==CRATE?25:100;hud_dirty=1;audio_sfx(SFX_EXPLOSION);
 if(e->type==CRATE){e->type=e->drop;e->hp=1;e->timer=0;e->hit=0;}
 else e->active=0;
}
void update_foes(void) {
 uint8_t i;
 int16_t dist,py;
 Foe *e;
 /* Keep the forgiving torso/leg hurtbox: the crested helmet is cosmetic. */
 py=(player_y>>4)+(crouched?8:2);
 for(i=0;i<MAX_FOES;i++) {
  e=&foes[i];if(!e->active)continue;
  if(e->x+16<(int16_t)camera_x-8){e->active=0;continue;}
  if(e->x>camera_x+176)continue;
  if(e->hit)e->hit--;
  if(e->type>=ITEM_MG) {
   if(overlaps(player_x+3,py,10,crouched?8:14,e->x,e->y,16,16)) {
    if(e->type==ITEM_HEAL){hp=3;}
    else {weapon=e->type==ITEM_MG?MACHINEGUN:ROCKET;ammo[weapon]+=weapon==MACHINEGUN?100:8;if(ammo[weapon]>999)ammo[weapon]=999;}
    audio_sfx(SFX_PICKUP);e->active=0;hud_dirty=1;
   }continue;
  }
  if(e->type==CRATE)continue;
  e->anim++;dist=player_x-e->x;
  if(e->type==INFANTRY && (dist>112||dist<-112)) {
   if((play_frames&3)==0){
    e->x+=e->dir;
    if(e->x<=e->home-20){e->x=e->home-20;e->dir=1;}
    if(e->x>=e->home+20){e->x=e->home+20;e->dir=-1;}
   }
  } else e->dir=dist>=0?1:-1;
  if(e->type==DRONE) {
   if((play_frames&3)==0){e->x+=e->dir;if(e->x<e->home-40)e->x=e->home-40;if(e->x>e->home+40)e->x=e->home+40;}
   e->y=72+((e->anim>>3)&7); /* Small, deterministic hover path. */
  }
  if(e->timer)e->timer--;
  if(!e->timer && e->x>=camera_x+8 && e->x<camera_x+152 && dist>-140&&dist<140) {
   add_hostile(e->x+(e->dir>0?16:0),e->y+6,e->dir*2,e->type==DRONE?1:0,0);
   e->timer=e->type==TURRET?112:(e->type==DRONE?120:145);
  }
  if(overlaps(player_x+3,py,10,crouched?8:14,e->x+2,e->y+2,12,14))hurt_player();
 }
}
void boss_death(void) {
 game_state=BOSS_DYING;state_timer=110;
 memset(hostile,0,sizeof(hostile));memset(shots,0,sizeof(shots));
 audio_music(0);audio_sfx(SFX_EXPLOSION);score+=1000;hud_dirty=1;
}
void update_projectiles(void) {
 uint8_t i,j;
 Shot *s;Foe *e;
 int16_t py=(player_y>>4)+(crouched?8:2);
 for(i=0;i<MAX_SHOTS;i++) {
  s=&shots[i];if(!s->life)continue;
  s->life--;s->x+=s->dx;s->y+=s->dy;
  if(s->x<(int16_t)camera_x-8||s->x>camera_x+168||s->y<0||s->y>FLOOR_Y){s->life=0;continue;}
  for(j=0;j<MAX_FOES;j++) {
   e=&foes[j];if(!e->active||e->type>=ITEM_MG)continue;
   if(overlaps(s->x,s->y,s->type==ROCKET?8:4,3,e->x+1,e->y+1,14,15)) {
    e->hit=7;s->life=0;
    if(e->hp<=s->damage)defeat_foe(j);
    else{e->hp-=s->damage;audio_sfx(SFX_IMPACT);effect(s->x,s->y,8);}
    break;
   }
  }
  if(s->life&&boss_active && s->x+4>=boss_x && s->x<boss_x+64 && s->y>=56 && s->y<120) {
   s->life=0;
   if(boss_open&&s->y>=80&&s->y<100) {
    if(boss_hp<=s->damage){boss_hp=0;boss_death();return;}
    boss_hp-=s->damage;boss_flash=6;score+=10;hud_dirty=1;audio_sfx(SFX_IMPACT);
   } else audio_sfx(SFX_IMPACT);
   effect(s->x,s->y,s->type==ROCKET?20:8);
  }
 }
 for(i=0;i<MAX_HOSTILE;i++) {
  s=&hostile[i];if(!s->life)continue;
  s->life--;s->x+=s->dx;s->y+=s->dy;
  if(s->x<(int16_t)camera_x-8||s->x>camera_x+168||s->y<0||s->y>124){s->life=0;continue;}
  if(overlaps(s->x,s->y,4,4,player_x+3,py,10,crouched?8:14)) {s->life=0;hurt_player();}
 }
}
void update_boss(void) {
 uint8_t wanted,interval,opening;
 if(!boss_active)return;
 boss_phase=boss_hp<=24?2:1;
 interval=mission_index==0?(boss_phase==1?104:78):
          (mission_index==1?(boss_phase==1?112:86):(boss_phase==1?108:82));
 opening=mission_index==0?(boss_phase==1?76:52):
         (mission_index==1?(boss_phase==1?84:60):(boss_phase==1?80:56));
 if(boss_timer)boss_timer--;
 boss_open=boss_timer>12 && boss_timer<opening;
 if(boss_timer==12) {
  /* Lock the target before firing; the warning gives time to move away. */
  boss_target_x=player_x+8;
  if(boss_target_x<camera_x+8)boss_target_x=camera_x+8;
  if(boss_target_x>boss_x-24)boss_target_x=boss_x-24;
  boss_aim_y=(player_y>>4)+7;
  if(boss_aim_y<64)boss_aim_y=64;
  if(boss_aim_y>110)boss_aim_y=110;
 }
 if(!boss_timer) {
  if(mission_index==0) {
   add_hostile(boss_x-5,110,-2,0,1);
   if(boss_phase==2){add_hostile(boss_x-5,86,-2,1,1);add_hostile(boss_x-5,64,-2,1,1);}
  } else if(mission_index==1) {
   /* DREDGER: cannon plus a telegraphed vertical depth charge. */
   add_hostile(boss_x-5,110,-2,0,1);
   if(boss_phase==2)add_hostile(boss_x-5,82,-2,1,1);
   if((boss_cycle&1)||boss_phase==2)add_hostile(boss_target_x,16,0,2,2);
  } else {
   /* NULLCORE: a height-locked scan beam, then a three-height fan. */
   add_hostile(boss_x-5,boss_aim_y,-3,0,3);
   if(boss_phase==2){add_hostile(boss_x-5,110,-2,0,3);add_hostile(boss_x-5,64,-2,1,3);}
  }
  boss_cycle++;boss_timer=interval;audio_sfx(SFX_ROCKET);
 }
 if(boss_flash)boss_flash--;
 wanted=boss_flash?2:(boss_open?1:0);
 if(wanted!=core_color) {
  uint16_t color;
  core_color=wanted;
  if(wanted==2)color=RGB(31,31,31);
  else if(wanted==1)color=mission_index==0?RGB(31,23,3):(mission_index==1?RGB(9,31,28):RGB(31,7,13));
  else color=mission_index==0?RGB(10,6,4):(mission_index==1?RGB(3,10,10):RGB(10,3,7));
  set_bkg_palette_entry(6,3,color);
 }
 if(boss_phase==2)set_bkg_palette_entry(5,2,mission_index==0?RGB(25,9,5):(mission_index==1?RGB(7,17,19):RGB(20,6,12)));
}
/* Reserve conservative eight-scanline bands before committing OAM.
   An 8x16 sprite touches two or three bands: no band exceeds ten entries.
   This guarantees the real scanline limit without 144-byte per-frame work. */
uint8_t sprite_piece(int16_t sx,int16_t sy,uint8_t tile,uint8_t prop) {
 uint8_t y0,y1,y;
 if(sx<=-8||sx>=160||sy<=-16||sy>=128||oam_count>=40)return 0;
 y0=sy<0?0:((uint8_t)sy>>3);y1=(uint8_t)(sy+15)>>3;if(y1>15)y1=15;
 for(y=y0;y<=y1;y++)if(scanline_load[y]>=10)return 0;
 for(y=y0;y<=y1;y++)scanline_load[y]++;
 set_sprite_tile(oam_count,tile);set_sprite_prop(oam_count,prop);
 move_sprite(oam_count,(uint8_t)(sx+8),(uint8_t)(sy+16));oam_count++;return 1;
}
void actor(int16_t x,int16_t y,uint8_t art,uint8_t pal,int8_t dir) {
 int16_t sx=x-camera_x;
 uint8_t flip=dir<0?S_FLIPX:0,t=art*4;
 sprite_piece(sx,y,t+(dir<0?2:0),pal|flip);
 sprite_piece(sx+8,y,t+(dir<0?0:2),pal|flip);
}
/* Standing ROOK uses a 16px upper block and an 8px visible lower block.
 * Transparent lower padding preserves the existing foot/physics anchor.
 * Raw tile IDs 100..127 end immediately before signed BG storage at 0x8800. */
void rook_actor(uint8_t pose) {
 int16_t x=player_x-camera_x,y=player_y>>4;
 uint8_t flip=facing<0?S_FLIPX:0,footflip=flip,t,feet=ROOK_FEET_IDLE;
 if(pose==4||pose==6){actor(player_x,y,pose,0,facing);return;}
 t=pose==8?ROOK_RUN_C:(pose==9?ROOK_RUN_D:pose*4);
 if(pose==3)feet=ROOK_FEET_JUMP;
 else if(pose==1||pose==8)feet=ROOK_FEET_RUN;
 else if(pose==2||pose==9)feet=ROOK_FEET_PASS;
 if(pose==8||pose==9)footflip^=S_FLIPX;
 /* Recoil changes the braced upper pose while the running legs keep cycling. */
 if(recoil&&invuln<=82&&pose!=3&&pose!=7)t=ROOK_SHOOT;
 sprite_piece(x,y-8,t+(flip?2:0),flip);
 sprite_piece(x+8,y-8,t+(flip?0:2),flip);
 sprite_piece(x,y+8,feet+(footflip?2:0),footflip);
 sprite_piece(x+8,y+8,feet+(footflip?0:2),footflip);
}
/* Commit one complete shadow-OAM layout before the VBlank DMA can copy it.
 * Larger ROOK poses make a mixed old/new layout exceed the scanline limit. */
void render(void) __critical {
 uint8_t i,n,a,p,art;
 Foe *e;Shot *s;
 memset(scanline_load,0,sizeof(scanline_load));oam_count=0;
 if(game_state==DYING)art=6;
 else if(invuln>82)art=5;
 else if(crouched)art=4;
 else if(aiming)art=7;
 else if(!grounded)art=3;
 else if(key&(J_LEFT|J_RIGHT)){a=(play_frames>>2)&3;art=a<2?1+a:6+a;}
 else art=0;
 if(game_state==DYING||!invuln||((invuln&4)==0))rook_actor(art);
 for(n=0;n<MAX_FOES;n++) {
  i=(n+render_rotation)%MAX_FOES;e=&foes[i];if(!e->active)continue;
  if(e->type==INFANTRY){a=8+((e->anim>>4)&1);p=1;}
  else if(e->type==TURRET){a=10;p=2;}
  else if(e->type==DRONE){a=11+((e->anim>>3)&1);p=3;}
  else{a=13+(e->type-CRATE);p=e->type==ITEM_HEAL?3:4;}
  if(e->hit)p=5;
  actor(e->x,e->y,a,p,e->dir);
  if(e->type<CRATE&&e->timer<16)sprite_piece(e->x-camera_x+4,e->y-10,96,7);
 }
 /* Rotate equal-priority bullets when a scanline is busy. */
 for(n=0;n<MAX_HOSTILE;n++) {
  i=(n+(render_rotation%MAX_HOSTILE))%MAX_HOSTILE;s=&hostile[i];if(s->life)
   sprite_piece(s->x-camera_x,s->y-5,92,7|(s->dx<0?S_FLIPX:0));
 }
 for(n=0;n<MAX_SHOTS;n++) {
  i=(n+(render_rotation&7))&7;s=&shots[i];if(s->life)
   sprite_piece(s->x-camera_x-(s->dy?3:0),s->y-7,80+s->type*4+(s->dy?2:0),6|(s->dx<0?S_FLIPX:0));
 }
 if(boss_active&&mission_index==1&&boss_timer>0&&boss_timer<=12)sprite_piece(boss_target_x-camera_x,8,96,7);
 for(i=0;i<3;i++)if(effects[i].life) {
  art=17+(effects[i].life>16?0:(effects[i].life>8?1:2));actor(effects[i].x,effects[i].y,art,5,1);
 }
 if(recoil&&invuln<=82&&game_state==PLAY) {
  sprite_piece(player_x-camera_x+(aiming?(facing>0?4:5):(facing>0?12:-3)),
    (player_y>>4)+(aiming?-16:(crouched?4:-1)),96,5);
 }
 if((play_frames&127)>88) {
  for(i=0;i<vent_count;i++)if(vents[i]>=camera_x&&vents[i]<camera_x+160)sprite_piece(vents[i]-camera_x,104,68,5);
 }
 for(i=oam_count;i<40;i++)hide_sprite(i);
 render_rotation++;
}
void pause_game(void) {
 game_state=PAUSED;audio_pause(1);HIDE_SPRITES;
 clear_window(8);move_win(7,40);
 window_text(7,1,"PAUSED");window_text(2,3,"START TO RESUME");
 /* SELECT only cycles weapons during play; do not advertise it here. */
}
void resume_game(void) {
 clear_window(2);move_win(7,128);hud();SHOW_SPRITES;
 game_state=PLAY;audio_pause(0);
}
void progress(void) {
 uint8_t s=player_x<mission->section_b?0:(player_x<mission->section_c?1:(player_x<arena_left?2:3));
 if(s!=section){section=s;hud_dirty=1;}
 if(player_x>=checkpoint_x&&!checkpoint){checkpoint=1;hp=3;ammo[1]=100;ammo[2]=8;banner=120;hud_dirty=1;audio_sfx(SFX_PICKUP);}
 if(player_x>=arena_left+16&&!boss_active){
  boss_active=1;boss_timer=90;camera_x=arena_left;redraw_world();
  memset(foes,0,sizeof(foes));memset(hostile,0,sizeof(hostile));
  hud_dirty=1;audio_music(3);
 }
}
void tick_play(void) {
 uint8_t i;
 play_frames++;
 if(pressed&J_START){pause_game();return;}
 if(banner){banner--;if(!banner)hud_dirty=1;}
 for(i=0;i<3;i++)if(effects[i].life)effects[i].life--;
 move_player();if(game_state!=PLAY){render();return;}
 progress();update_camera();
 if(!boss_active){spawn_encounters();update_foes();}
 update_boss();update_projectiles();
 if(hud_dirty || (play_frames&31)==0)hud();
 render();
}
void main(void) {
 uint8_t i;
 DISPLAY_OFF;
 if(_cpu==CGB_TYPE)cpu_fast();
 SPRITES_8x16;
 set_bkg_data(0,BG_TILES_COUNT,bg_tiles);
 set_sprite_data(0,SPRITE_TILES_COUNT,sprite_tiles);
 set_bkg_palette(0,8,bg_palettes);set_sprite_palette(0,8,sprite_palettes);
 audio_init();title_screen();
 previous_key=0;
 while(1) {
  wait_vbl_done();frame++;
  if(column_pending) {
   set_bkg_tiles(pending_bx,0,1,18,column_tiles);
   VBK_REG=1;set_bkg_tiles(pending_bx,0,1,18,column_attrs);VBK_REG=0;column_pending=0;
  }
  if(hud_pending) {
   set_win_tiles(0,0,20,2,ui_tiles);
   hud_pending=0;
  }
  key=joypad();pressed=key&~previous_key;
  audio_tick();
  switch(game_state) {
   case TITLE: if(pressed&(J_START|J_A)){audio_sfx(SFX_MENU);begin_campaign();}break;
   case PLAY:tick_play();break;
   case PAUSED:if(pressed&J_START)resume_game();break;
   case DYING:
    play_frames++;if(player_vy<48)player_vy+=4;player_y+=player_vy;
    render();if(state_timer)state_timer--;if(!state_timer){game_state=GAMEOVER;result_screen(0);}break;
   case GAMEOVER:
    if(pressed&J_A)start_mission(1);else if(pressed&J_START)title_screen();break;
   case BOSS_DYING:
    play_frames++;
    if((state_timer&7)==0){effect(boss_x+((state_timer*7)&47),56+((state_timer*3)&47),24);audio_sfx(SFX_EXPLOSION);}
    for(i=0;i<3;i++)if(effects[i].life)effects[i].life--;
    if((state_timer&7)==0){set_bkg_palette_entry(5,3,(state_timer&8)?RGB(31,27,15):RGB(7,5,4));}
    render();if(state_timer)state_timer--;
    if(!state_timer){game_state=mission_index+1<MISSION_COUNT?STAGE_CLEAR:VICTORY;result_screen(game_state==STAGE_CLEAR?2:1);}break;
   case STAGE_CLEAR:
    if(pressed&J_A)next_mission();else if(pressed&J_START)title_screen();break;
   case VICTORY:
    if(pressed&J_A)begin_campaign();else if(pressed&J_START)title_screen();break;
   default:title_screen();break;
  }
  previous_key=key;
 }
}
