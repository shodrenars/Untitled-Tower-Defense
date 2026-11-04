#   =====================================================================
#   game/game.py - THE GAME RULES (no pygame in here, only logic)
#   =====================================================================
#   Everything that decides what happens lives here: how ants walk, how
#   towers shoot, money, cards, rounds. Drawing is in client/main.py.
#
#   TABLE OF CONTENTS - search for a tag (Ctrl+F "[G4]") to jump to it
#     [G1]   Settings: all the fixed numbers
#     [G2]   Map path: where the ants walk
#     [G3]   Cards: rarities and the list of every card
#     [G4]   Tower stats: cost, damage and range per level
#     [G5]   Tower groups and fusion recipes
#     [G6]   class Tower: one tower on the map
#     [G7]   class DoingSomethingWithAnts: the whole running game
#     [G8]     Game state: everything the game remembers
#     [G9]     Spawning ants and the main update
#     [G10]    Slowing ants: freezers and fused towers
#     [G11]    Tower range and picking targets
#     [G12]    Towers firing
#     [G13]    Explosions
#     [G14]    Shop: buy, upgrade, sell
#     [G15]    Fusion
#     [G16]    Damage and money
#     [G17]    Using cards
#     [G18]    Totem of Undying and fire
#     [G19]    Rounds
#     [G20]    Removing dead ants
#
#   HOW THE ANTS ARE STORED (read this first)
#     The game can have 100 billion ants, so one object per ant would be
#     far too slow. Ants that spawn together are grouped into a "pack"
#     and one row in the numpy arrays describes the whole pack:
#       num      how many ants are in the pack
#       hp       hp of the ants waiting at the back of the pack
#       shield   shield of the ants at the back
#       fhp      hp of the front ant (only this one takes single shots)
#       fshield  shield of the front ant
#       progress how far along the path the pack has walked
#       cell     the spot on the path, as one number
#       speed    how fast it moves right now
#     A "cell" is one spot on the path: lane * PATH_LEN + step.

import math
import random

import numpy as np

# -----------------------------------------------------------------------------
# [G1] SETTINGS
# -----------------------------------------------------------------------------
# All the fixed numbers. Change one here and the whole game follows.
#
# Money earned for each point of damage dealt to ants.
money_gain_per_damage = 0.5

# How wide the road is, in parallel 1 pixel lanes.
LANES = 31

# Normal ant speed in pixels per second.
ANT_SPEED = 60

# How long an explosion stays on screen, in seconds.
EXPLOSION_TIME = 0.3

# Seconds between rockets in a volley.
ROCKET_GAP = 0.1

# Totem fire: lasts 20 seconds, hits for 5% of ant health and shield.
FIRE_TIME = 20
FIRE_DAMAGE = 0.05

# Leech cards: healing is per 1M damage, up to 10 hp each round.
LEECH_PER_DAMAGE = 1_000_000
LEECH_ROUND_CAP = 10

# Limits that stop numbers from growing too big for numpy to store.
STAT_CAP = 10**15
MONEY_CAP = 1e300

# The most ants alive at once, and the most packs the arrays can hold.
MAX_ANTS = 100_000_000_000
MAX_PACKS = 2_000_000

# Limits on cards and farms, and how often a card offer appears.
MAX_EQUIPPED = 5
MAX_FARMS = 5
CARD_EVERY_ROUNDS = 5

# Towers must be this level before they can be used in a fusion.
FUSION_LEVEL = 5

# Ants have reached the house once they walk past this x position.
PATH_END_X = 1679

# -----------------------------------------------------------------------------
# [G2] MAP PATH
# -----------------------------------------------------------------------------
# The route as a list of straight pieces, one row per piece:
#   (dx, dy, side, turn)
# Walk by (dx, dy) until x + side * y equals turn, then take the next
# row. Using x + y or x - y as the stop rule makes each lane stop at a
# slightly different spot, so all 31 lanes bend neatly round the corner
# and stay side by side.
ROUTE = (
    (1, 0, 1, 730),
    (0, 1, 1, 880),
    (1, 0, -1, -280),
    (0, -1, -1, 20),
    (1, 0, 1, 990),
    (0, 1, 1, 1290),
    (1, 0, -1, 120),
    (0, -1, -1, 420),
    (1, 0, 1, 1390),
    (0, 1, 1, 1690),
    (1, 0, -1, 520),
    (0, -1, -1, 820),
    (1, 0, 1, 1790),
    (0, 1, 1, 2090),
    (1, 0, -1, 930),
    (0, -1, -1, 1080),
)


# Walks one lane along ROUTE and returns every (x, y) point it visits.
def build_lane(lane):
    x, y = 10, 520 + lane
    points = [(x, y)]
    for dx, dy, side, turn in ROUTE:
        while x + side * y != turn:
            x += dx
            y += dy
            points.append((x, y))
    return points


# Builds all the lanes into two tables, PATH_X and PATH_Y, where each
# is indexed as [lane][step]. Inner lanes are a little shorter, so they
# get extended straight ahead until every lane has the same length.
def build_path():
    # The longest lane decides how long the table has to be.
    lanes = [build_lane(lane) for lane in range(LANES)]
    length = max(len(p) + PATH_END_X - p[-1][0] for p in lanes)

    # Stretch the shorter lanes to that same length.
    for points in lanes:
        x, y = points[-1]
        points += [(x + i, y) for i in range(1, length - len(points) + 1)]

    # Reorder [lane][step][x or y] into [x or y][lane][step].
    return np.array(lanes, dtype=np.int32).transpose(2, 0, 1)


# Built once when the game starts. PATH_XF and PATH_YF are the same
# tables flattened to one long list, so a cell number can index them.
PATH_X, PATH_Y = build_path()
PATH_LEN = PATH_X.shape[1]
PATH_XF = PATH_X.ravel()
PATH_YF = PATH_Y.ravel()

# -----------------------------------------------------------------------------
# [G3] CARDS
# -----------------------------------------------------------------------------
# Rarity names from worst to best, with their chances in percent.
RARITY_ORDER = ["common", "rare", "epic", "legendary", "secret"]
RARITY_WEIGHTS = [90, 5, 4, 0.99, 0.01]

# The colour each rarity gets on screen and on the website.
RARITY_COLORS = {
    "common": (150, 150, 150),
    "rare": (60, 120, 255),
    "epic": (160, 60, 220),
    "legendary": (255, 200, 0),
    "secret": (20, 20, 20),
}

# How many cards of a rarity you trade for one of the next rarity.
# Secret is missing on purpose: it cannot be traded up.
TRADE_UP_COST = {"common": 3, "rare": 3, "epic": 3, "legendary": 20}


# Builds all the cards of one rarity. Every rarity has the same basic
# set (cash, damage, fire rate, hp, regen, leech) with bigger numbers,
# plus optional "specials" that only that rarity has.
# Each row below is (card id, name shown to the player, effect, value).
def card_tier(rarity, percent, level, hp, specials=(), hp_id=None):
    leech_name = f"+0.0{level} hp per 1M damage (max 10 per round)"
    cards = (
        (f"cash_{percent}", f"+{percent}% cash", "cash", percent / 100),
        (f"damage_{percent}", f"+{percent}% damage", "damage", percent / 100),
        (f"speed_{percent}", f"+{percent}% fire rate", "speed", percent / 100),
        *specials,
        (hp_id or f"hp_{hp}", f"+{hp} hp instantly", "hp", hp),
        (f"regen_{level}", f"+{level} hp every round", "regen", level),
        (f"leech_{level}", leech_name, "leech", level / 100),
    )
    return {
        card_id: {"rarity": rarity, "name": name, effect: value}
        for card_id, name, effect, value in cards
    }


# The full card list. The effect name in each card is what card_sum()
# looks up later to work out how strong your equipped cards are.
CARDS = {
    **card_tier("common", 10, 1, 10),
    **card_tier(
        "rare",
        30,
        2,
        30,
        [("towers", "+3% damage per tower", "per_tower", 0.03)],
    ),
    **card_tier(
        "epic",
        50,
        3,
        50,
        [("rage", "more damage the less hp you have", "rage", 1)],
    ),
    **card_tier(
        "legendary",
        100,
        5,
        50,
        [
            (
                "rich",
                "+1 damage per 1M unspent cash",
                "cash_damage",
                1 / 1_000_000,
            ),
            ("crowd", "more cash per kill in big waves", "kill_bonus", 1),
            ("interest", "+1% of unspent cash every round", "interest", 0.01),
        ],
        "hp_50_leg",
    ),
    "totem": {"rarity": "secret", "name": "Totem of Undying", "totem": 1},
}


# Picks one random card: rarity first using the chances, then a random
# card of that rarity.
def roll_card():
    rarity = random.choices(RARITY_ORDER, weights=RARITY_WEIGHTS)[0]
    return random.choice(
        [cid for cid, c in CARDS.items() if c["rarity"] == rarity]
    )


# -----------------------------------------------------------------------------
# [G4] TOWER STATS
# -----------------------------------------------------------------------------
# Turns one row per level into {1: {...}, 2: {...}} so tables stay
# short. keys is a text of column names, the rows hold the numbers.
def stat_table(keys, *rows):
    keys = keys.split()
    return {level: dict(zip(keys, row)) for level, row in enumerate(rows, 1)}


# Turret: single shots at the ant furthest along the path.
TURRET_STATS = stat_table(
    "range damage cooldown cost",
    (200, 10, 1, 150),
    (240, 20, 0.5, 400),
    (280, 30, 0.3, 700),
    (320, 40, 0.1, 3250),
    (450, 100, 0.04, 29000),
)

# Bomb: explosions that hit every ant in the radius. Level 4 fires 3.
BOMB_STATS = stat_table(
    "range damage cooldown cost explosion_radius rockets",
    (150, 10, 1.0, 500000, 30, 1),
    (170, 20, 0.8, 500000, 35, 1),
    (190, 50, 0.6, 1000000, 40, 1),
    (230, 90, 0.5, 1600000, 45, 3),
    (240, 200, 0.3, 4000000, 55, 1),
)

# Freezer: ants in range slow down to freeze_multi pixels per second.
FREEZE_STATS = stat_table(
    "range cost freeze_multi",
    (65, 150, 60),
    (65, 150, 55),
    (65, 250, 45),
    (65, 400, 30),
    (65, 700, 20),
)

# Farm: pays money_given every round, money_multi boosts damage money.
FARM_STATS = stat_table(
    "cost money_given money_multi",
    (150, 50, 1),
    (400, 100, 1),
    (1000, 200, 1.01),
    (10000, 1000, 1.1),
    (50000, 2000, 1.2),
)

# Fused towers: the column names shared by all three kinds.
#   splash = share of the damage that also explodes on a hit
#   slow   = ants in range move at this share of their speed
FUSED_KEYS = "cost range damage cooldown explosion_radius splash slow rockets"
FUSED_STATS = {
    "railgun": stat_table(
        FUSED_KEYS,
        (50_000_000, 500, 1500, 0.05, 14, 0.3, 0.85, 1),
        (100_000_000, 520, 3000, 0.04, 15, 0.3, 0.82, 1),
        (400_000_000, 550, 4500, 0.03, 17, 0.35, 0.8, 1),
        (1_500_000_000, 580, 7500, 0.025, 18, 0.35, 0.75, 1),
        (6_000_000_000, 600, 15000, 0.02, 20, 0.4, 0.7, 1),
    ),
    "silo": stat_table(
        FUSED_KEYS,
        (100_000_000, 350, 1500, 0.6, 60, 0, 0.9, 3),
        (200_000_000, 380, 2500, 0.55, 62, 0, 0.88, 3),
        (800_000_000, 410, 4000, 0.5, 65, 0, 0.86, 3),
        (3_000_000_000, 440, 7000, 0.45, 70, 0, 0.83, 3),
        (12_000_000_000, 480, 15000, 0.4, 80, 0, 0.8, 3),
    ),
    "spire": stat_table(
        FUSED_KEYS,
        (40_000_000, 150, 300, 1.0, 0, 0, 0.6, 1),
        (80_000_000, 170, 600, 0.9, 0, 0, 0.5, 1),
        (300_000_000, 190, 1200, 0.8, 0, 0, 0.4, 1),
        (1_200_000_000, 210, 2500, 0.7, 0, 0, 0.3, 1),
        (5_000_000_000, 240, 6000, 0.6, 0, 0, 0.2, 1),
    ),
}

# -----------------------------------------------------------------------------
# [G5] TOWER GROUPS AND FUSION RECIPES
# -----------------------------------------------------------------------------
# The four normal towers. The website reads this table too.
BASIC_STATS = {
    "turret": TURRET_STATS,
    "farm": FARM_STATS,
    "freeze": FREEZE_STATS,
    "bomb": BOMB_STATS,
}

# Every tower kind in one place.
TOWER_STATS = {**BASIC_STATS, **FUSED_STATS}

# Which towers act first each frame: bombs, then fused, then turrets.
UPDATE_ORDER = (("bomb",), tuple(FUSED_STATS), ("turret",))

# Tower kinds that slow ants down.
SLOWERS = ("freeze", *FUSED_STATS)

# Tower kinds that fire single shots at the front ant.
SHOOTERS = ("turret", "railgun")

# Every extra Missile Silo you own doubles the price of the next one.
FUSE_COST_GROWTH = {"silo": 2}

# The names players see.
FUSION_NAMES = {
    "railgun": "Plasma Railgun",
    "silo": "Missile Silo",
    "spire": "Cryo Spire",
}

# How many level 5 towers each fused tower uses up.
FUSION_RECIPES = {
    "railgun": {"turret": 10, "freeze": 1, "bomb": 1},
    "silo": {"bomb": 10, "turret": 4, "freeze": 1},
    "spire": {"freeze": 10, "turret": 2, "bomb": 1},
}

# Text shown in the fuse menu.
FUSION_INFO = {
    "railgun": [
        "very fast heavy plasma shots",
        "small explosion on every hit",
        "slows ants in range",
    ],
    "silo": ["volleys of 3 big rockets", "fast reload", "slows ants in range"],
    "spire": [
        "strong slow zone, stacks with freeze",
        "frost blast hits all ants in range",
        "huge range",
    ],
}


# -----------------------------------------------------------------------------
# [G6] CLASS TOWER
# -----------------------------------------------------------------------------
# One tower on the map, of any kind. The kind decides which stat table
# it reads, and set_level copies that table's numbers onto the tower.
class Tower:
    # Starts a new level 1 tower at (x, y).
    def __init__(self, kind, x, y):
        self.kind = kind
        self.x = x
        self.y = y
        self.stats = TOWER_STATS[kind]

        # What a fused tower really cost, needed for a fair sell price.
        self.fuse_paid = self.stats[1]["cost"]

        # timer counts down to the next shot, since_shot counts up from the
        # last one. The next few values are used for aiming and animations.
        self.timer = 0.0
        self.since_shot = 99.0
        self.angle = 180.0
        self.shot_frame = 1
        self.anim = 0.0

        # Range the cached path cover was worked out for (see ensure_cover).
        self.cover_range = None

        # Rockets still waiting to fire in the current volley.
        self.rocket_queue = []
        self.rocket_timer = 0.0
        self.set_level(1)

    # Moves the tower to a level. __dict__.update turns every stat into a
    # normal attribute, so t.damage, t.range, t.cost and so on just work.
    def set_level(self, level):
        self.level = level
        self.__dict__.update(self.stats[level])

    # Price of the next upgrade, or None if it is already at max level.
    def next_cost(self):
        if self.level == len(self.stats):
            return None
        return self.stats[self.level + 1]["cost"]

    # Sell price: half of the current level's cost. Fused towers instead
    # return half of everything really paid for them.
    def sell_value(self):
        if self.kind not in FUSED_STATS:
            return self.cost * 0.5
        upgrades = sum(
            self.stats[level]["cost"] for level in range(2, self.level + 1)
        )
        return (self.fuse_paid + upgrades) * 0.5


# Chooses where a volley lands. cand is sorted front ant first, and
# each next rocket must land at least "spacing" steps further back so
# they do not all hit one spot. If there are too few spots, rockets
# repeat the first target.
def pick_rocket_targets(cand, count, spacing):
    targets = [int(cand[0])]
    last = targets[0] % PATH_LEN
    for c in cand[1:]:
        if len(targets) == count:
            break
        s = int(c) % PATH_LEN
        if s <= last - spacing:
            targets.append(int(c))
            last = s
    while len(targets) < count:
        targets.append(targets[0])
    return targets


# -----------------------------------------------------------------------------
# [G7] CLASS DOINGSOMETHINGWITHANTS
# -----------------------------------------------------------------------------
# The whole running game. One of these is created for each new game
# and it holds the ants, towers, money, cards and round.
class DoingSomethingWithAnts:
    # -------------------------------------------------------------------------
    # [G8] GAME STATE
    # -------------------------------------------------------------------------
    # Everything the game remembers.
    #
    # The pack arrays described at the top of this file. They are big, but
    # only the first self.packs rows are in use.
    def __init__(self):
        self.num = np.zeros(MAX_PACKS, dtype=np.int64)
        self.hp = np.zeros(MAX_PACKS, dtype=np.float64)
        self.shield = np.zeros(MAX_PACKS, dtype=np.float64)
        self.fhp = np.zeros(MAX_PACKS, dtype=np.float64)
        self.fshield = np.zeros(MAX_PACKS, dtype=np.float64)
        self.lane_off = np.zeros(MAX_PACKS, dtype=np.int32)
        self.cell = np.zeros(MAX_PACKS, dtype=np.int32)
        self.speed = np.zeros(MAX_PACKS, dtype=np.float32)
        self.progress = np.zeros(MAX_PACKS, dtype=np.float32)
        self.packs = 0

        # occ counts how many packs stand on each cell. cell_ants caches which
        # packs are on a cell, and is rebuilt every frame.
        self.occ = np.zeros(PATH_XF.size, dtype=np.int64)
        self.cell_ants = {}

        # All towers on the map, and the explosions being shown.
        self.towers = []
        self.explosions = []

        # Starting money, score, and money earned per round.
        self.money = 1000
        self.score = 0
        self.money_per_round = 0

        # Number of ants alive right now.
        self.count = 0

        # Damage per cell for the explosions of the current frame.
        self.blast_damage = None

        # Healing from leech cards so far this round.
        self.leech_round = 0.0
        # Your base health at the start of a game.
        self.basehp = 100

        # Cards owned, cards equipped, and the 3 cards on offer.
        self.inventory = []
        self.equipped = []
        self.card_choices = []

        # Totem fire: seconds left, and time since the last burn.
        self.fire_left = 0.0
        self.fire_acc = 0.0

        # Cached speed for each cell, and what it was built from.
        self.slow_key = None
        self.slow_table = None

        # Wave size and ant strength at the start of a game.
        self.reset_waves()

        # Ants still to spawn this wave, and how fast they appear.
        self.spawn_left = 0
        self.spawn_rate = 0.0
        self.spawn_acc = 0.0
        self.current_round = 0
        self.money_multi_per_damage = 1

    # -------------------------------------------------------------------------
    # [G9] SPAWNING ANTS AND THE MAIN UPDATE
    # -------------------------------------------------------------------------
    # Returns only the towers of the given kinds.
    def towers_of(self, kinds):
        return [t for t in self.towers if t.kind in kinds]

    # Adds this frame's new ants to the start of the road, as one new pack
    # for each lane that received ants.
    def spawn(self, dt):
        # spawn_acc collects fractions of ants until a whole one is ready.
        self.spawn_acc += self.spawn_rate * dt
        n = min(int(self.spawn_acc), self.spawn_left, MAX_ANTS - self.count)
        if n > 0 and self.packs + LANES <= MAX_PACKS:
            # Share the new ants randomly over the lanes.
            per_lane = np.random.multinomial(n, [1 / LANES] * LANES)
            lanes = np.flatnonzero(per_lane)

            # Fill in the next free rows of the pack arrays.
            s = slice(self.packs, self.packs + lanes.size)
            self.num[s] = per_lane[lanes]
            self.hp[s] = self.starting_hp
            self.shield[s] = math.floor(self.starting_shield)
            self.fhp[s] = self.hp[s]
            self.fshield[s] = self.shield[s]
            self.progress[s] = 0
            self.lane_off[s] = lanes * PATH_LEN
            self.speed[s] = ANT_SPEED
            self.packs += lanes.size
            self.count += n
            self.spawn_acc -= n
            self.spawn_left -= n

    # The main update, called once per frame. dt is the frame's length in
    # seconds. This one function moves the whole game forward.
    def updateants(self, dt):
        # Age the explosions and drop the finished ones.
        for e in self.explosions:
            e["age"] += dt
        self.explosions = [
            e for e in self.explosions if e["age"] < EXPLOSION_TIME
        ]

        # All ants are dead, so the next round starts by itself.
        if self.count == 0 and self.current_round > 0 and self.spawn_left == 0:
            self.nextround()

        # Add new ants if this wave still has some left.
        if self.spawn_left > 0:
            self.spawn(dt)

        # Move every pack forward at once.
        m = self.packs
        p = self.progress[:m]
        p += self.speed[:m] * dt

        # Turn progress into a cell number. minimum stops it at the path end.
        cell = self.cell[:m]
        np.minimum(p, PATH_LEN - 1, out=cell, casting="unsafe")
        cell += self.lane_off[:m]

        # Remember which packs have reached the house.
        at_base = np.flatnonzero(p >= PATH_LEN - 1)

        # Update speeds, and count how many packs are on each cell.
        self.apply_slows(m)
        self.occ = np.bincount(cell, minlength=PATH_XF.size)
        self.cell_ants = {}

        # Let every group of towers act.
        for kinds in UPDATE_ORDER:
            self.update_towers(self.towers_of(kinds), dt)

        # Burn ants if the totem fire is on.
        self.update_fire(dt)

        # Ants that reached the house cost 1 hp each, and at 0 hp the totem
        # gets a chance to save you.
        reached = int(self.num[at_base].sum())
        self.basehp -= reached
        if self.basehp <= 0:
            self.use_totem()

        # Those ants are done, so take them off the map.
        self.num[at_base] = 0
        self.count -= reached

        # Clear out the empty packs.
        self.remove_dead()

    # -------------------------------------------------------------------------
    # [G10] SLOWING ANTS
    # -------------------------------------------------------------------------
    # Gives each pack the speed for the cell it stands on. Building the
    # speed table is slow, so it only happens when a freezer or fused
    # tower is added, removed or upgraded.
    def apply_slows(self, n):
        slowers = self.towers_of(SLOWERS)

        # key describes the current slowers. Same key means same table.
        key = [(t.kind, t.x, t.y, t.level) for t in slowers]
        if key != self.slow_key:
            # speed = the strongest freezer on each cell (they do not add up).
            # factor = the strongest fused slow on each cell.
            speed = np.full(PATH_X.shape, ANT_SPEED, dtype=np.float32)
            factor = np.ones(PATH_X.shape, dtype=np.float32)
            for t in slowers:
                self.ensure_cover(t)
                if t.kind == "freeze":
                    np.minimum(speed, t.freeze_multi, out=speed, where=t.cover)
                else:
                    np.minimum(factor, t.slow, out=factor, where=t.cover)

            # Multiplying is what makes fused slows stack on top of freezers.
            self.slow_table = (speed * factor).ravel()
            self.slow_key = key

        # Every pack reads its speed from the table.
        self.speed[:n] = self.slow_table[self.cell[:n]]

    # -------------------------------------------------------------------------
    # [G11] TOWER RANGE AND PICKING TARGETS
    # -------------------------------------------------------------------------
    # Works out which path cells a tower can reach. Only redone when its
    # range changes, because towers never move.
    def ensure_cover(self, t):
        if t.cover_range != t.range:
            # Distance check to every cell, without a slow square root.
            dx = PATH_X - t.x
            dy = PATH_Y - t.y
            t.cover = dx * dx + dy * dy <= t.range * t.range

            # t.cells lists reachable cells with the furthest along first,
            # which
            # is why towers always shoot the ant closest to your house.
            lanes, steps = np.nonzero(t.cover)
            order = np.argsort(-steps, kind="stable")
            t.cells = (lanes * PATH_LEN + steps)[order]
            t.cover_idx = np.flatnonzero(t.cover.ravel())
            t.cover_range = t.range

    # Runs the timers and returns the towers that can fire now. A tower
    # with nothing to shoot rests at 0, ready to fire at the first ant.
    def ready_towers(self, towers, dt):
        ready = []
        for t in towers:
            t.since_shot += dt
            t.timer -= dt
            if t.timer <= 0:
                self.ensure_cover(t)
                if t.cells.size and self.count:
                    ready.append(t)
                else:
                    t.timer = 0
        return ready

    # Finds which packs stand on the given cells and caches the answer in
    # cell_ants. Cells with no packs get an empty result, so the same cell
    # is never searched for twice in one frame.
    def fetch_cells(self, cells):
        # Mark the wanted cells and find all packs standing on one.
        want = np.zeros(PATH_XF.size, dtype=bool)
        want[cells] = True
        idx = np.flatnonzero(want[self.cell[: self.packs]])
        c = self.cell[idx]

        # Sort by cell so that packs on the same cell sit next to each other.
        order = np.argsort(c, kind="stable")
        idx = idx[order]
        c = c[order]

        # Split at each change of cell and store one group per cell.
        bounds = np.flatnonzero(np.diff(c)) + 1
        for part in np.split(idx, bounds):
            if part.size:
                self.cell_ants[int(self.cell[part[0]])] = part

        # Wanted cells with nobody on them get an empty group.
        for cc in cells:
            self.cell_ants.setdefault(int(cc), idx[:0])

    # Finds the living pack furthest along the path in this tower's range.
    # Returns (pack index, cell), or (-1, -1) when there is nothing.
    def find_target(self, t):
        cand = t.cells[self.occ[t.cells] > 0]
        for c in cand:
            c = int(c)
            if c not in self.cell_ants:
                self.fetch_cells(cand[:8])
            packs = self.cell_ants[c]
            alive = packs[self.num[packs] > 0]
            if alive.size:
                return alive[0], c
        return -1, -1

    # -------------------------------------------------------------------------
    # [G12] TOWERS FIRING
    # -------------------------------------------------------------------------
    # Runs one group of towers for one frame.
    def update_towers(self, towers, dt):
        ready = self.ready_towers(towers, dt)
        self.blast_damage = None

        # Fire any rockets left over from a volley that already started.
        for t in towers:
            if t.rocket_queue:
                t.rocket_timer -= dt
                while t.rocket_queue and t.rocket_timer <= 0:
                    pose = t.rockets - len(t.rocket_queue) + 1
                    self.fire_rocket(t, t.rocket_queue.pop(0), pose)
                    t.rocket_timer += ROCKET_GAP

        # Look up ants for all shooters at once. Doing this in one go is what
        # keeps the game fast with hundreds of towers.
        shooters = [t for t in ready if t.kind in SHOOTERS]
        wants = [t.cells[self.occ[t.cells] > 0][:4] for t in shooters]
        wants = [w for w in wants if w.size]
        if wants:
            self.fetch_cells(np.unique(np.concatenate(wants)))

        # Each ready tower attacks in its own way.
        for t in ready:
            if t.kind in SHOOTERS:
                self.shoot(t)
            elif t.kind == "spire":
                self.frost(t)
            else:
                self.launch(t)

        # Apply all this group's explosion damage together.
        if self.blast_damage is not None:
            d = self.blast_damage[self.cell[: self.packs]]
            hit = np.flatnonzero((d > 0) & (self.num[: self.packs] > 0))
            self.hit_packs(hit, d[hit])

    # Turns a tower to face cell c.
    def aim(self, t, c):
        t.angle = math.degrees(
            math.atan2(int(PATH_YF[c]) - t.y, int(PATH_XF[c]) - t.x)
        )

    # Starts the cooldown. Fire rate cards make it shorter.
    def reload(self, t):
        t.timer += t.cooldown / (1 + self.card_sum("speed"))

    # Turret and railgun attack. The loop allows several shots in one
    # frame, which very fast towers need at low FPS.
    def shoot(self, t):
        while t.timer <= 0:
            target, c = self.find_target(t)
            if target < 0:
                t.timer = 0
                break
            self.aim(t, c)
            self.hit_front(target, self.tower_damage(t.damage))

            # The railgun also makes a small explosion on every hit.
            if t.kind == "railgun":
                self.blast(
                    c,
                    t.explosion_radius,
                    self.tower_damage(t.damage * t.splash),
                )
            self.reload(t)
            t.since_shot = 0.0
            t.shot_frame = random.randint(1, 4)

    # Bomb and silo attack: fire the first rocket now, queue the rest.
    def launch(self, t):
        if t.rocket_queue:
            return
        cand = t.cells[self.occ[t.cells] > 0]
        if cand.size == 0:
            t.timer = 0
            return
        targets = pick_rocket_targets(cand, t.rockets, t.explosion_radius)
        pose = 1 if t.rockets > 1 else random.randint(1, 4)
        self.fire_rocket(t, targets[0], pose)
        t.rocket_queue = targets[1:]
        t.rocket_timer = ROCKET_GAP
        self.reload(t)

    # Cryo Spire attack: damages every ant in its whole range.
    def frost(self, t):
        if not (self.occ[t.cells] > 0).any():
            t.timer = 0
            return
        self.add_blast(t.cover_idx, self.tower_damage(t.damage))
        self.reload(t)
        t.since_shot = 0.0

    # -------------------------------------------------------------------------
    # [G13] EXPLOSIONS
    # -------------------------------------------------------------------------
    # Adds damage to cells. It is all applied together at the end of the
    # group, so one big blast costs the same as a small one.
    def add_blast(self, cells, damage):
        if self.blast_damage is None:
            self.blast_damage = np.zeros(PATH_XF.size, dtype=np.int64)
        self.blast_damage[cells] += damage

    # One explosion of radius r centred on cell c.
    def blast(self, c, r, per_ant):
        tx = int(PATH_XF[c])
        ty = int(PATH_YF[c])

        # Only check cells near the blast along the path, not the whole map.
        s = c % PATH_LEN
        w = 2 * r + LANES
        window = (
            np.arange(LANES)[:, None] * PATH_LEN
            + np.arange(max(0, s - w), min(PATH_LEN, s + w + 1))
        ).ravel()
        dx = PATH_XF[window] - tx
        dy = PATH_YF[window] - ty

        # Keep the cells inside the circle, and add the picture to the list.
        self.add_blast(window[dx * dx + dy * dy <= r * r], per_ant)
        self.explosions.append({"x": tx, "y": ty, "r": r, "age": 0.0})

    # Fires one rocket. pose is the animation frame to show.
    def fire_rocket(self, t, c, pose):
        self.aim(t, c)
        self.blast(c, t.explosion_radius, self.tower_damage(t.damage))
        t.since_shot = 0.0
        t.shot_frame = pose

    # -------------------------------------------------------------------------
    # [G14] SHOP
    # -------------------------------------------------------------------------
    # Buys a new tower. Returns None if the farm limit is reached or there
    # is not enough money.
    def buy(self, kind, x, y):
        cost = TOWER_STATS[kind][1]["cost"]
        full = kind == "farm" and len(self.towers_of(("farm",))) >= MAX_FARMS
        if full or self.money < cost:
            return None
        self.money -= cost
        tower = Tower(kind, x, y)
        self.towers.append(tower)
        return tower

    # Buys one level, or as many as you can afford when to_max is True.
    def upgrade(self, tower, to_max=False):
        cost = tower.next_cost()
        while cost is not None and self.money >= cost:
            self.money -= cost
            tower.set_level(tower.level + 1)
            cost = tower.next_cost() if to_max else None

    # Removes a tower and pays back its sell value.
    def sell(self, tower):
        self.towers.remove(tower)
        self.money += tower.sell_value()

    # -------------------------------------------------------------------------
    # [G15] FUSION
    # -------------------------------------------------------------------------
    # Returns towers of this kind that are high enough level for fusing.
    def fusion_ready(self, part):
        return [t for t in self.towers_of((part,)) if t.level >= FUSION_LEVEL]

    # Shows how many of each needed part you have: {part: (have, need)}.
    def fusion_parts(self, kind):
        return {
            part: (len(self.fusion_ready(part)), need)
            for part, need in FUSION_RECIPES[kind].items()
        }

    # True if you have enough of every part.
    def has_fusion_parts(self, kind):
        return all(
            have >= need for have, need in self.fusion_parts(kind).values()
        )

    # Fusion price, including the silo doubling.
    def fuse_cost(self, kind):
        growth = FUSE_COST_GROWTH.get(kind, 1)
        owned = len(self.towers_of((kind,)))
        return FUSED_STATS[kind][1]["cost"] * growth**owned

    # True if you have both the towers and the money.
    def can_fuse(self, kind):
        return self.has_fusion_parts(kind) and self.money >= self.fuse_cost(
            kind
        )

    # Does the fusion: uses up the parts and places the new tower.
    def fuse(self, kind, x, y):
        if not self.can_fuse(kind):
            return None
        for part, need in FUSION_RECIPES[kind].items():
            # Uses the towers closest to the new tower first.
            ready = self.fusion_ready(part)
            ready.sort(key=lambda t: (t.x - x) ** 2 + (t.y - y) ** 2)
            for t in ready[:need]:
                self.towers.remove(t)
        cost = self.fuse_cost(kind)
        self.money -= cost
        tower = Tower(kind, x, y)
        tower.fuse_paid = cost
        self.towers.append(tower)
        return tower

    # -------------------------------------------------------------------------
    # [G16] DAMAGE AND MONEY
    # -------------------------------------------------------------------------
    # Adds up one effect across all equipped cards.
    def card_sum(self, key):
        return sum(CARDS[cid].get(key, 0) for cid in self.equipped)

    # The total damage multiplier from cards.
    def damage_mult(self):
        m = (
            1
            + self.card_sum("damage")
            + self.card_sum("per_tower") * len(self.towers)
        )

        # Rage card: the lower your hp, the more damage you do.
        rage = self.card_sum("rage")
        if rage:
            m *= 1 + rage * max(0, (100 - self.basehp) / 100)
        return m

    # Final damage of one hit after cards. The "rich" card adds damage
    # based on your unspent money.
    def tower_damage(self, base):
        return int(
            min(
                base * self.damage_mult()
                + self.card_sum("cash_damage") * self.money,
                STAT_CAP,
            )
        )

    # Pays out for damage dealt and ants killed, and does the leech
    # healing. Every hit in the game ends up here.
    def reward(self, dealt, kills):
        self.money += (
            dealt
            * money_gain_per_damage
            * self.money_multi_per_damage
            * (1 + self.card_sum("cash"))
        )

        # Leech cards heal you, up to the limit per round.
        leech = self.card_sum("leech")
        if leech:
            heal = min(
                dealt / LEECH_PER_DAMAGE * leech,
                LEECH_ROUND_CAP - self.leech_round,
            )
            if heal > 0:
                self.basehp += heal
                self.leech_round += heal

        # Crowd card: more money per kill the bigger the wave still is.
        bonus = self.card_sum("kill_bonus")
        if kills and bonus:
            remaining = self.count + self.spawn_left
            ant_value = self.starting_hp * money_gain_per_damage
            self.money += kills * bonus * remaining / 1000 * ant_value

        # Keep money under the cap, then count the kills.
        self.money = min(self.money, MONEY_CAP)
        self.count -= kills
        self.score += kills

    # Single shot: damages only the front ant of pack i. The shield takes
    # damage first, then what is left goes to hp.
    def hit_front(self, i, damage):
        absorbed = min(float(self.fshield[i]), damage)
        self.fshield[i] -= absorbed
        to_hp = damage - absorbed
        dealt = min(to_hp, max(float(self.fhp[i]), 0))
        self.fhp[i] -= to_hp
        kills = 0

        # Front ant died, so the next ant in the pack steps up.
        if self.fhp[i] <= 0:
            kills = 1
            self.num[i] -= 1
            self.fhp[i] = self.hp[i]
            self.fshield[i] = self.shield[i]
            if self.num[i] == 0:
                self.occ[self.cell[i]] -= 1
        self.reward(dealt, kills)

    # Area damage: hits every ant in the given packs. Waiting ants share
    # one hp value, so one calculation covers all of them.
    def hit_packs(self, idx, damage):
        num = self.num[idx]

        # Damage the ants at the back, and count the damage actually dealt.
        hp0 = self.hp[idx]
        absorbed = np.minimum(self.shield[idx], damage)
        self.shield[idx] -= absorbed
        to_hp = damage - absorbed
        self.hp[idx] = hp0 - to_hp
        dealt = (
            np.minimum(to_hp, np.maximum(hp0, 0)).astype(np.float64)
            * (num - 1)
        ).sum()

        # Damage the front ants the same way.
        fhp0 = self.fhp[idx]
        absorbed = np.minimum(self.fshield[idx], damage)
        self.fshield[idx] -= absorbed
        to_hp = damage - absorbed
        self.fhp[idx] = fhp0 - to_hp
        dealt += (
            np.minimum(to_hp, np.maximum(fhp0, 0)).astype(np.float64).sum()
        )

        # Work out how many ants died in each pack.
        rest_dead = self.hp[idx] <= 0
        front_dead = self.fhp[idx] <= 0
        kills_each = rest_dead * (num - 1) + front_dead
        left = num - kills_each
        self.num[idx] = left

        # Packs with survivors get a fresh front ant.
        new_front = idx[front_dead & (left > 0)]
        self.fhp[new_front] = self.hp[new_front]
        self.fshield[new_front] = self.shield[new_front]

        # Packs that are now empty no longer count as standing on their cell.
        emptied = idx[(left == 0) & (num > 0)]
        if emptied.size:
            np.subtract.at(self.occ, self.cell[emptied], 1)
        self.reward(float(dealt), int(kills_each.sum()))

    # -------------------------------------------------------------------------
    # [G17] USING CARDS
    # -------------------------------------------------------------------------
    # Takes card i from the offer. Hp cards work at once, others are kept.
    def pick_card(self, i):
        card_id = self.card_choices[i]
        if "hp" in CARDS[card_id]:
            self.basehp += CARDS[card_id]["hp"]
        else:
            self.inventory.append(card_id)
        self.card_choices = []

    # Moves a card to an equipped slot. False if all slots are full.
    def equip(self, card_id):
        if len(self.equipped) >= MAX_EQUIPPED:
            return False
        self.inventory.remove(card_id)
        self.equipped.append(card_id)
        return True

    # Moves a card back to the inventory.
    def unequip(self, card_id):
        self.equipped.remove(card_id)
        self.inventory.append(card_id)

    # Trades cards for one of the next rarity. The clicked card is used
    # first. Returns the new card, or None if the trade is not possible.
    def trade_up(self, card_id):
        rarity = CARDS[card_id]["rarity"]
        need = TRADE_UP_COST.get(rarity)

        # Any cards of the same rarity count, they do not have to match.
        same = [
            cid for cid in self.inventory if CARDS[cid]["rarity"] == rarity
        ]
        if need is None or len(same) < need:
            return None
        same.sort(key=lambda cid: cid != card_id)
        for cid in same[:need]:
            self.inventory.remove(cid)

        # Hp cards are left out because trade-ups give a card you can equip.
        next_rarity = RARITY_ORDER[RARITY_ORDER.index(rarity) + 1]
        new_card = random.choice(
            [
                cid
                for cid, c in CARDS.items()
                if c["rarity"] == next_rarity and "hp" not in c
            ]
        )
        self.inventory.append(new_card)
        return new_card

    # -------------------------------------------------------------------------
    # [G18] TOTEM OF UNDYING AND FIRE
    # -------------------------------------------------------------------------
    # Saves you from death: uses the totem, sets hp to 100, starts the fire.
    def use_totem(self):
        if "totem" in self.equipped:
            self.equipped.remove("totem")
            self.basehp = 100
            self.fire_left = FIRE_TIME
            self.fire_acc = 0.0

    # Burns all ants once per second while the totem fire is on.
    def update_fire(self, dt):
        if self.fire_left <= 0:
            return
        self.fire_left -= dt
        self.fire_acc += dt
        while self.fire_acc >= 1:
            self.fire_acc -= 1
            if self.packs:
                damage = float(
                    math.ceil(
                        (self.starting_hp + self.starting_shield) * FIRE_DAMAGE
                    )
                )
                alive = np.flatnonzero(self.num[: self.packs] > 0)
                self.hit_packs(alive, damage)

    # -------------------------------------------------------------------------
    # [G19] ROUNDS
    # -------------------------------------------------------------------------
    # Puts wave size and ant strength back to the values of round 0.
    def reset_waves(self):
        self.ants_this_round = 10
        self.starting_hp = 10
        self.starting_shield = 1

    # Makes the next wave harder: 10% more ants, +1 hp, 10% more shield.
    def scale_wave(self):
        self.ants_this_round = min(
            int(self.ants_this_round * 1.1) + 1, STAT_CAP
        )
        self.starting_hp += 1
        self.starting_shield = min(self.starting_shield * 1.1, MONEY_CAP)

    # F5 menu: jumps straight to a round. Removes the ants on the map, then
    # scales the wave as many times as playing up to it would.
    def set_round(self, target):
        target = max(target, 1)
        self.packs = self.count = self.spawn_left = 0
        self.spawn_acc = 0.0
        self.reset_waves()
        for _ in range(target - 1):
            self.scale_wave()
        self.current_round = target - 1
        self.nextround()

    # Starts the next round.
    def nextround(self):
        # Regen and interest cards pay out, except on the very first round.
        if self.current_round > 0:
            self.basehp += self.card_sum("regen")
            self.money += self.money * self.card_sum("interest")
        self.current_round += 1
        self.leech_round = 0.0

        # Every 5th round offers 3 cards.
        if self.current_round % CARD_EVERY_ROUNDS == 0:
            self.card_choices = [roll_card() for _ in range(3)]

        # Make the wave harder and queue its ants. Left over ants from the
        # last wave stay in the queue. They all spawn over 10 seconds.
        self.scale_wave()
        self.spawn_left += self.ants_this_round
        self.spawn_rate = self.spawn_left / 10

        # Farms pay out and set the money multiplier for this round.
        self.money_multi_per_damage = 1
        self.money_per_round = 0
        for t in self.towers_of(("farm",)):
            self.money += t.money_given
            self.money_per_round += t.money_given
            self.money_multi_per_damage *= t.money_multi
        self.money = min(self.money, MONEY_CAP)

    # -------------------------------------------------------------------------
    # [G20] REMOVING DEAD ANTS
    # -------------------------------------------------------------------------
    # Deletes empty packs by moving living packs from the end of the arrays
    # into the holes, so the used rows stay packed together.
    def remove_dead(self):
        m = self.packs
        dead = np.flatnonzero(self.num[:m] <= 0)
        if dead.size == 0:
            return
        k = m - dead.size
        holes = dead[dead < k]
        fill = np.flatnonzero(self.num[k:m] > 0) + k
        for arr in (
            self.num,
            self.hp,
            self.shield,
            self.fhp,
            self.fshield,
            self.lane_off,
            self.progress,
            self.speed,
        ):
            arr[holes] = arr[fill]
        self.packs = k
