/* Authored campaign maps. Add a descriptor to extend the campaign. */
#include "missions.h"
#define COUNT(a) (sizeof(a)/sizeof((a)[0]))
static const Encounter cinder_encounters[] = {
 {176,104,INFANTRY,0},{320,104,INFANTRY,0},{432,104,CRATE,ITEM_MG},
 {544,104,INFANTRY,0},{640,104,INFANTRY,0},{816,104,TURRET,0},
 {920,104,ITEM_HEAL,0},{1024,104,TURRET,0},{1136,104,INFANTRY,0},
 {1280,104,CRATE,ITEM_ROCKET},{1392,104,TURRET,0},{1600,104,INFANTRY,0},
 {1696,104,ITEM_MG,0},{1792,78,DRONE,0},{1904,104,INFANTRY,0},
 {2000,104,TURRET,0},{2096,72,DRONE,0},{2304,104,CRATE,ITEM_HEAL},
 {2384,78,DRONE,0},{2528,104,INFANTRY,0},{2640,104,TURRET,0},
 {2720,72,DRONE,0},{2848,104,CRATE,ITEM_ROCKET},{3008,104,INFANTRY,0},
 {3104,104,ITEM_MG,0}
};
static const Platform cinder_platforms[] = {
 {368,64,96},{640,128,96},{976,64,96},{1056,48,80},{1440,144,96},
 {1744,80,96},{1968,64,96},{2160,128,96},{2416,80,96},{2656,80,96},
 {2880,128,96},{3152,64,96}
};
static const uint16_t cinder_pits[]={712,1512,2200,2928};
static const uint8_t cinder_widths[]={32,32,40,40};
static const uint16_t cinder_vents[]={1184,2464};

/* Dock aprons lead to suspended canal bridges and the harbor pump station.
   Two batteries are mounted on platforms, changing the height of incoming fire. */
static const Encounter tidebreak_encounters[] = {
 {176,104,INFANTRY,0},{288,104,CRATE,ITEM_MG},{368,104,TURRET,0},
 {528,76,DRONE,0},{640,104,INFANTRY,0},{784,104,ITEM_HEAL,0},
 {896,80,TURRET,0},{1152,104,CRATE,ITEM_ROCKET},{1280,104,INFANTRY,0},
 {1392,72,DRONE,0},{1472,104,TURRET,0},{1680,64,INFANTRY,0},
 {1840,104,TURRET,0},{1984,72,DRONE,0},{2112,104,CRATE,ITEM_HEAL},
 {2352,104,INFANTRY,0},{2464,104,CRATE,ITEM_ROCKET}
};
static const Platform tidebreak_platforms[] = {
 {160,64,96},{432,112,96},{864,128,96},{960,96,80},{1120,64,96},
 {1536,144,96},{1664,64,80},{1936,96,96},{2160,128,96},
 {2392,64,96},{2528,48,96}
};
static const uint16_t tidebreak_pits[]={464,1008,1600,2200};
static const uint8_t tidebreak_widths[]={32,40,40,40};
static const uint16_t tidebreak_vents[]={704,1344,1888};

/* Reactor hall: overhead machinery, vent timing, and elevated batteries.
   Supplies break up the dangerous stretches before the command vault. */
static const Encounter blackout_encounters[] = {
 {160,72,DRONE,0},{256,104,CRATE,ITEM_MG},{368,104,INFANTRY,0},
 {480,104,TURRET,0},{640,104,CRATE,ITEM_HEAL},{768,72,DRONE,0},
 {1024,80,TURRET,0},{1168,104,INFANTRY,0},{1328,104,CRATE,ITEM_ROCKET},
 {1456,72,DRONE,0},{1648,104,TURRET,0},{1792,80,INFANTRY,0},
 {1904,72,DRONE,0},{2096,104,ITEM_HEAL,0},{2240,104,TURRET,0},
 {2352,72,DRONE,0},{2496,104,INFANTRY,0},{2592,104,CRATE,ITEM_ROCKET},
 {2784,72,DRONE,0},{2864,104,ITEM_MG,0}
};
static const Platform blackout_platforms[] = {
 {336,64,96},{512,112,96},{800,64,96},{992,96,96},{1184,112,96},
 {1408,64,96},{1520,80,96},{1760,80,96},{1952,144,96},
 {2208,64,96},{2368,64,96},{2592,144,96},{2832,80,96}
};
static const uint16_t blackout_pits[]={552,1224,2000,2640};
static const uint8_t blackout_widths[]={32,40,40,40};
static const uint16_t blackout_vents[]={832,1552,2400};

const Mission missions[MISSION_COUNT]={
 {cinder_encounters,cinder_platforms,cinder_pits,cinder_widths,cinder_vents,
  "OPERATION CINDER",{"ASH QUARTER","FURNACE STREET","BLACKFORGE GATE"},"IRONMAW",
  3456,3296,3392,3200,960,1728,
  COUNT(cinder_encounters),COUNT(cinder_platforms),4,2,48},
 {tidebreak_encounters,tidebreak_platforms,tidebreak_pits,tidebreak_widths,tidebreak_vents,
  "OPERATION TIDEBREAK",{"DOCK APRON","CANAL BRIDGES","PUMP STATION"},"DREDGER",
  2816,2656,2752,2560,864,1792,
  COUNT(tidebreak_encounters),COUNT(tidebreak_platforms),4,3,48},
 {blackout_encounters,blackout_platforms,blackout_pits,blackout_widths,blackout_vents,
  "OPERATION BLACKOUT",{"COOLING TUNNELS","INDUCTION HALL","COMMAND VAULT"},"NULLCORE",
  3200,3040,3136,2944,960,2112,
  COUNT(blackout_encounters),COUNT(blackout_platforms),4,3,48}
};
