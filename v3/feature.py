import json
import re
from team_parser import parse_team_file, parse_team_text

NATURE_MODIFIERS = {
    "Lonely": {"atk": 1.1, "def": 0.9, "spa": 1.0, "spd": 1.0, "spe": 1.0},
    "Adamant": {"atk": 1.1, "def": 1.0, "spa": 0.9, "spd": 1.0, "spe": 1.0},
    "Naughty": {"atk": 1.1, "def": 1.0, "spa": 1.0, "spd": 0.9, "spe": 1.0},
    "Brave": {"atk": 1.1, "def": 1.0, "spa": 1.0, "spd": 1.0, "spe": 0.9},

    "Bold": {"atk": 0.9, "def": 1.1, "spa": 1.0, "spd": 1.0, "spe": 1.0},
    "Impish": {"atk": 1.0, "def": 1.1, "spa": 0.9, "spd": 1.0, "spe": 1.0},
    "Lax": {"atk": 1.0, "def": 1.1, "spa": 1.0, "spd": 0.9, "spe": 1.0},
    "Relaxed": {"atk": 1.0, "def": 1.1, "spa": 1.0, "spd": 1.0, "spe": 0.9},

    "Modest": {"atk": 0.9, "def": 1.0, "spa": 1.1, "spd": 1.0, "spe": 1.0},
    "Mild": {"atk": 1.0, "def": 0.9, "spa": 1.1, "spd": 1.0, "spe": 1.0},
    "Rash": {"atk": 1.0, "def": 1.0, "spa": 1.1, "spd": 0.9, "spe": 1.0},
    "Quiet": {"atk": 1.0, "def": 1.0, "spa": 1.1, "spd": 1.0, "spe": 0.9},

    "Calm": {"atk": 0.9, "def": 1.0, "spa": 1.0, "spd": 1.1, "spe": 1.0},
    "Gentle": {"atk": 1.0, "def": 0.9, "spa": 1.0, "spd": 1.1, "spe": 1.0},
    "Careful": {"atk": 1.0, "def": 1.0, "spa": 0.9, "spd": 1.1, "spe": 1.0},
    "Sassy": {"atk": 1.0, "def": 1.0, "spa": 1.0, "spd": 1.1, "spe": 0.9},

    "Timid": {"atk": 0.9, "def": 1.0, "spa": 1.0, "spd": 1.0, "spe": 1.1},
    "Hasty": {"atk": 1.0, "def": 0.9, "spa": 1.0, "spd": 1.0, "spe": 1.1},
    "Jolly": {"atk": 1.0, "def": 1.0, "spa": 0.9, "spd": 1.0, "spe": 1.1},
    "Naive": {"atk": 1.0, "def": 1.0, "spa": 1.0, "spd": 0.9, "spe": 1.1},

    "Serious": {"atk": 1.0, "def": 1.0, "spa": 1.0, "spd": 1.0, "spe": 1.0},
}

def pokemon_dex() -> dict[str, dict]:
    with open("data/replays/pokedex_gen9championsregmb/gen9pokedex.json", "r") as f:
        pokemon = json.load(f)
        return pokemon
def item_dex() -> dict[str, dict]:
    with open("data/replays/pokedex_gen9championsregmb/gen9items.json", "r") as f:
        itm_dx = json.load(f)
        return itm_dx

def move_dex() -> dict[str, dict]:
    with open("data/replays/pokedex_gen9championsregmb/gen9moves.json", "r") as f:
        mv_dx = json.load(f)
        return mv_dx
def points_to_stats(points: dict[str, int], base_stats: dict[str, int], nature: str) -> dict[str, int]:
    """Convert H/A/B/C/D/S points and base stats to final stats using a nature modifier."""
    final_stats = {"hp": 0, "atk": 0, "def":0, "spa":0, "spd":0, "spe":0}
    for stat_key in ["hp", "atk", "def", "spa", "spd", "spe"]:
        base = base_stats[stat_key]
        point = points[stat_key]
        if stat_key == "hp":
            final_stats[stat_key] = int(base + point +75) / 500
        else:
            nature_modifier = NATURE_MODIFIERS[nature][stat_key]
            final_stats[stat_key] = int((base + point + 20) * nature_modifier) / 500
    return final_stats

def can_mega_with_item(itm_dx: dict, item: str, pokemon_name: str) -> int:
    can_mega = {"flag": 0, "form_key": None}
    if "megaStone" in itm_dx[item] and pokemon_name in itm_dx[item]["megaStone"]:
        can_mega["flag"] = 1
        can_mega["form_key"] = "".join(itm_dx[item]["megaStone"][pokemon_name].split("-")).lower()
        return can_mega
    return can_mega

def normalize_base_stats(base_stats: dict[str, int]) -> dict[str, float]:
    return {
        "hp": base_stats["hp"] / 255.0,
        "atk": base_stats["atk"] / 255.0,
        "def": base_stats["def"] / 255.0,
        "spa": base_stats["spa"] / 255.0,
        "spd": base_stats["spd"] / 255.0,
        "spe": base_stats["spe"] / 255.0,
    }

def self_pokemon_feature_convert(pk_dx: dict, itm_dx: dict, target_pokemon: dict) -> dict:
    features = {"species_key": None, # embedding
                "types": None, #embedding
                "stats": None, #calculate
                "ability_key": None,
                "item_key": None,
                "is_mega": None,
                "form_key": None,
                "moves": None,
                "weight": None}

    target_dex = pk_dx[target_pokemon["name_key"]]

    # weight
    weight = target_dex["weightkg"] / 1000
    # normalized stats
    base_stats = target_dex["baseStats"]
    nature = target_pokemon["nature"]
    points = target_pokemon["points"]
    # can mega?
    item_name = "".join(target_pokemon["item"].split()).lower()  # アイテム辞書が小文字のスペースなしをキーとしているため
    can_mega = can_mega_with_item(itm_dx, item_name, target_pokemon["name"])

    # move
    features["species_key"] = target_pokemon["name_key"]
    features["types"] = [t.lower() for t in target_dex["types"]]
    features["stats"] = points_to_stats(points, base_stats, nature)
    features["ability_key"] = target_pokemon["ability_key"]
    features["item_key"] = item_name
    features["is_mega"] = can_mega["flag"]
    features["form_key"] = can_mega["form_key"]
    features["moves"] = [re.sub(r"[^a-z0-9]+", "", t.lower()) for t in target_pokemon["moves"]]
    features["weight"] = weight
    return features
def opposite_pokemon_feature_convert(pk_dx: dict, target_pokemon_key: str) -> dict:
    target_dex = pk_dx[target_pokemon_key]

    features = {
        "species_key": target_pokemon_key,
        "types": [t.lower() for t in target_dex["types"]],
        "base_stats": normalize_base_stats(target_dex["baseStats"]),
        "has_mega_form": int(
            "otherFormes" in target_dex
            and any("Mega" in f for f in target_dex["otherFormes"])
        ),
        "weight": target_dex["weightkg"] / 1000,
    }
    return features

if __name__ == "__main__":
    team = parse_team_file("teams/my_party_v2.txt")
    pk_dx = pokemon_dex()
    itm_dx = item_dex()
    mv_dx = move_dex()
    print(self_pokemon_feature_convert(pk_dx, itm_dx, team["metagross"]))
    print(opposite_pokemon_feature_convert(pk_dx, "garchomp"))
