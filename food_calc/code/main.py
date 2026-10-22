"""Command line front-end for the DSTMeta crockpot calculator.

Examples
--------
``py food_calc/code/main.py Meat Berries Berries Berries``
``py food_calc/code/main.py --stat Sanity Ice Butter Honey Berries``
``py food_calc/code/main.py --check``

Without ingredients the program asks for them interactively.
"""

import argparse
import sys

import alg


def get_user_food():
    """Read ingredients from stdin until ``done`` or end of input."""
    print("Enter food items one per line, then 'done':")
    food = []
    while True:
        try:
            item = input("> ").strip()
        except EOFError:
            break
        if not item:
            continue
        if item.lower() == "done":
            break
        food.append(item)
    return food


def resolve_names(names):
    """Map names to their canonical spelling and collect unknown ones."""
    resolved = []
    unknown = []
    for name in names:
        canonical = alg.resolve_food_name(name)
        if canonical is None:
            resolved.append(name)
            unknown.append(name)
        else:
            resolved.append(canonical)
    return resolved, unknown


def format_stats(dish):
    stats = alg.get_food_stats(dish)
    if stats is None:
        return "stats unknown"
    hunger, sanity, health = stats
    return f"hunger {hunger:g}, sanity {sanity:g}, health {health:g}"


def non_negative(text):
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a number") from None
    if value < 0:
        raise argparse.ArgumentTypeError("cannot be negative")
    return value


def run_check():
    warnings = alg.data_warnings()
    if not warnings:
        print("Data files look consistent.")
        return 0
    for warning in warnings:
        print(f"warning: {warning}")
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Work out what you can cook in a Don't Starve Together crockpot."
    )
    parser.add_argument(
        "ingredients",
        nargs="*",
        help="ingredients you own; omit to enter them interactively",
    )
    parser.add_argument(
        "--stat",
        choices=alg.STAT_NAMES,
        default="Hunger",
        help="stat to optimize (default: Hunger)",
    )
    parser.add_argument(
        "--warly",
        action="store_true",
        help="include Warly's Portable Crock Pot exclusive recipes",
    )
    parser.add_argument(
        "--loss-hunger",
        type=non_negative,
        default=0.0,
        metavar="N",
        help="allowed net hunger loss (default: 0)",
    )
    parser.add_argument(
        "--loss-sanity",
        type=non_negative,
        default=0.0,
        metavar="N",
        help="allowed net sanity loss (default: 0)",
    )
    parser.add_argument(
        "--loss-health",
        type=non_negative,
        default=0.0,
        metavar="N",
        help="allowed net health loss (default: 0)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the data files and exit",
    )
    args = parser.parse_args(argv)

    if args.check:
        return run_check()

    ingredients = args.ingredients or get_user_food()
    if not ingredients:
        print("No ingredients given.", file=sys.stderr)
        return 1

    ingredients, unknown = resolve_names(ingredients)
    for name in unknown:
        print(
            f"warning: {name!r} is not in the data files; "
            "it is used as a plain ingredient",
            file=sys.stderr,
        )

    dishes = alg.cookable_dishes(ingredients, args.warly)
    if not dishes:
        print("Nothing can be cooked from these ingredients.")
    else:
        ranking = sorted(
            dishes,
            key=lambda dish: (-alg.get_food_stat(dish, args.stat), dish),
        )
        print(f"Cookable dishes ({len(ranking)}):")
        for dish in ranking:
            score = alg.get_food_stat(dish, args.stat)
            print(
                f"  {dish}: {format_stats(dish)}"
                f"  [{args.stat.lower()} {score:g},"
                f" {len(dishes[dish])} combination(s)]"
            )

    best = alg.best_single_dish(ingredients, args.stat, args.warly)
    if best is not None:
        score, dish, combo = best
        print()
        print(
            f"Best single dish by {args.stat}: {dish} "
            f"({score:g}) from {', '.join(combo)}"
        )

    total, actions = alg.find_best_plan(
        ingredients,
        args.stat,
        args.warly,
        losses={
            "Hunger": args.loss_hunger,
            "Sanity": args.loss_sanity,
            "Health": args.loss_health,
        },
    )
    totals = alg.plan_totals(actions)
    print()
    print(f"Best plan by {args.stat} (total {total:g}):")
    for action in actions:
        if action[0] == "keep":
            print(f"  {alg.describe_action(action)} (not eaten)")
        elif action[0] == "prep":
            print(f"  {alg.describe_action(action)}")
        else:
            print(f"  {alg.describe_action(action)}: {format_stats(action[2])}")
    print(
        "  totals: "
        + ", ".join(f"{stat.lower()} {value:g}" for stat, value in totals.items())
    )
    print(
        "  allowed loss: "
        + ", ".join(
            f"{stat.lower()} {value:g}"
            for stat, value in (
                ("Hunger", args.loss_hunger),
                ("Sanity", args.loss_sanity),
                ("Health", args.loss_health),
            )
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
