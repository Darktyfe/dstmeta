"""Crockpot recipe engine for DSTMeta.

The engine follows the rules of the Don't Starve Together crockpot:

* every ingredient carries a set of weighted tags (``*Meat``, ``*Vegetable``,
  ``*Fish``, ...) taken from ``value.txt``;
* an ingredient is also its own tag, so ``*Asparagus`` matches both
  ``Asparagus`` and ``Cooked Asparagus``.  Processing words such as ``Cooked``,
  ``Roasted`` or ``Prepared`` are ignored when matching;
* recipe conditions are sums over all four slots and are compared with
  ``>``, ``>=``, ``<``, ``<=``, ``==`` or ``=``;
* a recipe is rejected if any slot carries an excluded tag;
* the valid recipe with the highest priority wins.

Ingredients can also be roasted on a campfire or dried on a drying rack.
``cooked_table.txt`` maps raw foods to their cooked counterparts and
``dried_table.txt`` maps them to their dried counterparts (jerky, dried kelp,
...).  :func:`find_best_plan` weighs eating raw, roasting, drying and cooking
four items in the pot.  Dried variants are opt-in because a drying rack is
much slower than a campfire.
"""

from __future__ import annotations

import itertools
import math
import re
from collections import Counter
from functools import lru_cache

import basic_func
import cpp_engine

version = "0.5-alpha"

RECIPES = basic_func.file_to_list("recipes.txt")
WARLY_RECIPES = basic_func.file_to_list("warly_recipes.txt")
VALUES = basic_func.file_to_list("value.txt")
STATS = basic_func.file_to_list("food.txt")
COOKED = basic_func.file_to_list("cooked_table.txt")
DRIED = basic_func.file_to_list("dried_table.txt")

STAT_NAMES = ("Hunger", "Sanity", "Health")
SLOTS = 4

# Prepared dishes cannot be used as crockpot ingredients.  The game also
# refuses Dead Wobster / Delicious Wobster (a living Wobster is required for
# Wobster recipes) and Cooked Mandrake (Mandrake Soup needs a raw Mandrake).
_RECIPE_DISHES = frozenset(
    name for name, _, _, _ in RECIPES + WARLY_RECIPES
)
_NON_POT_FOODS = _RECIPE_DISHES | {
    "Dead Wobster",
    "Delicious Wobster",
    "Cooked Mandrake",
}

# Words that describe how an ingredient was prepared rather than what it is.
_PROCESSING_WORDS = frozenset({
    "baked",
    "braised",
    "cooked",
    "fried",
    "grilled",
    "hot",
    "juicy",
    "prepared",
    "ripe",
    "roast",
    "roasted",
    "sliced",
    "toasted",
    "winter",
})

# Tag spelling differences between the recipe files and value.txt.
_TAG_ALIASES = {
    "diary": "dairy",
    "monster": "monster meat",
    "monster food": "monster meat",
}


def get_version():
    """Return the current version of the program."""
    return version


def _normalize(text):
    """Lower-case text and keep only letters, digits and single spaces."""
    text = text.lower().replace("'", "")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _singular(word):
    """Very small singularizer: ``berries`` -> ``berry``, ``legs`` -> ``leg``."""
    if word.endswith("ies") and len(word) > 3:
        return word[:-3] + "y"
    if word.endswith(("sses", "shes", "ches", "xes")):
        return word[:-2]
    if word.endswith("s") and not word.endswith(("ss", "us", "is", "as", "os")):
        return word[:-1]
    return word


def _canonical_tag(tag):
    """Normalize a tag and resolve known aliases."""
    tag = tag.strip()
    if tag.startswith("*"):
        tag = tag[1:]
    key = " ".join(_singular(word) for word in _normalize(tag).split())
    return _TAG_ALIASES.get(key, key)


@lru_cache(maxsize=None)
def _name_forms(name):
    """Return the normalized name forms an ingredient tag can match."""
    normalized = _normalize(name)
    words = normalized.split()
    while words and words[0] in _PROCESSING_WORDS:
        words.pop(0)

    forms = set()
    stripped = " ".join(words)
    if stripped:
        forms.add(" ".join(_singular(word) for word in stripped.split()))
    return frozenset(forms)


@lru_cache(maxsize=None)
def ingredient_tags(name):
    """Return ``{tag: weight}`` contributed by one ingredient."""
    tags = {}
    for tag, weight in VALUES.get(name, {}).items():
        canonical = _canonical_tag(tag)
        tags[canonical] = tags.get(canonical, 0.0) + weight

    # Like DST's per-vegetable tags ("potato", "asparagus", ...), every
    # ingredient can be referred to by its own name.  Explicit weights from
    # value.txt win over the implicit 1.0.
    for form in _name_forms(name):
        tags.setdefault(form, 1.0)
    return tags


def _compare(actual, operator, expected):
    if operator in ("==", "="):
        return abs(actual - expected) <= 1e-9
    if operator == ">":
        return actual > expected
    if operator == ">=":
        return actual >= expected
    if operator == "<":
        return actual < expected
    if operator == "<=":
        return actual <= expected
    raise ValueError(f"Unsupported operator: {operator!r}")


def _split_list(text):
    return [part.strip() for part in text.split(",") if part.strip()]


def _parse_condition(text):
    """Parse ``>= 1.0 *Meat`` into ``(">=", 1.0, "meat")``."""
    try:
        operator, number, tag = text.split(None, 2)
    except ValueError:
        raise ValueError(f"Malformed condition: {text!r}") from None
    return operator, float(number), _canonical_tag(tag)


def _conditions_met(conditions, tag_maps):
    for text in _split_list(conditions):
        operator, expected, tag = _parse_condition(text)
        actual = sum(tags.get(tag, 0.0) for tags in tag_maps)
        if not _compare(actual, operator, expected):
            return False
    return True


def _is_excluded(excludes, tag_maps):
    for text in _split_list(excludes):
        tag = _canonical_tag(text)
        if any(tag in tags for tags in tag_maps):
            return True
    return False


def crockpot(ingredients, warly=False):
    """Return the dish produced by exactly four ``ingredients``.

    With ``warly=True`` the Portable Crock Pot recipes are included as well.
    ``None`` means no recipe matched (which should not happen as long as
    ``Wet Goop`` is in ``recipes.txt``).
    """
    ingredients = tuple(ingredients)
    if len(ingredients) != SLOTS:
        raise ValueError(f"the crockpot needs {SLOTS} ingredients, got {len(ingredients)}")
    if any(name in _NON_POT_FOODS for name in ingredients):
        return None

    tag_maps = [ingredient_tags(name) for name in ingredients]
    recipes = RECIPES + WARLY_RECIPES if warly else RECIPES

    best_name = None
    best_priority = None
    for name, conditions, excludes, priority in recipes:
        if not _conditions_met(conditions, tag_maps):
            continue
        if _is_excluded(excludes, tag_maps):
            continue
        if best_priority is None or priority > best_priority:
            best_name, best_priority = name, priority
    return best_name


@lru_cache(maxsize=None)
def _cook_cached(ingredients, warly):
    return crockpot(ingredients, warly)


def cook(ingredients, warly=False):
    """Cached :func:`crockpot`; the order of the four items does not matter."""
    return _cook_cached(tuple(sorted(ingredients)), warly)


def can_cook(dish, ingredients, warly=False):
    """Return ``True`` if these four ingredients produce ``dish``."""
    return len(ingredients) == SLOTS and crockpot(ingredients, warly) == dish


def get_cooked_variant(name):
    """Return the campfire-cooked form of ``name``, or ``None``."""
    return COOKED.get(name)


def get_dried_variant(name):
    """Return the drying-rack form of ``name``, or ``None``."""
    return DRIED.get(name)


def can_comb(food_list):
    """Return every distinct 4-ingredient combination of ``food_list``.

    Ingredients are consumed per slot, so a combination never uses an item
    more often than it appears in the inventory.
    """
    return {tuple(sorted(combo)) for combo in itertools.combinations(food_list, SLOTS)}


@lru_cache(maxsize=None)
def _recipe_tags():
    """Return every tag a crockpot recipe can observe."""
    tags = set()
    for recipes in (RECIPES, WARLY_RECIPES):
        for _, conditions, excludes, _ in recipes:
            for text in _split_list(conditions):
                tags.add(_parse_condition(text)[2])
            for text in _split_list(excludes):
                tags.add(_canonical_tag(text))
    return frozenset(tags)


@lru_cache(maxsize=None)
def _pot_signature(name):
    """Return the tags of ``name`` that can change a crockpot result.

    Tags that no recipe looks at (for example the implicit "jerky" name tag)
    cannot change the dish, so ingredients with the same signature are
    interchangeable in the pot.
    """
    tags = ingredient_tags(name)
    observed = _recipe_tags()
    return tuple(
        sorted((tag, weight) for tag, weight in tags.items() if tag in observed)
    )


@lru_cache(maxsize=None)
def _variant_options(name, dried=False):
    """Return the raw name plus processed forms that cook differently.

    A cooked or dried form with the same pot-relevant tags always cooks into
    the same dish, so it does not need to be tried in the pot.  The raw form
    is always first and therefore wins ties.
    """
    variants = [name]
    seen = {_pot_signature(name)}

    candidates = []
    cooked = COOKED.get(name)
    if cooked is not None:
        candidates.append(cooked)
    if dried:
        dried_name = DRIED.get(name)
        if dried_name is not None:
            candidates.append(dried_name)

    for candidate in candidates:
        signature = _pot_signature(candidate)
        if signature in seen:
            continue
        seen.add(signature)
        variants.append(candidate)
    return tuple(variants)


@lru_cache(maxsize=None)
def _variant_combos(combo, dried=False):
    """Return every distinct raw/cooked/dried variant of a 4-item combo."""
    variants = set()
    options = [_variant_options(item, dried) for item in combo]
    for variant in itertools.product(*options):
        variants.add(tuple(sorted(variant)))
    return tuple(sorted(variants))


@lru_cache(maxsize=None)
def _cooked_names():
    return frozenset(COOKED.values())


@lru_cache(maxsize=None)
def _dried_names():
    return frozenset(DRIED.values())


def _cooked_count(combo):
    """How many of these ingredients are cooked forms (for tie-breaking)."""
    cooked_names = _cooked_names()
    return sum(1 for name in combo if name in cooked_names)


def _processed_count(combo):
    """How many of these ingredients were processed into another item."""
    cooked_names = _cooked_names()
    dried_names = _dried_names()
    return sum(1 for name in combo if name in cooked_names or name in dried_names)


def _combo_key(combo):
    return _processed_count(combo), combo


def cookable_dishes(food_list, warly=False, dried=False):
    """Return ``{dish: [combination, ...]}`` for the given inventory.

    Combinations include raw, campfire-cooked and (when ``dried`` is true)
    drying-rack ingredients.  Each dish's combinations are ordered least
    processed first, so the rawest one is preferred when several produce the
    same dish.
    """
    dishes = {}
    for combo in can_comb(food_list):
        for used in _variant_combos(combo, dried):
            dish = cook(used, warly)
            if dish is None:
                continue
            bucket = dishes.setdefault(dish, [])
            if used not in bucket:
                bucket.append(used)
    for bucket in dishes.values():
        bucket.sort(key=_combo_key)
    return dishes


def get_food_stat(name, stat):
    """Return one stat of a food item, or ``0`` when it is not in food.txt."""
    if stat not in STAT_NAMES:
        raise ValueError(f"Unknown stat: {stat!r} (expected one of {STAT_NAMES})")
    return STATS.get(name, (0.0, 0.0, 0.0))[STAT_NAMES.index(stat)]


def get_food_stats(name):
    """Return ``(hunger, sanity, health)`` or ``None`` if stats are missing."""
    return STATS.get(name)


def known_foods():
    """Return every food name that appears in food.txt or value.txt."""
    return sorted(set(STATS) | set(VALUES))


@lru_cache(maxsize=None)
def _food_lookup():
    """Build a case- and plural-insensitive lookup of known food names."""
    lookup = {}
    for food in known_foods():
        lookup.setdefault(food.lower(), food)
        lookup.setdefault(_normalize(food), food)
        lookup.setdefault(
            " ".join(_singular(word) for word in _normalize(food).split()),
            food,
        )
    return lookup


def resolve_food_name(name):
    """Return the canonical spelling of a known food, or ``None``."""
    lookup = _food_lookup()
    key = name.strip().lower()
    if key in lookup:
        return lookup[key]
    normalized = " ".join(_singular(word) for word in _normalize(name).split())
    return lookup.get(normalized)


def unknown_food_message(names):
    """Return a user-facing error for names missing from the food data."""
    unique = list(dict.fromkeys(names))
    if len(unique) == 1:
        subject = f"{unique[0]!r} is not a food"
    else:
        subject = f"{', '.join(repr(name) for name in unique)} are not foods"
    return f"{subject} and should be removed from the ingredient list."


@lru_cache(maxsize=None)
def _item_action(name, stat, dried=False):
    """Return ``(value, action)`` for eating one item on its own.

    The action is one of ``("keep", name, name)``, ``("eat", name, name)``,
    ``("roast", name, cooked)`` or ``("dry", name, dried)``.  Keeping an item
    is the fallback because it contributes nothing instead of a negative
    value.
    """
    best_value = 0.0
    best_action = ("keep", name, name)

    raw_value = get_food_stat(name, stat)
    if raw_value > best_value:
        best_value = raw_value
        best_action = ("eat", name, name)

    cooked = COOKED.get(name)
    if cooked is not None:
        cooked_value = get_food_stat(cooked, stat)
        if cooked_value > best_value:
            best_value = cooked_value
            best_action = ("roast", name, cooked)

    if dried:
        dried_name = DRIED.get(name)
        if dried_name is not None:
            dried_value = get_food_stat(dried_name, stat)
            if dried_value > best_value:
                best_value = dried_value
                best_action = ("dry", name, dried_name)

    return best_value, best_action


def best_item_action(name, stat="Hunger", dried=False):
    """Return the best way to consume a single item."""
    return _item_action(name, stat, dried)[1]


@lru_cache(maxsize=None)
def _pot_options(combo, warly, dried=False):
    """Return ``(dish, ingredients, stats)`` for every useful dish this combo makes.

    When several raw/cooked/dried variants produce the same dish, the least
    processed variant is kept, so the UI never suggests cooking meat for no
    reason.  A dish that is no better than simply eating the same four items
    is dropped: it can never improve a plan.
    """
    by_dish = {}
    for used in _variant_combos(combo, dried):
        dish = cook(used, warly)
        if dish is None:
            continue
        stats = get_food_stats(dish) or (0.0, 0.0, 0.0)
        current = by_dish.get(dish)
        if current is None or _combo_key(used) < _combo_key(current[0]):
            by_dish[dish] = (used, tuple(float(value) for value in stats))

    # If eating the four items individually is at least as good in every stat,
    # using the pot for this particular dish cannot help any continuation.
    individual = [vector for vector, _ in _individual_frontier(combo, dried)]
    candidates = []
    for dish, (used, stats) in sorted(by_dish.items()):
        if any(
            all(base >= value - 1e-9 for base, value in zip(vector, stats))
            for vector in individual
        ):
            continue
        if any(
            all(
                other_value >= value - 1e-9
                for other_value, value in zip(other_stats, stats)
            )
            for other_stats, _, _ in candidates
        ):
            continue
        candidates = [
            (other_stats, other_used, other_dish)
            for other_stats, other_used, other_dish in candidates
            if not all(
                value >= other_value - 1e-9
                for value, other_value in zip(stats, other_stats)
            )
        ]
        candidates.append((stats, used, dish))

    return tuple(
        (dish, used, stats)
        for stats, used, dish in sorted(candidates, key=lambda item: item[2])
    )


def best_single_dish(food_list, stat="Hunger", warly=False, dried=False):
    """Return ``(score, dish, combination)`` for the best single dish.

    Returns ``None`` when nothing can be cooked.
    """
    best = None
    for dish, combinations in cookable_dishes(food_list, warly, dried).items():
        score = get_food_stat(dish, stat)
        if best is None or score > best[0]:
            best = (score, dish, combinations[0])
    return best


def normalize_losses(losses=None):
    """Return ``{stat: allowed_loss}`` with all three stats present.

    ``losses`` may be a mapping (``{"Hunger": 0, "Sanity": 5, ...}``) or a
    sequence of three numbers in ``Hunger, Sanity, Health`` order.  The default
    is zero for every stat, meaning the plan may not end below zero.
    """
    allowed = {stat: 0.0 for stat in STAT_NAMES}
    if losses is None:
        return allowed

    if isinstance(losses, dict):
        for stat in STAT_NAMES:
            value = losses.get(stat, losses.get(stat.lower(), 0.0))
            allowed[stat] = _checked_loss(value, stat)
        return allowed

    values = list(losses)
    if len(values) != len(STAT_NAMES):
        raise ValueError(
            f"expected {len(STAT_NAMES)} loss values, got {len(values)}"
        )
    for stat, value in zip(STAT_NAMES, values):
        allowed[stat] = _checked_loss(value, stat)
    return allowed


def _checked_loss(value, stat):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"allowed loss for {stat} must be a number") from None
    if not math.isfinite(number):
        raise ValueError(f"allowed loss for {stat} must be a finite number")
    if number < 0:
        raise ValueError(f"allowed loss for {stat} cannot be negative")
    return number


def _vector_add(left, right):
    return tuple(a + b for a, b in zip(left, right))


def _dominates(left, right):
    return (
        all(a >= b - 1e-9 for a, b in zip(left, right))
        and any(a > b + 1e-9 for a, b in zip(left, right))
    )


def _action_key(actions):
    """Prefer plans that cook fewer already-cooked ingredients and use fewer steps."""
    pot_cooked = sum(
        _cooked_count(action[1]) for action in actions if action[0] == "cook"
    )
    return pot_cooked, len(actions)


def _pareto(points):
    """Keep the nondominated ``(stats, actions)`` points."""
    unique = {}
    for vector, actions in points:
        rounded = tuple(round(value, 6) for value in vector)
        current = unique.get(rounded)
        if current is None or _action_key(actions) < _action_key(current[1]):
            unique[rounded] = (vector, actions)

    kept = []
    for vector, actions in unique.values():
        if any(_dominates(other, vector) for other, _ in kept):
            continue
        kept = [
            (other, other_actions)
            for other, other_actions in kept
            if not _dominates(vector, other)
        ]
        kept.append((vector, actions))
    return tuple(kept)


@lru_cache(maxsize=None)
def _individual_options(name, dried=False):
    """Return ``(stats, action)`` for keeping, eating, roasting or drying one item."""
    options = [((0.0, 0.0, 0.0), ("keep", name, name))]

    stats = get_food_stats(name)
    if stats is not None:
        options.append((tuple(float(value) for value in stats), ("eat", name, name)))

    cooked = COOKED.get(name)
    if cooked is not None:
        cooked_stats = get_food_stats(cooked)
        if cooked_stats is not None:
            options.append(
                (tuple(float(value) for value in cooked_stats), ("roast", name, cooked))
            )

    if dried:
        dried_name = DRIED.get(name)
        if dried_name is not None:
            dried_stats = get_food_stats(dried_name)
            if dried_stats is not None:
                options.append(
                    (tuple(float(value) for value in dried_stats),
                     ("dry", name, dried_name))
                )
    return tuple(options)


@lru_cache(maxsize=None)
def _individual_frontier(items, dried=False):
    """Pareto frontier of eating every item in ``items`` individually."""
    points = [((0.0, 0.0, 0.0), ())]
    for item in items:
        options = _individual_options(item, dried)
        points = [
            (_vector_add(vector, option_vector), actions + (action,))
            for vector, actions in points
            for option_vector, action in options
        ]
        points = list(_pareto(points))
    return tuple(points)


def _remove_items(remaining, key):
    rest = list(remaining)
    for item in key:
        rest.remove(item)
    return tuple(rest)


def _solve_frontier(inventory, warly, dried=False):
    """Return every nondominated plan for ``inventory`` as ``(stats, actions)``."""
    memo = {}

    def solve(remaining):
        if not remaining:
            return _individual_frontier(remaining, dried)
        if remaining in memo:
            return memo[remaining]

        points = list(_individual_frontier(remaining, dried))
        first = remaining[0]
        rest = remaining[1:]

        # Either the first item is used on its own (kept, eaten or roasted),
        # in which case the rest of the inventory is still free to cook, or it
        # joins three other items in the pot.  Enumerating only the pot groups
        # would miss every plan that leaves the first item out of the pot but
        # cooks some of the remaining items.
        points = []
        for option_stats, option_action in _individual_options(first):
            for sub_stats, sub_actions in solve(rest):
                points.append(
                    (
                        _vector_add(option_stats, sub_stats),
                        (option_action,) + sub_actions,
                    )
                )

        seen = set()
        for extra in itertools.combinations(rest, 3):
            key = tuple(sorted((first,) + extra))
            if key in seen:
                continue
            seen.add(key)

            sub = solve(_remove_items(remaining, key))
            for dish, used, dish_stats in _pot_options(key, warly, dried):
                action = ("cook", used, dish)
                for sub_stats, sub_actions in sub:
                    points.append(
                        (_vector_add(dish_stats, sub_stats), (action,) + sub_actions)
                    )

        points = _pareto(points)
        memo[remaining] = points
        return points

    return solve(inventory)


# The plan search runs in the native engine (food_calc/native/engine.dll) when
# that library is available; set to False to force the pure Python path.
_USE_NATIVE = True

# Task limits of the native engine (food_calc/native/engine.cpp).
_NATIVE_MAX_TYPES = 48
_NATIVE_MAX_PER_TYPE = 255
_NATIVE_MAX_INSTANCES = 1024


def _type_combos(counts, size, start=0, chosen=()):
    """Yield ``size`` type indices (ascending, repeats allowed) with counts."""
    if size == 0:
        yield chosen
        return
    for t in range(start, len(counts)):
        if counts[t]:
            counts[t] -= 1
            yield from _type_combos(counts, size - 1, t, chosen + (t,))
            counts[t] += 1


def _native_task(inventory, warly, dried=False):
    """Build the flat arrays for the native engine, or None outside its limits.

    Returns ``(task, types, dish_names, used_by)``: ``task`` packs stats and
    ids to hand to :mod:`cpp_engine`, and the rest converts native output back
    into action tuples.
    """
    types = sorted(set(inventory))
    if not types or len(types) > _NATIVE_MAX_TYPES:
        return None
    counts = [inventory.count(name) for name in types]
    if any(count > _NATIVE_MAX_PER_TYPE for count in counts):
        return None
    if len(inventory) > _NATIVE_MAX_INSTANCES:
        return None

    # Individual options per type, in keep/eat/roast/dry order.
    ind_off = [0]
    ind_kind = []
    ind_stats = []
    for name in types:
        for vector, action in _individual_options(name, dried):
            ind_kind.append(cpp_engine.ACTION_KINDS[action[0]])
            ind_stats.extend(float(value) for value in vector)
        ind_off.append(len(ind_kind))

    # Pot options for every distinct 4-item multiset of types.
    dish_names = []
    dish_ids = {}
    types_with_counts = list(counts)
    pot_keys = []
    pot_dish = []
    pot_stats = []
    pot_cooked = []
    pot_off = [0]
    used_by = {}

    def dish_id(dish):
        index = dish_ids.get(dish)
        if index is None:
            index = len(dish_names)
            dish_ids[dish] = index
            dish_names.append(dish)
        return index

    for combo in _type_combos(types_with_counts, 4):
        names = tuple(types[t] for t in combo)
        options = _pot_options(names, warly, dried)
        pot_keys.extend(combo)
        for dish, used, stats in options:
            pot_dish.append(dish_id(dish))
            pot_stats.extend(float(value) for value in stats)
            pot_cooked.append(_cooked_count(used))
            used_by[(combo, pot_dish[-1])] = used
        pot_off.append(len(pot_dish))

    task = (counts, ind_off, ind_stats, ind_kind, pot_keys, pot_off,
            pot_dish, pot_stats, pot_cooked)
    return task, types, dish_names, used_by


def _native_plan(inventory, stat_index, allowed, warly, dried=False):
    """Return ``(total, actions)`` from the native engine, or None."""
    import cpp_engine

    if not cpp_engine.available():
        return None

    built = _native_task(inventory, warly, dried)
    if built is None:
        return None
    task, types, dish_names, used_by = built
    counts, ind_off, ind_stats, ind_kind, pot_keys, pot_off, pot_dish, pot_stats, pot_cooked = task

    losses = [allowed[name] for name in STAT_NAMES]
    result = cpp_engine.solve(
        counts, ind_off, ind_stats, ind_kind, pot_keys, pot_off, pot_dish,
        pot_stats, pot_cooked, stat_index, losses,
    )
    if result is None:
        return None
    total, _totals, groups, individuals = result

    actions = []
    for dish_id, t0, t1, t2, t3 in groups:
        combo = (t0, t1, t2, t3)
        used = used_by[(combo, dish_id)]
        actions.append(("cook", tuple(used), dish_names[dish_id]))
    for t, name in enumerate(types):
        keep, eat, roast, dry = individuals[4 * t:4 * t + 4]
        for _ in range(keep):
            actions.append(("keep", name, name))
        for _ in range(eat):
            actions.append(("eat", name, name))
        for _ in range(roast):
            actions.append(("roast", name, COOKED.get(name) or name))
        for _ in range(dry):
            actions.append(("dry", name, DRIED.get(name) or name))
    return total, actions


def find_best_plan(food_list, stat="Hunger", warly=False, losses=None,
                   dried=False):
    """Return ``(total_score, actions)`` for the best use of the inventory.

    Every item is either eaten raw, roasted on a campfire, dried on a drying
    rack (only when ``dried`` is true), kept because it would be harmful, or
    grouped with three others into a crockpot dish.  ``losses`` limits how far
    the final totals may drop below zero for each stat; the default
    ``0, 0, 0`` forbids any net loss.
    """
    if stat not in STAT_NAMES:
        raise ValueError(f"Unknown stat: {stat!r} (expected one of {STAT_NAMES})")

    allowed = normalize_losses(losses)
    inventory = tuple(sorted(food_list))

    if _USE_NATIVE:
        native = _native_plan(
            inventory, STAT_NAMES.index(stat), allowed, warly, dried
        )
        if native is not None:
            return native

    points = _solve_frontier(inventory, warly, dried)

    feasible = [
        point
        for point in points
        if all(
            point[0][index] >= -allowed[name] - 1e-9
            for index, name in enumerate(STAT_NAMES)
        )
    ]
    if not feasible:
        # Keeping everything is always zero, so this should be unreachable.
        return 0.0, [("keep", item, item) for item in inventory]

    index = STAT_NAMES.index(stat)

    def rank(point):
        vector, actions = point
        pot_cooked, step_count = _action_key(actions)
        return vector[index], vector[2], vector[1], -pot_cooked, -step_count

    vector, actions = max(feasible, key=rank)
    return vector[index], _expand_prep(actions, inventory)


def plan_totals(actions):
    """Return ``{stat: total}`` for the food produced by a plan."""
    totals = {stat: 0.0 for stat in STAT_NAMES}
    for action in actions:
        # Kept food is not eaten, and prepping an ingredient only readies it
        # for the pot; neither contributes to the plan's totals.
        if action[0] in ("keep", "prep"):
            continue
        stats = get_food_stats(action[2]) or (0.0, 0.0, 0.0)
        for stat, value in zip(STAT_NAMES, stats):
            totals[stat] += value
    return totals


def describe_action(action):
    """Return a human readable description of one plan action."""
    kind, source, target = action
    if kind == "cook":
        return f"cook {', '.join(source)} -> {target}"
    if kind == "roast":
        return f"roast {source} -> {target}"
    if kind == "dry":
        return f"dry {source} -> {target}"
    if kind == "eat":
        return f"eat {source}"
    return f"keep {source}"


def data_warnings():
    """Return a list of data problems found in the txt files."""
    warnings = []
    sources = (("recipes.txt", RECIPES), ("warly_recipes.txt", WARLY_RECIPES))

    dishes = sorted({name for _, recipes in sources for name, _, _, _ in recipes})
    for dish in dishes:
        if dish not in STATS:
            warnings.append(f"food.txt has no stats for dish {dish!r}")

    for raw, cooked in COOKED.items():
        if raw not in STATS:
            warnings.append(f"cooked_table.txt: {raw!r} has no stats in food.txt")
        if cooked not in STATS:
            warnings.append(
                f"cooked_table.txt: {raw!r} -> {cooked!r} has no stats in food.txt"
            )

    for raw, dried in DRIED.items():
        if raw not in STATS:
            warnings.append(f"dried_table.txt: {raw!r} has no stats in food.txt")
        if dried not in STATS:
            warnings.append(
                f"dried_table.txt: {raw!r} -> {dried!r} has no stats in food.txt"
            )

    provided = set()
    ingredients = set(VALUES) | (set(STATS) - set(dishes))
    for name in ingredients:
        provided.update(ingredient_tags(name))

    for source, recipe_list in sources:
        for dish, conditions, excludes, _ in recipe_list:
            tags = []
            for text in _split_list(conditions):
                try:
                    tags.append(_parse_condition(text)[2])
                except ValueError as error:
                    warnings.append(f"{source}: {dish!r}: {error}")
            tags.extend(_canonical_tag(text) for text in _split_list(excludes))
            for tag in tags:
                if tag and tag not in provided:
                    warnings.append(
                        f"{source}: {dish!r} uses tag {tag!r} that no food provides"
                    )

    return warnings
