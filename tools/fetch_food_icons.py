"""Download the crockpot ingredient icons used by the site picker.

The icons come from the Don't Starve wiki (the same source as the food data).
They are trimmed, squared and scaled to 64x64 so every tile in the picker has
the same visual weight.  The result is committed under ``site/icons``; running
this script is only necessary when a food is added or an icon looks wrong.

Most icons come from the Fandom wiki.  A handful of items only have a usable
picture on wiki.gg, so ``DIRECT_ICONS`` points at those images explicitly.

Usage::

    py tools/fetch_food_icons.py
    py tools/fetch_food_icons.py --force Meat Ice
    py tools/fetch_food_icons.py --mode uc --force

Only the standard library and Pillow are required.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "food_calc" / "code"))

import alg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = ROOT / "site" / "icons"
API = "https://dontstarve.fandom.com/api.php"
USER_AGENT = "DSTMeta/0.1 (local food planner; icon downloader)"
SIZE = 64
BATCH = 40

# The wiki does not always use the in-game spelling for the icon file.
WIKI_ALIASES = {
    "Crop Seeds": "Crop Seeds Animated",
    "Roasted Garlic": "Roast Garlic",
    "Roasted Onion": "Roast Onion",
    "Roasted Toma Root": "Roast Toma Root",
}

# Icons taken straight from wiki.gg.  Either the Fandom wiki has no picture for
# the item, or its picture is the wrong one (Small Fishy Jerky vs Small Jerky,
# for example), so these URLs win over the Fandom lookup.
DIRECT_ICONS = {
    "Cooked Heat Gland": "https://dontstarve.wiki.gg/images/Cooked_Heat_Gland.png",
    "Dark Petals": "https://dontstarve.wiki.gg/images/Dark_Petals.png",
    "Dried Dark Petals": "https://dontstarve.wiki.gg/images/Dried_Dark_Petals.png",
    "Dried Fire Nettle Frond": "https://dontstarve.wiki.gg/images/Dried_Fire_Nettle_Frond.png",
    "Dried Foliage": "https://dontstarve.wiki.gg/images/Dried_Foliage.png",
    "Dried Forget-Me-Lots": "https://dontstarve.wiki.gg/images/Dried_Forget-Me-Lots.png",
    "Dried Lune Tree Blossom": "https://dontstarve.wiki.gg/images/Dried_Lune_Tree_Blossom.png",
    "Dried Petals": "https://dontstarve.wiki.gg/images/Dried_Petals.png",
    "Dried Succulent": "https://dontstarve.wiki.gg/images/Dried_Succulent.png",
    "Dried Tillweed": "https://dontstarve.wiki.gg/images/Dried_Tillweed.png",
    "Fishy Jerky": "https://dontstarve.wiki.gg/images/Fishy_Jerky.png",
    "Heat Gland": "https://dontstarve.wiki.gg/images/Heat_Gland_Dropped.png",
    "Small Fishy Jerky": "https://dontstarve.wiki.gg/images/Small_Fishy_Jerky.png",
    "Wobster": "https://dontstarve.wiki.gg/images/Wobster_%28DST%29.png",
    "Beefalo Horn": "https://dontstarve.wiki.gg/images/Beefalo_Horn.png",
    "Rabbit": "https://dontstarve.wiki.gg/images/Rabbit.png",
    # Uncompromising Mode adds its own foods.  They only appear in the picker
    # when the site runs in UC mode.
    "Boomberry": "https://uncompromisingmode.wiki.gg/images/Boomberry.png",
    "Burnt Rice": "https://uncompromisingmode.wiki.gg/images/Burnt_Rice.png",
    "Cooked Monster Egg": "https://uncompromisingmode.wiki.gg/images/Cooked_Monster_Egg.png",
    "Cooked Monster Morsel": "https://uncompromisingmode.wiki.gg/images/Cooked_Monster_Morsel.png",
    "Gloom Berry": "https://uncompromisingmode.wiki.gg/images/Gloom_Berry.png",
    "Grilled Scorpion Carapace": "https://uncompromisingmode.wiki.gg/images/Grilled_Scorpion_Carapace.png",
    "Monster Egg": "https://uncompromisingmode.wiki.gg/images/Monster_Egg.png",
    "Monster Morsel": "https://uncompromisingmode.wiki.gg/images/Monster_Morsel.png",
    "Rice Grains": "https://uncompromisingmode.wiki.gg/images/Rice_Grains.png",
    "Scorpion Carapace": "https://uncompromisingmode.wiki.gg/images/Scorpion_Carapace.png",
    "Small Monster Jerky": "https://uncompromisingmode.wiki.gg/images/Small_Monster_Jerky.png",
    "Zaspberry": "https://uncompromisingmode.wiki.gg/images/Zaspberry.png",
}

# UC-only items without a wiki picture.  The icon is derived from an existing
# one so the picker still has a distinct image for them.
GENERATED_ICONS = {
    "Green Foliage": ("Foliage", (0.62, 1.22, 0.6)),
}


def slug(name: str) -> str:
    """Return the file name (without extension) used for one food icon."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def api(params: dict) -> dict:
    params = {**params, "format": "json"}
    url = API + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def wiki_title(name: str) -> str:
    return WIKI_ALIASES.get(name, name)


def icon_urls(names: list[str]) -> dict[str, str]:
    """Return ``{food name: thumbnail URL}`` for the foods that exist."""
    titles: dict[str, list[str]] = {}
    for name in names:
        title = wiki_title(name)
        if title:
            titles.setdefault(f"File:{title}.png", []).append(name)

    urls: dict[str, str] = {}
    title_list = list(titles)
    for start in range(0, len(title_list), BATCH):
        batch = title_list[start : start + BATCH]
        data = api(
            {
                "action": "query",
                "titles": "|".join(batch),
                "prop": "imageinfo",
                "iiprop": "url",
                "iiurlwidth": "128",
            }
        )
        normalized = {
            item["to"]: item["from"]
            for item in data.get("query", {}).get("normalized", [])
        }
        for page in data.get("query", {}).get("pages", {}).values():
            title = normalized.get(page.get("title", ""), page.get("title", ""))
            page_names = titles.get(title)
            if page_names is None:
                continue
            info = (page.get("imageinfo") or [{}])[0]
            url = info.get("thumburl") or info.get("url")
            if url:
                for name in page_names:
                    urls[name] = url
        time.sleep(0.3)
    return urls


def placeholder() -> bytes:
    """An icon-shaped question mark for foods the wiki has no image for."""
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((6, 6, SIZE - 7, SIZE - 7), fill=(214, 190, 154, 255))
    try:
        font = ImageFont.truetype("arial.ttf", 38)
    except OSError:
        font = ImageFont.load_default()
    draw.text(
        (SIZE // 2, SIZE // 2 - 2),
        "?",
        fill=(74, 52, 26, 255),
        font=font,
        anchor="mm",
    )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def square_icon(data: bytes) -> bytes:
    """Trim transparent borders and fit the image into a square canvas."""
    from PIL import Image

    image = Image.open(io.BytesIO(data)).convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    if bbox:
        image = image.crop(bbox)

    side = max(image.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(image, ((side - image.width) // 2, (side - image.height) // 2))
    canvas = canvas.resize((SIZE, SIZE), Image.LANCZOS)
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def tinted_icon(base: str, factors: tuple[float, float, float]) -> bytes:
    """Recolour an existing icon, keeping its alpha channel."""
    from PIL import Image

    path = ICON_DIR / f"{slug(base)}.png"
    image = Image.open(path).convert("RGBA")
    red, green, blue, alpha = image.split()
    red = red.point(lambda value: min(255, round(value * factors[0])))
    green = green.point(lambda value: min(255, round(value * factors[1])))
    blue = blue.point(lambda value: min(255, round(value * factors[2])))
    recoloured = Image.merge("RGBA", (red, green, blue, alpha))
    buffer = io.BytesIO()
    recoloured.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def download(url: str) -> bytes:
    # Both wikis' image CDNs want a referer from the matching site.
    host = "dontstarve.wiki.gg" if "wiki.gg" in url else "dontstarve.fandom.com"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": f"https://{host}/",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*", help="only refresh these foods")
    parser.add_argument("--force", action="store_true", help="replace existing icons")
    parser.add_argument(
        "--mode",
        choices=alg.MODES,
        default=alg.DEFAULT_MODE,
        help="food data to read (default: dst; uc adds Uncompromising Mode)",
    )
    args = parser.parse_args()

    ICON_DIR.mkdir(parents=True, exist_ok=True)
    foods = alg.known_foods(args.mode)
    wanted = list(dict.fromkeys(args.names or foods))
    unknown = sorted(set(wanted) - set(foods))
    if unknown:
        parser.error(f"unknown foods: {', '.join(unknown)}")

    urls = icon_urls([name for name in wanted if name not in DIRECT_ICONS])
    fallback = None
    written = 0
    for name in wanted:
        path = ICON_DIR / f"{slug(name)}.png"
        if path.exists() and not args.force:
            continue
        url = DIRECT_ICONS.get(name) or urls.get(name)
        if url:
            raw = square_icon(download(url))
            label = "icon"
        elif name in GENERATED_ICONS:
            raw = tinted_icon(*GENERATED_ICONS[name])
            label = "tint"
        else:
            if fallback is None:
                fallback = placeholder()
            raw = fallback
            label = "empty"
        path.write_bytes(raw)
        written += 1
        print(f"{label:5} {name} -> {path.name}")

    required = foods
    if args.mode != alg.DEFAULT_MODE:
        # Dishes are rendered as text, so only the picker ingredients need art.
        required = alg.picker_foods(args.mode)
    missing = [
        name for name in required if not (ICON_DIR / f"{slug(name)}.png").exists()
    ]
    print(
        f"\n{len(required) - len(missing)}/{len(required)} foods have icons "
        f"({written} written)"
    )
    if missing:
        print("missing:", ", ".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
