# -----------------------------------------------------------------------------
# [C1] IMPORTS AND THE GAME WINDOW
# -----------------------------------------------------------------------------
# Standard Python tools, then numpy and pygame.
#   =====================================================================
#   client/main.py - THE GAME YOU SEE (window, drawing, input, server)
#   =====================================================================
#   Start it from the project folder with either of these:
#     python client/main.py
#     python -m client.main
#   The rules are in game/game.py. This file only shows the game, reads
#   the keyboard and mouse, and talks to the score server.
#
#   TABLE OF CONTENTS - search for a tag (Ctrl+F "[C7]") to jump to it
#     [C1]   Imports and the game window
#     [C2]   Colours, keys and settings
#     [C3]   Talking to the score server
#     [C4]   Loading pictures
#     [C5]   Button positions
#     [C6]   Small helpers: text, numbers, menus, cards
#     [C7]   Start menu
#     [C8]   Drawing the game: HUD, ants, explosions, toolbar
#     [C9]   F5 debug buttons
#     [C10]  Tower animation and drawing
#     [C11]  Placing preview, selected tower, totem fire
#     [C12]  run_game: the main game loop
#     [C13]  Fuse menu
#     [C14]  Card screens
#     [C15]  Pause, death and ESC screens
#     [C16]  Program start
#
#   CONTROLS (handled in [C12])
#     1 2 3 4 build  Q or right click cancel  E upgrade  Ctrl+E max
#     C sell  Shift+click or drag build and upgrade  Space next round
#     TAB cards  F fuse  P pause  ESC menu  F5 debug  F11 fullscreen

import atexit
import json
import os
import random
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from itertools import product

import numpy as np
import pygame

# Running "python client/main.py" only looks for imports inside client/,
# so add the project folder too. This line is what lets it find game/.
if not __package__:
    sys.path.append(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

# Rules and data from game/game.py, and the bad word filter.
from game.game import (
    BASIC_STATS,
    CARDS,
    EXPLOSION_TIME,
    FUSED_STATS,
    FUSION_INFO,
    FUSION_LEVEL,
    FUSION_NAMES,
    FUSION_RECIPES,
    MAX_EQUIPPED,
    PATH_XF,
    PATH_YF,
    RARITY_COLORS,
    RARITY_ORDER,
    ROCKET_GAP,
    TOWER_STATS,
    TRADE_UP_COST,
    DoingSomethingWithAnts,
)
from game.names import name_allowed

# The score server's address, and the main project folder.
API_URL = "http://127.0.0.1:8000"
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Start pygame. The clock keeps the game at 60 frames per second.
pygame.init()
clock = pygame.time.Clock()

# Everything is drawn for a 1920x1080 screen. SCALED fits it to the
# real window size, so the positions below never need to change.
GAME_WIDTH = 1920
GAME_HEIGHT = 1080
CENTER_X = GAME_WIDTH / 2
CENTER_Y = GAME_HEIGHT / 2

screen = pygame.display.set_mode(
    (GAME_WIDTH, GAME_HEIGHT), pygame.RESIZABLE | pygame.SCALED
)

# -----------------------------------------------------------------------------
# [C2] COLOURS, KEYS AND SETTINGS
# -----------------------------------------------------------------------------
# Colours used all over the game. GRASS is the map's exact grass colour,
# used to check where towers may be built.
WHITE = (255, 255, 255)
RED = (255, 0, 0)
SOFT_RED = (255, 90, 90)
GREEN = (80, 255, 80)
GOLD = (255, 219, 88)
CRIMSON = (220, 20, 60)
NAVY = (25, 25, 112)
GRAY = (200, 200, 200)
DARK = (25, 25, 25)
GRASS = (27, 132, 12)

# Each fused tower's colour.
FUSED_COLORS = {
    "railgun": (168, 64, 255),
    "silo": (255, 140, 0),
    "spire": (90, 220, 230),
}

# Tower kind to the start of its picture file name.
SPRITE_NAMES = {
    "turret": "turret",
    "farm": "farm",
    "freeze": "freeze",
    "bomb": "bomb",
    "railgun": "plasma_railgun",
    "silo": "missile_silo",
    "spire": "cryo_spire",
}

# Number keys choose a tower, Q stops placing.
BUILD_KEYS = {
    pygame.K_1: "turret",
    pygame.K_2: "farm",
    pygame.K_3: "freeze",
    pygame.K_4: "bomb",
    pygame.K_q: None,
}

# Animation speeds, shift drag spacing and the card size.
BOMB_FRAME_TIME = 0.1
FUSED_FRAME_TIME = 0.06
DRAG_STEP = 10
CARD_W, CARD_H = 320, 440

# Picture folder as a full path, so the game runs from any folder.
TEXTURES = os.path.join(PROJECT_DIR, "client", "textures")
FONT_FILE = os.path.join(TEXTURES, "PublicPixel.ttf")
PIXEL_FONT = pygame.font.Font(FONT_FILE, 32)
CARD_FONT = pygame.font.Font(FONT_FILE, 18)
SMALL_CARD_FONT = pygame.font.Font(FONT_FILE, 12)


# -----------------------------------------------------------------------------
# [C3] TALKING TO THE SCORE SERVER
# -----------------------------------------------------------------------------
# Sends one request to the server and returns (status code, data).
# If the server is offline it returns (None, None) instead of crashing.
def request(method, path, data=None, timeout=2.0):
    body = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        API_URL + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except (OSError, ValueError):
        return None, None


# Starts the score server in the background if it is not running, and
# stops it again when the game closes.
def ensure_server():
    if request("GET", "/hello", timeout=0.5)[0] == 200:
        return
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "api.main:app",
                "--port",
                "8000",
            ],
            cwd=PROJECT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return
    atexit.register(process.terminate)


# Gets the best scores, or None if the server cannot be reached.
def top_scores(limit):
    status, data = request(
        "GET", "/scores/top?limit=" + str(limit), timeout=1.0
    )
    return data if status == 200 else None


# Saves a score, then calls done(status, stats). It runs in a separate
# thread so a slow server never freezes the game.
def submit_score(name, score, round_reached, done):
    def work():
        data = {"player": name, "score": score, "round": round_reached}
        status, _ = request("POST", "/scores", data)
        path = "/players/" + urllib.parse.quote(name, safe="") + "/stats"
        stats = request("GET", path, timeout=1.0)[1] if status == 201 else None
        done(status, stats)

    threading.Thread(target=work, daemon=True).start()


# -----------------------------------------------------------------------------
# [C4] LOADING PICTURES
# -----------------------------------------------------------------------------
# Loads one picture from the textures folder.
def load_image(name):
    path = os.path.join(TEXTURES, name + ".png")
    return pygame.image.load(path).convert_alpha()


# Cuts a tall picture into square animation frames, top to bottom.
def load_sheet(name, size=40):
    sheet = load_image(name)
    return [
        sheet.subsurface((0, i * size, size, size))
        for i in range(sheet.get_height() // size)
    ]


# Fused towers are 80x80, normal towers are 40x40.
def tower_size(kind):
    return 80 if kind in FUSED_STATS else 40


# Every tower's pictures: TOWER_FRAMES[kind][level - 1][frame].
TOWER_FRAMES = {
    kind: [load_sheet(name + str(i), tower_size(kind)) for i in range(1, 6)]
    for kind, name in SPRITE_NAMES.items()
}

# Bases drawn under the towers that rotate.
LEGS = {
    "turret": load_image("turret_legs1"),
    "bomb": load_image("bomb_legs"),
}
LEGS["railgun"] = pygame.transform.scale_by(LEGS["turret"], 2)

# The explosion, and the map scaled up 10 times to fill the screen.
explosion_frames = load_sheet("explosion")
map_image = pygame.transform.scale_by(load_image("map").convert(), 10)
map_rect = map_image.get_rect()

# Ants are too many to draw one at a time. ant_mask marks every pixel
# that has ants, then they are all coloured in one go.
ant_mask = np.zeros(screen.get_size(), dtype=bool)
ANT_COLOR = screen.map_rgb((90, 35, 10))

# -----------------------------------------------------------------------------
# [C5] BUTTON POSITIONS
# -----------------------------------------------------------------------------
# The tower icons in the bottom bar.
ICON_RECTS = {
    "turret": pygame.Rect(50, 960, 80, 80),
    "farm": pygame.Rect(160, 960, 80, 80),
    "freeze": pygame.Rect(270, 960, 80, 80),
    "bomb": pygame.Rect(380, 960, 80, 80),
}

# The CARDS, FUSE and CLOSE buttons, and the F5 "funny button".
CARDS_RECT = pygame.Rect(490, 960, 190, 80)
FUSE_RECT = pygame.Rect(690, 960, 190, 80)
DIE_RECT = pygame.Rect(0, 300, 120, 50)

# F5 buttons as (rect, title, sub title, value to change, amount).
DEBUG_BUTTONS = [
    (pygame.Rect(900 + i * 200, 960, 190, 80), *button)
    for i, button in enumerate(
        (
            ("+1M", "MONEY", "money", 10**6),
            ("+1B", "MONEY", "money", 10**9),
            ("+1T", "MONEY", "money", 10**12),
            ("+100", "HEALTH", "basehp", 100),
        )
    )
]

# The F5 round box, and how many digits it accepts.
ROUND_RECT = pygame.Rect(1700, 960, 190, 80)
ROUND_DIGITS = 6
CLOSE_RECT = pygame.Rect(GAME_WIDTH - 260, 40, 200, 60)

# The orange fire stripe for the totem: strong at the front, fading out.
fire_band = pygame.Surface((200, GAME_HEIGHT), pygame.SRCALPHA)
for i in range(200):
    pygame.draw.line(
        fire_band,
        (255, 110 + i // 4, 0, int(200 * (1 - i / 200))),
        (i, 0),
        (i, GAME_HEIGHT),
    )


# -----------------------------------------------------------------------------
# [C6] SMALL HELPERS
# -----------------------------------------------------------------------------
# A tower's first picture, with its legs under it if it has any.
def base_layers(kind):
    frame = TOWER_FRAMES[kind][0][0]
    return [LEGS[kind], frame] if kind in LEGS else [frame]


# The square a tower takes up on the map if centred on pos.
def tower_box(kind, pos):
    size = tower_size(kind)
    return pygame.Rect(pos[0] - size // 2, pos[1] - size // 2, size, size)


# The square of a tower that is already placed.
def box_of(t):
    return tower_box(t.kind, (t.x, t.y))


# Draws text. anchor says where, like center=(x, y) or topleft=(x, y).
def draw_text(text, color, font=PIXEL_FONT, **anchor):
    image = font.render(text, font is PIXEL_FONT, color)
    screen.blit(image, image.get_rect(**anchor))


# Full number up to a trillion, then scientific like 5.363e+14.
def big_number(n):
    if n < 10**12:
        return str(int(n))
    return f"{float(n):.3e}"


# Short form like 500K, 50M or 12B.
def short_number(n):
    for size, suffix in (
        (10**12, "T"),
        (10**9, "B"),
        (10**6, "M"),
        (10**3, "K"),
    ):
        if n >= size:
            return f"{n / size:.1f}".rstrip("0").rstrip(".") + suffix
    return str(int(n))


# Splits text into lines that fit a given width.
def wrap_text(text, font, max_width):
    lines = []
    line = ""
    for word in text.split():
        test = word if line == "" else line + " " + word
        if font.size(test)[0] <= max_width:
            line = test
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


# A darkened copy of the screen, used as a background behind menus.
def dimmed(alpha):
    overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    background = screen.copy()
    background.blit(overlay, (0, 0))
    return background


# Opens a menu. The clock.tick afterwards stops the time spent in the
# menu from counting as game time, otherwise ants would jump forward.
def open_menu(menu, *args):
    result = menu(*args)
    clock.tick()
    return result


# Closes the game completely.
def quit_game():
    pygame.quit()
    sys.exit()


# The red CLOSE button of the card and fuse menus.
def draw_close_button():
    pygame.draw.rect(screen, DARK, CLOSE_RECT)
    pygame.draw.rect(screen, CRIMSON, CLOSE_RECT, 4)
    draw_text("CLOSE", WHITE, CARD_FONT, center=CLOSE_RECT.center)


# Draws one card, a bit bigger while the mouse is on it. Returns the
# final rectangle, so extra text can be placed on it.
def draw_card(card_id, rect, font, hover=False):
    card = CARDS[card_id]
    rarity = card["rarity"]
    secret = rarity == "secret"
    color = RARITY_COLORS[rarity]

    if hover:
        rect = rect.inflate(rect.width // 16, rect.width // 16)

    # Card body and border. Secret cards are black with a gray border.
    pygame.draw.rect(screen, (0, 0, 0) if secret else DARK, rect)
    pygame.draw.rect(
        screen,
        (110, 110, 110) if secret else color,
        rect,
        max(3, rect.width // 50),
    )
    draw_text(
        rarity.upper(),
        WHITE if secret else color,
        font,
        midtop=(rect.centerx, rect.top + rect.height * 0.07),
    )

    # The card's text, one line at a time.
    y = rect.top + rect.height * 0.27
    for line in wrap_text(card["name"], font, rect.width - rect.width // 8):
        draw_text(line, WHITE, font, midtop=(rect.centerx, y))
        y += font.get_linesize() + 6
    return rect


# -----------------------------------------------------------------------------
# [C7] START MENU
# -----------------------------------------------------------------------------
# The first screen. It runs until you quit the whole program.
def start_menu():
    ensure_server()
    high_score = "HIGH SCORE: server starting..."

    # Asks the server for the best score every 2 seconds, in the background
    # so the menu stays smooth.
    def refresh_high_score():
        nonlocal high_score
        tries = 0
        while True:
            top = top_scores(1)
            tries += 1
            if top is None:
                state = "starting..." if tries < 5 else "offline"
                high_score = "HIGH SCORE: server " + state
            elif not top:
                high_score = "HIGH SCORE: none yet"
            else:
                score = big_number(top[0]["score"])
                high_score = f"HIGH SCORE: {top[0]['player']} {score}"
            time.sleep(2)

    threading.Thread(target=refresh_high_score, daemon=True).start()

    # Starts a game with the typed name. Keeps restarting while you press R
    # on the death screen. A blocked name does nothing.
    def play():
        name = player_name.strip() or "Player"
        if not name_allowed(name):
            return None
        result = run_game(name)
        while result == "restart":
            result = run_game(name)
        pygame.key.set_repeat(400, 50)
        return result

    # Buttons, and text input for the name box.
    start_rect = pygame.Rect(CENTER_X - 90, CENTER_Y + 50, 200, 50)
    quit_rect = pygame.Rect(CENTER_X - 90, CENTER_Y + 150, 200, 50)
    player_name = ""
    pygame.key.set_repeat(400, 50)
    pygame.key.start_text_input()
    running = True
    while running:
        # Read keyboard and mouse. play() only returns "quit" for a full exit.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    running = play() != "quit"
                elif event.key == pygame.K_BACKSPACE:
                    player_name = player_name[:-1]

            elif event.type == pygame.TEXTINPUT:
                for ch in event.text:
                    if len(player_name) < 20 and ch.isprintable():
                        player_name += ch

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if start_rect.collidepoint(event.pos):
                    running = play() != "quit"
                elif quit_rect.collidepoint(event.pos):
                    running = False

        # Draw the menu.
        screen.fill((70, 130, 180))
        draw_text("Untitled Tower Defense", NAVY, topleft=(610, 290))
        draw_text("Username:", NAVY, topleft=(835, 440))
        draw_text("Start Game", NAVY, center=start_rect.center)
        draw_text("Quit Game", NAVY, center=quit_rect.center)
        draw_text(
            "Press ENTER to start",
            (250, 250, 250),
            CARD_FONT,
            center=(CENTER_X, CENTER_Y + 250),
        )
        draw_text(
            high_score, GOLD, CARD_FONT, center=(CENTER_X, CENTER_Y + 300)
        )

        # The name box grows with the name. A warning shows for blocked names.
        width = max(200, PIXEL_FONT.size(player_name)[0] + 10)
        input_rect = pygame.Rect(
            CENTER_X - width / 2, CENTER_Y - 60, width, 50
        )
        pygame.draw.rect(screen, (4, 2, 115), input_rect)
        draw_text(
            player_name,
            (250, 250, 250),
            topleft=(input_rect.x + 5, input_rect.y + 5),
        )
        if not name_allowed(player_name):
            draw_text(
                "that name is not allowed",
                (120, 0, 0),
                CARD_FONT,
                center=(CENTER_X, CENTER_Y + 25),
            )

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


# -----------------------------------------------------------------------------
# [C8] DRAWING THE GAME
# -----------------------------------------------------------------------------
# The F5 info text down the left side.
def draw_debug(ants):
    for y, text in (
        (150, "ants to spawn " + str(ants.spawn_left)),
        (200, "fps " + str(int(clock.get_fps()))),
        (250, "alive ants " + str(ants.count)),
        (350, "ant hp " + big_number(ants.starting_hp)),
        (400, "ant shield " + big_number(ants.starting_shield)),
        (450, "money multi " + str(ants.money_multi_per_damage)),
        (500, "money per round " + str(ants.money_per_round)),
    ):
        draw_text(text, WHITE, topleft=(0, y))
    draw_text("funny button :}", NAVY, topleft=DIE_RECT.topleft)


# Score, money, health and round at the top.
def draw_hud(ants):
    for text, color, pos in (
        ("SCORE: ", GOLD, (10, 20)),
        (big_number(ants.score), GOLD, (200, 20)),
        ("MONEY: ", GOLD, (10, 80)),
        (big_number(ants.money), GOLD, (200, 80)),
        ("HEALTH: ", CRIMSON, (1000, 20)),
        (str(int(ants.basehp)), CRIMSON, (1220, 20)),
        ("ROUND: ", WHITE, (1000, 80)),
        (str(ants.current_round), WHITE, (1200, 80)),
    ):
        draw_text(text, color, topleft=pos)


# Draws every ant at once. Marks the pixels of occupied cells, widens
# each mark to 4x4 so ants are visible, then colours all marked pixels.
def draw_ants(ants):
    occupied = ants.occ > 0
    ant_mask[:] = False
    ant_mask[PATH_XF[occupied], PATH_YF[occupied]] = True
    ant_mask[1:, :] |= ant_mask[:-1, :]
    ant_mask[2:, :] |= ant_mask[:-2, :]
    ant_mask[:, 1:] |= ant_mask[:, :-1]
    ant_mask[:, 2:] |= ant_mask[:, :-2]

    screen_pixels = pygame.surfarray.pixels2d(screen)
    screen_pixels[ant_mask] = ANT_COLOR
    del screen_pixels


# Draws explosions. The first two frames are fixed, then a random
# ending is picked once and kept for that explosion.
def draw_explosions(ants):
    for e in ants.explosions:
        t = e["age"] / EXPLOSION_TIME
        if t < 1 / 3:
            frame = 0
        elif t < 2 / 3:
            frame = 1
        else:
            frame = e.setdefault(
                "pick", random.randint(2, len(explosion_frames) - 1)
            )
        size = e["r"] * 2
        img = pygame.transform.scale(explosion_frames[frame], (size, size))
        screen.blit(img, img.get_rect(center=(e["x"], e["y"])))


# A dark bottom bar button with a title and small text.
def draw_menu_button(rect, border, title, sub, sub_color):
    pygame.draw.rect(screen, DARK, rect)
    pygame.draw.rect(screen, border, rect, 4)
    draw_text(
        title, WHITE, CARD_FONT, center=(rect.centerx, rect.centery - 14)
    )
    draw_text(
        sub,
        sub_color,
        SMALL_CARD_FONT,
        center=(rect.centerx, rect.centery + 18),
    )


# The bottom bar: tower icons, prices, and the CARDS and FUSE buttons.
def draw_toolbar(ants):
    for kind, rect in ICON_RECTS.items():
        for layer in base_layers(kind):
            screen.blit(pygame.transform.scale_by(layer, 2), rect)
        cost = short_number(TOWER_STATS[kind][1]["cost"]).lower()
        draw_text(cost, WHITE, topleft=(rect.x - 10, 910))
    draw_menu_button(
        CARDS_RECT,
        RARITY_COLORS["legendary"],
        "CARDS",
        f"{len(ants.equipped)}/{MAX_EQUIPPED}  [TAB]",
        GRAY,
    )
    ready = sum(ants.can_fuse(kind) for kind in FUSION_RECIPES)
    draw_menu_button(
        FUSE_RECT,
        FUSED_COLORS["railgun"],
        "FUSE",
        f"{ready} READY  [F]",
        GREEN if ready else GRAY,
    )


# -----------------------------------------------------------------------------
# [C9] F5 DEBUG BUTTONS
# -----------------------------------------------------------------------------
# Draws the F5 buttons. The round box turns green while you type.
def draw_debug_buttons(round_text):
    for rect, title, sub, _, _ in DEBUG_BUTTONS:
        draw_menu_button(rect, GOLD, title, sub, GRAY)
    typing = round_text is not None
    draw_menu_button(
        ROUND_RECT,
        GREEN if typing else GOLD,
        round_text + "_" if typing else "ROUND",
        "ENTER = GO" if typing else "CLICK TO SET",
        GRAY,
    )


# Handles a click on a money or health button. Returns True if one was
# hit, so the click does not also place a tower.
def press_debug_button(ants, pos):
    for rect, _, _, stat, amount in DEBUG_BUTTONS:
        if rect.collidepoint(pos):
            setattr(ants, stat, getattr(ants, stat) + amount)
            return True
    return False


# Handles keys while typing a round. Enter jumps to it, ESC cancels,
# Backspace deletes. Returns the new text, or None when finished.
def edit_round(ants, text, key):
    if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        if text:
            ants.set_round(int(text))
        return None
    if key == pygame.K_ESCAPE:
        return None
    return text[:-1] if key == pygame.K_BACKSPACE else text


# -----------------------------------------------------------------------------
# [C10] TOWER ANIMATION AND DRAWING
# -----------------------------------------------------------------------------
# Loops through frames for a while after a shot, then back to frame 0.
def animate(t, dt, duration, frame_time, first, count):
    if t.since_shot >= duration:
        t.anim = 0.0
        return 0
    t.anim += dt
    return first + int(t.anim / frame_time) % count


# Chooses which picture of a tower to show right now. last is the
# number of the final frame.
def tower_frame(t, dt, last):
    if t.kind == "railgun":
        return animate(t, dt, 0.3, FUSED_FRAME_TIME, 1, last)
    if t.kind == "spire":
        return animate(t, dt, t.cooldown + 0.2, 0.12, 0, last + 1)

    # Silo: firing frames during a volley, then a short reload frame.
    if t.kind == "silo":
        if t.since_shot < ROCKET_GAP:
            return min(t.shot_frame, last - 1)
        waiting = t.since_shot < ROCKET_GAP + 0.3
        return last if waiting and not t.rocket_queue else 0

    # High level single rocket bombs loop while reloading.
    if t.kind == "bomb" and t.rockets == 1 and t.level >= 3:
        duration = t.cooldown + BOMB_FRAME_TIME
        return animate(t, dt, duration, BOMB_FRAME_TIME, 1, last)

    # Everything else flashes one shot frame. Farms and freezers never
    # fire, so they always show frame 0.
    return min(t.shot_frame, last) if t.since_shot < 0.1 else 0


# Draws legs first, then the rotated tower on top.
def draw_tower(t, dt):
    center = (t.x, t.y)
    if t.kind in LEGS:
        screen.blit(LEGS[t.kind], LEGS[t.kind].get_rect(center=center))
    frames = TOWER_FRAMES[t.kind][t.level - 1]
    frame = frames[tower_frame(t, dt, len(frames) - 1)]
    img = pygame.transform.rotate(frame, 180 - t.angle)
    screen.blit(img, img.get_rect(center=center))


# -----------------------------------------------------------------------------
# [C11] PLACING PREVIEW, SELECTED TOWER, TOTEM FIRE
# -----------------------------------------------------------------------------
# Preview under the mouse while choosing where to build. Red boxes show
# what is already placed, and the circle shows the range.
def draw_placing(ants, kind, pos, can_place):
    for t in ants.towers:
        pygame.draw.rect(screen, RED, box_of(t), 2)
    rect = tower_box(kind, pos)
    for layer in base_layers(kind):
        ghost = layer.copy()
        ghost.set_alpha(150)
        screen.blit(ghost, rect)
    fused = kind in FUSED_STATS
    pygame.draw.rect(screen, GREEN if fused and can_place else RED, rect, 2)
    if kind != "farm":
        pygame.draw.circle(
            screen, WHITE, pos, TOWER_STATS[kind][1]["range"], 1
        )
    if fused:
        draw_text(
            f"PLACE {FUSION_NAMES[kind].upper()}   RIGHT CLICK = CANCEL",
            FUSED_COLORS[kind],
            CARD_FONT,
            midtop=(CENTER_X, 140),
        )


# Red box, range circle and upgrade price of the clicked tower.
def draw_selected(t):
    fused = t.kind in FUSED_STATS
    pygame.draw.rect(screen, RED, box_of(t), 2)
    if t.kind != "farm":
        pygame.draw.circle(screen, WHITE, (t.x, t.y), t.range, 1)
    if fused:
        draw_text(
            FUSION_NAMES[t.kind].upper(),
            FUSED_COLORS[t.kind],
            CARD_FONT,
            topleft=(1400, 120),
        )
    cost = t.next_cost()
    if cost is not None:
        text = short_number(cost) if fused else str(cost)
        draw_text("cost: " + text, WHITE, topleft=(1400, 70))
    draw_text(f"level: {t.level}/5", WHITE, topleft=(1400, 20))


# The fire stripe crossing the screen right to left each second.
def draw_fire(ants):
    wave_x = GAME_WIDTH - ants.fire_acc * (GAME_WIDTH + fire_band.get_width())
    screen.blit(fire_band, (wave_x, 0))
    draw_text(
        f"TOTEM FIRE {int(ants.fire_left) + 1}",
        (255, 140, 0),
        CARD_FONT,
        midtop=(CENTER_X, 140),
    )


# -----------------------------------------------------------------------------
# [C12] RUN_GAME: THE MAIN GAME LOOP
# -----------------------------------------------------------------------------
# Plays one whole game. Each loop: read input, update the rules, draw.
# Returns "quit", "restart" or "menu" for start_menu to act on.
def run_game(player_name):
    pygame.key.set_repeat()
    ants = DoingSomethingWithAnts()

    # What the player is doing right now.
    #   debug_menu  is the F5 menu open
    #   round_text  digits typed in the round box, None when not typing
    #   placing     tower kind being placed, None when not placing
    #   selected    the clicked tower
    #   drag_pos    last mouse position, for shift dragging
    debug_menu = False
    round_text = None
    placing = None
    selected = None
    drag_pos = pygame.mouse.get_pos()

    # True if a tower fits here: inside the map, not touching another
    # tower, and on grass.
    def can_place(kind, pos):
        rect = tower_box(kind, pos)
        if not map_rect.contains(rect) or any(
            rect.colliderect(box_of(t)) for t in ants.towers
        ):
            return False

        # Check grass colour. Normal towers test only their corners, fused
        # towers test a grid of points all over.
        step = 4 if kind in FUSED_STATS else rect.w - 1
        spots = product(
            range(rect.left, rect.right, step),
            range(rect.top, rect.bottom, step),
        )
        return all(
            map_image.get_at(spot) == GRASS
            for spot in (*spots, (rect.right - 1, rect.bottom - 1))
        )

    # Buys the tower being placed, if this spot is allowed.
    def place_tower(pos):
        if placing in BASIC_STATS and can_place(placing, pos):
            return ants.buy(placing, *pos)
        return None

    # Finds the tower under the mouse.
    def tower_at(pos, kinds=TOWER_STATS):
        for t in ants.towers:
            if t.kind in kinds and box_of(t).collidepoint(pos):
                return t
        return None

    # Shift click: builds here, or uses the tower already here, then buys
    # as many upgrades as you can afford. Fused towers are skipped.
    def shift_build(pos):
        kinds = (placing,) if placing in BASIC_STATS else BASIC_STATS
        tower = place_tower(pos) or tower_at(pos, kinds)
        if tower:
            ants.upgrade(tower, to_max=True)

    # Shift drag: fast mouse moves skip pixels, so this fills in the points
    # along the way, one every DRAG_STEP pixels.
    def drag_towers(start, end):
        x_move = end[0] - start[0]
        y_move = end[1] - start[1]
        steps = max(abs(x_move), abs(y_move)) // DRAG_STEP + 1
        for step in range(1, steps + 1):
            shift_build(
                (
                    start[0] + x_move * step // steps,
                    start[1] + y_move * step // steps,
                )
            )

    # True while Shift is held.
    def shift_held():
        return pygame.key.get_mods() & pygame.KMOD_SHIFT

    # Opens the fuse menu. Choosing a tower starts placing it.
    def choose_fusion():
        nonlocal placing, selected
        kind = open_menu(fuse_menu, ants)
        if kind:
            placing = kind
            selected = None

    # The game loop, about 60 times per second. dt = seconds since last frame.
    while True:
        dt = clock.tick(60) / 1000

        # INPUT: go through every key press and mouse action.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"

            # While typing a round number, take all keys so that typing 1 does
            # not
            # also choose a tower.
            if round_text is not None:
                if event.type == pygame.TEXTINPUT:
                    # Only digits are accepted, up to the limit.
                    digits = [ch for ch in event.text if ch.isdecimal()]
                    round_text += "".join(digits)
                    round_text = round_text[:ROUND_DIGITS]
                if event.type == pygame.KEYDOWN:
                    round_text = edit_round(ants, round_text, event.key)
                    continue

            # Keyboard controls.
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if open_menu(esc_menu) == "quit":
                        return "quit"
                elif event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                elif event.key == pygame.K_SPACE:
                    ants.nextround()
                elif event.key == pygame.K_F5:
                    debug_menu = not debug_menu
                elif event.key == pygame.K_p:
                    open_menu(pause_screen)
                elif event.key == pygame.K_TAB:
                    open_menu(card_menu, ants)
                elif event.key == pygame.K_f:
                    choose_fusion()
                elif event.key in BUILD_KEYS:
                    placing = BUILD_KEYS[event.key]
                    selected = None
                elif selected and event.key == pygame.K_c:
                    ants.sell(selected)
                    selected = None
                elif selected and event.key == pygame.K_e:
                    to_max = pygame.key.get_mods() & pygame.KMOD_CTRL
                    ants.upgrade(selected, to_max)

            # Dragging with Shift held builds towers along the mouse's path.
            if event.type == pygame.MOUSEMOTION:
                if event.buttons[0] and shift_held():
                    drag_towers(drag_pos, event.pos)
                drag_pos = event.pos

            # Right click cancels placing and selection.
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                placing = None
                selected = None

            # Left click. It can mean many things, checked in order.
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                drag_pos = pos
                round_text = None

                # F5 buttons come first. They skip the rest, so using one does
                # not
                # cancel what you are placing or deselect your tower.
                if debug_menu and ROUND_RECT.collidepoint(pos):
                    round_text = ""
                    continue
                if debug_menu and press_debug_button(ants, pos):
                    continue
                if debug_menu and DIE_RECT.collidepoint(pos):
                    ants.basehp = 0

                # The CARDS and FUSE buttons, or dropping a fused tower.
                if CARDS_RECT.collidepoint(pos):
                    open_menu(card_menu, ants)
                elif FUSE_RECT.collidepoint(pos):
                    choose_fusion()
                elif (
                    placing in FUSED_STATS
                    and can_place(placing, pos)
                    and ants.fuse(placing, *pos)
                ):
                    placing = None

                # Select the tower here, unless busy placing.
                selected = None if placing else tower_at(pos)
                icon = [
                    k for k, r in ICON_RECTS.items() if r.collidepoint(pos)
                ]

                # Tower icon, Shift build, or a normal build.
                if icon:
                    placing = icon[0]
                elif shift_held():
                    shift_build(pos)
                elif place_tower(pos):
                    placing = None

        # RULES: move the game forward one frame. This also clears the screen.
        screen.blit(map_image, (0, 0))
        ants.updateants(dt)

        # Debug text goes under everything else.
        if debug_menu:
            draw_debug(ants)

        # Game over if hp ran out and no totem saved you.
        if ants.basehp <= 0:
            return death_screen(ants, player_name)

        # DRAW: everything else, back to front.
        draw_hud(ants)
        draw_ants(ants)
        draw_explosions(ants)
        draw_toolbar(ants)
        if debug_menu:
            draw_debug_buttons(round_text)
        for t in ants.towers:
            draw_tower(t, dt)
        if placing:
            pos = pygame.mouse.get_pos()
            draw_placing(ants, placing, pos, can_place(placing, pos))
        if selected:
            draw_selected(selected)
        if ants.fire_left > 0:
            draw_fire(ants)

        # The card offer pauses the game until you pick one.
        if ants.card_choices:
            open_menu(card_pick_screen, ants)

        pygame.display.flip()


# -----------------------------------------------------------------------------
# [C13] FUSE MENU
# -----------------------------------------------------------------------------
# Draws one fused tower's panel: picture, recipe, stats and button.
def draw_fuse_panel(ants, kind, panel, button, mouse):
    color = FUSED_COLORS[kind]
    ready = ants.can_fuse(kind)
    box = panel.inflate(12, 12) if panel.collidepoint(mouse) else panel
    pygame.draw.rect(screen, DARK, box)
    pygame.draw.rect(screen, color, box, 6)
    draw_text(
        FUSION_NAMES[kind].upper(),
        color,
        CARD_FONT,
        midtop=(panel.centerx, panel.top + 24),
    )

    # The tower's picture at double size.
    art = pygame.Surface((80, 80), pygame.SRCALPHA)
    for layer in base_layers(kind):
        art.blit(layer, (0, 0))
    art = pygame.transform.scale_by(art, 2)
    screen.blit(art, art.get_rect(midtop=(panel.centerx, panel.top + 64)))

    # Recipe list: green once you have enough, red if not.
    x = panel.left + 40
    y = panel.top + 250
    draw_text(
        f"RECIPE (ALL LEVEL {FUSION_LEVEL})",
        GRAY,
        SMALL_CARD_FONT,
        topleft=(x, y),
    )
    y += 30
    for part, (have, need) in ants.fusion_parts(kind).items():
        draw_text(
            f"{need}x {part.upper()}   {min(have, need)}/{need}",
            GREEN if have >= need else SOFT_RED,
            CARD_FONT,
            topleft=(x, y),
        )
        y += 34

    # The price, green if you can pay it.
    cost = ants.fuse_cost(kind)
    draw_text(
        "COST   " + short_number(cost),
        GREEN if ants.money >= cost else SOFT_RED,
        CARD_FONT,
        topleft=(x, y),
    )
    y += 50

    # What the tower does.
    draw_text("POWERS", GRAY, SMALL_CARD_FONT, topleft=(x, y))
    y += 28
    for info in FUSION_INFO[kind]:
        for line in wrap_text(info, SMALL_CARD_FONT, panel.w - 80):
            draw_text(line, WHITE, SMALL_CARD_FONT, topleft=(x, y))
            y += 22
        y += 6

    # Level 1 numbers.
    stats = FUSED_STATS[kind][1]
    draw_text(
        f"LV1  DMG {big_number(stats['damage'])}  "
        f"EVERY {stats['cooldown']}s  RANGE {stats['range']}",
        color,
        SMALL_CARD_FONT,
        topleft=(x, y),
    )
    draw_text(
        f"SLOWS ANTS TO {int(stats['slow'] * 100)}% SPEED",
        color,
        SMALL_CARD_FONT,
        topleft=(x, y + 24),
    )

    # The FUSE button, or the reason you cannot press it yet.
    hover = ready and button.collidepoint(mouse)
    pygame.draw.rect(screen, color if ready else (70, 70, 70), button)
    pygame.draw.rect(screen, WHITE if hover else (0, 0, 0), button, 4)
    if ready:
        label = "FUSE"
    elif ants.has_fusion_parts(kind):
        label = "NEED MORE MONEY"
    else:
        label = "NEED MORE TOWERS"
    draw_text(
        label,
        (0, 0, 0) if ready else (170, 170, 170),
        CARD_FONT,
        center=button.center,
    )


# The message shown after clicking FUSE when you are not ready.
def fuse_message(ants, kind):
    if ants.has_fusion_parts(kind):
        need = f"need {short_number(ants.fuse_cost(kind))} money"
    else:
        need = f"not enough level {FUSION_LEVEL} towers"
    return f"{need} for {FUSION_NAMES[kind]}"


# The fuse screen. Returns the chosen kind, or None if closed. Nothing
# is paid here, that happens when the tower is placed.
def fuse_menu(ants):
    background = dimmed(200)
    kinds = list(FUSION_RECIPES)

    # Three panels side by side, centred, each with a button.
    w, h, gap = 540, 720, 40
    left = CENTER_X - (len(kinds) * w + (len(kinds) - 1) * gap) / 2
    panels = [
        pygame.Rect(left + i * (w + gap), 170, w, h) for i in range(len(kinds))
    ]
    buttons = [
        pygame.Rect(p.x + 40, p.bottom - 90, p.w - 80, 60) for p in panels
    ]
    message = ""

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE,
                pygame.K_f,
            ):
                return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if CLOSE_RECT.collidepoint(event.pos):
                    return None
                for kind, b in zip(kinds, buttons):
                    if b.collidepoint(event.pos):
                        if ants.can_fuse(kind):
                            return kind
                        message = fuse_message(ants, kind)

        mouse = pygame.mouse.get_pos()
        screen.blit(background, (0, 0))
        draw_text("FUSE TOWERS", WHITE, midtop=(CENTER_X, 50))
        draw_text(
            f"all towers in a recipe must be level {FUSION_LEVEL}"
            " - towers and money are used when you place the fused tower",
            GRAY,
            SMALL_CARD_FONT,
            midtop=(CENTER_X, 110),
        )
        for kind, panel, button in zip(kinds, panels, buttons):
            draw_fuse_panel(ants, kind, panel, button, mouse)
        draw_text(message, (255, 220, 120), CARD_FONT, midtop=(CENTER_X, 910))
        draw_text(
            "F / ESC: close", GRAY, SMALL_CARD_FONT, midtop=(CENTER_X, 960)
        )
        draw_close_button()

        pygame.display.flip()
        clock.tick(60)


# -----------------------------------------------------------------------------
# [C14] CARD SCREENS
# -----------------------------------------------------------------------------
# The "pick 1 of 3" screen. It stays until you click a card.
def card_pick_screen(ants):
    background = dimmed(180)
    gap = 80
    left = CENTER_X - (3 * CARD_W + 2 * gap) / 2
    rects = [
        pygame.Rect(
            left + i * (CARD_W + gap), CENTER_Y - CARD_H / 2, CARD_W, CARD_H
        )
        for i in range(3)
    ]

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, r in enumerate(rects):
                    if r.collidepoint(event.pos):
                        ants.pick_card(i)
                        return

        mouse = pygame.mouse.get_pos()
        screen.blit(background, (0, 0))
        draw_text(
            "PICK A CARD",
            WHITE,
            center=(CENTER_X, CENTER_Y - CARD_H / 2 - 80),
        )
        for card_id, r in zip(ants.card_choices, rects):
            draw_card(card_id, r, CARD_FONT, r.collidepoint(mouse))
        pygame.display.flip()
        clock.tick(60)


# Does a trade up and returns the message to show.
def trade_message(ants, card_id):
    rarity = CARDS[card_id]["rarity"]
    new_card = ants.trade_up(card_id)
    if new_card:
        card = CARDS[new_card]
        return f"traded up into {card['name']} ({card['rarity']})"
    if rarity == "secret":
        return "secret cards can't be traded up"
    return f"need {TRADE_UP_COST[rarity]} {rarity} cards to trade up"


# One card in the grid: its amount, and TRADE UP if you have enough.
def draw_inventory_card(ants, card_id, rect, mouse):
    drawn = draw_card(card_id, rect, SMALL_CARD_FONT, rect.collidepoint(mouse))
    draw_text(
        "x" + str(ants.inventory.count(card_id)),
        WHITE,
        SMALL_CARD_FONT,
        bottomleft=(drawn.left + 10, drawn.bottom - 10),
    )
    rarity = CARDS[card_id]["rarity"]
    same = sum(1 for c in ants.inventory if CARDS[c]["rarity"] == rarity)
    if same >= TRADE_UP_COST.get(rarity, same + 1):
        draw_text(
            "TRADE UP",
            GREEN,
            SMALL_CARD_FONT,
            midbottom=(drawn.centerx, drawn.bottom - 30),
        )


# The TAB screen: equipped cards on top, your cards below.
def card_menu(ants):
    background = dimmed(200)
    gap = 20
    w, h = 150, 170
    cols = 9
    rows_visible = 3
    equip_left = CENTER_X - (MAX_EQUIPPED * w + (MAX_EQUIPPED - 1) * gap) / 2
    equip_rects = [
        pygame.Rect(equip_left + i * (w + gap), 110, w, h)
        for i in range(MAX_EQUIPPED)
    ]
    grid_left = CENTER_X - (cols * w + (cols - 1) * gap) / 2
    scroll = 0
    message = ""

    while True:
        # Your cards with duplicates grouped, worst rarity first.
        groups = sorted(
            set(ants.inventory),
            key=lambda c: (RARITY_ORDER.index(CARDS[c]["rarity"]), c),
        )

        # Keep scroll in range, and work out where visible cards go.
        total_rows = (len(groups) + cols - 1) // cols
        scroll = max(0, min(scroll, total_rows - rows_visible))
        inv_rects = []
        for k, card_id in enumerate(groups):
            row = k // cols - scroll
            if 0 <= row < rows_visible:
                x = grid_left + k % cols * (w + gap)
                rect = pygame.Rect(x, 390 + row * (h + gap), w, h)
                inv_rects.append((card_id, rect))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE,
                pygame.K_TAB,
            ):
                return

            # Mouse wheel scrolls.
            if event.type == pygame.MOUSEWHEEL:
                scroll -= event.y
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if CLOSE_RECT.collidepoint(event.pos):
                    return

                # Clicking an equipped card takes it off.
                for i, r in enumerate(equip_rects):
                    if r.collidepoint(event.pos) and i < len(ants.equipped):
                        card_id = ants.equipped[i]
                        ants.unequip(card_id)
                        message = "unequipped " + CARDS[card_id]["name"]
                for card_id, r in inv_rects:
                    if r.collidepoint(event.pos):
                        message = (
                            "equipped " + CARDS[card_id]["name"]
                            if ants.equip(card_id)
                            else f"all {MAX_EQUIPPED} slots are full"
                        )

            # Right click trades up.
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                for card_id, r in inv_rects:
                    if r.collidepoint(event.pos):
                        message = trade_message(ants, card_id)

        mouse = pygame.mouse.get_pos()
        screen.blit(background, (0, 0))
        draw_text(
            f"EQUIPPED {len(ants.equipped)}/{MAX_EQUIPPED}",
            WHITE,
            midtop=(CENTER_X, 50),
        )
        for i, r in enumerate(equip_rects):
            if i < len(ants.equipped):
                draw_card(
                    ants.equipped[i],
                    r,
                    SMALL_CARD_FONT,
                    r.collidepoint(mouse),
                )
            else:
                pygame.draw.rect(screen, (80, 80, 80), r, 3)

        draw_text("YOUR CARDS", WHITE, midtop=(CENTER_X, 330))
        if not groups:
            draw_text(
                "no cards yet, you get one every 5 rounds",
                (160, 160, 160),
                CARD_FONT,
                midtop=(CENTER_X, 480),
            )
        for card_id, r in inv_rects:
            draw_inventory_card(ants, card_id, r, mouse)

        if total_rows > rows_visible:
            draw_text(
                f"scroll for more  {scroll + 1}/"
                f"{total_rows - rows_visible + 1}",
                (160, 160, 160),
                SMALL_CARD_FONT,
                midtop=(CENTER_X, 1020),
            )
        draw_text(
            "LEFT CLICK: equip / unequip    RIGHT CLICK: trade up    "
            "TAB / ESC: close",
            GRAY,
            SMALL_CARD_FONT,
            midtop=(CENTER_X, 300),
        )
        draw_text(message, (255, 220, 120), CARD_FONT, midtop=(CENTER_X, 975))
        draw_close_button()

        pygame.display.flip()
        clock.tick(60)


# -----------------------------------------------------------------------------
# [C15] PAUSE, DEATH AND ESC SCREENS
# -----------------------------------------------------------------------------
# The P pause screen. It draws once, then waits for P.
def pause_screen():
    screen.blit(dimmed(140), (0, 0))
    draw_text("PAUSED", WHITE, center=(CENTER_X, CENTER_Y - 40))
    draw_text(
        "press P to continue",
        (220, 220, 220),
        CARD_FONT,
        center=(CENTER_X, CENTER_Y + 20),
    )
    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                return
        clock.tick(30)


# The game over screen. Saves the score and shows the result as soon as
# the server answers. Returns "restart", "menu" or "quit".
def death_screen(ants, player_name):
    background = dimmed(160)
    status = "SAVING SCORE..."
    best = None

    # Runs when the server answers.
    def saved(code, stats):
        nonlocal status, best
        if code == 201:
            status = "SCORE SAVED TO THE LEADERBOARD"
            best = stats
        elif code is None:
            status = "SERVER OFFLINE - SCORE NOT SAVED"
        else:
            status = f"SCORE NOT SAVED ({code})"

    submit_score(player_name, ants.score, ants.current_round, saved)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return "restart"
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                    return "menu"

        screen.blit(background, (0, 0))
        draw_text("YOU DIED", CRIMSON, center=(CENTER_X, CENTER_Y - 300))
        draw_text("SCORE", GOLD, center=(CENTER_X, CENTER_Y - 200))
        draw_text(
            big_number(ants.score), GOLD, center=(CENTER_X, CENTER_Y - 130)
        )
        draw_text(
            f"ROUND {ants.current_round}   PLAYER {player_name}",
            WHITE,
            CARD_FONT,
            center=(CENTER_X, CENTER_Y - 60),
        )
        draw_text(status, GOLD, CARD_FONT, center=(CENTER_X, CENTER_Y + 20))
        if best:
            draw_text(
                f"YOUR BEST {big_number(best['best_score'])}"
                f"   GAMES PLAYED {best['games']}",
                WHITE,
                CARD_FONT,
                center=(CENTER_X, CENTER_Y + 70),
            )
        draw_text(
            "R - play again      ESC - menu",
            (220, 220, 220),
            CARD_FONT,
            center=(CENTER_X, CENTER_Y + 160),
        )
        pygame.display.flip()
        clock.tick(30)


# The ESC menu. It draws once, then waits. Returns "continue" or "quit".
def esc_menu():
    continue_rect = pygame.Rect(CENTER_X - 90, CENTER_Y + 50, 200, 50)
    quit_rect = pygame.Rect(CENTER_X - 90, CENTER_Y - 50, 200, 50)
    screen.blit(dimmed(160), (0, 0))
    draw_text("continue", (0, 144, 160), center=continue_rect.center)
    draw_text("quit", CRIMSON, center=quit_rect.center)
    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "continue"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if continue_rect.collidepoint(event.pos):
                    return "continue"
                if quit_rect.collidepoint(event.pos):
                    return "quit"
        clock.tick(30)


# -----------------------------------------------------------------------------
# [C16] PROGRAM START
# -----------------------------------------------------------------------------
# Runs the game when this file is started.
if __name__ == "__main__":
    start_menu()
