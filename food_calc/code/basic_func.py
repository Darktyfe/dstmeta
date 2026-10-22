"""Parsing helpers for the DSTMeta food database.

Data files live in ``food_calc/data`` and are plain text with one record per
line.  Blank lines are ignored, so trailing newlines and spacing are harmless.

Record formats
--------------
food.txt     ``Name: hunger, sanity, health``
value.txt    ``Ingredient: *Tag - weight, *Tag - weight, ...``
recipes.txt  ``Dish; conditions; excludes; priority``

Conditions are ``<op> <number> <tag>`` separated by ``,`` (``>= 1.0 *Meat``).
Excludes are bare tags separated by ``,`` (``*Meat, Twigs``).  An empty field
means "none".
"""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def read_file(file_name):
    """Return the contents of a file from ``food_calc/data``."""
    with open(DATA_DIR / file_name, "r", encoding="utf-8") as file:
        return file.read()


def _lines(file_name):
    """Yield stripped, non-empty lines together with their 1-based numbers."""
    for number, line in enumerate(read_file(file_name).splitlines(), start=1):
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
    """Parse ``Raw: Cooked`` into a ``(raw, cooked)`` pair."""
    raw, cooked = line.split(": ", 1)
    return raw.strip(), cooked.strip()


def file_to_list(file_name):
    """Load one of the data files into the structure the engine expects.

    * ``food.txt``         -> ``{name: (hunger, sanity, health)}``
    * ``value.txt``        -> ``{ingredient: {tag: weight}}``
    * ``recipes.txt``      -> ``[(name, conditions, excludes, priority)]``
    * ``warly_recipes.txt``-> ``[(name, conditions, excludes, priority)]``
    * ``cooked_table.txt`` -> ``{raw: cooked}``
    """
    parsers = {
        "food.txt": (parse_food_line, dict),
        "value.txt": (parse_value_line, dict),
        "recipes.txt": (parse_recipe_line, list),
        "warly_recipes.txt": (parse_recipe_line, list),
        "cooked_table.txt": (parse_cooked_line, dict),
    }
    try:
        parser, container = parsers[file_name]
    except KeyError:
        raise ValueError(f"Unsupported file type: {file_name}") from None

    records = []
    for number, line in _lines(file_name):
        try:
            records.append(parser(line))
        except ValueError as error:
            raise ValueError(f"{file_name}:{number}: {error}: {line!r}") from None
    return container(records)
