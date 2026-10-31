"""Small local web server for the DSTMeta calculator.

Run from the repository root:

    py site/server.py

The server uses only the Python standard library and reuses the engine in
``food_calc/code`` so the CLI and the site always agree.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent
CODE_DIR = ROOT.parent / "food_calc" / "code"
sys.path.insert(0, str(CODE_DIR))

import alg  # noqa: E402  (path is set up above)
import cpp_engine  # noqa: E402

MAX_INGREDIENTS = 100
MAX_INGREDIENT_TYPES = 24
MAX_BODY_BYTES = 1_000_000
MAX_DISHES = 80
STAT_KEYS = alg.STAT_NAMES

NAMES_RU_PATH = ROOT / "names_ru.json"

MESSAGES = {
    "en": {
        "errNoIngredients": "Add at least one ingredient.",
        "errBadIngredients": "ingredients must be text or a list of names",
        "errTooMany": "Too many ingredients for one plan (max {max}).",
        "errTooManyKinds": (
            "Too many different ingredients for one plan "
            "(max {max} kinds, got {kinds})."
        ),
        "errStat": "stat must be one of {stats}",
        "errBadMode": "mode must be \"dst\" or \"uc\"",
        "errUnknownOne": (
            "{name!r} is not a food and should be removed from the ingredient "
            "list."
        ),
        "errUnknownMany": (
            "{names} are not foods and should be removed from the ingredient "
            "list."
        ),
        "errBadRequest": "request body must be a JSON object",
        "errBadBody": "Invalid request body.",
        "errUnexpected": "The calculator hit an unexpected error.",
        "errNotFound": "Not found.",
    },
    "ru": {
        "errNoIngredients": "Сначала добавьте хотя бы один ингредиент.",
        "errBadIngredients": (
            "Ингредиенты должны быть текстом или списком названий."
        ),
        "errTooMany": (
            "Слишком много ингредиентов для одного плана (максимум {max})."
        ),
        "errTooManyKinds": (
            "Слишком много разных ингредиентов для одного плана "
            "(максимум {max} видов, получено {kinds})."
        ),
        "errStat": "Характеристика должна быть одной из: {stats}.",
        "errBadMode": "Режим должен быть «dst» или «uc».",
        "errUnknownOne": (
            "«{name}» — не еда. Уберите его из списка ингредиентов."
        ),
        "errUnknownMany": (
            "Не еда: {names}. Уберите их из списка ингредиентов."
        ),
        "errBadRequest": "тело запроса должно быть JSON-объектом",
        "errBadBody": "Некорректный запрос.",
        "errUnexpected": "В калькуляторе произошла непредвиденная ошибка.",
        "errNotFound": "Не найдено.",
    },
}


def normalize_lang(value):
    """Return the interface language used for error messages."""
    if isinstance(value, str) and value.lower().startswith("ru"):
        return "ru"
    return "en"


def message(lang, key, **values):
    """Return a localized server message."""
    text = MESSAGES.get(lang, MESSAGES["en"]).get(key, MESSAGES["en"][key])
    return text.format(**values) if values else text


def load_ru_names():
    """Load the English-to-Russian food names served to the browser."""
    try:
        data = json.loads(NAMES_RU_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {
        str(name): str(translated)
        for name, translated in data.items()
        if name and translated
    }


RU_NAMES = load_ru_names()


def ru_key(name):
    """Normalize a Russian food name for lookup (ё and case insensitive)."""
    return " ".join(str(name).strip().casefold().replace("ё", "е").split())


RU_LOOKUP = {ru_key(translated): name for name, translated in RU_NAMES.items()}


def parse_ingredients(value, lang="en"):
    """Accept a newline/comma separated string or a list of names."""
    if isinstance(value, str):
        chunks = value.replace(",", "\n").splitlines()
    elif isinstance(value, list):
        chunks = [str(item) for item in value]
    else:
        raise ValueError(message(lang, "errBadIngredients"))

    names = [chunk.strip() for chunk in chunks if chunk.strip()]
    if not names:
        raise ValueError(message(lang, "errNoIngredients"))
    if len(names) > MAX_INGREDIENTS:
        raise ValueError(message(lang, "errTooMany", max=MAX_INGREDIENTS))
    return names


def check_ingredient_types(names, lang="en"):
    """Reject inventories with more kinds than the planner handles quickly."""
    kinds = len(set(names))
    if kinds > MAX_INGREDIENT_TYPES:
        raise ValueError(
            message(
                lang,
                "errTooManyKinds",
                max=MAX_INGREDIENT_TYPES,
                kinds=kinds,
            )
        )


def resolve_names(names, mode=alg.DEFAULT_MODE):
    """Return canonical names and a list of names the data files do not know."""
    resolved = []
    unknown = []
    for name in names:
        canonical = alg.resolve_food_name(name, mode)
        if canonical is None:
            translated = RU_LOOKUP.get(ru_key(name))
            if translated is not None:
                canonical = alg.resolve_food_name(translated, mode)
        if canonical is None:
            resolved.append(name)
            unknown.append(name)
        else:
            resolved.append(canonical)
    return resolved, unknown


def stats_dict(name, over_time=True, mode=alg.DEFAULT_MODE):
    stats = alg.get_food_stats(name, over_time, mode)
    if stats is None:
        return {stat: 0.0 for stat in STAT_KEYS}
    return {stat: float(value) for stat, value in zip(STAT_KEYS, stats)}


def action_dict(action, over_time=True, mode=alg.DEFAULT_MODE):
    kind, source, target = action
    result = {
        "kind": kind,
        "description": alg.describe_action(action),
        "food": target,
        "stats": stats_dict(target, over_time, mode),
    }
    if kind == "cook":
        result["ingredients"] = list(source)
    elif kind in ("roast", "dry"):
        result["source"] = source
    return result


def dish_dict(dish, combo, score, over_time=True, mode=alg.DEFAULT_MODE):
    return {
        "name": dish,
        "stats": stats_dict(dish, over_time, mode),
        "score": float(score),
        "combination": list(combo),
    }


def calculate(payload):
    """Run one calculation and return JSON-serialisable results."""
    if not isinstance(payload, dict):
        raise ValueError(message("en", "errBadRequest"))
    lang = normalize_lang(payload.get("lang"))
    try:
        mode = alg.get_mode(payload.get("mode"))
    except ValueError:
        raise ValueError(message(lang, "errBadMode")) from None
    names = parse_ingredients(payload.get("ingredients", ""), lang)
    stat = payload.get("stat", "Hunger")
    if stat not in STAT_KEYS:
        raise ValueError(message(lang, "errStat", stats=", ".join(STAT_KEYS)))
    warly = bool(payload.get("warly", False))
    # The site checkboxes are "Ignore Dried variants", "Ignore Milkmade Hat"
    # and "Ignore over time stats"; all three default to on.
    dried = not bool(payload.get("ignoreDried", True))
    milkmade = not bool(payload.get("ignoreMilkmade", True))
    over_time = not bool(payload.get("ignoreOverTime", True))
    losses = alg.normalize_losses(payload.get("losses"))

    ingredients, unknown = resolve_names(names, mode)
    if unknown:
        if lang == "ru":
            unique = list(dict.fromkeys(unknown))
            if len(unique) == 1:
                raise ValueError(message("ru", "errUnknownOne", name=unique[0]))
            quoted = ", ".join(f"«{name}»" for name in unique)
            raise ValueError(message("ru", "errUnknownMany", names=quoted))
        raise ValueError(alg.unknown_food_message(unknown))
    check_ingredient_types(ingredients, lang)
    exact = not alg.needs_fast_plan(ingredients)

    total, actions = alg.find_best_plan(
        ingredients, stat, warly, losses=losses, dried=dried,
        over_time=over_time, milkmade=milkmade, mode=mode,
    )
    totals = {
        key: float(value)
        for key, value in alg.plan_totals(actions, over_time, mode).items()
    }

    dishes = []
    if len(ingredients) >= alg.SLOTS:
        cooked = alg.cookable_dishes(
            ingredients, warly, dried, milkmade, mode=mode
        )
        for dish, combinations in cooked.items():
            score = alg.get_food_stat(dish, stat, over_time, mode)
            dishes.append(
                dish_dict(dish, combinations[0], score, over_time, mode)
            )
        dishes.sort(key=lambda item: (-item["score"], item["name"]))
    total_dishes = len(dishes)
    dishes = dishes[:MAX_DISHES]

    best_dish = None
    if dishes:
        top = dishes[0]
        best_dish = {
            "name": top["name"],
            "stats": top["stats"],
            "score": top["score"],
            "combination": top["combination"],
        }

    return {
        "ingredients": ingredients,
        "stat": stat,
        "lang": lang,
        "mode": mode,
        "warly": warly,
        "dried": dried,
        "milkmade": milkmade,
        "overTime": over_time,
        "losses": losses,
        "engine": cpp_engine.engine_name() if exact else "Python",
        "exact": exact,
        "total": float(total),
        "totals": totals,
        "plan": [action_dict(action, over_time, mode) for action in actions],
        "bestDish": best_dish,
        "dishes": dishes,
        "totalDishes": total_dishes,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "DSTMeta/0.6"

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/health":
            self.send_json(HTTPStatus.OK, {"status": "ok"})
            return
        if path == "/api/foods":
            query = parse_qs(parsed.query)
            try:
                mode = alg.get_mode(query.get("mode", [alg.DEFAULT_MODE])[0])
            except ValueError:
                self.send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": message("en", "errBadMode")},
                )
                return
            self.send_json(
                HTTPStatus.OK,
                {
                    "mode": mode,
                    "foods": alg.picker_foods(mode),
                    "stats": list(STAT_KEYS),
                    "maxIngredients": MAX_INGREDIENTS,
                    "maxIngredientTypes": MAX_INGREDIENT_TYPES,
                },
            )
            return
        if path in ("", "/"):
            path = "/index.html"
        self.serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        lang = normalize_lang(query.get("lang", ["en"])[0])
        if parsed.path != "/api/calculate":
            self.send_json(
                HTTPStatus.NOT_FOUND, {"error": message(lang, "errNotFound")}
            )
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY_BYTES:
            self.send_json(
                HTTPStatus.BAD_REQUEST, {"error": message(lang, "errBadBody")}
            )
            return

        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if isinstance(payload, dict):
                lang = normalize_lang(payload.get("lang"))
            result = calculate(payload)
        except ValueError as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        except Exception as error:  # pragma: no cover - defensive
            self.log_error("calculation failed: %s", error)
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": message(lang, "errUnexpected")},
            )
            return

        self.send_json(HTTPStatus.OK, result)

    def serve_static(self, path):
        relative = path.lstrip("/")
        candidate = (ROOT / relative).resolve()
        if ROOT not in candidate.parents or candidate.name == "server.py":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return
        if not candidate.is_file():
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return

        content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
        if candidate.suffix == ".js":
            content_type = "text/javascript; charset=utf-8"
        elif candidate.suffix in (".html", ".css"):
            content_type += "; charset=utf-8"

        body = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))


def main():
    global MAX_INGREDIENTS, MAX_INGREDIENT_TYPES
    parser = argparse.ArgumentParser(description="Run the DSTMeta website.")
    parser.add_argument("--host", default="127.0.0.1", help="interface to bind")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on")
    parser.add_argument(
        "--max-ingredients",
        type=int,
        default=MAX_INGREDIENTS,
        metavar="N",
        help=(
            "ingredients accepted per calculation (default: %(default)s); "
            "large plans take much longer to search"
        ),
    )
    parser.add_argument(
        "--max-types",
        type=int,
        default=MAX_INGREDIENT_TYPES,
        metavar="N",
        help=(
            "different ingredient kinds accepted per calculation "
            "(default: %(default)s)"
        ),
    )
    parser.add_argument("--open", action="store_true", help="open the page in a browser")
    args = parser.parse_args()

    if args.max_ingredients < 1:
        parser.error("--max-ingredients must be at least 1")
    if args.max_types < 1:
        parser.error("--max-types must be at least 1")
    MAX_INGREDIENTS = args.max_ingredients
    MAX_INGREDIENT_TYPES = args.max_types

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"DSTMeta is running at {url}")
    print("Press Ctrl+C to stop.")
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
