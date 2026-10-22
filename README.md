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

Then open <http://127.0.0.1:8000>. Use `--port 8080` to change the port and
`--open` to launch the browser automatically. The page has the same options as
the CLI: choose `Hunger`, `Sanity` or `Health`, enable Warly's exclusive
recipes, and set permissible losses. Results are calculated by the Python
engine, so the page and the CLI always agree. To keep the exhaustive search
responsive, the web planner accepts up to 18 ingredients per calculation; the
CLI has no such limit.

## Usage

Requires Python 3.8+ (no third-party packages).

```bat
py food_calc\code\main.py Meat Berries Berries Berries
py food_calc\code\main.py --stat Sanity Ice Butter Honey Berries
py food_calc\code\main.py --warly Asparagus Asparagus Ice Ice
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
normal characters cannot cook. `--check` validates the data files and lists
gaps.

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

The output has three parts: every dish the ingredients can make (best first),
the best single dish, and the best plan for the whole inventory. The plan may
eat ingredients raw, roast them on a campfire first (for example `Carrot` ->
`Roasted Carrot`), keep ingredients that would hurt, or group four items into a
dish. It is an exhaustive search, so it finds the highest total for the chosen
stat rather than only the best single dish. When several raw/cooked variants
produce the same dish, the least-processed variant is preferred, so the planner
does not roast an ingredient before putting it in the pot unless doing so is
actually useful.

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
    main.py         command line interface
    test_alg.py     unit tests for the engine
  data/
    food.txt        food and dish stats
    value.txt       ingredient tags and weights
    recipes.txt     crockpot recipes
    cooked_table.txt  campfire raw -> cooked conversions
    warly_recipes.txt Warly's Portable Crock Pot recipes
site/
  index.html        calculator page
  styles.css        page theme
  app.js            form handling and result rendering
  server.py         local web server and JSON API
  test_site.py      tests for the website API
```

## Data format

`food.txt` — one food per line:

```
Meatballs: 62.5, 5, 3
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

Conditions are comma-separated `<op> <number> <tag>` and are summed over the
four slots. Supported operators: `>`, `>=`, `<`, `<=`, `==`, `=`. A recipe is
rejected when any slot has an excluded tag; the valid recipe with the highest
priority wins.

Tags in recipes may be categories (`*Meat`, `*Vegetable`), ingredient names
(`Honey`, `Twigs`) or starred ingredient names (`*Asparagus`). An ingredient
always matches its own name, and processing words (`Cooked`, `Roasted`,
`Prepared`, `Braised`, ...) are ignored for that match, so `*Asparagus`
matches `Cooked Asparagus`. `*Monster`, `*Monster Food` and `*Diary` are
accepted as aliases of `*Monster Meat` and `*Dairy`.

## Notes

* Permissible losses apply to the plan's final totals, not individual dishes.
  A dish may have a negative stat if the rest of the plan offsets it, and the
  whole result stays within the budget.
* Recipe selection models tags and priorities, not cooking time or freshness.
* Drying racks are not part of the search; `cooked_table.txt` only covers
  campfire cooking.
* A few recipes in the game have raw-only ingredient rules (for example Turkey
  Dinner). Those rules are not modelled; the engine treats cooked forms as
  interchangeable with their raw counterparts in the pot.
