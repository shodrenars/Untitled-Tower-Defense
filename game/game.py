import numpy as np
import random
import math

money_gain_per_damage = 0.5
LANES = 31          
ANT_SPEED = 60     
EXPLOSION_TIME = 0.3

def move_step(x, y, d):
    go_forward = (d == 0) & (((y >= 520) & (y <= 550)) | ((y >= 370) & (y <= 400)) | ((y >= 670) & (y <= 700)))
    x[go_forward] += 1
    #uz leju
    go_down = (d == 1) & (((x >= 180) & (x <= 210)) | ((x >= 590) & (x <= 620)) | ((x >= 990) & (x <= 1020)) | ((x >= 1390) & (x <= 1420)) | ((x >= 1600) & (x <= 1630)))
    y[go_down] += 1
    #uz augsu
    go_up = (d == 2) & (((x >= 390) & (x <= 420)) | ((x >= 790) & (x <= 820)) | ((x >= 1190) & (x <= 1220)) | ((x >= 1600) & (x <= 1630)))
    y[go_up] -= 1

    # d = 0 pa labi
    # d = 1 uz leju
    # d = 2 uz augsu
    #pirmais pagrieziens
    turn = (d == 0) & (y >= 520) & (y <= 550) & (x+y == 730)
    d[turn] = 1
    # otrais pagriziens
    turn = (d == 1) & (x >=180) & (x<=210) & (x+y == 880)
    d[turn] = 0
    # trešais pagrieziens
    turn = (d == 0) & (y >= 670) & (y <= 700) & (y-x == 280)
    d[turn] = 2
    # ceturtais pagrieziens
    turn = (d == 2) & (x >= 390) & (x <= 420) & (x-y == 20)
    d[turn] = 0
    # piektais pagrieziens
    turn = (d == 0) & (y >= 370) & (y <= 400) & (x+y == 990)
    d[turn] = 1
    # sestais pagrieziens
    turn = (d == 1) & (x >= 590) & (x <= 620) & (x+y == 1290)
    d[turn] = 0
    # septitais pagriziens
    turn = (d == 0) & (y >= 670) & (y <= 700) & (x - y == 120)
    d[turn] = 2
    # astotais pagrieziens
    turn = (d == 2) & (x >= 790) & (x <= 820) & (x - y == 420)
    d[turn] = 0
    # devitais pagrieziens
    turn = (d == 0) & (y >= 370) & (y <= 400) & (x + y == 1390)
    d[turn] = 1
    # desmitais pagrieziens
    turn = (d == 1) & (x >= 990) & (x <= 1020) & (x + y == 1690)
    d[turn] = 0
    # vienpadsmitais pagrieziens
    turn = (d == 0) & (y >= 670) & (y <= 700) & (x - y == 520)
    d[turn] = 2
    # divpadsmitais pagrieziens
    turn = (d == 2) & (x >= 1190) & (x <= 1220) & (x - y == 820)
    d[turn] = 0
    # trīspadsmitais pagrieziens
    turn = (d == 0) & (y >= 370) & (y <= 400) & (x + y == 1790)
    d[turn] = 1
    # četrpadsmitais pagrieziens
    turn = (d == 1) & (x >= 1390) & (x <= 1420) & (x + y == 2090)
    d[turn] = 0
    # piecpadsmitais pagrieziens
    turn = (d == 0) & (y >= 670) & (y <= 700) & (x - y == 930)
    d[turn] = 2
    # sešpadsmitais pagrieziens
    turn = (d == 2) & (x >= 1600) & (x <= 1630) & (x - y == 1080)
    d[turn] = 0   

def build_path():
    x = np.full(LANES, 10, dtype=np.int16)
    y = np.arange(520, 520 + LANES, dtype=np.int16)
    d = np.zeros(LANES, dtype=np.int8)
    xs = [x.copy()]
    ys = [y.copy()]
    for _ in range(100000):
        move_step(x, y, d)
        xs.append(x.copy())
        ys.append(y.copy())
        if ((d == 0) & (y >= 520) & (y <= 550) & (x >= 1679)).all():
            break
    else:
        raise RuntimeError("bla kkads cels neaizgaja pareizi")
    return np.array(xs).T, np.array(ys).T

PATH_X, PATH_Y = build_path()
class doingsomethingwithants:
    def __init__(self, max_ants=10000000):
        self.max_ants = max_ants
        self.active = np.zeros(max_ants, dtype = np.bool)
        self.x = np.zeros(max_ants, dtype=np.int16)
        self.y = np.zeros(max_ants, dtype=np.int16)
        self.hp = np.zeros(max_ants, dtype=np.int32)
        self.shield = np.zeros(max_ants, dtype = np.int32)
        self.lane = np.zeros(max_ants, dtype=np.int8)
        self.speed = np.zeros(max_ants, dtype=np.float32)
        self.progress = np.zeros(max_ants, dtype=np.float32)
        self.path_x, self.path_y = PATH_X, PATH_Y
        self.path_len = self.path_x.shape[1]
        self.turrets = []
        self.explosions = []
        self.bombs = []
        self.freezes = []
        self.farms = []
        self.money = 1000
        self.score = 0
        self.money_per_round = 0
        self.cover_range = None
        
        self.count = 0
        self.basehp = 100
        self.ants_per_second = 0
        self.ants_this_round = 10
        self.ants_need_to_spawn = 0
        self.starting_hp = 10
        self.starting_shield = 1
        self.spawn_left = 0    
        self.spawn_rate = 0.0   
        self.spawn_acc = 0.0
        self.current_round = 0
        self.money_multi_per_damage = 1

    def updateants(self, dt):
        for e in self.explosions:
            e["age"] += dt
        self.explosions = [e for e in self.explosions if e["age"] < EXPLOSION_TIME]
        if self.count == 0 and self.current_round > 0 and self.spawn_left == 0:
            self.nextround()
        if self.spawn_left > 0:
            self.spawn_acc += self.spawn_rate * dt
            n = min(int(self.spawn_acc), self.spawn_left, self.max_ants - self.count)
            if n > 0:
                self.spawn_acc -= n
                self.spawn_left -= n
                s = slice(self.count, self.count + n)
                self.hp[s] = self.starting_hp
                self.shield[s] = self.starting_shield
                self.progress[s] = 0
                self.count += n
                self.lane[s] = np.random.randint(0, LANES, size=n)
                self.speed[s] = ANT_SPEED

        n = self.count
        lane = self.lane[:n]
        p = self.progress[:n]
        p += self.speed[:n] * dt
        self.apply_freezes(n)
        step = p.astype(np.int32)
        at_base = step >= self.path_len - 1
        np.minimum(step, self.path_len - 1, out=step)
        self.x[:n] = self.path_x[lane, step]
        self.y[:n] = self.path_y[lane, step]

        self.update_turrets(dt)
        self.basehp -= np.count_nonzero(at_base)
        hp = self.hp[:n]
        hp[at_base] = 0
        self.remove_dead()
        self.remove_dead()

    def update_turrets(self, dt):
        self.update_bombs(dt)
        ready = []
        for t in self.turrets:
            t.since_shot += dt
            t.timer -= dt
            if t.timer <= 0:
                ready.append(t)

        n = self.count
        if not ready or n == 0:
            for t in ready:
                t.timer = 0
            return

        lane = self.lane[:n]
        hp = self.hp[:n]
        step = np.minimum(self.progress[:n], self.path_len - 1).astype(np.int16)
        order = np.argsort(step, kind="stable")
        counts = np.bincount(step, minlength=self.path_len)
        starts = np.concatenate(([0], np.cumsum(counts)))

        for t in ready:
            if t.cover_range != t.range:  
                dx = self.path_x.astype(np.int32) - t.x
                dy = self.path_y.astype(np.int32) - t.y
                t.cover = dx * dx + dy * dy <= t.range * t.range
                t.steps = np.flatnonzero(t.cover.any(axis=0))[::-1]
                t.cover_range = t.range

        
            while t.timer <= 0:
                target = -1
                busy = t.steps[counts[t.steps] > 0]
                for s in busy:
                    here = order[starts[s]:starts[s + 1]]
                    ok = here[t.cover[lane[here], s] & (hp[here] > 0)]
                    if ok.size:
                        target = ok[0]
                        break
                if target < 0:
                    t.timer = 0   
                    break

                damage_done = 0

                t.angle = math.degrees(math.atan2(int(self.y[target]) - t.y, int(self.x[target]) - t.x))
                if self.shield[target] >= t.damage:
                    self.shield[target] -= t.damage
                elif self.shield[target]<= t.damage and self.shield[target] != 0:
                    tempt = t.damage
                    tempt -= self.shield[target]
                    if tempt <= self.hp[target]:
                        damage_done = tempt
                    else:
                        damage_done = self.hp[target] 
                    self.money += damage_done * money_gain_per_damage * self.money_multi_per_damage
                    self.shield[target] = 0
                    self.hp[target] -= tempt
                else:
                    self.hp[target] -= t.damage
                    self.money += t.damage * money_gain_per_damage * self.money_multi_per_damage
                t.timer += t.cooldown
                t.since_shot = 0.0
                t.shot_frame = random.randint(1, 4)
    def apply_freezes(self, n):
        speed = self.speed[:n]
        speed[:] = ANT_SPEED 
        if not self.freezes or n == 0:
            return
        lane = self.lane[:n]
        step = np.minimum(self.progress[:n], self.path_len - 1).astype(np.int32)
        for f in self.freezes:
            if f.cover_range != f.range:  
                dx = self.path_x.astype(np.int32) - f.x
                dy = self.path_y.astype(np.int32) - f.y
                f.cover = dx * dx + dy * dy <= f.range * f.range
                f.cover_range = f.range
            in_range = f.cover[lane, step]
            np.minimum(speed, f.slow_speed, out=speed, where=in_range)

    def update_bombs(self, dt):
        ready = []
        for b in self.bombs:
            b.since_shot += dt
            b.timer -= dt
            if b.timer <= 0:
                ready.append(b)

        n = self.count
        if not ready or n == 0:
            for b in ready:
                b.timer = 0
            return

        lane = self.lane[:n]
        hp = self.hp[:n]
        step = np.minimum(self.progress[:n], self.path_len - 1).astype(np.int16)
        order = np.argsort(step, kind="stable")
        counts = np.bincount(step, minlength=self.path_len)
        starts = np.concatenate(([0], np.cumsum(counts)))
        x = self.x[:n].astype(np.int32)
        y = self.y[:n].astype(np.int32)

        for b in ready:
            if b.cover_range != b.range:   # new or upgraded
                dx = self.path_x.astype(np.int32) - b.x
                dy = self.path_y.astype(np.int32) - b.y
                b.cover = dx * dx + dy * dy <= b.range * b.range
                b.steps = np.flatnonzero(b.cover.any(axis=0))[::-1]
                b.cover_range = b.range

            target = -1
            busy = b.steps[counts[b.steps] > 0]
            for s in busy:
                here = order[starts[s]:starts[s + 1]]
                ok = here[b.cover[lane[here], s] & (hp[here] > 0)]
                if ok.size:
                    target = ok[0]
                    break
            if target < 0:
                b.timer = 0   
                continue

            
            tx = int(x[target])
            ty = int(y[target])
            dx = x - tx
            dy = y - ty
            r = b.explosion_radius
            hit = np.flatnonzero((dx * dx + dy * dy <= r * r) & (hp > 0))

            
            absorbed = np.minimum(self.shield[hit], b.damage)
            self.shield[hit] -= absorbed
            to_hp = b.damage - absorbed
            self.money += np.minimum(to_hp, hp[hit]).sum() * money_gain_per_damage
            self.hp[hit] -= to_hp

            self.explosions.append({"x": tx, "y": ty, "r": r, "age": 0.0})
            b.angle = math.degrees(math.atan2(ty - b.y, tx - b.x))
            b.timer += b.cooldown
            b.since_shot = 0.0
            b.shot_frame = random.randint(1, 4)

    def nextround(self):
     
        self.current_round += 1
        self.ants_this_round = int(self.ants_this_round * 1.1) + 1
        self.starting_hp +=1
        self.starting_shield *= 1.1
        self.spawn_left += self.ants_this_round
        self.spawn_rate = self.spawn_left / 10  
        self.money_multi_per_damage = 1
        self.money_per_round = 0
        for i in self.farms:
            self.money += FARM_STATS[i.level]["money_given"]
            self.money_per_round += FARM_STATS[i.level]["money_given"]
            self.money_multi_per_damage *= FARM_STATS[i.level]["money multi on damage"]

        
    def remove_dead(self):
        n = self.count
        alive = self.hp[:n] > 0
        k = int(alive.sum())
        if k == n:
            return
        for arr in (self.x, self.y, self.hp, self.lane, self.shield, self.progress, self.speed):
            arr[:k] = arr[:n][alive]
        self.count = k
        self.score += n - k

TURRET_STATS = {
    1: {"range": 200, "damage": 10,  "cooldown": 1, "cost": 150},
    2: {"range": 240, "damage": 20,  "cooldown": 0.5, "cost": 400},
    3: {"range": 280, "damage": 30, "cooldown": 0.3, "cost": 700},
    4: {"range": 320, "damage": 40, "cooldown": 0.1, "cost": 3250},
    5: {"range": 450, "damage": 100, "cooldown": 0.04, "cost": 29000},
}


class Turret:
    def __init__(self, x, y, level=1):
        stats = TURRET_STATS[level]
        self.cost = stats["cost"]
        self.x = x
        self.y = y
        self.timer = 0.0 
        self.cover_range = None     
        self.angle = 180.0   
        self.since_shot = 99.0
        self.set_level(level)
        self.shot_frame = 1

    def set_level(self, level):
        self.level = level
        stats = TURRET_STATS[level]
        self.range = stats["range"]
        self.damage = stats["damage"]
        self.cooldown = stats["cooldown"]

    def upgrade(self):
        if self.level < len(TURRET_STATS):
            self.set_level(self.level + 1)
   

BOMB_STATS = {
    1: {"range": 150, "damage": 10,  "cooldown": 1.0, "cost": 500000,  "explosion_radius": 30},
    2: {"range": 170, "damage": 20,  "cooldown": 0.8, "cost": 500000,  "explosion_radius": 35},
    3: {"range": 190, "damage": 50, "cooldown": 0.6, "cost": 1000000, "explosion_radius": 40},
    4: {"range": 210, "damage": 100, "cooldown": 0.5, "cost": 1600000, "explosion_radius": 45},
    5: {"range": 240, "damage": 200, "cooldown": 0.3, "cost": 4000000, "explosion_radius": 55},
}
class Bomb:
    def __init__(self, x, y, level=1):
        stats = BOMB_STATS[level]
        self.cost = stats["cost"]
        self.x = x
        self.y = y
        self.timer = 0.0
        self.since_shot = 99.0
        self.angle = 180.0
        self.shot_frame = 1
        self.cover_range = None
        self.set_level(level)

    def set_level(self, level):
        self.level = level
        stats = BOMB_STATS[level]
        self.range = stats["range"]
        self.damage = stats["damage"]
        self.cooldown = stats["cooldown"]
        self.explosion_radius = stats["explosion_radius"]

    def upgrade(self):
        if self.level < len(BOMB_STATS):
            self.set_level(self.level + 1)

FREEZE_STATS = {
    1: {"range": 65, "cost": 150, "freeze_multi": 60},
    2: {"range": 65, "cost": 150, "freeze_multi": 55},
    3: {"range": 65, "cost": 250, "freeze_multi": 45},
    4: {"range": 65, "cost": 400, "freeze_multi": 30},
    5: {"range": 65, "cost": 700, "freeze_multi": 20},
}

class Freeze:
    def __init__(self, x, y, level=1):
        stats = FREEZE_STATS[level]
        self.cost = stats["cost"]
        self.x = x
        self.y = y
        self.cover_range = None
        self.set_level(level)

    def set_level(self, level):
        self.level = level
        stats = FREEZE_STATS[level]
        self.range = stats["range"]
        self.slow_speed = stats["freeze_multi"]

    def upgrade(self):
        if self.level < len(FREEZE_STATS):
            self.set_level(self.level + 1)

FARM_STATS = {
    1: { "cost": 150, "money_given": 50, "money multi on damage": 1},
    2: { "cost": 400, "money_given": 100, "money multi on damage": 1},
    3: { "cost": 1000, "money_given": 200, "money multi on damage": 1.01},
    4: { "cost": 10000, "money_given": 1000, "money multi on damage": 1.1},
    5: { "cost": 50000, "money_given": 2000, "money multi on damage": 1.2},
}

class Farm:
    def __init__(self, x, y, level=1):
        stats = FARM_STATS[level]
        self.cost = stats["cost"]
        self.x = x
        self.y = y
        self.money_multi = stats["money multi on damage"]
        self.set_level(level)

    def set_level(self, level):
        self.level = level
        stats = FARM_STATS[level]

    def upgrade(self):
        if self.level < len(FARM_STATS):
            self.set_level(self.level + 1)