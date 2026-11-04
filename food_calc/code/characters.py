"""Per-character eating rules for DSTMeta.

The planner normally treats every food as identical for every survivor.  This
module adds the character-specific parts: favourite foods, diets, monster-food
immunities, health rules, stat scaling and Warly's repeated-dish penalty.

The numbers are taken from the Don't Starve wiki and, for Uncompromising Mode,
its Balance Changes pages.  Food types themselves live in
``food_calc/data/food_types.txt`` so the engine can pass them in.
"""

from __future__ import annotations

DEFAULT_CHARACTER = "wilson"

# Food ids match the ids used by the site's portrait picker.
CHARACTER_IDS = (
    "wilson",
    "willow",
    "wolfgang",
    "wendy",
    "wx-78",
    "wickerbottom",
    "woodie",
    "wes",
    "maxwell",
    "wigfrid",
    "webber",
    "winona",
    "warly",
    "walter",
    "wortox",
    "wormwood",
    "wurt",
    "wanda",
    "wonkey",
    "winky",
    "wathom",
    "wixie",
)

# Diets:
#   all          - no restriction
#   meat_goodies - meat and Goodies food types (Wigfrid, Wathom)
#   crockpot     - only Crock Pot dishes (Warly)
#   vegetarian   - anything that is not Meat type (Wurt)
DIETS = {
    "wigfrid": "meat_goodies",
    "warly": "crockpot",
    "wurt": "vegetarian",
    "wathom": "meat_goodies",
}

# Maximum Hunger values that matter to the planner.  Other characters have a
# high enough cap that it rarely changes a plan; these three are called out by
# the game and by the site's character notes.
MAX_HUNGER = {
    "wes": 75.0,
    "wigfrid": 120.0,
    "walter": 110.0,
}

# Webber ignores the negative Health/Sanity of these monster foods.  Durian and
# Extra Smelly Durian are deliberately absent: they still hurt him.
WEBBER_SAFE_MONSTER_FOODS = frozenset({
    "Monster Meat",
    "Cooked Monster Meat",
    "Monster Jerky",
    "Monster Lasagna",
    "Monster Tartare",
    "Heat Gland",
    "Cooked Heat Gland",
    # Uncompromising Mode monster items.
    "Monster Morsel",
    "Cooked Monster Morsel",
    "Small Monster Jerky",
    "Monster Egg",
    "Cooked Monster Egg",
})

# The favourite foods in normal Don't Starve Together give +15 Hunger.
VANILLA_FAVOURITES = {
    "wilson": ("Bacon and Eggs",),
    "willow": ("Spicy Chili",),
    "wolfgang": ("Roasted Potato",),
    "wendy": ("Banana Pop",),
    "wx-78": ("Butter Muffin",),
    "wickerbottom": ("Surf 'n' Turf",),
    "woodie": ("Honey Nuggets",),
    "wes": ("Fresh Fruit Crepes",),
    "maxwell": ("Wobster Dinner",),
    "wigfrid": ("Turkey Dinner",),
    "webber": ("Ice Cream",),
    "winona": ("Vegetable Stinger",),
    "walter": ("Trail Mix",),
    "wortox": ("Pomegranate", "Sliced Pomegranate"),
    "wormwood": ("Cooked Banana",),
    "wurt": ("Durian", "Extra Smelly Durian"),
    "wanda": ("Taffy",),
    "wonkey": ("Banana",),
}

# In Uncompromising Mode favourite foods give Sanity instead of Hunger.  The
# amount depends on the food and character (5-15); Winky is the exception and
# gets all three stats.  These are the per-food bonuses from the UC wiki table.
UC_FAVOURITE_SANITY = {
    "wilson": {"Bacon and Eggs": 15.0},
    "willow": {"Spicy Chili": 10.0},
    "wolfgang": {"Roasted Potato": 5.0},
    "wendy": {"Banana Pop": 10.0},
    "wx-78": {"Butter Muffin": 10.0},
    "wickerbottom": {"Surf 'n' Turf": 15.0},
    "woodie": {"Honey Nuggets": 10.0},
    "wes": {"Fresh Fruit Crepes": 15.0},
    "maxwell": {"Wobster Dinner": 15.0},
    "wigfrid": {"Turkey Dinner": 15.0},
    "webber": {"Ice Cream": 15.0},
    "winona": {"Vegetable Stinger": 10.0},
    "walter": {
        "Trail Mix": 15.0,
        "Jerky": 15.0,
        "Fishy Jerky": 15.0,
        "Small Jerky": 10.0,
        "Small Fishy Jerky": 10.0,
        "Dried Kelp Fronds": 5.0,
    },
    "wortox": {"Pomegranate": 5.0, "Sliced Pomegranate": 5.0},
    "wormwood": {"Cooked Banana": 5.0},
    "wurt": {"Durian": 15.0, "Extra Smelly Durian": 15.0},
    "wanda": {"Taffy": 5.0},
    "wonkey": {"Banana": 5.0},
    "wathom": {"Hard Shell Tacos": 10.0},
    "wixie": {"Boomberry Pancakes": 15.0},
}

# Warly's food-memory multiplier by serving number (1 = new dish).  The UC
# version also gives the first serving a +20% bonus.
WARLY_MULTIPLIERS = {
    "dst": (1.0, 0.9, 0.8, 0.65, 0.5, 0.3),
    "uc": (1.2, 0.8, 0.7, 0.55, 0.4, 0.3),
}


def normalize(character):
    """Return a known character id, or ``None`` when character rules are off."""
    if character is None:
        return None
    value = str(character).strip().lower()
    if not value or value in ("none", "off"):
        return None
    return value if value in CHARACTER_IDS else None


def max_hunger(character):
    """Return the character's Hunger cap, or ``None`` when it is not modelled."""
    return MAX_HUNGER.get(character)


def can_eat(character, name, food_types, is_dish):
    """Return whether ``character`` is allowed to eat ``name``."""
    diet = DIETS.get(character, "all")
    if diet == "all":
        return True
    if diet == "crockpot":
        return bool(is_dish)
    types = food_types.get(name, ())
    if diet == "meat_goodies":
        return "meat" in types or "goodies" in types
    if diet == "vegetarian":
        return "meat" not in types
    return True


def favorite_bonus(character, name, mode, over_time):
    """Return the ``(hunger, sanity, health)`` favourite-food bonus.

    UC bonuses are gradual Sanity and are therefore omitted when over-time
    stats are ignored.  Winky's immediate +15 all-stats bonus always applies,
    while her extra 15 Sanity is gradual.
    """
    if character is None:
        return (0.0, 0.0, 0.0)

    if character == "winky" and name == "Powdercake":
        bonus = [15.0, 15.0, 15.0]
        if over_time:
            bonus[1] += 15.0
        return tuple(bonus)

    if mode == "uc":
        sanity = UC_FAVOURITE_SANITY.get(character, {}).get(name)
        if sanity is None or not over_time:
            return (0.0, 0.0, 0.0)
        return (0.0, sanity, 0.0)

    if name in VANILLA_FAVOURITES.get(character, ()):
        return (15.0, 0.0, 0.0)
    return (0.0, 0.0, 0.0)


def adjust_stats(character, name, stats, over_time, mode, food_types):
    """Apply character immunities, favourite foods and health rules."""
    if character is None:
        return tuple(float(value) for value in stats)

    hunger, sanity, health = (float(value) for value in stats)
    types = food_types.get(name, ())

    if character == "webber" and name in WEBBER_SAFE_MONSTER_FOODS:
        sanity = max(sanity, 0.0)
        health = max(health, 0.0)

    if character == "winky" and ("monster" in types or "raw" in types):
        sanity = max(sanity, 0.0)
        health = max(health, 0.0)

    if character == "wathom" and "raw" in types and "monster" not in types:
        sanity = max(sanity, 0.0)
        health = max(health, 0.0)

    if character == "wurt" and name in ("Durian", "Extra Smelly Durian"):
        sanity = max(sanity, 0.0)
        health = max(health, 0.0)

    bonus = favorite_bonus(character, name, mode, over_time)
    hunger += bonus[0]
    sanity += bonus[1]
    health += bonus[2]

    if character == "wormwood":
        health = 0.0
    elif character == "wanda":
        # Taffy is her favourite and loses its health penalty; other food can
        # hurt her but never heal her.
        health = 0.0 if name == "Taffy" else min(health, 0.0)

    if character == "wortox":
        hunger *= 0.5
        sanity *= 0.5
        health *= 0.5

    return (hunger, sanity, health)


def warly_multiplier(serving, mode):
    """Return the stat multiplier for Warly's ``serving``-th use of a dish."""
    schedule = WARLY_MULTIPLIERS.get(mode, WARLY_MULTIPLIERS["dst"])
    index = max(0, min(int(serving) - 1, len(schedule) - 1))
    return schedule[index]


def warly_first_multiplier(mode):
    """Return the multiplier for a dish Warly has not eaten in this plan."""
    return warly_multiplier(1, mode)
