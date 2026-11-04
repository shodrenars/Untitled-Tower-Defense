# -----------------------------------------------------------------------------
# [A1] IMPORTS AND SETUP
# -----------------------------------------------------------------------------
# Python tools, FastAPI, our database file and the game's data.
#   =====================================================================
#   api/main.py - THE SCORE SERVER (all the web addresses)
#   =====================================================================
#   Start it with: uvicorn api.main:app --reload
#   The game also starts it by itself. Try every address at /docs.
#   The game and the website only touch the database through here.
#
#   TABLE OF CONTENTS - search for a tag (Ctrl+F "[A3]") to jump to it
#     [A1]   Imports and setup
#     [A2]   Checking incoming data
#     [A3]   Admin password check
#     [A4]   Scores: hello, save, delete, rename, top list
#     [A5]   Player stats and game info
#     [A6]   Website pages

import os
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from api import db
from game.game import (
    BASIC_STATS,
    CARD_EVERY_ROUNDS,
    CARDS,
    FUSED_STATS,
    FUSION_INFO,
    FUSION_LEVEL,
    FUSION_NAMES,
    FUSION_RECIPES,
    MAX_EQUIPPED,
    RARITY_COLORS,
    RARITY_ORDER,
    RARITY_WEIGHTS,
    TRADE_UP_COST,
)
from game.names import name_allowed

# Folder paths and the biggest score the database can hold.
API_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_SCORE = 2**63 - 1

# The private password file. It is in .gitignore so it stays on this PC.
ADMIN_FILE = os.path.join(os.path.dirname(API_DIR), "admin_password.txt")

# Create the server. CORS lets pages opened by double click reach it.
app = FastAPI(title="Untitled Tower Defense API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Make sure the scores table exists.
db.init()


# -----------------------------------------------------------------------------
# [A2] CHECKING INCOMING DATA
# -----------------------------------------------------------------------------
# A player name: spaces trimmed, 1 to 20 characters, no bad words.
# FastAPI answers 422 by itself when this check fails.
class NameIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    player: str = Field(min_length=1, max_length=20)

    @field_validator("player")
    @classmethod
    def check_name(cls, value):
        if not name_allowed(value):
            raise ValueError("Šāds vārds nav atļauts")
        return value


# A score to save: a valid name plus score and round.
class ScoreIn(NameIn):
    score: int = Field(ge=0, le=MAX_SCORE)
    round: int = Field(default=0, ge=0, le=1_000_000_000)


# -----------------------------------------------------------------------------
# [A3] ADMIN PASSWORD CHECK
# -----------------------------------------------------------------------------
# Reads the password from the private file every time, so changing it
# needs no restart. Empty means there is no password set.
def admin_password():
    try:
        with open(ADMIN_FILE, encoding="utf-8") as file:
            return file.read().strip()
    except OSError:
        return ""


# Stops the request with 401 unless the password is right. A missing or
# empty file blocks everyone. compare_digest stops timing guesses.
def require_admin(x_admin_password: str = Header(default="")):
    password = admin_password()
    if not password or not secrets.compare_digest(
        x_admin_password.encode(), password.encode()
    ):
        raise HTTPException(status_code=401, detail="Nepareiza parole")


# Add this to an address to make it need the password.
admin_only = [Depends(require_admin)]


# -----------------------------------------------------------------------------
# [A4] SCORES
# -----------------------------------------------------------------------------
# Checks that the server is running. The game uses this at startup.
@app.get("/hello")
def hello():
    return {"message": "Sveiks no Untitled Tower Defense servera!"}


# Saves a score. Answers 201, or 422 for bad data.
@app.post("/scores", status_code=201)
def add_score(entry: ScoreIn):
    score_id = db.add_score(entry.player, entry.score, entry.round)
    return {"id": score_id, **entry.model_dump()}


# Lets the website test a password. Answers 200, or 401 if wrong.
@app.post("/admin/login", dependencies=admin_only)
def admin_login():
    return {"message": "Parole pareiza"}


# Admin: deletes a score. Answers 204, 401, or 404 if it does not exist.
@app.delete("/scores/{score_id}", status_code=204, dependencies=admin_only)
def delete_score(score_id: int):
    if not db.delete_score(score_id):
        raise HTTPException(status_code=404, detail="Tāda rezultāta nav")


# Admin: changes a score's name. The name goes through the same checks
# as a new score, so a rename cannot add a bad word.
@app.patch("/scores/{score_id}", dependencies=admin_only)
def rename_score(score_id: int, entry: NameIn):
    if not db.rename_score(score_id, entry.player):
        raise HTTPException(status_code=404, detail="Tāda rezultāta nav")
    return {"id": score_id, "player": entry.player}


# The best scores, highest first. limit must be 1 to 100.
@app.get("/scores/top")
def top_scores(limit: int = Query(default=10, ge=1, le=100)):
    return db.top_scores(limit)


# -----------------------------------------------------------------------------
# [A5] PLAYER STATS AND GAME INFO
# -----------------------------------------------------------------------------
# One player's games played and best results, or 404 if unknown.
@app.get("/players/{name}/stats")
def player_stats(name: str):
    stats = db.player_stats(name)
    if stats is None:
        raise HTTPException(status_code=404, detail="Tāda spēlētāja nav")
    return stats


# All tower and card numbers. The rules page reads them from here, so
# the website always matches the real game.
@app.get("/game-info")
def game_info():
    return {
        "towers": BASIC_STATS,
        "cards": [{"id": card_id, **card} for card_id, card in CARDS.items()],
        "rarities": [
            {
                "name": name,
                "chance": weight,
                "color": RARITY_COLORS[name],
                "trade_up": TRADE_UP_COST.get(name),
            }
            for name, weight in zip(RARITY_ORDER, RARITY_WEIGHTS)
        ],
        "fused": {
            kind: {
                "name": FUSION_NAMES[kind],
                "recipe": FUSION_RECIPES[kind],
                "info": FUSION_INFO[kind],
                "stats": FUSED_STATS[kind],
            }
            for kind in FUSION_RECIPES
        },
        "fusion_level": FUSION_LEVEL,
        "max_equipped": MAX_EQUIPPED,
        "card_every_rounds": CARD_EVERY_ROUNDS,
    }


# -----------------------------------------------------------------------------
# [A6] WEBSITE PAGES
# -----------------------------------------------------------------------------
# The main address sends visitors to the leaderboard.
@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/pages/index.html")


# Serves the CSS and JS at /static, and the HTML pages at /pages.
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(API_DIR, "static")),
    name="static",
)
app.mount(
    "/pages",
    StaticFiles(directory=os.path.join(API_DIR, "templates"), html=True),
    name="pages",
)
