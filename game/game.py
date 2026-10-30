import numpy as np
import random

current_round = 0
class doingsomethingwithants:
    def __init__(self, max_ants=1000000):
        self.active = np.zeros(max_ants, dtype = np.bool)
        self.x = np.zeros(max_ants, dtype=np.int16)
        self.y = np.zeros(max_ants, dtype=np.int16)
        self.hp = np.zeros(max_ants, dtype=np.int16)
        self.direction = np.zeros(max_ants, dtype=np.int8)

        self.ants_per_second = 0
        self.ants_this_round = 10
        self.ants_need_to_spawn = 0
        self.starting_hp = 10

    def updateants(self, dt):
        if self.ants_need_to_spawn > 0:
            self.ants_need_to_spawn -= self.ants_per_second
            inactive_slots = np.where(~self.active)[0]
            actual_spawn_count = min(self.ants_per_second, len(inactive_slots))
            spawn_slots = inactive_slots[:int(actual_spawn_count)]
            
            self.active[spawn_slots] = True
            self.x[spawn_slots] = 10
            self.y[spawn_slots] = random.randint(520,550)
        #pa kreisi
        go_forward = np.where(self.active & (self.direction == 0) & (((self.y >= 520) & (self.x <= 550)) |  ((self.y >= 370) & (self.y <= 400)) | ((self.y >= 670) & (self.y <= 700))))[0]
        self.x[go_forward] += 1
        #uz leju
        go_down = np.where(self.active & (self.direction == 1) & (((self.x >= 180) & (self.x <= 210)) |((self.x >= 790) & (self.x <= 820)) |((self.x >= 1190) & (self.x <= 1220)) |((self.x >= 1600) & (self.x <= 1630))))[0]        
        self.y[go_down] += 1
        #uz augsu
        go_up = np.where(self.active & (self.direction == 2) & (((self.x > 390) & (self.x < 420)) |((self.x >= 590) & (self.x <= 620)) |((self.x >= 990) & (self.x <= 1020)) |((self.x >= 1390) & (self.x <= 1420)) ))[0]        
        self.x[go_up] -=1


    def nextround(self):
        global current_round
        current_round += 1
        self.ants_this_round = self.ants_this_round * 0.10 + self.ants_this_round
        self.ants_need_to_spawn += self.ants_this_round
        self.starting_hp = self.starting_hp * 0.01 + self.starting_hp
        self.ants_per_second = self. ants_need_to_spawn / 60
        


