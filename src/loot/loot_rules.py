"""
Shared loot-roll settings for the Light & Sky loot generator (src/loot).

Edit the values in this file to rebalance or restyle rarities; nothing else
needs to change.
"""

# Rarities in display order (lowest to highest).
RARITIES = ["Common", "Rare", "Legendary", "Exotic"]

# Relative odds for a random (non-forced) rarity roll. These are weights, so
# they don't need to add up to 100. Exotic is not listed here: it comes from
# the separate exotic chances below.
RARITY_ODDS = {
    "Common": 50,
    "Rare": 35,
    "Legendary": 15,
}

# Chance that a randomly generated item is upgraded to Exotic.
# Each is a probability between 0 and 1 (0.01 = 1%).
WEAPON_EXOTIC_CHANCE = 0.01
ARMOR_EXOTIC_CHANCE = 0.01

# Number of regular perks for each rarity, as (minimum, maximum).
# Exotic items get these regular perks plus one exotic perk.
PERK_COUNTS = {
    "Common": (0, 1),
    "Rare": (2, 3),
    "Legendary": (4, 4),
    "Exotic": (4, 4),
}

# Bright rarity colors, used on the dark app background (tiles, card border).
RARITY_COLORS = {
    "Common": "#FFFFFF",
    "Rare": "#00FFFF",
    "Legendary": "#7F3FBF",
    "Exotic": "#DACD61",
}

# Darker versions of the same hues, used for text and accents drawn on the
# light loot card so they stay readable.
CARD_INK_COLORS = {
    "Common": "#55544e",
    "Rare": "#006b7a",
    "Legendary": "#6a2fa8",
    "Exotic": "#7a6510",
}


def roll_rarity(rng):
    """Pick a non-Exotic rarity using RARITY_ODDS."""
    names = list(RARITY_ODDS)
    return rng.choices(names, weights=[RARITY_ODDS[n] for n in names], k=1)[0]


def perk_count_for_rarity(rarity, rng):
    """Roll how many regular perks an item of this rarity gets."""
    minimum, maximum = PERK_COUNTS.get(rarity, (0, 0))
    return rng.randint(minimum, maximum)


def perk_count_text(rarity):
    """Describe the perk count for a rarity, e.g. "0-1" or "4"."""
    minimum, maximum = PERK_COUNTS[rarity]
    return str(minimum) if minimum == maximum else f"{minimum}-{maximum}"
