#   =====================================================================
#   game/names.py - THE BAD WORD FILTER
#   =====================================================================
#   Decides if a player name is allowed. The game and the server both
#   use name_allowed(), and the word lists are in game/blocked_names.txt.
#
#   TABLE OF CONTENTS - search for a tag (Ctrl+F "[N3]") to jump to it
#     [N1]   Letter swaps: tables for sneaky spellings
#     [N2]   Loading the word lists
#     [N3]   Search patterns
#     [N4]   Cleaning up a name
#     [N5]   Checking for close matches
#     [N6]   name_allowed: the final check

import itertools
import os
import re
import unicodedata

# -----------------------------------------------------------------------------
# [N1] LETTER SWAPS
# -----------------------------------------------------------------------------
# Where the word list is stored.
WORDS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "blocked_names.txt"
)

# Cyrillic letters that LOOK like Latin ones.
LOOKS_LIKE = str.maketrans("авеёкмнорстухіїјѕ", "abeekmhopctyxiijs")

# Cyrillic letters by how they SOUND.
SOUNDS_LIKE = str.maketrans(
    dict(zip("абвгдезиклмнопрстуфхцыэ", "abvgdeziklmnoprstufhcie"))
    | {
        "ё": "e",
        "ж": "z",
        "й": "j",
        "ч": "ch",
        "ш": "sh",
        "щ": "sh",
        "ь": "",
        "ъ": "",
        "ю": "ju",
        "я": "ja",
    }
)

# Numbers and symbols used in place of letters, like 3 for e or @ for a.
SYMBOLS = str.maketrans(
    dict(zip("023456789@$€£!+(<¢", "ozeasgtbgaselitccc"))
    | dict(zip("αβεικνορτυχøłđı", "abeiknoptukoldi"))
    | {"æ": "ae", "œ": "oe"}
)

# Letters that sound the same get merged, so k, c, q and x all match.
SOUND_GROUPS = (
    ("ck", "k"),
    ("ch", "k"),
    ("c", "k"),
    ("q", "k"),
    ("x", "k"),
    ("y", "i"),
    ("v", "u"),
    ("w", "u"),
)


# -----------------------------------------------------------------------------
# [N2] LOADING THE WORD LISTS
# -----------------------------------------------------------------------------
# Reads blocked_names.txt. A [section] line starts a new list.
def load_words():
    sections = {}
    with open(WORDS_FILE, encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line.startswith("["):
                words = sections.setdefault(line.strip("[]"), [])
            elif line:
                words.append(line)
    return sections


# Rewrites text so same sounding spellings become identical.
def fold_sounds(text):
    text = re.sub("g+h+", "g", re.sub("p+h+", "f", text))
    for old, new in SOUND_GROUPS:
        text = text.replace(old, new)
    return text


# Builds a regex that also matches stretched spellings, so "fuuuck"
# still counts. Letters written twice must appear at least twice.
def word_pattern(word):
    parts = []
    for letter, group in itertools.groupby(word):
        size = len(list(group))
        parts.append(letter + ("+" if size == 1 else "{" + str(size) + ",}"))
    return "".join(parts)


# -----------------------------------------------------------------------------
# [N3] SEARCH PATTERNS
# -----------------------------------------------------------------------------
# Built once at startup. SAFE words like "classic" are hidden before
# checking, so a bad word inside a normal word is not a false alarm.
WORDS = load_words()
SAFE = sorted(WORDS["safe"], key=len, reverse=True)
SIMILAR = [fold_sounds(word) for word in WORDS["similar"]]

# Words from the [similar] list, also searched for backwards.
REVERSED = re.compile(
    "|".join(word_pattern(word).replace("g{", "[gk]{") for word in SIMILAR)
)

# Words that are blocked anywhere inside a name.
ANYWHERE = re.compile(
    "|".join(
        word_pattern(fold_sounds(word)).replace("g{", "[gk]{")
        for word in WORDS["anywhere"]
    )
    + "|"
    + REVERSED.pattern
)

# Words only blocked as a whole word, with an optional plural ending.
WHOLE = re.compile(
    "(?:" + "|".join(word_pattern(word) for word in WORDS["whole"]) + ")"
    "(?:e?s)?"
)


# -----------------------------------------------------------------------------
# [N4] CLEANING UP A NAME
# -----------------------------------------------------------------------------
# Removes accents, so ā becomes a.
def plain_letters(text):
    return "".join(
        letter
        for letter in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(letter)
    )


# Returns every way the name could be read. Some symbols have more than
# one meaning, so all the combinations are tried.
def spellings(name):
    # Split camelCase into separate words.
    spaced = "".join(
        " " + now if before.islower() and now.isupper() else now
        for before, now in zip(" " + name, name)
    )
    text = unicodedata.normalize("NFKC", spaced).casefold()
    text = text.replace("š", "sh").replace("č", "ch")

    # A second version without digits at the edges of words.
    edge_digits = re.sub(r"(?<![^\W\d_])\d+|\d+(?![^\W\d_])", " ", text)
    results = set()

    # Try each mix: digits or not, look or sound, 1 as i or l, * as a vowel.
    for start, alphabet, one, hole in itertools.product(
        (text, edge_digits), (LOOKS_LIKE, SOUNDS_LIKE), "il", "aeiou"
    ):
        changed = start.replace("1", one).replace("|", one)
        changed = changed.replace("*", hole).translate(alphabet)
        results.add(plain_letters(changed.translate(SYMBOLS)))
    return results


# Splits text into words and joins spaced out letters like "f u c k".
def words_in(text):
    words = re.findall(r"[a-z]+", text)
    merged = []
    for is_single, group in itertools.groupby(
        words, key=lambda word: len(word) == 1
    ):
        merged += ["".join(group)] if is_single else list(group)
    return merged


# Hides allowed words so they cannot trigger the filter.
def hide_safe(text):
    for word in SAFE:
        text = text.replace(word, "-")
    return text


# -----------------------------------------------------------------------------
# [N5] CHECKING FOR CLOSE MATCHES
# -----------------------------------------------------------------------------
# True if two letters count as the same (g and k count).
def same_sound(first, second):
    return first == second or first + second in ("gk", "kg")


# Edit distance: how many letter changes turn one word into the other.
def distance(first, second):
    row = list(range(len(second) + 1))
    for i, a in enumerate(first, 1):
        previous, row[0] = row[0], i
        for j, b in enumerate(second, 1):
            cost = 0 if same_sound(a, b) else 1
            previous, row[j] = row[j], min(
                row[j] + 1, row[j - 1] + 1, previous + cost
            )
    return row[-1]


# True if any part of text is within 1 change of word and has the same
# first and last sound. This catches near misses.
def close_to(text, word):
    for size in range(len(word) - 1, len(word) + 2):
        for start in range(len(text) - size + 1):
            end = start + size
            part = text[start:end]
            if (
                same_sound(part[0], word[0])
                and same_sound(part[-1], word[-1])
                and distance(part, word) <= 1
            ):
                return True
    return False


# -----------------------------------------------------------------------------
# [N6] NAME_ALLOWED
# -----------------------------------------------------------------------------
# The final check: True if a name is fine, False if it is blocked.
# Each spelling goes through the three tests below.
def name_allowed(name):
    for text in spellings(name):
        # Test 1: is any single word a blocked whole word?
        for word in words_in(text):
            if word in SAFE:
                continue
            if WHOLE.fullmatch(word) or WHOLE.fullmatch(word.strip("x")):
                return False

        # Test 2: is a blocked word anywhere in the name, even backwards?
        solid = fold_sounds(hide_safe(re.sub(r"[^a-z]", "", text)))
        if ANYWHERE.search(solid) or REVERSED.search(solid[::-1]):
            return False

        # Test 3: is any part very close to a word in the [similar] list?
        limited = re.sub(r"(.)\1{2,}", r"\1\1", solid)
        if any(close_to(limited, word) for word in SIMILAR):
            return False
    return True
