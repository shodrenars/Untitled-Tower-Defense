import sys
import os
import pygame
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.game import doingsomethingwithants
import numpy as np


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

ant_image = pygame.image.load("client/textures/ant.png").convert_alpha()

original_map_image = pygame.image.load("client/textures/map.png").convert_alpha()


scaled_map_image = pygame.transform.scale_by(original_map_image,10)


map_rect = scaled_map_image.get_rect()
ant_rect = ant_image.get_rect()

map_rect.topleft = (0,0)


PIXEL_FONT = pygame.font.Font("client/textures/PublicPixel.ttf", 32)

def draw_pixel_text(surface, text, color):
    text_surface = PIXEL_FONT.render(text, False, color)
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
    ants = doingsomethingwithants()
    ant_pixels = pygame.surfarray.pixels3d(ant_image)
    img_w, img_h = ant_image.get_size()
    running = True
    while running:
        dt = clock.tick(60)/1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                if event.key == pygame.K_SPACE:
                    ants.nextround()
        
        
        
                
        
        screen.blit(scaled_map_image, (0, 0))
        ants.updateants(dt)
        dzivas_skudras = ants.active
        xs = ants.x[dzivas_skudras].astype(int)
        ys = ants.y[dzivas_skudras].astype(int)
        
        valid_mask = (xs >= 0) & (xs < GAME_WIDTH - 3) & (ys >= 0) & (ys < GAME_HEIGHT - 3)
        xs = xs[valid_mask]
        ys = ys[valid_mask]
        
        screen_pixels = pygame.surfarray.pixels3d(screen)
        ant_color = (90, 35, 10) 
        
        for dx in range(4):
            for dy in range(4):
                screen_pixels[xs + dx, ys + dy, :] = ant_color
                
        del screen_pixels  
        
        pygame.display.flip()

        
        pygame.display.flip()

        
        pygame.display.flip()


       
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
  start_menu()
