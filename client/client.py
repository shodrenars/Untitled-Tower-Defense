import sys
import os
import pygame
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.game import doingsomethingwithants, Turret
import numpy as np
from game.game import TURRET_STATS

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

bomb_frames1 = load_sheet("client/textures/bomb1.png")
bomb_frames2 = load_sheet("client/textures/bomb2.png")
bomb_frames3 = load_sheet("client/textures/bomb3.png")
bomb_frames4 = load_sheet("client/textures/bomb4.png")
bomb_frames5 = load_sheet("client/textures/bomb5.png")

freeze_frames1 = load_sheet("client/textures/freeze1.png")
freeze_frames2 = load_sheet("client/textures/freeze2.png")
freeze_frames3 = load_sheet("client/textures/freeze3.png")
freeze_frames4 = load_sheet("client/textures/freeze4.png")
freeze_frames5 = load_sheet("client/textures/freeze5.png")

farm_frames1 = load_sheet("client/textures/farm1.png")
farm_frames2 = load_sheet("client/textures/farm2.png")
farm_frames3 = load_sheet("client/textures/farm3.png")
farm_frames4 = load_sheet("client/textures/farm4.png")
farm_frames5 = load_sheet("client/textures/farm5.png")


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

    preview_turret = turret_frames1[0].copy()
    preview1 = original_turret_legs.copy()

    die_button_rect = pygame.Rect(0, 300, 120, 50)
    die_button = draw_pixel_text(screen, "die", (25, 25, 112))
    die_text_rect_button = die_button.get_rect(center=die_button_rect.center)

    placing = False
    turret_icon_rect = scaled_turret.get_rect(topleft=(50, 960))
    tower_rect = turret_frames1[0].get_rect()

    running = True
    while running:
        dt = clock.tick(240)/1000
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
                    placing = True

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if debug_menu and die_button_rect.collidepoint(event.pos):
                    ants.basehp = 0
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if turret_icon_rect.collidepoint(event.pos):
                        placing = True
                    elif placing:
                        for i in ants.turrets:
                            if preview_turret.get_rect(center=event.pos).colliderect(preview_turret.get_rect(center=(i.x, i.y))):
                                break
                        if scaled_map_image.get_at(preview_turret.get_rect(center=event.pos).topleft)!= (130, 88, 0):
                            if scaled_map_image.get_at(preview_turret.get_rect(center=event.pos).topright)!= (130, 88, 0):
                                if scaled_map_image.get_at(preview_turret.get_rect(center=event.pos).bottomleft)!= (130, 88, 0):
                                    if scaled_map_image.get_at(preview_turret.get_rect(center=event.pos).bottomright)!= (130, 88, 0):
                                        ants.turrets.append(Turret(*event.pos))
                                        placing = False
                if event.button == 3:     
                    placing = False
                

        screen.blit(scaled_map_image, (0, 0))
        ants.updateants(dt)

        if debug_menu == True:
            ants_left_to_spawn = draw_pixel_text(screen,str(ants.spawn_left),(255,255,255))
            debug_fps = draw_pixel_text(screen, str(int(clock.get_fps())),(255,255,255))
            debug_alive_ants = draw_pixel_text(screen, str(ants.count),(255,255,255))

            screen.blit(debug_alive_ants,(0,250))
            screen.blit(debug_fps,(0,200))
            screen.blit(ants_left_to_spawn,(0,150))

            screen.blit(die_button, die_button_rect)
            

        if ants.basehp <=0:
            death_screen()

        # utilities score moeny hp nshi
        score_text = draw_pixel_text(screen, "SCORE: ", (255, 219, 88))

        money_text = draw_pixel_text(screen, "MONEY: ", (255, 219, 88))

        health_text = draw_pixel_text(screen, "HEALTH: ", (220, 20, 60))
        health_itself_text = draw_pixel_text(screen, str(ants.basehp),(220,20,60))
        round_text = draw_pixel_text(screen, "ROUND: ", (255,255,255))
        round_itself_text = draw_pixel_text(screen, str(ants.current_round),(255,255,255))

        screen.blit(score_text, (10,20))
        screen.blit(money_text, (10, 80))
        screen.blit(health_text,(1100,20))
        screen.blit(health_itself_text,(1320,20))
        screen.blit(round_text,(1100,80))
        screen.blit(round_itself_text,(1300,80))

        #ants
        n = ants.count
        xs = ants.x[:n]
        ys = ants.y[:n]
        w, h = mask.shape
        ok = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)

        mask[:] = False
        mask[xs[ok], ys[ok]] = True
        mask[1:, :] |= mask[:-1, :]
        mask[2:, :] |= mask[:-2, :]
        mask[:, 1:] |= mask[:, :-1]
        mask[:, 2:] |= mask[:, :-2]

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

        for t in ants.turrets:
            screen.blit(original_turret_legs, original_turret_legs.get_rect(center=(t.x, t.y)))
            screen.blit(turret_frames1[0], turret_frames1[0].get_rect(center=(t.x, t.y)))

        if placing:
            mx, my = pygame.mouse.get_pos()
            preview_turret.set_alpha(150)         
            preview1.set_alpha(150) 
            screen.blit(preview_turret, preview_turret.get_rect(center=(mx, my)))
            screen.blit(preview1, preview1.get_rect(center=(mx,my)))
            pygame.draw.circle(screen, (255, 255, 255), (mx, my), 150, 1)  # range
        pygame.display.flip() 
    

    pygame.quit()
    sys.exit()

def death_screen():
    overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))
    text = draw_pixel_text(screen, "YOU DIED", (220, 20, 60))
    
    screen.blit(text, text.get_rect(center=(GAME_WIDTH / 2, GAME_HEIGHT / 2-300)))
    
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
