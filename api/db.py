#   =====================================================================
#   api/db.py - THE DATABASE (everything that touches game.db)
#   =====================================================================
#   game.db is a SQLite file that keeps scores after a restart. It is in
#   .gitignore, so it never goes to GitHub. All queries use ? spots for
#   values, which protects against SQL injection.
#
#   TABLE OF CONTENTS - search for a tag (Ctrl+F "[D2]") to jump to it
#     [D1]   Connecting and creating the table
#     [D2]   Saving and reading scores
#     [D3]   Changing scores (admin)
#     [D4]   Player stats

import os
import sqlite3
from contextlib import closing

# -----------------------------------------------------------------------------
# [D1] CONNECTING AND CREATING THE TABLE
# -----------------------------------------------------------------------------
# The database file sits in the project folder.
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game.db"
)


# Opens the database. row_factory lets rows be read by column name.
def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


# Creates the scores table the first time the server starts.
def init():
    with closing(connect()) as con, con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player TEXT NOT NULL,
                score INTEGER NOT NULL,
                round INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """)


# -----------------------------------------------------------------------------
# [D2] SAVING AND READING SCORES
# -----------------------------------------------------------------------------
# Saves one score and returns its new id. "with con" saves the change
# for real, and closing() closes the connection afterwards.
def add_score(player, score, round_reached):
    with closing(connect()) as con, con:
        cur = con.execute(
            "INSERT INTO scores (player, score, round) VALUES (?, ?, ?)",
            (player, score, round_reached),
        )
        return cur.lastrowid


# The best scores, highest first. On a tie the older score wins.
def top_scores(limit):
    with closing(connect()) as con:
        rows = con.execute(
            "SELECT id, player, score, round, created_at FROM scores "
            "ORDER BY score DESC, id ASC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


# -----------------------------------------------------------------------------
# [D3] CHANGING SCORES (ADMIN)
# -----------------------------------------------------------------------------
# Deletes one score. Returns False if no such score exists.
def delete_score(score_id):
    with closing(connect()) as con, con:
        cur = con.execute("DELETE FROM scores WHERE id = ?", (score_id,))
        return cur.rowcount > 0


# Changes one score's name. Returns False if no such score exists.
def rename_score(score_id, player):
    with closing(connect()) as con, con:
        cur = con.execute(
            "UPDATE scores SET player = ? WHERE id = ?", (player, score_id)
        )
        return cur.rowcount > 0


# -----------------------------------------------------------------------------
# [D4] PLAYER STATS
# -----------------------------------------------------------------------------
# Games played and best results for one name, None if they never played.
def player_stats(player):
    with closing(connect()) as con:
        row = con.execute(
            "SELECT COUNT(*) AS games, MAX(score) AS best_score, "
            "MAX(round) AS best_round FROM scores WHERE player = ?",
            (player,),
        ).fetchone()
    if row["games"] == 0:
        return None
    return {
        "player": player,
        "games": row["games"],
        "best_score": row["best_score"],
        "best_round": row["best_round"],
    }
