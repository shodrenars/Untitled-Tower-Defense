import numpy as np
import random


class doingsomethingwithants:
    def __init__(self, max_ants=10000000):
        self.max_ants = max_ants
        self.active = np.zeros(max_ants, dtype = np.bool)
        self.x = np.zeros(max_ants, dtype=np.int16)
        self.y = np.zeros(max_ants, dtype=np.int16)
        self.hp = np.zeros(max_ants, dtype=np.int16)
        self.direction = np.zeros(max_ants, dtype=np.int8)
        self.shield = np.zeros(max_ants, dtype = np.int16)
        self.turrets = []
        
        self.count = 0
        self.basehp = 100
        self.ants_per_second = 0
        self.ants_this_round = 10
        self.ants_need_to_spawn = 0
        self.starting_hp = 10
        self.starting_shield = 10
        self.spawn_left = 0    
        self.spawn_rate = 0.0   
        self.spawn_acc = 0.0
        self.current_round = 0

    def updateants(self, dt):
        if self.count == 0 and self.current_round > 0 and self.spawn_left == 0:
            self.nextround()
        if self.spawn_left > 0:
            self.spawn_acc += self.spawn_rate * dt
            n = min(int(self.spawn_acc), self.spawn_left, self.max_ants - self.count)
            if n > 0:
                self.spawn_acc -= n
                self.spawn_left -= n
                s = slice(self.count, self.count + n)
                self.x[s] = 10
                self.y[s] = np.random.randint(520, 551, size=n)  
                self.hp[s] = self.starting_hp
                self.shield[s] = self.starting_shield
                self.direction[s] = 0
                self.count += n

        n = self.count
        x, y, d = self.x[:n], self.y[:n], self.direction[:n]

        #pa kreisi
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

        damage_ants = (d == 0) & (y>=520) & (y <= 550) & (x >= 1679)
        how_much = np.count_nonzero(damage_ants)
        self.basehp -= how_much
        hp = self.hp[:n]
        hp[damage_ants] = 0
        self.remove_dead()

    def nextround(self):
     
        self.current_round += 1
        self.ants_this_round = int(self.ants_this_round * 1.1) + 1
        self.starting_hp *= 1.01
        self.starting_shield *= 1.01
        self.spawn_left += self.ants_this_round
        self.spawn_rate = self.spawn_left / 10  
        

    def remove_dead(self):
        
        n = self.count
        alive = self.hp[:n] > 0
        k = int(alive.sum())
        for arr in (self.x, self.y, self.hp, self.direction, self.shield):
            arr[:k] = arr[:n][alive]
        self.count = k

TURRET_STATS = {
    1: {"range": 150, "damage": 5,  "cooldown": 1.0, "cost": 100},
    2: {"range": 170, "damage": 8,  "cooldown": 0.8, "cost": 150},
    3: {"range": 190, "damage": 12, "cooldown": 0.6, "cost": 250},
    4: {"range": 210, "damage": 18, "cooldown": 0.5, "cost": 400},
    5: {"range": 240, "damage": 30, "cooldown": 0.3, "cost": 700},
}


class Turret:
    def __init__(self, x, y, level=1):
        stats = TURRET_STATS
        self.cost = stats["cost"]
        self.x = x
        self.y = y
        self.set_level(level)

    def set_level(self, level):
        self.level = level
        stats = TURRET_STATS[level]
        self.range = stats["range"]
        self.damage = stats["damage"]
        self.cooldown = stats["cooldown"]

    def upgrade(self):
        if self.level < len(TURRET_STATS):
            self.set_level(self.level + 1)
   

