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
from urllib.parse import urlparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent
CODE_DIR = ROOT.parent / "food_calc" / "code"
sys.path.insert(0, str(CODE_DIR))

import alg  # noqa: E402  (path is set up above)

MAX_INGREDIENTS = 18
MAX_BODY_BYTES = 1_000_000
MAX_DISHES = 80
STAT_KEYS = alg.STAT_NAMES


def parse_ingredients(value):
    """Accept a newline/comma separated string or a list of names."""
    if isinstance(value, str):
        chunks = value.replace(",", "\n").splitlines()
    elif isinstance(value, list):
        chunks = [str(item) for item in value]
    else:
        raise ValueError("ingredients must be text or a list of names")

    names = [chunk.strip() for chunk in chunks if chunk.strip()]
    if not names:
        raise ValueError("Add at least one ingredient.")
    if len(names) > MAX_INGREDIENTS:
        raise ValueError(
            f"Too many ingredients for one plan (max {MAX_INGREDIENTS})."
        )
    return names


def resolve_names(names):
    """Return canonical names and a list of names the data files do not know."""
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


def stats_dict(name):
    stats = alg.get_food_stats(name)
    if stats is None:
        return {stat: 0.0 for stat in STAT_KEYS}
    return {stat: float(value) for stat, value in zip(STAT_KEYS, stats)}


def action_dict(action):
    kind, source, target = action
    result = {
        "kind": kind,
        "description": alg.describe_action(action),
        "food": target,
        "stats": stats_dict(target),
    }
    if kind == "cook":
        result["ingredients"] = list(source)
    elif kind == "roast":
        result["source"] = source
    return result


def dish_dict(dish, combo, score):
    return {
        "name": dish,
        "stats": stats_dict(dish),
        "score": float(score),
        "combination": list(combo),
    }


def calculate(payload):
    """Run one calculation and return JSON-serialisable results."""
    names = parse_ingredients(payload.get("ingredients", ""))
    stat = payload.get("stat", "Hunger")
    if stat not in STAT_KEYS:
        raise ValueError(f"stat must be one of {', '.join(STAT_KEYS)}")
    warly = bool(payload.get("warly", False))
    losses = alg.normalize_losses(payload.get("losses"))

    ingredients, unknown = resolve_names(names)
    total, actions = alg.find_best_plan(
        ingredients, stat, warly, losses=losses
    )
    totals = {key: float(value) for key, value in alg.plan_totals(actions).items()}

    dishes = []
    if len(ingredients) >= alg.SLOTS:
        cooked = alg.cookable_dishes(ingredients, warly)
        for dish, combinations in cooked.items():
            score = alg.get_food_stat(dish, stat)
            dishes.append(dish_dict(dish, combinations[0], score))
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
        "unknown": unknown,
        "stat": stat,
        "warly": warly,
        "losses": losses,
        "total": float(total),
        "totals": totals,
        "plan": [action_dict(action) for action in actions],
        "bestDish": best_dish,
        "dishes": dishes,
        "totalDishes": total_dishes,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "DSTMeta/0.6"

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/foods":
            self.send_json(
                HTTPStatus.OK,
                {"foods": alg.known_foods(), "stats": list(STAT_KEYS)},
            )
            return
        if path in ("", "/"):
            path = "/index.html"
        self.serve_static(path)

    def do_POST(self):
        if urlparse(self.path).path != "/api/calculate":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY_BYTES:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid request body."})
            return

        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = calculate(payload)
        except ValueError as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        except Exception as error:  # pragma: no cover - defensive
            self.log_error("calculation failed: %s", error)
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "The calculator hit an unexpected error."},
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
    parser = argparse.ArgumentParser(description="Run the DSTMeta website.")
    parser.add_argument("--host", default="127.0.0.1", help="interface to bind")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on")
    parser.add_argument("--open", action="store_true", help="open the page in a browser")
    args = parser.parse_args()

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
