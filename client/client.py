import sys
import os
import pygame
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.game import doingsomethingwithants, Turret, Bomb, Farm , Freeze
import numpy as np
from game.game import TURRET_STATS, BOMB_STATS, FREEZE_STATS, FARM_STATS

clock = pygame.time.Clock()
pygame.init()

info = pygame.display.Info()
SCREEN_WIDTH = info.current_w
SCREEN_HEIGHT = info.current_h


screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME)

GAME_WIDTH = 1920
GAME_HEIGHT = 1080

flags = pygame.RESIZABLE | pygame.SCALED
screen = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT), flags)

def load_sheet(path, frame_w=40, frame_h=40, scale=1):
    sheet = pygame.image.load(path).convert_alpha()
    frames = []
    for i in range(sheet.get_height() // frame_h):
        frame = sheet.subsurface((0, i * frame_h, frame_w, frame_h))
        frames.append(pygame.transform.scale_by(frame, scale))
    return frames

turret_frames1 = load_sheet("client/textures/turret1.png")
turret_frames2 = load_sheet("client/textures/turret2.png")
turret_frames3 = load_sheet("client/textures/turret3.png")
turret_frames4 = load_sheet("client/textures/turret4.png")
turret_frames5 = load_sheet("client/textures/turret5.png")
turret_levels = [turret_frames1, turret_frames2, turret_frames3, turret_frames4, turret_frames5]

bomb_frames1 = load_sheet("client/textures/bomb1.png")
bomb_frames2 = load_sheet("client/textures/bomb2.png")
bomb_frames3 = load_sheet("client/textures/bomb3.png")
bomb_frames4 = load_sheet("client/textures/bomb4.png")
bomb_frames5 = load_sheet("client/textures/bomb5.png")
bomb_levels = [bomb_frames1, bomb_frames2, bomb_frames3, bomb_frames4, bomb_frames5]

freeze_frames1 = load_sheet("client/textures/freeze1.png")
freeze_frames2 = load_sheet("client/textures/freeze2.png")
freeze_frames3 = load_sheet("client/textures/freeze3.png")
freeze_frames4 = load_sheet("client/textures/freeze4.png")
freeze_frames5 = load_sheet("client/textures/freeze5.png")
freeze_levels = [freeze_frames1, freeze_frames2, freeze_frames3, freeze_frames4, freeze_frames5]

farm_frames1 = load_sheet("client/textures/farm1.png")
farm_frames2 = load_sheet("client/textures/farm2.png")
farm_frames3 = load_sheet("client/textures/farm3.png")
farm_frames4 = load_sheet("client/textures/farm4.png")
farm_frames5 = load_sheet("client/textures/farm5.png")
farm_levels = [farm_frames1, farm_frames2, farm_frames3, farm_frames4, farm_frames5]
explosion_frames = load_sheet("client/textures/explosion.png")

original_turret_legs = pygame.image.load("client/textures/turret_legs1.png").convert_alpha()
original_map_image = pygame.image.load("client/textures/map.png").convert_alpha()
bomb_legs_image = pygame.image.load("client/textures/bomb_legs.png").convert_alpha()

scaled_turret = pygame.transform.scale_by(turret_frames1[0], 2)
scaled_turret_legs = pygame.transform.scale_by(original_turret_legs, 2)
scaled_bomb_turret = pygame.transform.scale_by(bomb_frames1[0], 2)
scaled_bomb_legs = pygame.transform.scale_by(bomb_legs_image, 2)
scaled_freeze = pygame.transform.scale_by(freeze_frames1[0], 2)
scaled_farm = pygame.transform.scale_by(farm_frames1[0],2)
scaled_map_image = pygame.transform.scale_by(original_map_image,10)


map_rect = scaled_map_image.get_rect()

map_rect.topleft = (0,0)


PIXEL_FONT = pygame.font.Font("client/textures/PublicPixel.ttf", 32)

def draw_pixel_text(surface, text, color):
    text_surface = PIXEL_FONT.render(text, True, color)
    return text_surface


def start_menu(): 

    # drawings ig
    game_name=draw_pixel_text(screen, "Untitled Tower Defense",(25,25,112))

    game_name1=draw_pixel_text(screen,"Username:",(25,25,112))

    start_button_rect = pygame.Rect(GAME_WIDTH/2 - 90, GAME_HEIGHT/2 +50, 200, 50)
    start_button=draw_pixel_text(screen,"Start Game",(25,25,112))
    text_rect = start_button.get_rect(center=start_button_rect.center)

    quit_button_rect = pygame.Rect(GAME_WIDTH/2 - 90, GAME_HEIGHT/2 + 150, 200, 50)
    quit_button=draw_pixel_text(screen,"Quit Game",(25,25,112))
    text_rect1 = quit_button.get_rect(center=quit_button_rect.center)


    active = False
    player_name = ""
    pygame.key.set_repeat(400, 50)
    input_rect = pygame.Rect(GAME_WIDTH/2 - 140/2, GAME_HEIGHT/2 - 60, 200, 50)
    running = True
    while running:
        #inputs
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                elif event.key == pygame.K_BACKSPACE:
                    player_name = player_name[:-1]
                else:
                    if len(player_name) < 20 and event.unicode.isprintable() and event.unicode != "":
                        player_name += event.unicode
                        
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if start_button_rect.collidepoint(event.pos):
                        run_game()
                    elif quit_button_rect.collidepoint(event.pos):
                        running = False

                
        #rendering
        screen.fill((70, 130, 180))
        
        screen.blit(game_name,(GAME_WIDTH/2-350,GAME_HEIGHT/2-250))
        screen.blit(game_name1,(GAME_WIDTH/2-125,GAME_HEIGHT/2-100))
        screen.blit(start_button, text_rect)
        screen.blit(quit_button, text_rect1)

        pygame.draw.rect(screen, (4, 2, 115), input_rect)
        user_name_text = draw_pixel_text(screen, player_name, (250,250,250))

        screen.blit(user_name_text,(input_rect.x+5, input_rect.y+5))
        input_rect.w = max(200, user_name_text.get_width()+10)
        input_rect.x = GAME_WIDTH / 2 - input_rect.w / 2

        pygame.display.flip()

        clock.tick(60)


def run_game():
    debug_menu = False
    pygame.key.set_repeat()
    mask = np.zeros(screen.get_size(), dtype=bool)
    ants = doingsomethingwithants()
    ant_color = screen.map_rgb((90, 35, 10))

    preview_turret = turret_frames1[0].copy()
    preview1 = original_turret_legs.copy()
    preview_bomb = bomb_frames1[0].copy()
    preview2 = bomb_legs_image.copy()
    preview_freeze = freeze_frames1[0].copy()
    preview_farm = farm_frames1[0].copy()

    die_button_rect = pygame.Rect(0, 300, 120, 50)
    die_button = draw_pixel_text(screen, "funny button :}", (25, 25, 112))
    die_text_rect_button = die_button.get_rect(center=die_button_rect.center)

    placing_turret = False
    placing_bomb = False
    placing_farm = False
    placing_freeze = False

    turret_icon_rect = scaled_turret.get_rect(topleft=(50, 960))
    bomb_icon_rect = scaled_bomb_turret.get_rect(topleft=(160,960))
    freeze_icon_rect = scaled_freeze.get_rect(topleft=(270,960))
    farm_icon_rect = scaled_farm.get_rect(topleft=(380,960))

    blocked = False
    running = True
    selected = None
    
    while running:
        dt = clock.tick(60)/1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if esc_menu() == "quit":
                        running = False
                    clock.tick()  
                if event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                if event.key == pygame.K_SPACE:
                    ants.nextround()
                if event.key == pygame.K_F5:
                    debug_menu = not debug_menu
                if event.key == pygame.K_1:
                    placing_turret = True
                    placing_bomb = False
                    placing_freeze = False
                    placing_farm = False
                    selected = None
                if event.key == pygame.K_2:
                    placing_turret = False
                    placing_bomb = True
                    placing_freeze = False
                    placing_farm = False
                    selected = None
                if event.key == pygame.K_3:
                    placing_turret = False
                    placing_bomb = False
                    placing_freeze = True
                    placing_farm = False
                    selected = None
                if event.key == pygame.K_4:
                    placing_turret = False
                    placing_bomb = False
                    placing_freeze = False
                    placing_farm = True
                    selected = None
                if event.key == pygame.K_q:
                    placing_turret = False
                    placing_bomb = False
                    placing_freeze = False
                    placing_farm = False
                    selected = None
                if event.key == pygame.K_e:
                    if selected != None:
                        if isinstance(selected, Turret):
                            if selected.level !=5:
                                if ants.money >= TURRET_STATS[selected.level+1]["cost"]:
                                    Turret.upgrade(selected)
                                    ants.money -= TURRET_STATS[selected.level]["cost"]
                        if isinstance(selected, Bomb):
                            if selected.level !=5:
                                if ants.money >= BOMB_STATS[selected.level+1]["cost"]:
                                    Bomb.upgrade(selected)
                                    ants.money -= BOMB_STATS[selected.level]["cost"]
                        if isinstance(selected, Farm):
                            if selected.level !=5:
                                if ants.money >= FARM_STATS[selected.level+1]["cost"]:
                                    Farm.upgrade(selected)
                                    ants.money -= FARM_STATS[selected.level]["cost"]
                            
                        if isinstance(selected, Freeze):
                            if selected.level !=5:
                                if ants.money >= FREEZE_STATS[selected.level+1]["cost"]:
                                    Freeze.upgrade(selected)
                                    ants.money -= FREEZE_STATS[selected.level]["cost"]


            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if debug_menu and die_button_rect.collidepoint(event.pos):
                    ants.basehp = 0

                selected = None
                for i in ants.turrets:
                    if preview_turret.get_rect(center=(i.x, i.y)).collidepoint(event.pos):
                        if not placing_turret and not placing_bomb and not placing_farm and not placing_freeze:
                            selected = i
                            break
                for i in ants.bombs:
                    if preview_bomb.get_rect(center=(i.x, i.y)).collidepoint(event.pos):
                        if not placing_turret and not placing_bomb and not placing_farm and not placing_freeze:
                            selected = i
                            break
                for i in ants.freezes:
                    if preview_freeze.get_rect(center=(i.x, i.y)).collidepoint(event.pos):
                        if not placing_turret and not placing_bomb and not placing_farm and not placing_freeze:
                            selected = i
                            break
                for i in ants.farms:
                    if preview_farm.get_rect(center=(i.x, i.y)).collidepoint(event.pos):
                        if not placing_turret and not placing_bomb and not placing_farm and not placing_freeze:
                            selected = i
                            break

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if turret_icon_rect.collidepoint(event.pos):
                        placing_turret = True
                    elif placing_turret:
                        blocked = False
                        for i in ants.turrets:
                            if preview_turret.get_rect(center=event.pos).colliderect(preview_turret.get_rect(center=(i.x, i.y))):
                                blocked = True
                                break
                        for i in ants.bombs:
                            if preview_turret.get_rect(center=event.pos).colliderect(preview_bomb.get_rect(center = (i.x, i.y))):
                                blocked = True
                                break
                        for i in ants.freezes:
                            if preview_turret.get_rect(center=event.pos).colliderect(preview_freeze.get_rect(center = (i.x, i.y))):
                                blocked = True
                                break
                        for i in ants.farms:
                            if preview_turret.get_rect(center=event.pos).colliderect(preview_farm.get_rect(center = (i.x, i.y))):
                                blocked = True
                                break
                        if map_rect.contains(preview_turret.get_rect(center=event.pos)) == True: 
                            if scaled_map_image.get_at(preview_turret.get_rect(center=event.pos).topleft)== (27, 132, 12):
                                if scaled_map_image.get_at(preview_turret.get_rect(center=event.pos).topright)== (27, 132, 12):
                                    if scaled_map_image.get_at(preview_turret.get_rect(center=event.pos).bottomleft)== (27, 132, 12):
                                        if scaled_map_image.get_at(preview_turret.get_rect(center=event.pos).bottomright)== (27, 132, 12):
                                            if blocked != True:
                                                if ants.money >= TURRET_STATS[1]["cost"]:
                                                    ants.money -= TURRET_STATS[1]["cost"]
                                                    ants.turrets.append(Turret(*event.pos))
                                                    placing_turret = False
                    if bomb_icon_rect.collidepoint(event.pos):
                        placing_bomb = True
                    elif placing_bomb:
                        blocked = False
                        for i in ants.turrets:
                            if preview_turret.get_rect(center=event.pos).colliderect(preview_turret.get_rect(center=(i.x, i.y))):
                                blocked = True
                                break
                        for i in ants.bombs:
                            if preview_turret.get_rect(center=event.pos).colliderect(preview_bomb.get_rect(center = (i.x, i.y))):
                                blocked = True
                                break
                        for i in ants.freezes:
                            if preview_turret.get_rect(center=event.pos).colliderect(preview_freeze.get_rect(center = (i.x, i.y))):
                                blocked = True
                                break
                        for i in ants.farms:
                            if preview_turret.get_rect(center=event.pos).colliderect(preview_farm.get_rect(center = (i.x, i.y))):
                                blocked = True
                                break
                        if map_rect.contains(preview_bomb.get_rect(center=event.pos)) == True:
                            if scaled_map_image.get_at(preview_bomb.get_rect(center=event.pos).topleft)== (27, 132, 12):
                                if scaled_map_image.get_at(preview_bomb.get_rect(center=event.pos).topright)== (27, 132, 12):
                                    if scaled_map_image.get_at(preview_bomb.get_rect(center=event.pos).bottomleft)== (27, 132, 12):
                                        if scaled_map_image.get_at(preview_bomb.get_rect(center=event.pos).bottomright)== (27, 132, 12):
                                            if blocked != True:   
                                                if ants.money >= BOMB_STATS[1]["cost"]:
                                                    ants.money -= BOMB_STATS[1]["cost"] 
                                                    ants.bombs.append(Bomb(*event.pos))
                                                    placing_bomb = False
                    if freeze_icon_rect.collidepoint(event.pos):
                        placing_freeze = True
                    elif placing_freeze:
                        blocked = False
                        for i in ants.turrets:
                            if preview_turret.get_rect(center=event.pos).colliderect(preview_turret.get_rect(center=(i.x, i.y))):
                                blocked = True
                                break
                        for i in ants.bombs:
                            if preview_turret.get_rect(center=event.pos).colliderect(preview_bomb.get_rect(center = (i.x, i.y))):
                                blocked = True
                                break
                        for i in ants.freezes:
                            if preview_turret.get_rect(center=event.pos).colliderect(preview_freeze.get_rect(center = (i.x, i.y))):
                                blocked = True
                                break
                        for i in ants.farms:
                            if preview_turret.get_rect(center=event.pos).colliderect(preview_farm.get_rect(center = (i.x, i.y))):
                                blocked = True
                                break
                        if map_rect.contains(preview_freeze.get_rect(center=event.pos)) == True: 
                            if scaled_map_image.get_at(preview_freeze.get_rect(center=event.pos).topleft)== (27, 132, 12):
                                if scaled_map_image.get_at(preview_freeze.get_rect(center=event.pos).topright)== (27, 132, 12):
                                    if scaled_map_image.get_at(preview_freeze.get_rect(center=event.pos).bottomleft)== (27, 132, 12):
                                        if scaled_map_image.get_at(preview_freeze.get_rect(center=event.pos).bottomright)== (27, 132, 12):
                                            if blocked != True: 
                                                if ants.money >= FREEZE_STATS[1]["cost"]:
                                                    ants.money -= FREEZE_STATS[1]["cost"]
                                                    ants.freezes.append(Freeze(*event.pos))
                                                    placing_freeze = False
                    if farm_icon_rect.collidepoint(event.pos):
                        placing_farm = True
                    elif placing_farm:
                        blocked = False
                        for i in ants.turrets:
                            if preview_turret.get_rect(center=event.pos).colliderect(preview_turret.get_rect(center=(i.x, i.y))):
                                blocked = True
                                break
                        for i in ants.bombs:
                            if preview_turret.get_rect(center=event.pos).colliderect(preview_bomb.get_rect(center = (i.x, i.y))):
                                blocked = True
                                break
                        for i in ants.freezes:
                            if preview_turret.get_rect(center=event.pos).colliderect(preview_freeze.get_rect(center = (i.x, i.y))):
                                blocked = True
                                break
                        for i in ants.farms:
                            if preview_turret.get_rect(center=event.pos).colliderect(preview_farm.get_rect(center = (i.x, i.y))):
                                blocked = True
                                break
                        if map_rect.contains(preview_farm.get_rect(center=event.pos)) == True:
                            if scaled_map_image.get_at(preview_farm.get_rect(center=event.pos).topleft)== (27, 132, 12):
                                if scaled_map_image.get_at(preview_farm.get_rect(center=event.pos).topright)== (27, 132, 12):
                                    if scaled_map_image.get_at(preview_farm.get_rect(center=event.pos).bottomleft)== (27, 132, 12):
                                        if scaled_map_image.get_at(preview_farm.get_rect(center=event.pos).bottomright)== (27, 132, 12):
                                            if blocked != True: 
                                                if ants.money >= FARM_STATS[1]["cost"]:
                                                    ants.money -= FARM_STATS[1]["cost"]
                                                    ants.farms.append(Farm(*event.pos))
                                                    placing_farm = False
                if event.button == 3:     
                    placing_turret = False
                    placing_bomb = False
                    placing_freeze = False
                    placing_farm = False
                    selected = None
                

        screen.blit(scaled_map_image, (0, 0))
        ants.updateants(dt)

        def draw_tower_hitboxes():
            for t in ants.turrets:
                pygame.draw.rect(screen,(255,0,0), turret_frames1[0].get_rect(center = (t.x, t.y)), 2)
            for t in ants.bombs:
                pygame.draw.rect(screen,(255,0,0), bomb_frames1[0].get_rect(center = (t.x, t.y)), 2)
            for t in ants.freezes:
                pygame.draw.rect(screen,(255,0,0), freeze_frames1[0].get_rect(center = (t.x, t.y)), 2)
            for t in ants.farms:
                pygame.draw.rect(screen,(255,0,0), farm_frames1[0].get_rect(center = (t.x, t.y)), 2)
        
        
        if debug_menu == True:
            ants_left_to_spawn = draw_pixel_text(screen,"ants to spawn " + str(ants.spawn_left),(255,255,255))
            debug_fps = draw_pixel_text(screen, "fps " + str(int(clock.get_fps())),(255,255,255))
            debug_alive_ants = draw_pixel_text(screen, "alive ants " + str(ants.count),(255,255,255))
            debug_ant_hp = draw_pixel_text(screen, "ant hp " + str(int(ants.starting_hp)),(255,255,255))
            debug_ant_shield = draw_pixel_text(screen,"ant shield " + str(int(ants.starting_shield)),(255,255,255))

            screen.blit(debug_alive_ants,(0,250))
            screen.blit(debug_fps,(0,200))
            screen.blit(ants_left_to_spawn,(0,150))
            screen.blit(debug_ant_hp,(0,350))
            screen.blit(debug_ant_shield,(0,400))

            screen.blit(die_button, die_button_rect)
            

        if ants.basehp <=0:
            death_screen(ants)

        # utilities score moeny hp nshi
        score_text = draw_pixel_text(screen, "SCORE: ", (255, 219, 88))
        score_itself_text = draw_pixel_text(screen, str(int(ants.score)), (255,219,88))
        money_text = draw_pixel_text(screen, "MONEY: ", (255, 219, 88))
        money_itself_text = draw_pixel_text(screen, str(int(ants.money)), (255,219,88))
        health_text = draw_pixel_text(screen, "HEALTH: ", (220, 20, 60))
        health_itself_text = draw_pixel_text(screen, str(ants.basehp),(220,20,60))
        round_text = draw_pixel_text(screen, "ROUND: ", (255,255,255))
        round_itself_text = draw_pixel_text(screen, str(ants.current_round),(255,255,255))

        screen.blit(score_text, (10,20))
        screen.blit(score_itself_text,(200,20))
        screen.blit(money_text, (10, 80))
        screen.blit(money_itself_text,(200,80))
        screen.blit(health_text,(1100,20))
        screen.blit(health_itself_text,(1320,20))
        screen.blit(round_text,(1100,80))
        screen.blit(round_itself_text,(1300,80))

        #ants

        n = ants.count
        mask[:] = False
        mask[ants.x[:n], ants.y[:n]] = True
        mask[1:, :] |= mask[:-1, :]
        mask[2:, :] |= mask[:-2, :]
        mask[:, 1:] |= mask[:, :-1]
        mask[:, 2:] |= mask[:, :-2]

        screen_pixels = pygame.surfarray.pixels2d(screen)
        screen_pixels[mask] = ant_color
        del screen_pixels

        screen_pixels = pygame.surfarray.pixels3d(screen)
        screen_pixels[mask] = (90, 35, 10)
        del screen_pixels
        
        # towers

        screen.blit(scaled_turret_legs,(50,960))
        screen.blit(scaled_turret, (50,960))
        screen.blit(scaled_bomb_legs,(160,960))
        screen.blit(scaled_bomb_turret,(160, 960))
        screen.blit(scaled_freeze,(270,960))
        screen.blit(scaled_farm,(380,960))

        turret_cost = draw_pixel_text(screen, str(TURRET_STATS[1]["cost"]),(255,255,255))
        bomb_turret_cost = draw_pixel_text(screen, str(BOMB_STATS[1]["cost"]),(255,255,255))
        freeze_cost = draw_pixel_text(screen, str(FREEZE_STATS[1]["cost"]),(255,255,255))
        farm_cost = draw_pixel_text(screen, str(FARM_STATS[1]["cost"]),(255,255,255))

        screen.blit(turret_cost,(40,910))
        screen.blit(bomb_turret_cost,(150,910))
        screen.blit(freeze_cost,(260,910))
        screen.blit(farm_cost,(370,910))

        for t in ants.turrets:
            screen.blit(original_turret_legs, original_turret_legs.get_rect(center=(t.x, t.y)))
            frames = turret_levels[t.level - 1]
            frame = 0
            if t.since_shot < 0.1:
                frame = min(t.shot_frame, len(frames) - 1)
            img = pygame.transform.rotate(frames[frame], 180 - t.angle)
            screen.blit(img, img.get_rect(center=(t.x, t.y)))

        if placing_turret:
            draw_tower_hitboxes()
            mx, my = pygame.mouse.get_pos()
            preview_turret.set_alpha(150)         
            preview1.set_alpha(150) 
            screen.blit(preview_turret, preview_turret.get_rect(center=(mx, my)))
            screen.blit(preview1, preview1.get_rect(center=(mx,my)))
            pygame.draw.rect(screen, (255, 0, 0), preview1.get_rect(center=(mx, my)), 2)
            pygame.draw.circle(screen, (255, 255, 255), (mx, my), TURRET_STATS[1]["range"], 1) 
        

        if placing_bomb:
            draw_tower_hitboxes()
            mx, my = pygame.mouse.get_pos()
            preview_bomb.set_alpha(150)         
            preview2.set_alpha(150) 
            screen.blit(preview_bomb, preview_bomb.get_rect(center=(mx, my)))
            screen.blit(preview2, preview2.get_rect(center=(mx,my)))
            pygame.draw.rect(screen, (255, 0, 0), preview1.get_rect(center=(mx, my)), 2)
            pygame.draw.circle(screen, (255, 255, 255), (mx, my), BOMB_STATS[1]["range"], 1) 
        

        if placing_freeze:
            draw_tower_hitboxes()
            mx, my = pygame.mouse.get_pos()
            preview_freeze.set_alpha(150)          
            screen.blit(preview_freeze, preview_freeze.get_rect(center=(mx, my)))
            pygame.draw.rect(screen, (255, 0, 0), preview1.get_rect(center=(mx, my)), 2)
            pygame.draw.circle(screen, (255, 255, 255), (mx, my),FREEZE_STATS[1]["range"], 1) 
      
        if placing_farm:
            draw_tower_hitboxes()
            mx, my = pygame.mouse.get_pos()
            preview_farm.set_alpha(150)    
            pygame.draw.rect(screen, (255, 0, 0), preview1.get_rect(center=(mx, my)), 2)      
            screen.blit(preview_farm, preview_farm.get_rect(center=(mx, my)))
      
        if selected:
            pygame.draw.rect(screen,(255,0,0), turret_frames1[0].get_rect(center = (selected.x, selected.y)), 2)
            tower_level_text = draw_pixel_text(screen, "level: "+ str(selected.level) + "/5", (255,255,255))
            screen.blit(tower_level_text, (1550,20))
            if isinstance(selected, Turret):
                pygame.draw.circle(screen, (255, 255, 255), (selected.x, selected.y), TURRET_STATS[selected.level]["range"], 1) 
                if selected.level != 5:
                    turret_upgrade = draw_pixel_text(screen, "cost: " + str(TURRET_STATS[selected.level+1]["cost"]), (255,255,255))
                    screen.blit(turret_upgrade,(1550,70))
            if isinstance(selected, Bomb):
                pygame.draw.circle(screen, (255, 255, 255), (selected.x, selected.y), BOMB_STATS[selected.level]["range"], 1) 
                if selected.level != 5:
                    bomb_upgrade = draw_pixel_text(screen, "cost: " + str(BOMB_STATS[selected.level+1]["cost"]), (255,255,255))
                    screen.blit(bomb_upgrade,(1550,70))
            if isinstance(selected, Freeze):
                pygame.draw.circle(screen, (255, 255, 255), (selected.x, selected.y), FREEZE_STATS[selected.level]["range"], 1) 
                if selected.level != 5:
                    freeze_upgrade = draw_pixel_text(screen, "cost: " + str(FREEZE_STATS[selected.level+1]["cost"]), (255,255,255))
                    screen.blit(freeze_upgrade,(1550,70))
            if isinstance(selected, Farm):
                pygame.draw.circle(screen, (255, 255, 255), (selected.x, selected.y), FARM_STATS[selected.level]["range"], 1) 
                if selected.level != 5:
                    farm_upgrade = draw_pixel_text(screen, "cost: " + str(FARM_STATS[selected.level+1]["cost"]), (255,255,255))
                    screen.blit(farm_upgrade,(1550,70))


        pygame.display.flip() 
    

    pygame.quit()
    sys.exit()

def death_screen(ants):
    overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))

    text = draw_pixel_text(screen, "YOU DIED", (220, 20, 60))
    score = draw_pixel_text(screen, "SCORE", (255,219,88))
    score_itself = draw_pixel_text(screen,str(ants.score),(255,219,88))
    
    screen.blit(text, text.get_rect(center=(GAME_WIDTH / 2, GAME_HEIGHT / 2-300)))
    screen.blit(score, score.get_rect(center = (GAME_WIDTH / 2, GAME_HEIGHT / 2 -200)))
    screen.blit(score_itself, score_itself.get_rect(center = (GAME_WIDTH / 2, GAME_HEIGHT / 2 -100)))
    
    pygame.display.flip()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
        clock.tick(30)

    pygame.quit()
    sys.exit()

def esc_menu():
    overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)

    continue_button_rect = pygame.Rect(GAME_WIDTH/2 - 90, GAME_HEIGHT/2 +50, 200, 50)
    continue_button=draw_pixel_text(screen,"continue",(0,144,160))
    continue_text_rect = continue_button.get_rect(center=continue_button_rect.center)

    quit_button_rect = pygame.Rect(GAME_WIDTH/2 - 90, GAME_HEIGHT/2 -50, 200, 50)
    quit_button=draw_pixel_text(screen,"quit",(220, 20, 60))
    quit_text_rect = quit_button.get_rect(center=quit_button_rect.center)

    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))
    screen.blit(continue_button, continue_text_rect)
    screen.blit(quit_button, quit_text_rect)
    pygame.display.flip()


    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "continue"        
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if continue_button_rect.collidepoint(event.pos):
                    return "continue"
                if quit_button_rect.collidepoint(event.pos):
                    return "quit"
        clock.tick(30)

    

if __name__ == "__main__":
  start_menu()
