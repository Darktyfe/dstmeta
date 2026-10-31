"""Parsing helpers for the DSTMeta food database.

Data files live in ``food_calc/data`` and are plain text with one record per
line.  Blank lines are ignored, so trailing newlines and spacing are harmless.

Record formats
--------------
food.txt         ``Name: hunger, sanity, health``
over_time.txt    ``Name: hunger, sanity, health`` (the gradual part of the stats)
value.txt        ``Ingredient: *Tag - weight, *Tag - weight, ...``
recipes.txt      ``Dish; conditions; excludes; priority``
cooked_table.txt ``Raw: Cooked``
dried_table.txt  ``Raw: Dried``

Conditions are ``<op> <number> <tag>`` separated by ``,`` (``>= 1.0 *Meat``).
A ``!`` before an ingredient name matches the raw item only (``!Drumstick``),
so cooked variants do not count.  Excludes are bare tags separated by ``,``
(``*Meat, Twigs``).  An empty field means "none".

Modes
-----
``data/`` holds the base (Don't Starve Together) numbers.  ``data/uc/`` holds
an *overlay* for Uncompromising Mode: every file there has the same format and
is merged into the base when ``mode="uc"``.  ``food.txt``, ``value.txt``,
``cooked_table.txt``, ``dried_table.txt`` and ``over_time.txt`` replace whole
records by name; ``recipes.txt`` and ``warly_recipes.txt`` replace every rule
of a dish that the overlay mentions.
"""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DEFAULT_MODE = "dst"
MODES = ("dst", "uc")


def normalize_mode(mode=None):
    """Return a valid mode name, defaulting to ``dst``."""
    if mode is None:
        return DEFAULT_MODE
    if mode not in MODES:
        raise ValueError(f"Unknown mode: {mode!r} (expected one of {MODES})")
    return mode


def read_file(file_name):
    """Return the contents of a base data file."""
    with open(DATA_DIR / file_name, "r", encoding="utf-8") as file:
        return file.read()


def read_mode_file(file_name, mode="dst"):
    """Return an overlay file, or ``None`` when that mode has no such file."""
    mode = normalize_mode(mode)
    if mode == DEFAULT_MODE:
        return read_file(file_name)
    path = DATA_DIR / mode / file_name
    if not path.is_file():
        return None
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def _lines(file_name, mode="dst"):
    """Yield stripped, non-empty lines together with their 1-based numbers."""
    text = read_mode_file(file_name, mode) or ""
    for number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if line:
            yield number, line


def parse_food_line(line):
    """Parse ``Name: hunger, sanity, health`` into ``(name, stats)``."""
    name, rest = line.split(": ", 1)
    hunger, sanity, health = (float(value) for value in rest.split(", "))
    return name.strip(), (hunger, sanity, health)


def parse_recipe_line(line):
    """Parse ``Dish; conditions; excludes; priority`` into a 4-tuple."""
    fields = [field.strip() for field in line.split(";")]
    if len(fields) != 4:
        raise ValueError(f"expected 4 ';'-separated fields, got {len(fields)}")
    name, conditions, excludes, priority = fields
    return name, conditions, excludes, int(priority)


def parse_value_line(line):
    """Parse ``Ingredient: *Tag - weight, ...`` into ``(name, values)``."""
    name, rest = line.split(": ", 1)
    values = {}
    for chunk in rest.split(", "):
        tag, number = chunk.split(" - ")
        values[tag.strip()] = float(number)
    return name.strip(), values


def parse_cooked_line(line):
    """Parse ``Raw: Result`` into a ``(raw, result)`` pair."""
    raw, cooked = line.split(": ", 1)
    return raw.strip(), cooked.strip()


def _parse_file(file_name, mode="dst"):
    """Parse one data file (base or overlay) into ``(parser, container, records)``."""
    parsers = {
        "food.txt": (parse_food_line, dict),
        "over_time.txt": (parse_food_line, dict),
        "value.txt": (parse_value_line, dict),
        "recipes.txt": (parse_recipe_line, list),
        "warly_recipes.txt": (parse_recipe_line, list),
        "cooked_table.txt": (parse_cooked_line, dict),
        "dried_table.txt": (parse_cooked_line, dict),
    }
    try:
        parser, container = parsers[file_name]
    except KeyError:
        raise ValueError(f"Unsupported file type: {file_name}") from None

    label = file_name if mode == DEFAULT_MODE else f"{mode}/{file_name}"
    records = []
    for number, line in _lines(file_name, mode):
        try:
            records.append(parser(line))
        except ValueError as error:
            raise ValueError(f"{label}:{number}: {error}: {line!r}") from None
    return parser, container, records


def file_to_list(file_name, mode="dst"):
    """Load one of the data files into the structure the engine expects.

    * ``food.txt``         -> ``{name: (hunger, sanity, health)}``
    * ``over_time.txt``    -> ``{name: (hunger, sanity, health)}``
    * ``value.txt``        -> ``{ingredient: {tag: weight}}``
    * ``recipes.txt``      -> ``[(name, conditions, excludes, priority)]``
    * ``warly_recipes.txt``-> ``[(name, conditions, excludes, priority)]``
    * ``cooked_table.txt`` -> ``{raw: cooked}``
    * ``dried_table.txt``  -> ``{raw: dried}``

    With a non-default ``mode`` the matching overlay file from ``data/<mode>/``
    is merged in.  Dictionary files replace records by key; recipe files drop
    every base rule whose dish the overlay also defines and append the overlay
    rules, so a rebalanced dish does not keep its old DST rules.
    """
    mode = normalize_mode(mode)
    _, container, records = _parse_file(file_name, DEFAULT_MODE)
    base = container(records)
    if mode == DEFAULT_MODE:
        return base

    if not read_mode_file(file_name, mode):
        return base
    _, _, overlay = _parse_file(file_name, mode)
    if container is dict:
        merged = dict(base)
        merged.update(container(overlay))
        return merged

    replaced = {record[0] for record in overlay}
    kept = [record for record in base if record[0] not in replaced]
    return kept + list(overlay)
