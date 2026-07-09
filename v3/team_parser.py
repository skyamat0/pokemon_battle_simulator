"""Parse Pokemon Showdown team exports for v3 selection features."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


STAT_KEYS = {
    "HP": "hp",
    "Atk": "atk",
    "Def": "def",
    "SpA": "spa",
    "SpD": "spd",
    "Spe": "spe",
}
POINT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")


def to_id(name: str) -> str:
    """Return a Pokemon Showdown-style ID."""
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def blank_points() -> dict[str, int]:
    return {key: 0 for key in POINT_KEYS}


def parse_points(line: str) -> dict[str, int]:
    """Parse an EVs/stat-points line into H/A/B/C/D/S keys."""
    points = blank_points()
    raw = line.split(":", 1)[1].strip() if ":" in line else line.strip()
    if not raw:
        return points

    for part in raw.split("/"):
        tokens = part.strip().split()
        if len(tokens) < 2:
            continue
        value = int(tokens[0])
        stat = " ".join(tokens[1:])
        key = STAT_KEYS.get(stat)
        if key is None:
            raise ValueError(f"Unknown stat label in points line: {stat!r}")
        points[key] = value
    return points


def parse_header(line: str) -> tuple[str, str | None]:
    """Parse the first line of a Showdown set into species and item."""
    left, sep, item = line.partition(" @ ")
    item = item.strip() if sep else None

    name_part = left.strip()
    species_match = re.search(r"\(([^()]*)\)\s*(?:\([MF]\))?$", name_part)
    if species_match:
        species = species_match.group(1).strip()
    else:
        species = re.sub(r"\s+\([MF]\)$", "", name_part).strip()

    if not species:
        raise ValueError(f"Could not parse species from header: {line!r}")
    return species, item


def parse_set(block: str) -> tuple[str, dict]:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Empty Pokemon set block")

    species, item = parse_header(lines[0])
    record = {
        "name": species,
        "name_key": to_id(species),
        "ability": None,
        "ability_key": None,
        "points": blank_points(),
        "item": item,
        "item_key": to_id(item) if item else None,
        "moves": [],
        "move_keys": [],
        "nature": None,
"nature_key": None,
    }

    for line in lines[1:]:
        if line.startswith("Ability:"):
            ability = line.split(":", 1)[1].strip()
            record["ability"] = ability
            record["ability_key"] = to_id(ability)
        elif line.startswith("EVs:"):
            record["points"] = parse_points(line)
        elif line.endswith(" Nature"):
            nature = line.removesuffix(" Nature").strip()
            record["nature"] = nature
            record["nature_key"] = to_id(nature)
        elif line.startswith("- "):
            move = line[2:].strip()
            record["moves"].append(move)
            record["move_keys"].append(to_id(move))

    return record["name_key"], record


def parse_team_text(text: str) -> dict[str, dict]:
    """Parse a full Showdown team export into a dict keyed by species ID."""
    team = {}
    blocks = re.split(r"\n\s*\n", text.strip())
    for block in blocks:
        if not block.strip():
            continue
        key, record = parse_set(block)
        if key in team:
            raise ValueError(f"Duplicate species key in team: {key}")
        team[key] = record
    return team


def parse_team_file(path: str | Path) -> dict[str, dict]:
    return parse_team_text(Path(path).read_text())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("team_file")
    args = parser.parse_args()
    print(json.dumps(parse_team_file(args.team_file), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
