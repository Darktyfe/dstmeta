"""Command line front-end for the DSTMeta crockpot calculator.

Examples
--------
``py food_calc/code/main.py Meat Berries Berries Berries``
``py food_calc/code/main.py --stat Sanity Ice Butter Honey Berries``
``py food_calc/code/main.py --dried --stat Sanity Meat Meat Meat Meat``
``py food_calc/code/main.py --mode uc Boomberry Boomberry Egg Egg``
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


def resolve_names(names, mode=alg.DEFAULT_MODE):
    """Map names to their canonical spelling and collect unknown ones."""
    resolved = []
    unknown = []
    for name in names:
        canonical = alg.resolve_food_name(name, mode)
        if canonical is None:
            resolved.append(name)
            unknown.append(name)
        else:
            resolved.append(canonical)
    return resolved, unknown


def format_stats(dish, over_time=True, mode=alg.DEFAULT_MODE):
    stats = alg.get_food_stats(dish, over_time, mode)
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


def run_check(mode=alg.DEFAULT_MODE):
    warnings = alg.data_warnings(mode)
    if not warnings:
        print(f"Data files look consistent ({alg.get_mode(mode)} mode).")
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
        "--mode",
        choices=alg.MODES,
        default=alg.DEFAULT_MODE,
        help="game data to use (default: dst; uc adds Uncompromising Mode)",
    )
    parser.add_argument(
        "--warly",
        action="store_true",
        help="include Warly's Portable Crock Pot exclusive recipes",
    )
    parser.add_argument(
        "--dried",
        action="store_true",
        help="use drying-rack variants (Jerky, dried kelp, ...)",
    )
    parser.add_argument(
        "--over-time",
        action="store_true",
        help="count stats a food gives gradually (Soothing Tea, Jellybeans, ...)",
    )
    parser.add_argument(
        "--milkmade",
        action="store_true",
        help="allow the Milkmade Hat, which is worn rather than eaten",
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
        return run_check(args.mode)

    ingredients = args.ingredients or get_user_food()
    ingredients, unknown = resolve_names(ingredients, args.mode)
    if unknown:
        print(f"error: {alg.unknown_food_message(unknown)}", file=sys.stderr)
        return 1

    if len(ingredients) < alg.SLOTS:
        print(
            f"Need at least {alg.SLOTS} ingredients to fill the crockpot, "
            f"got {len(ingredients)}.",
            file=sys.stderr,
        )
        return 1

    dishes = alg.cookable_dishes(
        ingredients, args.warly, args.dried, args.milkmade, args.mode
    )
    if not dishes:
        print("Nothing can be cooked from these ingredients.")
    else:
        ranking = sorted(
            dishes,
            key=lambda dish: (
                -alg.get_food_stat(dish, args.stat, args.over_time, args.mode),
                dish,
            ),
        )
        print(f"Cookable dishes ({len(ranking)}):")
        for dish in ranking:
            score = alg.get_food_stat(
                dish, args.stat, args.over_time, args.mode
            )
            print(
                f"  {dish}: {format_stats(dish, args.over_time, args.mode)}"
                f"  [{args.stat.lower()} {score:g},"
                f" {len(dishes[dish])} combination(s)]"
            )

    best = alg.best_single_dish(
        ingredients, args.stat, args.warly, args.dried,
        args.over_time, args.milkmade, args.mode,
    )
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
        dried=args.dried,
        over_time=args.over_time,
        milkmade=args.milkmade,
        mode=args.mode,
    )
    totals = alg.plan_totals(actions, args.over_time, args.mode)
    print()
    if alg.needs_fast_plan(ingredients):
        print(
            "note: this inventory is too large for the exhaustive search; "
            "the plan comes from the fast beam search and may miss the "
            "exact optimum."
        )
    print(f"Best plan by {args.stat} (total {total:g}):")
    for action in actions:
        if action[0] == "keep":
            print(f"  {alg.describe_action(action)} (not eaten)")
        elif action[0] in ("prep", "kill"):
            print(f"  {alg.describe_action(action)}")
        else:
            print(
                f"  {alg.describe_action(action)}: "
                f"{format_stats(action[2], args.over_time, args.mode)}"
            )
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
