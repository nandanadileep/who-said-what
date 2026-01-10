CANONICAL_CHARACTERS = {
    # Main
    "Sheldon": ["sheldon", "sehldon", "shedon", "shldon", "sheldon)", "sheldon-bot"],
    "Leonard": ["leonard", "leoanard", "leonard)", "leonard:", "leonard-warrior"],
    "Penny": ["penny", "penny)", "penny(voice)", "penny-warrior"],
    "Howard": ["howard", "howard)", "howatd"],
    "Raj": ["raj", "raj)", "rajj"],

    # Extended mains
    "Amy": ["amy", "amy(off)", "amy farrah fowler"],
    "Bernadette": ["bernadette", "bermadette", "bernedette"],
    "Stuart": ["stuart"],

    # Relatives
    "Mary Cooper": ["mary"],
    "Beverly Hofstadter": ["beverly", "beverley"],
    "Debbie Wolowitz": ["debbie"],
    "Wyatt": ["wyatt"],
    "Susan": ["susan"],
}

BANNED_CHARACTERS = {
    "scene", "voice", "voiceover", "crowd", "staff", "woman", "man",
    "waiter", "waitress", "doctor", "nurse", "announcer",
    "mother", "father", "dad", "mom", "child", "children"
}


def build_character_lookup():
    lookup = {}
    for canonical, variants in CANONICAL_CHARACTERS.items():
        for v in variants:
            lookup[v] = canonical
    return lookup


LOOKUP = build_character_lookup()


def normalize_character(raw_name: str):
    if not isinstance(raw_name, str):
        return None

    name = raw_name.strip().lower()

    # Drop stage directions like (laughing)
    if name.startswith("(") and name.endswith(")"):
        return None

    if name in BANNED_CHARACTERS:
        return None

    return LOOKUP.get(name)
