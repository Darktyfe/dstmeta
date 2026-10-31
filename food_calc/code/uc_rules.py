"""Crock Pot rules that Uncompromising Mode adds or replaces.

The base game data files describe every recipe as a list of tag thresholds.
A few Uncompromising Mode recipes cannot be written that way because their
tests mix "either A or B" clauses, count exact raw items, or apply the mod's
shared filler limits.  Those rules live here and are offered to
:func:`alg.crockpot` as extra candidates, so they compete with the ordinary
recipes by priority exactly like they do in the game.

Sources
-------
* ``init/init_food/init_crockpot.lua``, ``init/init_food/monsterfoods.lua`` and
  ``init/init_tuning.lua`` from the Uncompromising Mode repository's ``live``
  branch;
* the Uncompromising Mode wiki's Crock Pot page (revision 13949) for the
  UC-only dish stats, and its Balance Changes/Food page (revision 11896) for
  the rebalanced vanilla stats, both in ``data/uc/food.txt``.

The mod's options are assumed to be in their default (enabled) state:
``crockpotmonstmeat``, ``generalcrockblocker``, ``icecrockblocker``,
``rice``, ``newrecipes``, ``monstereggs``, ``farmfoodredux``,
``sr_foodrebalance``, ``icecream_buff``, ``meatball``, ``bonestew_nerf``,
``seeds``, ``beebox_nerf``, ``rawcropsnerf`` and ``butterflywings_nerf``.
"""

from __future__ import annotations

# Dishes defined here.  They are crockpot results, so the pot and the site
# picker must not offer them as ingredients.
DISHES = frozenset({
    "Boomberry Pancakes",
    "California King",
    "Deviled Eggs",
    "Devils Fruit Cake",
    "Gloomberry Jam",
    "Hard Shell Tacos",
    "Liceloaf",
    "Seafood Paella",
    "Simple Salad",
    "Snot Roast",
    "Snowcone",
    "Steamed Hams",
    "Stuffed Peeper Poppers",
    "Zazpberry Parfait",
})

# Base recipes whose test is replaced by a rule below.  The original row must
# not stay active: when the Uncompromising test fails, the DST row would
# otherwise still match (for example Monster Lasagna with diluted monster
# meat, or Kabobs with ice in the pot).
OVERRIDDEN = frozenset({"Monster Lasagna", "Kabobs"})

# Tags that only the rules below look at.  ``_recipe_tags`` unions these in so
# the pot still distinguishes ingredients whose UC values differ.
TAGS = frozenset({
    "dairy",
    "egg",
    "fish",
    "foliage",
    "frozen",
    "inedible",
    "insectoid",
    "meat",
    "monster meat",
    "rice",
    "sweetener",
    "vegetable",
})

# Filler limits from TUNING.DSTU in ``init/init_tuning.lua``.
_ICE_LIMIT = 1.0
_TWIG_LIMIT = 1.0
_ICE_PLUS_TWIG_LIMIT = 1.0

_TERMITE = 1.0

_TRUNKS = frozenset({
    "Koalefant Trunk",
    "Winter Koalefant Trunk",
    "Koalefant Trunk Steak",
})
_CARROTS = frozenset({"Carrot", "Roasted Carrot"})
_POTATOES = frozenset({"Potato", "Roasted Potato"})
_ONIONS = frozenset({"Onion", "Roasted Onion"})
_CORNS = frozenset({"Corn", "Popcorn"})
_BARNACLES = frozenset({"Barnacles", "Cooked Barnacles"})
_PEPPERS = frozenset({"Pepper", "Roasted Pepper"})
_POMEGRANATES = frozenset({"Pomegranate", "Sliced Pomegranate"})
_MEAT = frozenset({"Meat", "Cooked Meat"})
_MORSELS = frozenset({"Morsel", "Cooked Morsel"})
_FOLIAGE_ITEMS = frozenset({"Foliage", "Forget-Me-Lots", "Green Foliage"})


def _total(tag_maps):
    """Add up every tag over the four ingredients."""
    totals = {}
    for tags in tag_maps:
        for tag, weight in tags.items():
            totals[tag] = totals.get(tag, 0.0) + weight
    return totals


def _count(ingredients, names):
    return sum(1 for item in ingredients if item in names)


def _has(ingredients, names):
    return any(item in names for item in ingredients)


def _limit_ice(tags):
    frozen = tags.get("frozen", 0.0)
    foliage = tags.get("foliage", 0.0)
    return not frozen or frozen + foliage <= _ICE_LIMIT + 1e-9


def _limit_twigs(tags):
    inedible = tags.get("inedible", 0.0)
    foliage = tags.get("foliage", 0.0)
    return not inedible or inedible + foliage <= _TWIG_LIMIT + 1e-9


def _limit_ice_and_twigs(tags):
    frozen = tags.get("frozen", 0.0)
    inedible = tags.get("inedible", 0.0)
    foliage = tags.get("foliage", 0.0)
    if not frozen or not inedible:
        return True
    return frozen + inedible + foliage <= _ICE_PLUS_TWIG_LIMIT + 1e-9


def _fillers_ok(tags):
    """The mod's shared ``UncompromisingFillers`` test."""
    return (
        _limit_ice(tags)
        and _limit_twigs(tags)
        and _limit_ice_and_twigs(tags)
    )


def _monster_lasagna(ingredients, tags):
    monster = tags.get("monster meat", 0.0)
    meat = tags.get("meat", 0.0)
    if not monster or tags.get("inedible", 0.0):
        return False
    if tags.get("insectoid", 0.0) >= _TERMITE:
        return False
    if not ((meat and monster > meat) or monster >= 3):
        return False
    return _limit_ice(tags)


def _kabobs(ingredients, tags):
    return bool(
        tags.get("meat", 0.0)
        and _count(ingredients, {"Twigs"})
        and tags.get("monster meat", 0.0) <= 3.5
        and _fillers_ok(tags)
        and tags.get("insectoid", 0.0) < _TERMITE
    )


def _deviled_eggs(ingredients, tags):
    return bool(
        tags.get("monster meat", 0.0) >= 2
        and tags.get("egg", 0.0)
        and not tags.get("meat", 0.0)
    )


def _hard_shell_tacos(ingredients, tags):
    return bool(
        _count(ingredients, {"Scorpion Carapace"}) > 1
        and tags.get("vegetable", 0.0) >= 0.5
    )


def _liceloaf(ingredients, tags):
    return bool(
        tags.get("rice", 0.0) >= 2
        and _fillers_ok(tags)
        and tags.get("insectoid", 0.0) < _TERMITE
        and not tags.get("inedible", 0.0)
    )


def _seafood_paella(ingredients, tags):
    return bool(
        tags.get("rice", 0.0)
        and tags.get("vegetable", 0.0) >= 2
        and (
            _has(ingredients, {"Wobster"})
            or tags.get("fish", 0.0) >= 2
        )
        and _fillers_ok(tags)
    )


def _california_king(ingredients, tags):
    return bool(
        _has(ingredients, _BARNACLES)
        and _has(ingredients, {"Wobster"})
        and _has(ingredients, _PEPPERS)
        and tags.get("frozen", 0.0)
    )


def _steamed_hams(ingredients, tags):
    return bool(
        _has(ingredients, _FOLIAGE_ITEMS)
        and tags.get("vegetable", 0.0) >= 1
        and _has(ingredients, _MEAT)
        and not (
            tags.get("monster meat", 0.0)
            or tags.get("inedible", 0.0)
            or _has(ingredients, _MORSELS)
        )
    )


def _simple_salad(ingredients, tags):
    if tags.get("foliage", 0.0) <= 1:
        return False
    return not (
        tags.get("frozen", 0.0) >= 1
        and tags.get("sweetener", 0.0) >= 1
    )


def _boomberry_pancakes(ingredients, tags):
    return bool(
        _count(ingredients, {"Boomberry"}) >= 2
        and tags.get("egg", 0.0) > 1
    )


def _snowcone(ingredients, tags):
    ice = _count(ingredients, {"Ice"})
    return bool(ice > 1 or (ice and _count(ingredients, {"Twigs"})))


def _zazpberry_parfait(ingredients, tags):
    return bool(
        _has(ingredients, {"Zaspberry"})
        and tags.get("sweetener", 0.0)
        and tags.get("dairy", 0.0)
        and not tags.get("monster meat", 0.0)
        and not tags.get("inedible", 0.0)
        and _fillers_ok(tags)
    )


def _gloomberry_jam(ingredients, tags):
    return bool(
        _has(ingredients, {"Gloom Berry"})
        and _has(ingredients, {"Boomberry"})
        and not tags.get("monster meat", 0.0)
        and not tags.get("inedible", 0.0)
        and _fillers_ok(tags)
    )


def _snot_roast(ingredients, tags):
    return bool(
        _has(ingredients, _TRUNKS)
        and _has(ingredients, _CARROTS)
        and _has(ingredients, _POTATOES)
        and _has(ingredients, _ONIONS)
    )


def _stuffed_peeper_poppers(ingredients, tags):
    # The mod's test says ``names_durian or names_durian_cooked``; the second
    # name has a typo upstream, so only raw durians match in game.
    return bool(
        _has(ingredients, {"Milky Whites"})
        and tags.get("monster meat", 0.0) >= 2
        and _has(ingredients, {"Durian"})
        and not tags.get("inedible", 0.0)
    )


def _devils_fruit_cake(ingredients, tags):
    return bool(
        _has(ingredients, _POMEGRANATES)
        and tags.get("egg", 0.0) >= 2
        and not tags.get("meat", 0.0)
    )


# (dish, priority, test) in the order the mod adds/replaces the recipes.
_RULES = (
    ("Monster Lasagna", 51, _monster_lasagna),
    ("Kabobs", 5, _kabobs),
    ("Deviled Eggs", 52, _deviled_eggs),
    ("Hard Shell Tacos", 30, _hard_shell_tacos),
    ("Liceloaf", 30, _liceloaf),
    ("Seafood Paella", 30, _seafood_paella),
    ("California King", 30, _california_king),
    ("Steamed Hams", 30, _steamed_hams),
    ("Simple Salad", 20, _simple_salad),
    ("Boomberry Pancakes", 20, _boomberry_pancakes),
    ("Snowcone", 0.5, _snowcone),
    ("Zazpberry Parfait", 30, _zazpberry_parfait),
    ("Gloomberry Jam", 30, _gloomberry_jam),
    ("Snot Roast", 30, _snot_roast),
    ("Stuffed Peeper Poppers", 52, _stuffed_peeper_poppers),
    ("Devils Fruit Cake", 1, _devils_fruit_cake),
)


def candidates(ingredients, tag_maps):
    """Return ``(dish, priority)`` for every UC rule that matches these items.

    The caller merges the result into its ordinary recipe loop, so a rule only
    wins when its priority beats the other matching recipes.
    """
    tags = _total(tag_maps)
    return [
        (dish, priority)
        for dish, priority, test in _RULES
        if test(ingredients, tags)
    ]
