# DSTMeta

A Don't Starve Together food calculator. It tells you which crockpot dishes a
set of ingredients can produce, what those dishes restore, and which
combination is best for a chosen stat. It comes as a command line tool and as
a small local website.

## Web interface

The site lives in `site/` and reuses the same engine as the CLI. It needs only
Python 3.8+:

```bat
py site\server.py
```

On Windows you can also double-click `start.bat`, which runs the server with
`--open` and stops on an error instead of closing the window.

Then open <http://127.0.0.1:8000>. Use `--port 8080` to change the port and
`--open` to launch the browser automatically. The page has the same options as
the CLI: choose `Hunger`, `Sanity` or `Health`, enable Warly's exclusive
recipes, turn drying-rack variants on or off, ignore the Milkmade Hat, ignore
stats that are restored over time, and set permissible losses. The web planner
accepts up to 100 ingredients made of at most 24 different kinds per
calculation; raise those limits with `--max-ingredients N` and `--max-types N`.
The CLI has no caps. `GET /health` answers `{"status": "ok"}` for local
monitors and extensions that probe the server.

### Ingredient picker

Instead of typing a list, click the food icons in the picker (the same idea as
the Russian wiki's interactive crockpot). Each click adds one item, the count
appears in the tile, and the search box filters the grid. The picker is a flat
grid with no categories.

The picker offers only crockpot ingredients: foods with an entry in
`food_calc/data/value.txt`. Prepared dishes, gears, wet goop and other trinkets
that cannot be cooked, fried or dried stay out of the menu even though the CLI
still knows them. The tiles follow the food-value order of the DST wiki
(<https://dontstarve.wiki.gg/wiki/Food_Value/DST>): meat, monster meat, fish,
fruit, vegetable, egg, sweetener, dairy, frozen, inedible, decoration, fat,
magic and seed value, lightest first. That order lives in
`food_calc/data/picker_order.txt`; an ingredient missing from that file is
appended alphabetically instead of disappearing.

The icons are trimmed 64×64 PNGs downloaded from the Don't Starve wiki and
committed under `site/icons/`. `GET /api/foods` returns the ordered list:

```json
{
  "foods": ["Barnacles", "Cooked Barnacles", "Morsel", "Cooked Morsel"],
  "maxIngredients": 100,
  "maxIngredientTypes": 24
}
```

To refresh icons after changing the food data, run
`py tools\fetch_food_icons.py` (it needs Pillow). Most icons come from the
Fandom wiki; the handful where it has no picture or the wrong one (Heat Gland,
Cooked Heat Gland, Wobster, the fishy jerkies, Dark Petals and the dried
flowers and foliage) are fetched from wiki.gg via `DIRECT_ICONS`.

### Languages

The header has an `EN` / `RU` switch. It remembers the choice in
`localStorage`; a first visit follows the browser language. The interface
strings live in `site/i18n.js`, and `site/names_ru.json` maps every food name
to its Russian name. Russian names come from the Russian Don't Starve wiki
(<https://dont-starve.fandom.com/ru>), with the game's official translation
used as a fallback where the wiki has no separate page.

The API keeps canonical English names. The browser translates names for
display, while the server also accepts Russian ingredient names (with or
without `ё`) and maps them back to English before planning:

```json
{"ingredients": "Мясо\nМясо\nМясо\nЛёд", "stat": "Hunger", "lang": "ru"}
```

Passing `"lang": "ru"` also localizes validation errors returned by
`/api/calculate`. Omitting `lang` keeps the English API behaviour.

## Usage

Requires Python 3.8+ (no third-party packages).

```bat
py food_calc\code\main.py Meat Berries Berries Berries
py food_calc\code\main.py --stat Sanity Ice Butter Honey Berries
py food_calc\code\main.py --warly Asparagus Asparagus Ice Ice
py food_calc\code\main.py --dried --stat Sanity Meat Meat Meat Meat
py food_calc\code\main.py --check
```

Without arguments the program asks for ingredients one per line and stops at
`done`. When passing names with spaces as command line arguments, quote them
(`py food_calc\code\main.py "Monster Meat" "Monster Meat" Ice Ice`).

```bat
py food_calc\code\main.py
```

`--stat` chooses the stat to optimize (`Hunger`, `Sanity` or `Health`, default
`Hunger`). `--warly` adds Warly's Portable Crock Pot exclusive recipes, which
normal characters cannot cook. `--dried` adds drying-rack variants such as
`Meat` -> `Jerky` and `Kelp Fronds` -> `Dried Kelp Fronds`; it is off by
default because a rack is much slower than a campfire. On the site the same
option is the **Ignore Dried variants** switch, which starts enabled.
`--over-time` counts the part of a food's stats that is restored gradually
(for example 30 of Soothing Tea's 45 sanity or 120 of Jellybeans' 122 health);
by default only the stats given on the first bite are counted. `--milkmade`
allows the Milkmade Hat, which is worn as a hat instead of eaten; by default it
is ignored. On the site these are the **Ignore over time stats** and **Ignore
Milkmade Hat** switches, both starting enabled. `--check` validates the data
files and lists gaps.

`--loss-hunger`, `--loss-sanity` and `--loss-health` set the permissible net
loss for each stat (default `0`). A plan is only considered if its final totals
stay at or above the negative of these limits, so the defaults forbid any net
loss:

```bat
py food_calc\code\main.py --warly --loss-sanity 20 --loss-health 20 --stat Hunger "Monster Meat" "Monster Meat" Ice Ice
```

That allows Monster Tartare's `62.5` hunger despite its `-20` sanity and
health. With the default zero losses the same ingredients instead plan to eat
the ice and keep the monster meat, because no net-loss plan is allowed.

Unknown ingredient names are rejected with a hint to remove them instead of
being silently treated as filler. This catches typos and foods that are not in
the data files.

The output has three parts: every dish the ingredients can make (best first),
the best single dish, and the best plan for the whole inventory. The plan may
eat ingredients raw, roast them on a campfire first (for example `Carrot` ->
`Roasted Carrot`), dry them on a rack when `--dried` is enabled, keep
ingredients that would hurt, or group four items into a dish. For small and
duplicate-heavy inventories it is an exhaustive search, so it finds the highest
total for the chosen stat rather than only the best single dish. Very large
mixed inventories switch to a beam search that answers in a couple of seconds
but may miss the exact optimum (see below).

When several raw/cooked/dried variants produce the same dish, the
least-processed variant is preferred, so the planner does not roast or dry an
ingredient before putting it in the pot unless doing so is actually useful.
Pot results only depend on the tags a recipe can observe, so a variant whose
recipe-relevant tags are identical to the raw form is not tried in the pot at
all. Drying usually does not change crockpot values, so Jerky is used as a
snack and the raw meat is still used for cooking. Dried forms that really do
cook differently stay available: for example `Kelp Fronds` and `Drumstick`
are named in some recipes and their dried forms cannot replace them, while
drying an `Eel` lowers its fish value.

## The plan engine: C++ with Python fallback

The exhaustive plan search is ported to C++ in
`food_calc/native/engine.cpp` and ships compiled as
`food_calc/native/engine.dll` (Windows). The Python code in `alg.py` builds
one flat "task" per calculation (every useful pot combination with its dish
stats, plus the campfire options) and hands it to the library through
`food_calc/code/cpp_engine.py`; all recipe and tag logic stays in Python, so
the C++ side is only the heavy search. Both engines implement the same
algorithm with the same tie-breaking, and a dedicated test class compares
their plans on a mix of inventories.

If the library is missing or a task exceeds the native engine's limits (48
ingredient kinds, 255 copies of one kind, 1024 items overall), the program
falls back to the pure Python engine — same results, just slower.

The exact search keeps every nondominated plan for every count vector, so its
work grows with the product of `(count + 1)` over the ingredient kinds. Above
2,000,000 such states the planner switches to a beam search over pot groups:
it keeps the most promising partial plans, finishes each one with the leftover
items, and returns a valid plan without waiting for the exact answer. A typical
early-game backpack (about 75–80 items in 10 kinds) takes around a second;
24 different kinds take around ten seconds. The site marks such results as
`beam search (approximate)` in the Plan card and the plan summary, and the CLI
prints a note.

Rough wall-clock times for the worst case (20+ distinct ingredients), from
the current native engine and the fast planner:

|   | 18 distinct | 20 distinct | 22 distinct | 24 distinct |
|---|-------------|-------------|-------------|-------------|
| Exact search | ~2.5 s | ~6 s | too large | too large |
| Fast planner | not used | not used | ~7.5 s | ~11 s |

The site caps inputs at 100 items and 24 kinds so a request still finishes
within seconds. The optional drying search adds a few individual options per
ingredient and a handful of extra pot variants where drying changes a
recipe-relevant tag, so it stays in the same range.

Rebuilding the library needs any C++17 compiler:

```bat
py tools\fetch_compiler.py
py tools\build_engine.py
```

`fetch_compiler.py` downloads a portable MinGW-w64 (GCC 16.2) into
`tools/mingw64/` — only needed when no compiler is installed; it is ignored by
git. On Unix-like systems any `g++` works; the loader picks up
`libengine.so`/`libengine.dylib` from the same folder. Delete
`food_calc/native/engine.*` to force the Python engine (or set
`alg._USE_NATIVE = False` in code/tests).

## Tests

```bat
py food_calc\code\test_alg.py
py site\test_site.py
```

## Layout

```
food_calc/
  code/
    basic_func.py   parsing of the data files
    alg.py          tag matching, recipe selection, search
    cpp_engine.py   ctypes loader for the native engine
    main.py         command line interface
    test_alg.py     unit tests for the engine
  native/
    engine.cpp      C++ port of the plan search
    engine.dll      compiled library (Windows); libengine.so / libengine.dylib
  data/
    food.txt        food and dish stats
    value.txt       ingredient tags and weights
    recipes.txt     crockpot recipes
    cooked_table.txt  campfire raw -> cooked conversions
    dried_table.txt   drying rack raw -> dried conversions
    over_time.txt     gradual part of a food's stats
    warly_recipes.txt Warly's Portable Crock Pot recipes
    picker_order.txt  ingredient order used by the website picker
site/
  index.html        calculator page
  styles.css        page theme
  app.js            form handling and result rendering
  i18n.js           English and Russian interface strings
  names_ru.json     English-to-Russian food names
  icons/            64x64 ingredient icons for the picker
  server.py         local web server and JSON API
  test_site.py      tests for the website API
tools/
  build_engine.py   compile food_calc/native/engine.cpp
  fetch_compiler.py download a portable MinGW-w64 g++ (Windows)
  fetch_food_icons.py download the picker icons from the Don't Starve wiki
```

## Data format

`food.txt` — one food per line:

```
Meatballs: 62.5, 5, 3
```

`over_time.txt` — the part of those stats that is restored (or drained)
gradually instead of on the first bite, same three values per line. Most foods
are not listed:

```
Jellybeans: 0, 0, 120
Soothing Tea: 0, 30, 0
Milkmade Hat: 187.5, -5.3, 0
```

`value.txt` — ingredient tags; the weight is how much one item contributes:

```
Meat: *Meat - 1
Barnacles: *Meat - 0.25, *Fish - 0.25
```

`recipes.txt` — dish, conditions, excluded tags, priority:

```
Meatballs; > 0 *Meat; *Inedible; -1
```

`warly_recipes.txt` uses the same format; those recipes are only used with
`--warly`.

`cooked_table.txt` — raw food and its campfire-cooked form:

```
Carrot: Roasted Carrot
Corn: Popcorn
Meat: Cooked Meat
```

`dried_table.txt` uses the same format for drying-rack conversions:

```
Meat: Jerky
Monster Meat: Monster Jerky
Raw Fish: Fishy Jerky
Kelp Fronds: Dried Kelp Fronds
```

Conditions are comma-separated `<op> <number> <tag>` and are summed over the
four slots. Supported operators: `>`, `>=`, `<`, `<=`, `==`, `=`. A recipe is
rejected when any slot has an excluded tag; the valid recipe with the highest
priority wins.

Tags in recipes may be categories (`*Meat`, `*Vegetable`), ingredient names
(`Honey`, `Twigs`) or starred ingredient names (`*Asparagus`). An ingredient
always matches its own name, and processing words (`Cooked`, `Roasted`,
`Prepared`, `Braised`, ...) are ignored for that match, so `*Asparagus`
matches `Cooked Asparagus`. Prefixing a name with `!` turns that off and only
matches the raw item, which is what the game does for recipes such as Turkey
Dinner:

```
Turkey Dinner; >= 2.0 !Drumstick, > 1.0 *Meat, >= 0.5 *Fruit; ; 10
```

`*Monster`, `*Monster Food` and `*Diary` are accepted as aliases of
`*Monster Meat` and `*Dairy`.

## Notes

* Permissible losses apply to the plan's final totals, not individual dishes.
  A dish may have a negative stat if the rest of the plan offsets it, and the
  whole result stays within the budget.
* Recipe selection models tags and priorities, not cooking time or freshness.
* Drying-rack times are therefore ignored; `--dried` only adds the dried food
  as an option.
* Stats restored over time are not stacking effects: eating several Jellybeans
  does not heal more than one. By default the planner counts only the stats a
  food gives on the first bite; enable over-time stats to count the full value
  from `food.txt`.
* The Milkmade Hat is cooked in the pot but worn as a hat, so it is ignored by
  default. `--milkmade` treats it as an ordinary dish.
* Grim Galette swaps the eater's health and sanity percentages, which the
  additive stat model cannot express; only its flat stats are used.
* Turkey Dinner is the raw-only rule the engine models: `!Drumstick` in
  `recipes.txt` makes Fried Drumsticks fall through to Meatballs. Other
  raw-only rules in the game are not modelled, so there the engine treats
  cooked forms as interchangeable with their raw counterparts in the pot.
