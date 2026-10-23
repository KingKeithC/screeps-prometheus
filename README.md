# Screeps Prometheus Connector and Grafana Dashboard

This repo contains a Prometheus stats Collector to scrape stats from Screeps and present them in a format that can be scraped by Prometheus (or other compatible software.)

It also contains a Grafana dashboard for displaying the collected stats, and a sample below that can be used to collect the necessary series' the dashboard references.

## Usage

It is up to you to decide which stats you want to collect within screeps, and to define your own code
for writing them into the `stats` memory location.

However I have already written some stats code which you may wish to adapt as it can be used with the provided dashboard to get you started.

Much of the following uses custom functions, but I assume you already have similar existing functionality you can substitute it for in your program.

```ts
  function MapNameable<N extends { name: string; }, T>(iterOfNamed: Iterable<N>, mapper: (n: N) => T): Dictionary<T> {
    const ret: Dictionary<T> = {};
    for (const named of iterOfNamed) ret[named.name] = mapper(named);
    return ret;
  }

  const statsSchema = {
    time: { unit: "ticks", description: "Monotonicly increasing tick counter, the current 'time' of the Game.", },
    last_reset_time: { unit: "ticks", description: "Last time the Program was Reset (happens on code push, or semi-rarely by the platform)" },
    visible_rooms_count: { unit: "number", description: "The total number of visible rooms this tick." },
    gcl: {
        level: { unit: "number", description: "The current Global Control Level. Increased by upgrading controllers." },
        progress: { unit: "number", description: "Progress toward the next Global Control Level." },
        progressTotal: { unit: "number", description: "The Global Control Level will increase when Progress reaches this amount." },
    },
    gpl: {
        level: { unit: "number", description: "The current Global Power Level. Increased by harvesting Power from Highway rooms." },
        progress: { unit: "number", description: "Progress toward the next Global Power Level." },
        progressTotal: { unit: "number", description: "The Global Power Level will increase when Progress reaches this amount." },
    },
    cpu: {
        unusedBucket: { unit: "cpu", description: "How much CPU has accumulated in the bucket (limit 10k)." },
        used: { unit: "cpu", description: "How much CPU was used this tick in the execution of scripts." },
        limit: { unit: "cpu", description: "The maximum average limit of CPU usage. Excess unused amount below the limit contributes to the unusedBucket." },
        tickLimit: { unit: "cpu", description: "How much CPU total are we allowed to burst to (and consume from the bucket) this tick?" },
    },
    resources: {
        labelKeys: ["resourceType"],
        unit: "number",
        description: "Account level resources.",
    },
    meminfo: {
        unit: "bytes",
        description: "How much memory are scripts using.",
    },
    global_quota: {
        labelKeys: ["role"],
        unit: "number",
        description: "The maximum limit of creeps that may be spawned in all owned rooms.",
    },
    room_quota: {
        labelKeys: ["role", "room"],
        unit: "number",
        description: "The maximum limit of creeps that may be spawned in this role or room.",
    },
    assigned_room_count: {
        labelKeys: ["role", "room"],
        unit: "number",
        description: "The living number of creeps currently spawned by assigned room.",
    },
    my_creep_count: {
        labelKeys: ["room"],
        unit: "number",
        description: "The living number of creeps currently spawned by occupied room.",
    },
    neutral_structure_count: {
        labelKeys: ["room"],
        unit: "number",
        description: "Structures that have no owner.",
    },
    hostile_creep_count: {
        labelKeys: ["room"],
        unit: "number",
        description: "Living hostile creep count.",
    },
    my_structure_count: {
        labelKeys: ["room"],
        unit: "number",
        description: "Structures I own.",
    },
    hostile_structure_count: {
        labelKeys: ["room"],
        unit: "number",
        description: "Non-Neutral structures owned by someone else.",
    },
    dropped_energy_amount: {
        labelKeys: ["room"],
        unit: "number",
        description: "Total amount of energy sitting on the ground.",
    },
    my_constructions_count: {
        labelKeys: ["room"],
        unit: "number",
        description: "Count of ongoing Constructions sites.",
    },
    capacity_of_storage: {
        labelKeys: ["room"],
        unit: "number",
        description: "How much space is available in room storage.",
    },
    energy_in_storage: {
        labelKeys: ["room"],
        unit: "number",
        description: "How storage space is used by energy.",
    },
    energy_in_spawns: {
        labelKeys: ["room"],
        unit: "number",
        description: "Total energy of all spawns and extensions.",
    },
    energy_in_sources: {
        labelKeys: ["room"],
        unit: "number",
        description: "Total amount of all energy sources in the room.",
    },
    capacity_of_spawns: {
        labelKeys: ["room"],
        unit: "number",
        description: "Total capacity of all spawns and extensions.",
    },
    energy_in_containers: {
        labelKeys: ["room"],
        unit: "number",
        description: "Total amount of energy in all containers in the room.",
    },
    energy_in_my_creeps: {
        labelKeys: ["room"],
        unit: "number",
        description: "Total amount of energy my creeps are carrying in the room.",
    },
    energy_in_links: {
        labelKeys: ["room"],
        unit: "number",
        description: "Total amount of energy sitting in links in the room.",
    },
    spawns_in_progress: {
        labelKeys: ["room"],
        unit: "number",
        description: "Total amount of spawns in the spawning state.",
    },
    event_counts: {
        labelKeys: ["room", "event_type"],
        unit: "number",
        description: "Total times an event occured.",
    },
    event_amounts: {
        labelKeys: ["room", "event_type"],
        unit: "number",
        description: "Total amount for all occurences of event.",
    },
    }

  function GetCurrentStats(): ColonyStats {
    /* eslint-disable camelcase */
    const resources: Dictionary<number> = {};
    for (const r of Object.entries(Game.resources))
      resources[r[0]] = r[1] as number;

    const meminfo: Dictionary<number> = {};
    if (Game.cpu.getHeapStatistics) {
      for (const [k, v] of Object.entries(Game.cpu.getHeapStatistics()))
        meminfo[k] = v as number;

      // Not sure what this even means / it doesn't seem relevant to me.
      // and it breaks the homogeneity of the otherwise `byte` data types in this group
      if ("does_zap_garbage" in meminfo) delete meminfo.does_zap_garbage;
    }

    const stats = {
      schema: statsSchema,
      data: {
        time: Game.time,
        last_reset_time: this.stats.data.last_reset_time, // Carry forward unmodified time
        visible_rooms_count: Object.keys(Game.rooms).length,
        gcl: {
          level: Game.gcl.level,
          progress: Game.gcl.progress,
          progressTotal: Game.gcl.progressTotal,
        },
        gpl: {
          level: Game.gpl.level,
          progress: Game.gpl.progress,
          progressTotal: Game.gpl.progressTotal,
        },
        cpu: {
          unusedBucket: Game.cpu.bucket,
          used: Game.cpu.getUsed(),
          limit: Game.cpu.limit,
          tickLimit: Game.cpu.tickLimit,
        },
        resources,
        meminfo,
        global_quota: MapNameable(Object.values(this.Roles), ro => ro.GetGlobalQuota()),
        room_quota: MapNameable(Object.values(this.Roles), r => MapNameable(this.MyRooms, ro => r.GetRoomQuota(ro))),
        assigned_room_count: MapNameable(Object.values(this.Roles), r => MapNameable(this.MyRooms, ro => r.GetRoomCreepsInRole(ro).length)),
        my_creep_count: MapNameable(Object.values(Game.rooms), vr => vr.find(FIND_MY_CREEPS).length),
        neutral_structure_count: MapNameable(Object.values(Game.rooms), vr => vr.find(FIND_STRUCTURES, { filter: s => !("owner" in s) }).length),
        hostile_creep_count: MapNameable(Object.values(Game.rooms), vr => vr.find(FIND_HOSTILE_CREEPS).length),
        my_structure_count: MapNameable(Object.values(Game.rooms), vr => vr.find(FIND_MY_STRUCTURES).length),
        hostile_structure_count: MapNameable(Object.values(Game.rooms), vr => vr.find(FIND_HOSTILE_STRUCTURES).length),
        dropped_energy_amount: MapNameable(Object.values(Game.rooms), vr => sum(vr.find(FIND_DROPPED_RESOURCES), r => r.resourceType === RESOURCE_ENERGY ? r.amount : 0)),
        my_constructions_count: MapNameable(Object.values(Game.rooms), vr => vr.find(FIND_MY_CONSTRUCTION_SITES).length),
        capacity_of_storage: MapNameable(Object.values(Game.rooms), vr => vr.storage?.store.getCapacity() ?? 0),
        energy_in_storage: MapNameable(Object.values(Game.rooms), vr => vr.storage?.store.getUsedCapacity(RESOURCE_ENERGY) ?? 0),
        energy_in_spawns: MapNameable(Object.values(Game.rooms), vr => vr.energyAvailable),
        energy_in_sources: MapNameable(Object.values(Game.rooms), vr => sum(vr.find(FIND_SOURCES).map(s => s.energy))),
        capacity_of_spawns: MapNameable(Object.values(Game.rooms), vr => vr.energyCapacityAvailable),
        energy_in_containers: MapNameable(Object.values(Game.rooms), vr => sum(vr.find(FIND_STRUCTURES).map(s => s.structureType === STRUCTURE_CONTAINER ? s.store.getUsedCapacity(RESOURCE_ENERGY) : 0))),
        energy_in_my_creeps: MapNameable(Object.values(Game.rooms), vr => sum(vr.find(FIND_MY_CREEPS).map(s => s.store.getUsedCapacity(RESOURCE_ENERGY)))),
        energy_in_links: MapNameable(Object.values(Game.rooms), vr => sum(vr.find(FIND_STRUCTURES).map(s => s.structureType === STRUCTURE_LINK ? s.store.getUsedCapacity(RESOURCE_ENERGY) : 0))),
        spawns_in_progress: MapNameable(Object.values(Game.rooms), vr => vr.find(FIND_MY_SPAWNS).filter(s => s.spawning !== null && s.spawning !== undefined).length),
        event_counts: MapNameable(this.MyRooms, mr => mr.EventCounts),
        event_amounts: MapNameable(this.MyRooms, mr => mr.EventAmounts),
      }
    };
    /* eslint-enable camelcase */

    // Reset event accumulators on my rooms
    this.MyRooms.forEach(r => r.ResetEvents());

    return stats;
  }
```

The screeps API rate limits memory GET requests to 1440/day, which equates to 1/min. As such, it is recommended to set your Prometheus job
to scrape less frequently than that, otherwise you will be rate limited. Since stats are effectively only fetched every ~60 seconds (60-180 ticks in game), you do
not need to call your update stats function every tick, as most of the stats you calculate will go unread. I run mine every 30 ticks, and scrape every 90 seconds.

As a result of this, keep in mind that some stats you write into `Memory.stats` may never be read. I can't think of a straightforward solution
to this that would guarantee no stats get missed, while also respecting the rate limit on the API. It may be possible to embed a realtime-timestamp
into the stats when they are collected in game, then store those in an array, and 'unroll' the array on each scrape (or use a PushGateway), however I don't think it is enough of an issue to justify that complex of a solution.

If you are collecting stats about some rare event that you are worried may be missed due to being overwritten before the next scrape, you
can workaround the issue by tracking the stat as a counter and carrying the value of the counter forward when it doesn't change, like the
`last_reset_time` stat above. You can process the time series later to find when it changed.

Take care that the stat changes rarely enough or in small values so that it won't overflow by being added to constantly, since resetting the counter may
cause unexpected behaviour in your presentation layer.
